import json
from pathlib import Path
import hashlib
from operator import attrgetter
import re

from file_viewer import FileViewer, FileEntry, FileList

from util import *

# Define Constants

# TODO: argument for different db location
DB_FILE : Path   = Path("~/.cache/dotter/files.json").expanduser().absolute()
DB_DIR  : Path    = (DB_FILE.parent / "dots/").expanduser().absolute() 

HOME_PATH_PATTERN = re.compile(r"^(?:/home/|/Users/|[\w_]+:\\Users\\|/usr/home/)([^/\\]+)")


class Dotter:
    """
    Main class for this program, manages different viewers, JSON-database
    and move- and copy functionality

    :ivar __file_list:  Internal list of all registered files in JSON-database
    :ivar __cwd      :  Current working directory for file browser
    :ivar __dir_list :  Current list of files in cwd
    """

    def __load_db(self) -> FileList:
        if not self.__db_file.exists():
            return []

        with self.__db_file.open() as fl:
            data = json.load(fl)

        return [FileEntry(Path(file["path"]), file["name"])
                for file in data["files"]]


    def __save_json(self):
        data = { "files": [entry.to_dict() for entry in self.__file_list] }

        self.__db_file.parent.mkdir(exist_ok=True, parents=True)
        with self.__db_file.open("w+") as fl:
            json.dump(data, fl)


    # TODO: have self.__file_list as hashmap[md5 -> path] instead of list?
    def __is_registered(self, entry: FileEntry) -> bool:
        """
        Returns True, if entry is found in the current `__file_list`. Mutates
        `entry`, sets `entry.name` to the md5-hash of `entry.path`
        """

        # Might speeds up directory lookup but messes with add_selection logic
        # if not entry.path.is_symlink():
        #     return False

        if not entry.name:
            m = hashlib.md5()
            m.update(bytes(entry.path))
            entry.name = m.hexdigest()

        return any(e.name == entry.name for e in self.__file_list)


    def __read_cwd(self):
        """Load content of cwd into __dir_list without changing instances"""

        self.__dir_list.clear()
        self.__dir_list.extend([
            FileEntry(file) for file in list(self.__cwd.iterdir())])

        # Sort by pathname
        self.__dir_list.sort(key=attrgetter("path"))
        # Sort by dir/files
        self.__dir_list.sort(key=lambda x: x.path.is_dir(), reverse=True)

    
    def __change_dir(self, cmd: str):
        """Change `self.__cwd` and update `self.__dir_list`"""

        cmd_list = cmd.split()

        if len(cmd_list) < 2:
            print(err("Expected directory ID"))
            return

        if not cmd_list[1].isnumeric():
            if cmd_list[1] != "..":
                print(err("Expected directory ID to by numeric"))
                return
            new_cwd = FileEntry(self.__cwd.parent)

        else:
            idx = int(cmd_list[1])
            if not (0 <= idx < len(self.__dir_list)):
                print(err("Directory ID is out of bounds"))
                return
            new_cwd = self.__dir_list[idx]

        if not new_cwd.path.is_dir():
            print(err("cd expects directory as target"))
            return

        self.__cwd = new_cwd.path
        self.__read_cwd()


    def __init__(self, db_file: Path = DB_FILE, ask_actions: bool = True):
        self.__file_list: FileList  = self.__load_db()
        self.__cwd      : Path      = Path.cwd()
        self.__dir_list : FileList  = []
        self.__db_file  : Path      = db_file
        self.__db_dir   : Path      = db_file.parent / "dots/"
        self.__ask      : bool      = ask_actions

        self.__read_cwd()
        self.__db_dir.mkdir(exist_ok=True, parents=True)


    def add_selection(self, _: str):
        if self.__ask and 'Y' != input(
"""Add selected files? This will move those files from their location into your
DB_DIR and create symlinks on the old location (Y/n) """):
            return

        for dir_entry in filter(lambda e: e.selected, self.__dir_list):
            dir_entry.selected = False

            if dir_entry.path.is_dir():
                print(warn(f"Directories ({dir_entry.path}) will not be processed, please select files individually"))
                continue

            # This sets name for dir_entry
            already_registered = self.__is_registered(dir_entry)

            source = dir_entry.path
            dest = self.__db_dir / dir_entry.name

            if already_registered:
                print(warn(f"File {dir_entry.path} already registered, try to update"))

                if dir_entry.path.is_symlink():
                    source = source.resolve().absolute()
                    if source == dest:
                        print(warn(f"File {dir_entry.path} is a symlink to the already registered file, skipping"))
                        continue

            source.move(dest)
            source.symlink_to(dest)

            self.__file_list.append(dir_entry)

        self.__file_list.sort(key=attrgetter("path"))
        self.__save_json()


    def cleanup_list(self, _: str):
        if self.__ask and 'Y' != input(bold(fg("***CAUTION***\n", AC.RED)) +
"""This will remove all files from your JSON database with no existing source.
Also, all files from your DB_DIR with no entry in your JSON database will be
moved to DB_DIR/remove/. Continue? (Y/n) """):
            return

        # Remove entries from __file_list without corresponding source files
        buf_list = self.__file_list.copy()
        self.__file_list.clear()
        self.__file_list.extend(e for e in buf_list if (self.__db_dir / e.name).exists())

        # Move files without entries in JSON-database to DB_DIR/remove/
        backup_folder = self.__db_dir / "remove/"
        backup_folder.mkdir(exist_ok=True, parents=True)
        moved_files = 0

        md5_list = {e.name for e in self.__file_list}

        for file_path in self.__db_dir.iterdir():
            if file_path.is_dir() or file_path.name in md5_list:
                continue

            try:
                file_path.move(backup_folder / file_path.name)
            except OSError as e:
                print(err(f"Could not move file: {e}"))
                continue

            moved_files += 1

        print(warn(f"Moved {moved_files} to {backup_folder}"))
        self.__save_json()


    def delete_selection(self, cmd: str):
        if self.__ask and 'Y' != input(
"""Delete selected files?
This will remove all selected files from your JSON-database and
move them from your DB_DIR back to their original location. Use command 'd trash'
if you wish to move the files from your DB_DIR to DB_DIR/remove/ instead of
their original location (Y/n) """):
            return

        rm_set = False
        cmd_list = cmd.split()
        if len(cmd_list) > 1:
            if cmd_list[1] != "trash":
                print(err(f"Unknown command {cmd_list[1]}, aborting."))
                print(warn("Use 'd trash' if you want to move files to DB_DIR/remove instead of their original location."))
                return
            rm_set = True

        rm_dir = self.__db_dir / "remove/"

        for entry in filter(lambda e: e.selected, self.__file_list):
            source = self.__db_dir / entry.name
            dest = (rm_dir / entry.path.name) if rm_set else entry.path

            if not source.exists():
                print(err(f"Could not find source file for {dest} (at {source}), symlink will remain, removing entry from database."))
                continue

            if dest.exists():
                if not dest.is_symlink() or dest.resolve() != source:
                    print(err(f"{dest} appears be to a different file, skipping file"))
                    entry.selected = False
                    continue
                dest.unlink()

            dest.parent.mkdir(parents=True, exist_ok=True)
            source.copy(dest)
            # with dest.open('wb+') as fl:
            #     buf = source.read_bytes()
            #     if fl.write(buf) != len(buf):
            #         print(err(f"Could not write all to {dest}, leaving file in database"))
            #         entry.selected = False
            #         continue
            source.unlink()

        # Update JSON-database
        buf_list = self.__file_list.copy()
        self.__file_list.clear()
        self.__file_list.extend(e for e in buf_list if not e.selected)

        self.__save_json()


    def edit_selection(self, cmd: str):
        cmd_list = cmd.split()

        if len(cmd_list) < 2:
            print(err("Expected a command for 'edit' (choice from: 'user')"))
            return

        match cmd_list[1]:
            case "user" | "usr" | "u" | "uname":
                new_name = cmd_list[2] if len(cmd_list) > 2 else Path.home().name
                extend_list: FileList = []

                if self.__ask and 'Y' != input(f"""Edit selection?
This will change the home-name of all files to {new_name}. (Y/n) """):
                    return

                for entry in filter(lambda e: e.selected, self.__file_list):
                    # Only process home-paths with different user names
                    if (m := HOME_PATH_PATTERN.match(str(entry.path))) is None \
                        or (old_name := m[1]) == new_name:
                        continue

                    new_path = Path(str(entry.path).replace(old_name, new_name, 1))
                    new_entry = FileEntry(new_path)

                    # Sets 'name' property for new_entry
                    if self.__is_registered(new_entry):
                        print(err(f"File {new_path} is already registered, skipping"))
                        continue

                    old_source = self.__db_dir / entry.name
                    old_source.copy(self.__db_dir / new_entry.name)
                    extend_list.append(new_entry)

                self.__file_list.extend(extend_list)


    def main_view(self):
        def __dir_print(entry: FileEntry, i: int) -> str:
            return (f"{ bg('󰄬', AC.GREEN, False) if self.__is_registered(entry) else ' ' } "
                    f"{ fg('', AC.BLUE, False) if entry.path.is_dir() else '' } "
                    f"[{ '*' if entry.selected else ' ' }] "
                    f"{i:3d} {entry.path.name}\x1b[0m")

        dir_viewer = FileViewer("Filesystem", self.__dir_list)

        dir_viewer.add_command({"cd"}, self.__change_dir)
        dir_viewer.add_command({"add", "a"}, self.add_selection)
        dir_viewer.add_command({"list", "l"}, self.list_view)

        dir_viewer.set_help_line(
            f"{fg('cd', AC.BLUE)} <id|..> -> change dir; " +
            f"{fg('a', AC.BLUE)}dd -> add selection; " +
            f"{fg('l', AC.BLUE)}ist -> show registered files;")

        dir_viewer.show(__dir_print)


    def list_view(self, _: str):
        file_viewer = FileViewer("Dotter", self.__file_list)

        file_viewer.add_command({"delete", "d", "remove", "r"}, self.delete_selection)
        file_viewer.add_command({"edit", "e"}, self.edit_selection)
        file_viewer.add_command({"create", "c", "setup", "s"}, self.setup_selection)
        file_viewer.add_command({"cleanup"}, self.cleanup_list)

        file_viewer.set_help_line(
            f"{fg('d', AC.BLUE)}elete -> delete selection; " +
            f"{fg('e', AC.BLUE)}dit -> edit selection; " +
            f"{fg('s', AC.BLUE)}etup -> setup selected files; " +
            f"{fg('cleanup', AC.BLUE)} -> cleanup database; ")

        file_viewer.show()


    def setup_selection(self, _: str):
        if self.__ask and 'Y' != input(
            """Start Setup?
This will create new symlinks on your system at *exaclty* the paths of the
selected files. If you'd like to change e.g. the home directory, use 'edit'
command. Proceed with setup? (Y/n) """):
            return

        for entry in filter(lambda e: e.selected, self.__file_list):
            source = self.__db_dir / entry.name
            dest = entry.path

            if not source.exists():
                print(err(f"Could not find source file for {dest} (at {source})"))
                print(warn("\tYou might want to clean your database using 'cleanup' command in list-view"))
                continue

            if dest.exists():
                print(warn(f"{dest} already exists, skipping"))
                continue

            dest.parent.mkdir(exist_ok=True, parents=True)
            dest.symlink_to(source)
