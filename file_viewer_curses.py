from pathlib import Path
from typing import Callable, Self
import curses
from enum import IntEnum
# import re

# from util import *

type CommandCallback    = Callable[[FileViewer], None]
type PrintCallback      = Callable[[FileEntry, int, curses.window, bool], None]
type FileList           = list[FileEntry]

# TODO: Timestamps?
class FileEntry:
    def __init__(self, path: Path, name: str = "", selected: bool = False):
        self.path    : Path  = path.expanduser().absolute()
        self.name    : str   = name
        self.selected: bool  = selected

    def to_dict(self) -> dict[str, str]:
        return { "path": str(self.path.expanduser().absolute()), "name": self.name }


class ViewerCommand:
    def __init__(self, callback: CommandCallback, help_text: str):
        self.callback : CommandCallback = callback
        self.help_text: str             = help_text


class Colors(IntEnum):
    Directory   = 1
    Selected    = 2
    Green       = 3
    Red         = 4
    Yellow      = 5
    Help        = 6
    HelpShort   = 7


class ViewerTheme:
    Instance: Self | None = None

    def __init__(self):
        curses.start_color()
        curses.use_default_colors()

        curses.init_pair(Colors.Directory, 105, -1)
        curses.init_pair(Colors.Selected, -1, 34)
        curses.init_pair(Colors.Green, 34, -1)
        curses.init_pair(Colors.Red, 124, -1)
        curses.init_pair(Colors.Yellow, 220, -1)
        curses.init_pair(Colors.Help, -1, 240)
        curses.init_pair(Colors.HelpShort, 105, 240)

        ViewerTheme.Instance = self

    @classmethod
    def load(cls):
        return ViewerTheme.Instance if ViewerTheme.Instance else cls()



class FileViewerMode(IntEnum):
    Normal  = 0
    Select  = 1
    Command = 2


class FileViewer:
    @staticmethod
    def __default_print(
        entry: FileEntry,
        i: int,
        win: curses.window,
        line_selected: bool):

        sel = ' '
        if entry.selected:
            win.attron(curses.color_pair(Colors.Selected))
            sel = ''

        icon = ''
        if entry.path.is_dir():
            win.attron(curses.color_pair(Colors.Directory))
            icon = ''

        arr = '' if line_selected else ' '

        win.addstr(f"{arr} {icon} [{sel}] {i:3d} {entry.path}")
        win.attroff(curses.color_pair(Colors.Directory) |
                    curses.color_pair(Colors.Selected))


    def __init__(self, viewer_name: str, file_list: FileList, main_window: curses.window):
        self.window         : curses.window = main_window.derwin(2, 0)

        self.__list_pad_height  : int         = 25
        self.__list_pad_width   : int         = main_window.getmaxyx()[1]
        self.list_pad       : curses.window = curses.newpad(1024, self.__list_pad_width)

        self.cur_line       : int           = 0
        self.list_pad_top       : int           = 0
        self.mode: FileViewerMode = FileViewerMode.Normal
        self.__select_start: int = 0
        self.__select_end: int = 0

        self.__file_list  : FileList      = file_list
        self.__view_list: FileList      = file_list
        self.commands   : dict[str, ViewerCommand] = {}
        self.name       : str           = viewer_name

        self.__running  : bool          = True
        self.__help_line: str           = ""

        self.add_command('j',FileViewer.line_down)
        self.add_command('k', FileViewer.line_up)
        self.add_command('l', FileViewer.enter_dir)
        self.add_command('h', FileViewer.dir_up)
        self.add_command('v', FileViewer.toggle_select)

        self.add_command('q', FileViewer.quit_view,
            """Quits this viewer and returns either to the last Viewer or the shell""")


    def enter_dir(self):
        pass


    def dir_up(self):
        pass


    def line_down(self):
        # TODO: select
        if self.cur_line < len(self.__view_list):
            self.cur_line += 1

        if self.cur_line - self.list_pad_top >= self.__list_pad_height:
            self.list_pad_top += 1


    def line_up(self):
        # TODO: select
        if self.cur_line > 0:
            self.cur_line -= 1

        if self.cur_line < self.list_pad_top:
            self.list_pad_top -= 1


    def toggle_select(self):
        if self.mode == FileViewerMode.Select:
            self.mode = FileViewerMode.Normal
        else:
            self.mode = FileViewerMode.Select
            self.__select_start = self.cur_line


    def add_command(self, cmd: str | list[str], callback: CommandCallback, help_text: str = ""):
        if not isinstance(cmd, list):
            cmd = [cmd]

        for c in cmd:
            self.commands[c] = ViewerCommand(callback, help_text)


    def set_help_line(self, line: str):
        self.__help_line = line.rstrip() + "\n"


    def show(self, print_callback: PrintCallback = __default_print):
        while self.__running:
            self.window.clear()
            self.window.hline(0, 2, '-', 60)
            self.window.addstr(1, 2, self.name, curses.A_BOLD)

            self.list_pad.clear()
            # TODO: pad big enough?
            for i, entry in enumerate(self.__view_list):
                print_callback(entry, i, self.list_pad, self.cur_line == i)
                self.list_pad.addstr("\n")
            self.list_pad.refresh(self.list_pad_top, 0,
                                    2, 0, 2 + self.__list_pad_height, self.__list_pad_width)
            self.window.hline('-', 60)

            self.window.addstr("Viewer: ")
            self.window.addstr(self.name, curses.A_BOLD)
            self.window.addstr("\n")

            self.window.addstr("***Commands***\n", curses.A_BOLD)
            self.window.attron(curses.color_pair(Colors.Help))
            self.window.addstr("q -> quit viewer; j/k -> move up/down; h/l: move dirs; "+
                               "v -> select; " +
                               "/ -> filter; " +
                               ": -> enter command\n")

            self.window.addstr(self.__help_line.rstrip() + "\n")

            cmd = chr(self.window.getch())

            match cmd:
                case '\x1b':
                    self.mode = FileViewerMode.Normal

                # Filter list by regex user input
                case '/':
                    pass
                    # TODO: fuzzy matching
                    # if not cmd[1:]:
                    #     self.__view_list = self.file_list
                    # else:
                    #     self.__view_list = [entry for entry in self.file_list
                    #                         if re.search(cmd[1:], str(entry.path))]

                case _:
                    if cmd in self.commands.keys():
                        self.commands[cmd].callback(self)


    def quit_view(self):
        self.__running = False



def main(scr: curses.window):
    theme = ViewerTheme.load()
    FileViewer("", [], scr).show()


if __name__ == "__main__":
    curses.wrapper(main)



