import json
from pathlib import Path
import hashlib
from operator import attrgetter
import shutil

from file_viewer import FileViewer, FileEntry, FileList

from util import *

# Define Constants

DB_DIR  : Path    = Path("~/.cache/dotter/dots/").expanduser().absolute()
DB_FILE : Path   = Path("~/.cache/dotter/files.json").expanduser().absolute()


class Dotter:
    """
    Main class for this program, manages different viewers, JSON-database
    and move- and copy functionality

    :ivar __file_list:  Internal list of all registered files in JSON-database
    :ivar __cwd      :  Current working directory for file browser
    :ivar __dir_list :  Current list of files in cwd
    """

    def __load_db(self) -> FileList:
        if not DB_FILE.exists():
            return []

        with DB_FILE.open() as fl:
            data = json.load(fl)

        return [FileEntry(Path(file["path"]), file["name"])
                for file in data["files"]]


    def __save_json(self):
        data = { "files": [entry.to_dict() for entry in self.__file_list] }

        DB_FILE.parent.mkdir(exist_ok=True, parents=True)
        with DB_FILE.open("w+") as fl:
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
            if not (0 < idx < len(self.__dir_list)):
                print(err("Directory ID is out of bounds"))
                return
            new_cwd = self.__dir_list[idx]

        if not new_cwd.path.is_dir():
            print(err("cd expects directory as target"))
            return

        self.__cwd = new_cwd.path
        self.__read_cwd()


    def __init__(self):
        self.__file_list: FileList  = self.__load_db()
        self.__cwd      : Path      = Path.cwd()
        self.__dir_list : FileList  = []

        self.__read_cwd()
        DB_DIR.mkdir(exist_ok=True, parents=True)


    def add_selection(self, _: str):
        if 'Y' != input(
            "Add selection? This will move config-files from their location (Y/n)"):
            return

        for dir_entry in self.__dir_list:
            if not dir_entry.selected:
                continue

            dir_entry.selected = False

            if dir_entry.path.is_dir():
                print(warn(f"Directories ({dir_entry.path}) will not be processed, please select files individually"))
                continue

            # This sets name for dir_entry
            already_registered = self.__is_registered(dir_entry)

            source = dir_entry.path
            dest = DB_DIR / dir_entry.name

            if already_registered:
                print(warn(f"File {dir_entry.path} already registered, try to update"))

                if dir_entry.path.is_symlink():
                    source = source.resolve().absolute()
                    if source == dest:
                        print(warn(f"File {dir_entry.path} is a symlink to the already registered file, skipping"))
                        continue

            with dest.open('wb+') as fl:
                buf = source.read_bytes()
                if fl.write(buf) != len(buf):
                    print(err(f"Could not write all of {source}, leaving file"))
                    continue
            source.unlink()
            source.symlink_to(dest)

            self.__file_list.append(dir_entry)

        self.__file_list.sort(key=attrgetter("path"))
        self.__save_json()


    def cleanup_list(self, _: str):
        if 'Y' != input(bold(fg("***CAUTION***\n", AC.RED)) +
                "This will remove all files from your JSON database with no existing source, as well as all files from your DB_DIR with no entry in your JSON database. Continue? (Y/n)"):
            return

        # Remove entries from __file_list without corresponding source files
        buf_list = self.__file_list.copy()
        self.__file_list.clear()
        self.__file_list.extend(e for e in buf_list if (DB_DIR / e.name).exists())

        # Move files without entries in JSON-database to DB_DIR/remove/
        backup_folder = DB_DIR / "remove/"
        backup_folder.mkdir(exist_ok=True, parents=True)
        moved_files = 0

        for file_path in DB_DIR.iterdir():
            if file_path.is_dir() or \
                any(file_path.name == e.name for e in self.__file_list):
                continue

            shutil.move(file_path, backup_folder)
            print(f"* Moved {file_path.name} to 'remove/'")
            moved_files += 1

        print(warn(f"Moved {moved_files} to {backup_folder}"))
        self.__save_json()


    def delete_selection(self, _: str):
        if 'Y' != input(
            "Delete selected files? This will move config-files back to their original location (Y/n)"):
            return

        for entry in self.__file_list:
            if not entry.selected:
                continue

            source = DB_DIR / entry.name
            dest = entry.path

            print(f"* Restoring {dest}...")

            if not source.exists():
                print(err(f"Could not find source file for {dest} (at {source}), removing file from database, symlink will remain"))
                continue

            if dest.exists():
                if not dest.is_symlink() or dest.resolve() != source:
                    print(err(f"{dest} appears to be a different file, removing file from database"))
                    continue
                dest.unlink()

            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('wb+') as fl:
                buf = source.read_bytes()
                if fl.write(buf) != len(buf):
                    print(err(f"Could not write all to {dest}, leaving file in database"))
                    entry.selected = False
                    continue
            source.unlink()

        buf_list = self.__file_list.copy()
        self.__file_list.clear()
        self.__file_list.extend(e for e in buf_list if not e.selected)

        self.__save_json()


    def edit_selection(self, cmd: str):
        # TODO: Implement
        print(err("Edit selection not implemented yet"))


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
        # TODO: user-specific paths
        if 'Y' != input(
            "Start Setup? This will create new files on your system (Y/n)"):
            return

        for entry in self.__file_list:
            if not entry.selected:
                continue

            source = DB_DIR / entry.name
            dest = entry.path

            print(f"* Setup {dest}...")

            if not source.exists():
                print(err(f"Could not find source file for {dest} (at {source})"))
                print(warn("\tYou might want to clean your database using 'cleanup' command in list-view"))
                continue

            if dest.exists():
                print(warn(f"{dest} already exists, skipping"))
                continue

            dest.parent.mkdir(exist_ok=True, parents=True)
            dest.symlink_to(source)
