from pathlib import Path
from typing import Callable
import re

from util import *

# TODO: Timestamps?
class FileEntry:
    def __init__(self, path: Path, name: str = "", selected: bool = False):
        self.path    : Path  = path.expanduser().absolute()
        self.name    : str   = name
        self.selected: bool  = selected

    def to_dict(self) -> dict[str, str]:
        return { "path": str(self.path.expanduser().absolute()), "name": self.name }


type CommandCallback    = Callable[[str], None]


class ViewerCommand:
    def __init__(self, cmds: set[str], callback: CommandCallback, help_text: str):
        self.commands : set[str]        = cmds
        self.callback : CommandCallback = callback
        self.help_text: str             = help_text


type CommandList        = list[ViewerCommand]
type PrintCallback      = Callable[[FileEntry, int], str]
type FileList           = list[FileEntry]


class FileViewer:
    """
    Displays a list of files and enables the user to interact with it by
    filtering or selection

    :ivar file_list  :  Complete list of files processed by the Viewer
    :ivar commands   :  List of user defined commands and callbacks
    :ivar name       :  Title of this Viewer, only used for display

    :ivar __running  :  Internally used for main loop
    :ivar __set_value:  Internally used for selection/deselection mode
    :ivar __help_line:  User defined line to display as tutorial
    :ivar __view_list:  Displayed list, uses same FileEntry instances as `file_list`
    """

    @staticmethod
    def __default_print(entry: FileEntry, i: int) -> str:
        """
        Default method for displaying a file of the internal file list

        :param entry:   Current file entry to display
        :param i    :   Index of the current file display (0-based)

        :resurns    :   String to display per line
        """

        return (f"{fg('', AC.BLUE,False) if entry.path.is_dir() else ''} "    # Display directories with icon and blue color
                f"[{'*' if entry.selected else ' '}] "                                          # Display selection by a ticked/unticked box
                f"{i:3d} {entry.path}\x1b[0m")                                                  # Display ID for selection


    def __process_line(self, cmd_line: str):
        """
        Parse and process user input as comma or space separated
        line of numbers indicating IDs of the displayed file list for selection
        """

        # TODO: ugly...
        cmd_list = cmd_line.replace(',', ' ').replace('-', ' - ').split()
        begin = 0
        is_range = False

        for cmd in cmd_list:
            if not cmd.isnumeric():
                match cmd:
                    # Dash indicates range (n-m) of IDs to select
                    case '-':
                        is_range = True

                    # A star anywhere indicates selection of all files
                    case '*':
                        for entry in self.__view_list:
                            entry.selected = self.__set_value
                        break
                    
                    # Treat anything else as error
                    case _:
                        print(err("Expected list of numbers, ranges or * in file selection"))
                        return
                continue

            end = int(cmd)
            if 0 > end or end >= len(self.__view_list):
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
        self.file_list  : FileList      = file_list
        self.__view_list: FileList      = file_list
        self.commands   : CommandList   = []
        self.name       : str           = viewer_name

        self.__running  : bool          = True
        self.__set_value: bool          = True
        self.__help_line: str           = ""

        self.add_command({"quit", "q", "exit"}, self.quit_view,
            """Quits this viewer and returns either to the last Viewer or the shell""")

        self.add_command({"help", "h"}, self.show_help,
            """Display this help screen, write 'help <command>' to display specific help for <command>""")


    def add_command(self, command_list: set[str], callback: CommandCallback, help_text: str = ""):
        """
        Adds a command defined by `command_list` to available commands of this
        Viewer. When the user types a command from `command_list`, `callback` will
        be executed.

        :param command_list:    Set of strings which will call `callback`
        :param callback:        Callback to call when any string in
                                `command_list` is given to this Viewer. Should
                                have form (str) -> None
        :param help_text:       Help text for this command
        """

        self.commands.append(ViewerCommand(command_list, callback, help_text))


    def set_help_line(self, line: str):
        """
        Defines a short text line to be displayed above the command prompt
        """

        self.__help_line = line


    def show(self, print_callback: PrintCallback = __default_print):
        """
        Main method of the Viewer, contains infinite loop until user quits this
        instance of Viewer.

        :param print_callback:  Function to invoke per file of this list to display.
                                Expected to take FileEntry and an int-id as parameters
                                and to return a string.
        """

        while self.__running:

            # Display List of Files
            print(f"\n{' ' + bold(self.name) + ' ':-^60}\n")
            for i, entry in enumerate(self.__view_list):
                print(print_callback(entry, i))
            print(f"\n{'-':-^53}")

            print(f"Viewer: {bold(self.name)}, " +
                  f"Mode: {bold(fg('select', AC.GREEN) if self.__set_value else fg('deselect', AC.RED))}")

            print(bg(bold("***Commands***"), AC.GREY))
            print(bg(
                f"{fg('q', AC.BLUE)}uit -> quit viewer; " +
                f"{fg('/', AC.BLUE)} -> filter; " +
                f"{fg('!', AC.BLUE)} -> switch selection mode", AC.GREY))

            if self.__help_line:
                print(bg(self.__help_line, AC.GREY))

            if not (cmd := input(">> ").strip()):
                continue

            match cmd[0]:
                # Filter list by regex user input
                case '/':
                    # TODO: fuzzy matching
                    if not cmd[1:]:
                        self.__view_list = self.file_list
                    else:
                        self.__view_list = [entry for entry in self.file_list
                                            if re.search(cmd[1:], str(entry.path))]

                # Switch between select/deselect mode
                case '!':
                    self.__set_value = not self.__set_value

                case _:
                    cmd_list = cmd.split()

                    # Look in command list for a fit
                    for command in self.commands:
                        if cmd_list[0] in command.commands:
                            command.callback(cmd)
                            break

                    # Otherwise, process input as selection line
                    else:
                        self.__process_line(cmd)


    def quit_view(self, _: str):
        self.__running = False


    def show_help(self, cmd: str):
        cmd_list = cmd.split()
        if len(cmd_list) == 1:
            # TODO: help for general viewer
            return

        for command in self.commands:
            if cmd_list[0] in command.commands:
                print(command.help_text)
                break
        else:
            print(err(f"Unknown command '{cmd_list[0]}'"))






