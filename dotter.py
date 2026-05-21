import json
import tomllib
from pathlib import Path
import hashlib
from operator import attrgetter
import re
from typing import Callable
import curses

from file_viewer_curses import FileViewer, ViewerTheme, FileEntry, FileList
# from util import *


# Define Constants

HOME_PATH_PATTERN = re.compile(r"^(?:/home/|/Users/|[\w_]+:\\Users\\|/usr/home/)([^/\\]+)")


class Dotter:
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


    def __help_for(self, key: str) -> str:
        return f"Usage: {self.__texts[key]['usage']}\n{self.__texts[key]['help']}"


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

    
    def __move_to_remove(self, entry: FileEntry):
        old_location = self.__db_dir / entry.name
        if not old_location.exists():
            # print(err(f"File {old_location} does not exist, cannot move it to DB_DIR/dots/remove"))
            return

        new_location = self.__db_dir / f"remove" / entry.path.parent.name / entry.path.name
        while new_location.exists():
            new_location = new_location.with_stem(new_location.stem + "_copy")

        new_location.parent.mkdir(parents=True, exist_ok=True)
        old_location.move(new_location)


    def __read_cwd(self):
        """Load content of cwd into __dir_list without changing instances"""

        self.__dir_list.clear()
        self.__dir_list.extend([
            FileEntry(file) for file in list(self.__cwd.iterdir())])

        # Sort by pathname
        self.__dir_list.sort(key=attrgetter("path"))
        # Sort by dir/files
        self.__dir_list.sort(key=lambda x: x.path.is_dir(), reverse=True)


    def __init__(self, window: curses.window, db_file: Path, ask_actions: bool = True):
        # TODO actually load theme
        theme = ViewerTheme.load()

        self.__window   : curses.window = window

        self.__db_file  : Path          = db_file.expanduser().absolute()
        self.__db_dir   : Path          = db_file.parent / "dots/"

        self.__file_list: FileList      = self.__load_db()

        self.__cwd      : Path          = Path.cwd()
        self.__dir_list : FileList      = []

        self.__ask      : bool          = ask_actions

        with (Path(__file__).parent / "help.toml").open("rb") as fl:
            self.__texts: dict[str, dict[str, str]] = tomllib.load(fl)

        self.__read_cwd()
        self.__db_dir.mkdir(exist_ok=True, parents=True)


    def enter_dir(self, viewer: FileViewer):
        if not viewer.current_entry.path.is_dir():
            return
        self.__cwd = viewer.current_entry.path
        self.__read_cwd()
        viewer.set_cur_line(0)


    def dir_up(self, viewer: FileViewer):
        old_cwd = self.__cwd
        self.__cwd = self.__cwd.parent
        self.__read_cwd()

        for i, p in enumerate(self.__dir_list):
            if old_cwd == p.path:
                break
        else:
            i = 0

        viewer.set_cur_line(i)


    def add_selection(self, viewer: FileViewer):
        # TODO: Asks
        # if self.__ask and 'Y' != input(self.__texts["add"]["ask"]):
        #     return

        for dir_entry in filter(lambda e: e.selected, self.__dir_list):
            dir_entry.selected = False

            if dir_entry.path.is_dir():
                viewer.note(f"Directories will not be processed, please select files individually")
                continue

            # This sets name for dir_entry
            already_registered = self.__is_registered(dir_entry)

            source = dir_entry.path
            dest = self.__db_dir / dir_entry.name

            if already_registered:
                viewer.warn("Some files may have been moved to DB_DIR/dots/remove, as they were already registered")

                if source.is_symlink():
                    source = source.resolve().absolute()
                    if source == dest:
                        continue

                self.__move_to_remove(dir_entry)

            source.move(dest)
            source.symlink_to(dest)

            if not already_registered:
                self.__file_list.append(dir_entry)

        self.__file_list.sort(key=attrgetter("path"))
        self.__save_json()


    def cleanup_list(self, viewer: FileViewer):
        # TODO: Asking
        # if self.__ask and 'Y' != input(self.__texts["cleanup"]["ask"]):
        #     return

        # Remove entries from __file_list without corresponding source files
        buf_list = self.__file_list.copy()
        self.__file_list.clear()
        self.__file_list.extend(e for e in buf_list if (self.__db_dir / e.name).exists())

        # Move files without entries in JSON-database to DB_DIR/remove/
        backup_folder = self.__db_dir / "remove/"
        backup_folder.mkdir(exist_ok=True, parents=True)
        moved_files = 0

        md5_list = {e.name for e in self.__file_list}
        not_registered: Callable[[Path], bool] = \
            lambda x: not x.is_dir() and x.name not in md5_list

        for file_path in filter(not_registered, self.__db_dir.iterdir()):
            self.__move_to_remove(FileEntry(file_path, file_path.name))
            moved_files += 1

        viewer.note(f"Moved {moved_files} to {backup_folder}")
        self.__save_json()


    def restore_selection(self, viewer: FileViewer):
        # TODO: asks
        # TODO: log
        for entry in filter(lambda e: e.selected, self.__file_list):
            source = self.__db_dir / entry.name
            dest = entry.path

            if not source.exists():
                viewer.warn("Some source files could not be found, removed entries from database")
                continue

            if dest.exists() and (not dest.is_symlink() or dest.resolve() != source):
                viewer.note("Some files were not restores, as the destination appeared to link to/be different files")
                entry.selected = False
                continue

            dest.parent.mkdir(parents=True, exist_ok=True)
            source.move(dest)

        buf_list = self.__file_list.copy()
        self.__file_list.clear()
        self.__file_list.extend(e for e in buf_list if not e.selected)

        self.__save_json()


    def delete_selection(self, viewer: FileViewer):
        # TODO: rmove vs restore
        # TODO: Asks
        # if self.__ask and 'Y' != input(self.__texts["delete"]["ask"]):
        #   return

        for entry in filter(lambda e: e.selected, self.__file_list):
            self.__move_to_remove(entry)

        buf_list = self.__file_list.copy()
        self.__file_list.clear()
        self.__file_list.extend(e for e in buf_list if not e.selected)

        self.__save_json()


#     def edit_selection(self, viewer: FileViewer):
#         # TODO: prompts or as command
#         cmd_list = cmd.split()
#
#         if len(cmd_list) < 2:
#             print(err("Expected a command for 'edit' (choice from: 'user')"))
#             return
#
#         match cmd_list[1]:
#             case "user" | "usr" | "u" | "uname":
#                 new_name = cmd_list[2] if len(cmd_list) > 2 else Path.home().name
#                 extend_list: FileList = []
#
#                 if self.__ask and 'Y' != input(f"""Edit selection?
# This will change the home-name of all files to {new_name}. (Y/n) """):
#                     return
#
#                 for entry in filter(lambda e: e.selected, self.__file_list):
#                     entry.selected = False
#
#                     # Only process home-paths with different user names
#                     if (m := HOME_PATH_PATTERN.match(str(entry.path))) is None \
#                         or (old_name := m[1]) == new_name:
#                         continue
#
#                     new_path = Path(str(entry.path).replace(old_name, new_name, 1))
#                     new_entry = FileEntry(new_path)
#
#                     # Sets 'name' property for new_entry
#                     if self.__is_registered(new_entry):
#                         print(err(f"File {new_path} is already registered, skipping"))
#                         continue
#
#                     old_source = self.__db_dir / entry.name
#                     old_source.copy(self.__db_dir / new_entry.name)
#                     extend_list.append(new_entry)
#
#                     self.__file_list.extend(extend_list)
#
#             case other:
#                 print(err(f"Unknown edit command: {other}"))


    def main_view(self):
        # def __dir_print(entry: FileEntry, i: int) -> str:
        #     return (f"{ bg('󰄬', AC.GREEN, False) if self.__is_registered(entry) else ' ' } "
        #             f"{ fg('', AC.BLUE, False) if entry.path.is_dir() else '' } "
        #             f"[{ '' if entry.selected else ' ' }] "
        #             f"{i:3d} {entry.path.name}\x1b[0m")

        dir_viewer = FileViewer("Filesystem", self.__dir_list, self.__window)

        dir_viewer.add_command('l', self.enter_dir)
        dir_viewer.add_command('h', self.dir_up)

        dir_viewer.add_command('a', self.add_selection,
                               self.__help_for("add"))

        dir_viewer.add_command('t', self.list_view,
                               self.__help_for("list"))

        dir_viewer.set_help_line(
            "l -> enter dir; " +
            "h -> dir up; " +
            "a -> add selection; " +
            "t -> show registered files; ")

        dir_viewer.show()


    def list_view(self, viewer: FileViewer):
        window = self.__window.subwin(0, 0)
        file_viewer = FileViewer("Dotter", self.__file_list, window)

        file_viewer.add_command('r', self.restore_selection)

        file_viewer.add_command('d',
                                self.delete_selection,
                                self.__help_for("delete"))

        # file_viewer.add_command('e',
        #                         self.edit_selection,
        #                         self.__help_for("edit"))

        file_viewer.add_command('s',
                                self.setup_selection,
                                self.__help_for("setup"))

        file_viewer.add_command('cl',
                                self.cleanup_list,
                                self.__help_for("cleanup"))

        file_viewer.set_help_line(
            "r -> restore selection; " +
            "d -> delete selection; " +
            "s -> Setup selection; " +
            "cl -> clean database; ")

        file_viewer.show()


    def setup_selection(self, viewer: FileViewer):
        # TODO: asks
        # if self.__ask and 'Y' != input(self.__texts["setup"]["ask"]):
        #     return

        for entry in filter(lambda e: e.selected, self.__file_list):
            entry.selected = False

            source = self.__db_dir / entry.name
            dest = entry.path

            if not source.exists():
                viewer.warn("Some source files were not found")
                continue

            if dest.exists():
                viewer.note("Some files already existed and were skipped")
                continue

            dest.parent.mkdir(exist_ok=True, parents=True)
            dest.symlink_to(source)
