import json
from pathlib import Path
import hashlib
from operator import attrgetter
import re
from typing import Callable
import curses

from file_viewer_modes import FileEntry, FileViewerModeType
from file_viewer_curses import FileViewer, FileList
from file_viewer_theme import ViewerTheme

from prompts import yesno_prompt, prompt


# Define Constants

HOME_PATH_PATTERN = re.compile(r"^(?:/home/|/Users/|[\w_]+:\\Users\\|/usr/home/)([^/\\]+)")


class Dotter:
    """
    Main class for Dotter: Handles management of symlinks and registered files
    as well as JSON-database

    :ivar __window      : curses.window Main window, created by curses.wrapper

    :ivar __db_file     : Path          Path to the JSON-database file
    :ivar __db_dir      : Path          Path to DB_DIR for saving config files

    :ivar __file_list   : FileList      Current list of registered files

    :ivar __cwd         : Path          Current working directory for file browser
    :ivar __dir_list    : FileList      List of Files in current working directory
    """

    def __load_db(self) -> FileList:
        """Loads FileList from JSON database"""
        if not self.__db_file.exists():
            return []

        with self.__db_file.open() as fl:
            data = json.load(fl)

        return [FileEntry(Path(file["path"]), file["name"])
                for file in data["files"]]


    def __save_json(self):
        """Saves current file list to JSON database"""
        data = { 
            "files": [entry.to_dict() for entry in self.__file_list] }

        self.__db_file.parent.mkdir(exist_ok=True, parents=True)
        with self.__db_file.open("w+") as fl:
            json.dump(data, fl)


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
        """Moves file from dotter/dots/ directory to dotter/dots/remove"""

        old_location = self.__db_dir / entry.name
        if not old_location.exists():
            return

        new_location = self.__db_dir / "remove" / entry.path.parent.name / entry.path.name
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


    def __init__(self, window: curses.window, db_file: Path, theme_file: str = ""):
        theme = ViewerTheme(theme_file)

        self.__window   : curses.window = window

        self.__db_file  : Path          = db_file.expanduser().absolute()
        self.__db_dir   : Path          = db_file.parent / "dots/"

        self.__file_list: FileList      = self.__load_db()

        self.__cwd      : Path          = Path.cwd()
        self.__dir_list : FileList      = []

        self.__read_cwd()
        self.__db_dir.mkdir(exist_ok=True, parents=True)


    def enter_dir(self, viewer: FileViewer):
        """
        Set cwd to directory described by viewer.current_entry
        Only available in File Browser View
        """

        if not viewer.current_entry.path.is_dir():
            return

        self.__cwd = viewer.current_entry.path
        self.__read_cwd()
        viewer.refresh()

        viewer.cur_line = 0


    def dir_up(self, viewer: FileViewer):
        """
        Change cwd to parent directory of current file
        Only available in File Browser View
        """

        old_cwd = self.__cwd
        self.__cwd = self.__cwd.parent
        self.__read_cwd()
        viewer.refresh()

        for i, p in enumerate(self.__dir_list):
            if old_cwd == p.path:
                break
        else:
            i = 0

        viewer.cur_line = i


    def add_selection(self, viewer: FileViewer):
        """
        Adds all selected files to the database
        Only Available in file browser view
        """

        lst = list(filter(lambda e: e.selected, self.__dir_list))
        if not yesno_prompt(viewer.window,
            f"Add {len(lst)} Files to the database?\n" + 
            "This will move files and create symlinks."):
            return

        for dir_entry in lst:
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

        viewer.note("Added files")
        viewer.refresh()


    def cleanup_list(self, viewer: FileViewer):
        """
        Removes entries from database without corresponding source files
        in DB_DIR, as well as files from DB_DIR without corresponding entries
        in JSON-Database. This is non-destructive, any files will be moved
        to DB_DIR/dots/remove/
        Only Available in Dotter File List View
        """

        if not yesno_prompt(viewer.window,
            "Clean Database and move unlinked\n"+
            "files to DB_DIR/dots/remove?"):
            return

        # Remove entries from __file_list without corresponding source files
        buf_list = self.__file_list.copy()
        self.__file_list.clear()
        self.__file_list.extend(e for e in buf_list if (self.__db_dir / e.name).exists())

        # Move files without entries in JSON-database to DB_DIR/remove/
        moved_files = 0

        md5_list = {e.name for e in self.__file_list}
        not_registered: Callable[[Path], bool] = \
            lambda x: not x.is_dir() and x.name not in md5_list

        for file_path in filter(not_registered, self.__db_dir.iterdir()):
            self.__move_to_remove(FileEntry(file_path, file_path.name))
            moved_files += 1

        self.__save_json()

        viewer.note(f"Moved {moved_files} to DB_DIR/dots/remove/")
        viewer.refresh()


    def restore_selection(self, viewer: FileViewer):
        """
        Move all files back to their original locations
        Only available in Dotter File list View
        """

        lst = list(filter(lambda e: e.selected, self.__file_list))
        if not yesno_prompt(viewer.window,
            f"Move {len(lst)} files back to their\n"+
            "original location and remove them\n"+
            "from the database?"):
            return

        for entry in lst:
            source = self.__db_dir / entry.name
            dest = entry.path

            if not source.exists():
                viewer.warn("Some source files could not be found, removed entries from database")
                continue

            if dest.exists():
                if not dest.is_symlink() or dest.resolve() != source:
                    viewer.note("Some files were not restored, as the destination appeared to link to/be different files")
                    entry.selected = False
                    continue
                dest.unlink()

            dest.parent.mkdir(parents=True, exist_ok=True)
            source.move(dest)

        buf_list = self.__file_list.copy()
        self.__file_list.clear()
        self.__file_list.extend(e for e in buf_list if not e.selected)

        self.__save_json()

        viewer.note("Restored files")
        viewer.refresh()


    def delete_selection(self, viewer: FileViewer):
        """
        Move all selected files to DB/dots/remove/
        Only available in Dotter File list View
        """

        lst = list(filter(lambda e: e.selected, self.__file_list))
        if not yesno_prompt(viewer.window,
            f"Move {len(lst)} files to DB_DIR/dots/remove/ and remove\n" +
            "them from the database?"):
            return

        for entry in lst:
            self.__move_to_remove(entry)

        buf_list = self.__file_list.copy()
        self.__file_list.clear()
        self.__file_list.extend(e for e in buf_list if not e.selected)

        self.__save_json()

        viewer.refresh()
        viewer.note("Moved files to DB_DIR/dots/remove/")


    def edit_selection(self, viewer: FileViewer):
        """
        Sets all Home paths to a specified other username
        Only available in Dotter file list view
        """
        # TODO: Change Home paths to other systems?
        # TODO: More Editing capabilities (e.g. regex?)
        # TODO: As Command

        new_name = prompt(viewer.window, "New User: ")
        new_name = None
        if not new_name:
            return

        extend_list: FileList = []

        for entry in filter(lambda e: e.selected, self.__file_list):
            entry.selected = False

            # Only process home-paths with different user names
            if (m := HOME_PATH_PATTERN.match(str(entry.path))) is None \
                or (old_name := m[1]) == new_name:
                continue

            new_path = Path(str(entry.path).replace(old_name, new_name, 1))
            new_entry = FileEntry(new_path)

            # Sets 'name' property for new_entry
            if self.__is_registered(new_entry):
                continue

            old_source = self.__db_dir / entry.name
            old_source.copy(self.__db_dir / new_entry.name)
            extend_list.append(new_entry)

        self.__file_list.extend(extend_list)
        viewer.refresh()


    def main_view(self):
        """ListView and Filebrowser for the cwd"""

        def dict_print(viewer: FileViewer, entry: FileEntry, i: int, /, **kwargs):
            icon = "󰃁 " if self.__is_registered(entry) else "  "
            FileViewer.default_print(viewer, entry, i, prepend_icon=icon)

        dir_viewer = FileViewer("Filesystem", self.__dir_list, self.__window)

        dir_viewer.add_command('l', self.enter_dir,
                               modes={FileViewerModeType.Normal})
        dir_viewer.add_command('h', self.dir_up,
                               modes={FileViewerModeType.Normal})

        dir_viewer.add_command('a', self.add_selection,
                               modes={FileViewerModeType.Normal})

        dir_viewer.add_command('t', self.list_view,
                               modes={FileViewerModeType.Normal})

        dir_viewer.set_help_line(
            "l -> enter dir; " +
            "h -> dir up; " +
            "a -> add selection; " +
            "t -> show registered files; ")

        dir_viewer.show(dict_print)


    def list_view(self, viewer: FileViewer):
        """ListView of all registered files"""

        window = self.__window.subwin(0, 0)
        file_viewer = FileViewer("Registered Files", self.__file_list, window)

        file_viewer.add_command('r', self.restore_selection,
                                modes={FileViewerModeType.Normal})
        file_viewer.add_command('d', self.delete_selection,
                                modes={FileViewerModeType.Normal})
        file_viewer.add_command('e', self.edit_selection,
                                modes={FileViewerModeType.Normal})
        file_viewer.add_command('s', self.setup_selection,
                                modes={FileViewerModeType.Normal})
        file_viewer.add_command('cl', self.cleanup_list,
                                modes={FileViewerModeType.Normal})

        file_viewer.set_help_line(
            "r -> restore selection; " +
            "e -> edit home path; " +
            "d -> delete selection; " +
            "s -> Setup selection; " +
            "cl -> clean database; ")

        file_viewer.show()
        del window


    def setup_selection(self, viewer: FileViewer):
        """
        Creates symlinks on the system for all selected files
        Only available in Dotter File List
        """

        lst = list(filter(lambda e: e.selected, self.__file_list))
        if not yesno_prompt(viewer.window,
            f"Setup {len(lst)} files on your system?\n"+
            "These files will be created\n"+
            "*exactly* at their paths!\n"+
            "This will create symlinks\n"+
            "on your system"):
            return

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

        viewer.note("Files setup")
