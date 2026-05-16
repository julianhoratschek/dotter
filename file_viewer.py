from pathlib import Path
from typing import Callable
import re

from util import *

# TODO: Timestamps?
class FileEntry:
    def __init__(self, path: Path, name: str = "", selected: bool = False):
        self.path       : Path  = path.expanduser().absolute()
        self.name       : str   = name
        self.selected   : bool  = selected

    def to_dict(self) -> dict[str, str]:
        return { "path": str(self.path.expanduser().absolute()), "name": self.name }


type PrintCallback      = Callable[[FileEntry, int], str]
type FileList           = list[FileEntry]
type CommandCallback    = Callable[[str], None]
type CommandList        = list[tuple[set[str], CommandCallback]]


class FileViewer:
    @staticmethod
    def __default_print(entry: FileEntry, i: int) -> str:
        return (f"{fg('', AC.BLUE,False) if entry.path.is_dir() else ''} "
                f"[{'*' if entry.selected else ' '}] "
                f"{i:2d} {entry.path.name}\x1b[0m")


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
                        print(err("Expected list of numbers, ranges or * in file selection"))
                        return
                continue

            end = int(cmd)
            if 0 > end >= len(self.__view_list):
                print(err(f"Index {end} not an option in the selection list"))
                return

            if is_range:
                for i in range(begin, end+1):
                    self.__view_list[i].selected = self.__set_value
                is_range = False

            else:
                self.__view_list[end].selected = self.__set_value
            begin = end


    def __init__(self, viewer_name: str, file_list: FileList):
        self.file_list      : FileList      = file_list
        self.__view_list    : FileList      = file_list
        self.commands       : CommandList   = []
        self.name           : str           = viewer_name

        self.__running      : bool          = True
        self.__set_value    : bool          = True
        self.__help_line    : str           = ""

        self.add_command({"quit", "q", "exit"}, self.quit_view)


    def add_command(self, command_list: set[str], callback: CommandCallback):
        self.commands.append((command_list, callback))


    def set_help_line(self, line: str):
        self.__help_line = line


    def show(self, print_callback: PrintCallback = __default_print):
        while self.__running:
            print(f"\n{' ' + bold(self.name) + ' ':-^60}\n")
            for i, entry in enumerate(self.__view_list):
                print(print_callback(entry, i))

            print(f"\n{'-':-^53}")
            print(f"Viewer: {bold(self.name)}, " +
                  f"Mode: {bold(fg('select', AC.GREEN) if self.__set_value else fg('deselect', AC.RED))}")
            print(bg(
                f"{fg('q', AC.BLUE)}uit -> quit viewer; " +
                f"{fg('/', AC.BLUE)} -> filter; " +
                f"{fg('!', AC.BLUE)} -> switch selection mode", AC.GREY))
            if self.__help_line:
                print(bg(self.__help_line, AC.GREY))

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
