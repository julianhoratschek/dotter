from pathlib import Path
import json
from typing import Callable
import hashlib
import re

DB_DIR: Path = Path("~/.cache/dotter/dots/").expanduser()
DB_FILE: Path = Path("~/.cache/dotter/files.json").expanduser()


# TODO: Timestamps?
class FileEntry:
    def __init__(self, path: Path, name: str = "", selected: bool = False):
        self.path: Path = path.expanduser().absolute()
        self.name: str = name
        self.selected: bool = selected

    def to_dict(self):
        return { "path": str(self.path.expanduser().absolute()), "name": self.name }


type CommandCallback = Callable[[str], None]
type PrintCallback = Callable[[FileEntry, int], str]
type CommandList = list[tuple[set[str], CommandCallback]]
type FileList = list[FileEntry]


class FileViewer:
    @staticmethod
    def __default_print(entry: FileEntry, i: int) -> str:
        return (f"{ '' if entry.path.is_dir() else ''} "
                f"[{'*' if entry.selected else ' '}] "
                f"{i:2d} {entry.path.name}")


    def __process_line(self, cmd_line: str):
        cmd_list = cmd_line.replace(',', ' ').split()
        begin = 0
        is_range = False

        for cmd in cmd_list:
            if not cmd.isnumeric():
                match cmd:
                    case '-':
                        is_range = True

                    case '*':
                        for entry in self.__view_list:
                            entry.selected = self.__set_value
                        break
                    
                    case _:
                        print("!! Expected list of numbers, ranges or * in file selection")
                        return
                continue

            end = int(cmd)
            if 0 > end >= len(self.__view_list):
                print(f"!! Index {end} not an option in the selection list")
                return

            if is_range:
                for i in range(begin, end+1):
                    self.__view_list[i].selected = self.__set_value
                is_range = False

            else:
                self.__view_list[end].selected = self.__set_value
            begin = end


    def __init__(self, viewer_name: str, file_list: FileList):
        self.file_list: FileList    = file_list
        self.commands: CommandList  = []
        self.name: str              = viewer_name

        self.__running: bool        = True
        self.__set_value: bool      = True
        self.__view_list: FileList  = file_list

        self.add_command({"quit", "q", "exit"}, self.quit_view)


    def add_command(self, command_list: set[str], callback: CommandCallback):
        self.commands.append((command_list, callback))


    def show(self, print_callback: PrintCallback = __default_print):
        while self.__running:
            print("\n----------------------------------------\n")
            for i, entry in enumerate(self.__view_list):
                print(print_callback(entry, i))

            print("\n----------------------------------------")
            print(f"Viewer: {self.name}, Mode: {'select' if self.__set_value else 'deselect'}")
            print("q -> quit viewer; / -> filter; ! -> switch selection mode")

            if not (cmd := input(">> ").strip()):
                continue

            match cmd[0]:
                case '/':
                    # TODO: fuzzy matching
                    if not cmd[1:]:
                        self.__view_list = self.file_list
                    else:
                        self.__view_list = [entry for entry in self.file_list
                                            if re.search(cmd[1:], str(entry.path))]
                case '!':
                    self.__set_value = not self.__set_value

                case _:
                    if not (cmd_list := cmd.split()):
                        continue

                    found_command = False
                    for command in self.commands:
                        if found_command := (cmd_list[0] in command[0]):
                            command[1](cmd)
                            break

                    if not found_command:
                        self.__process_line(cmd)


    def quit_view(self, _: str):
        self.__running = False


class Dotter:
    def __load_db(self) -> FileList:
        if not DB_FILE.exists():
            return []

        with DB_FILE.open() as fl:
            data = json.load(fl)

        return [FileEntry(Path(file["path"]), file["name"])
                for file in data["files"]]


    def __save_json(self):
        print("-- Write changes --")

        data = {
            "files": [entry.to_dict() for entry in self.__file_list] }

        DB_FILE.parent.mkdir(exist_ok=True, parents=True)
        with DB_FILE.open("w+") as fl:
            json.dump(data, fl)

    
    def __change_dir(self, cmd: str):
        cmd_list = cmd.split()

        if len(cmd_list) < 2:
            print("!! Expected directory ID")
            return

        if not cmd_list[1].isnumeric():
            print("!! Expected directory ID to by numeric")
            return

        idx = int(cmd_list[1])
        if 0 > idx >= len(self.__dir_list):
            print("!! Directory ID is out of bounds")
            return

        new_cwd = self.__dir_list[idx]
        if not new_cwd.path.is_dir():
            print("!! cd expects directory as target")
            return

        self.__cwd = new_cwd.path

        self.__dir_list.clear()
        self.__dir_list.append(FileEntry(Path("..")))
        self.__dir_list.extend([
            FileEntry(file) for file in list(self.__cwd.iterdir())])


    def __init__(self):
        self.__file_list: FileList  = self.__load_db()
        self.__cwd: Path            = Path.cwd()

        self.__dir_list: FileList   = [FileEntry(Path(".."))]
        self.__dir_list.extend([
            FileEntry(file) for file in list(self.__cwd.iterdir())])

        DB_DIR.mkdir(exist_ok=True, parents=True)


    def add_selection(self, _: str):
        u_choice = input("Add selection? This will move config-files from their location (Y/n)")
        if u_choice != 'Y':
            return

        print("-- Adding selection --")

        for dir_entry in self.__dir_list:
            if not dir_entry.selected:
                continue

            file_path = dir_entry.path

            m = hashlib.md5()
            m.update(bytes(file_path))

            file_entry = FileEntry(file_path, m.hexdigest())
            source = file_path
            dest = DB_DIR / file_entry.name

            print(f"\t* Linking {source}...")
            with dest.open('wb+') as fl:
                fl.write(source.read_bytes())
            source.unlink()
            source.symlink_to(dest)

            self.__file_list.append(file_entry)

        self.__save_json()

        print("-- Done --")


    def delete_selection(self, _: str):
        u_choice = input("Delete selected files? This will move config-files back to their original location (Y/n)")
        if u_choice != 'Y':
            return

        print("-- Deleting selection --")

        remove_indices: list[int] = []
        for i, entry in enumerate(self.__file_list):
            if not entry.selected:
                continue

            print(f"\t* Unlinking {entry.path}...")
            source = DB_DIR / entry.name
            # TODO: test, if correct link or changed
            dest = entry.path
            dest.unlink()

            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('wb+') as fl:
                fl.write(source.read_bytes())
            source.unlink()
            remove_indices.append(i)

        print("-- Updating internal list --")
        for i in remove_indices:
            del self.__file_list[i]

        self.__save_json()

        print("-- Done --")


    def edit_selection(self, cmd: str):
        # TODO: Implement
        print("Edit selection not implemented yet")


    def main_view(self):
        def __dir_print(entry: FileEntry, i: int) -> str:
            in_list = any(entry.path == e.path for e in self.__file_list)
            return (f"{ '󰄬' if in_list else ' ' } "
                    f"{ '' if entry.path.is_dir() else '' } "
                    f"[{ '*' if entry.selected else ' ' }] "
                    f"{i:2d} {entry.path.name}")

        dir_viewer = FileViewer("Filesystem", self.__dir_list)
        dir_viewer.add_command({"cd"}, self.__change_dir)
        dir_viewer.add_command({"add", "a"}, self.add_selection)
        dir_viewer.add_command({"list", "l"}, self.list_view)
        dir_viewer.show(__dir_print)


    def list_view(self, _: str):
        file_viewer = FileViewer("Dotter", self.__file_list)
        file_viewer.add_command({"delete", "d", "remove", "r"}, self.delete_selection)
        file_viewer.add_command({"edit", "e"}, self.edit_selection)
        file_viewer.add_command({"create", "c", "setup", "s"}, self.setup_selection)
        file_viewer.show()


    def setup_selection(self, _: str):
        # TODO: user-specific paths
        u_choice = input("Start Setup? This will create new files on your system (Y/n)")
        if u_choice != 'Y':
            return

        print("-- Setup selection --")

        for entry in self.__file_list:
            if not entry.selected:
                continue

            source = DB_DIR / entry.name
            dest = entry.path

            print(f"\t* Setup {dest}...")
            if dest.exists():
                print(f"\t!! ALREADY EXISTS, skipping")
                continue
            dest.parent.mkdir(exist_ok=True, parents=True)
            dest.symlink_to(source)

        print("-- Done --")


if __name__ == "__main__":
    Dotter().main_view()
