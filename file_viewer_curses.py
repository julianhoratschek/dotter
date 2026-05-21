from pathlib import Path
from typing import Callable, Self
import curses
from enum import IntEnum
# import re


type CommandCallback    = Callable[[FileViewer], None]
type PrintCallback      = Callable[[FileViewer, FileEntry, int], None]
type FileList           = list[FileEntry]


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
    Warning     = 3
    Note        = 4
    Help        = 5
    HelpShort   = 6
    PreSelect   = 7


class ViewerTheme:
    Instance: Self | None = None

    def __init__(self):
        curses.curs_set(0)

        curses.start_color()
        curses.use_default_colors()

        curses.init_pair(Colors.Directory, 105, -1)
        curses.init_pair(Colors.Selected, -1, 34)
        curses.init_pair(Colors.Warning, 124, -1)
        curses.init_pair(Colors.Note, 220, -1)
        curses.init_pair(Colors.Help, -1, 240)
        curses.init_pair(Colors.HelpShort, 105, 240)
        curses.init_pair(Colors.PreSelect, -1, 34)

        ViewerTheme.Instance = self

    @classmethod
    def load(cls):
        return ViewerTheme.Instance if ViewerTheme.Instance else cls()


class FileViewerMode(IntEnum):
    Normal  = 0
    Select  = 1
    Command = 2
    Filter  = 3


def fliprange(a: int, b: int) -> range:
    return range(min(a, b), max(a, b) + 1)


class FileViewer:
    @staticmethod
    def __default_print(
        viewer: FileViewer,
        entry: FileEntry,
        i: int):

        pad = viewer.list_pad

        if viewer.mode == FileViewerMode.Select and \
           i in fliprange(viewer.selection_start, viewer.cur_line):
            pad.addch(' ', curses.color_pair(Colors.PreSelect))
        else:
            pad.addch(' ')

        icon = ''
        sel_str = "   "
        if entry.path.is_dir():
            pad.attron(curses.color_pair(Colors.Directory))
            icon = ''
        else:
            sel_str = "[ ]"
            if entry.selected:
                pad.attron(curses.color_pair(Colors.Selected))
                sel_str = "[]"

        arr = '' if viewer.cur_line == i else ' '

        pad.addstr(f"{arr} {icon} {sel_str} {i:3d} {entry.path}")
        pad.attroff(curses.color_pair(Colors.Directory) |
                    curses.color_pair(Colors.Selected))


    def __init__(self, viewer_name: str, file_list: FileList, main_window: curses.window):
        self.window             : curses.window     = main_window.derwin(2, 0)

        self.__list_pad_height  : int               = 25
        self.__list_pad_width   : int               = main_window.getmaxyx()[1]
        self.list_pad           : curses.window     = curses.newpad(1024, self.__list_pad_width)

        self.cur_line           : int               = 0
        self.selection_start    : int               = 0
        self.list_pad_top       : int               = 0
        self.mode               : FileViewerMode    = FileViewerMode.Normal

        self.__file_list        : FileList          = file_list
        self.__view_list        : FileList          = file_list
        self.commands           : dict[str, ViewerCommand] = {}
        self.name               : str               = viewer_name

        self.__running          : bool              = True
        self.__help_line        : str               = ""
        self.__note             : str               = ""
        self.__warning          : str               = ""

        self.add_command('j',FileViewer.line_down)
        self.add_command('k', FileViewer.line_up)
        self.add_command(["gg", "g0"], FileViewer.goto_top)
        self.add_command('G', FileViewer.goto_bottom)
        self.add_command('v', FileViewer.toggle_select)

        self.add_command('q', FileViewer.quit_view,
            """Quits this viewer and returns either to the last Viewer or the shell""")


    @property
    def current_entry(self) -> FileEntry:
        return self.__view_list[self.cur_line - self.list_pad_top]


    def line_down(self):
        if self.cur_line < len(self.__view_list) - 1:
            self.cur_line += 1

        if self.cur_line - self.list_pad_top >= self.__list_pad_height:
            self.list_pad_top += 1


    def line_up(self):
        if self.cur_line > 0:
            self.cur_line -= 1

        if self.cur_line < self.list_pad_top:
            self.list_pad_top -= 1

    def goto_top(self):
        self.cur_line = 0
        self.list_pad_top = 0

    def goto_bottom(self):
        self.cur_line = len(self.__view_list) - 1
        self.list_pad_top = len(self.__view_list) - self.__list_pad_height
        if self.list_pad_top < 0:
            self.list_pad_top = 0


    def normal_mode(self):
        match self.mode:
            case FileViewerMode.Select:
                self.toggle_select(exit_only=True)

            case FileViewerMode.Command:
                pass

            case FileViewerMode.Filter:
                pass

            case FileViewerMode.Normal:
                pass


    def toggle_select(self, exit_only: bool = False):
        if self.mode == FileViewerMode.Select:
            self.mode = FileViewerMode.Normal
            for i in fliprange(self.selection_start, self.cur_line):
                self.select_entry(i, flip=False)

        elif not exit_only:
            self.mode = FileViewerMode.Select
            self.selection_start = self.cur_line


    def add_command(self, cmd: str | list[str], callback: CommandCallback, help_text: str = ""):
        if not isinstance(cmd, list):
            cmd = [cmd]

        for c in cmd:
            self.commands[c] = ViewerCommand(callback, help_text)


    def set_help_line(self, line: str):
        self.__help_line = line.rstrip() + "\n"


    def select_entry(self, i: int, flip: bool = True):
        e = self.__view_list[i]
        if e.path.is_dir():
            return
        e.selected = not e.selected if flip else True


    def show(self, print_callback: PrintCallback = __default_print):
        while self.__running:
            self.window.clear()
            self.window.hline(0, 2, '-', 60)
            self.window.addstr(1, 2, self.name, curses.A_BOLD)
            self.window.hline(6 + self.__list_pad_height, 2, '-', 60)

            if self.__warning:
                self.window.addstr(8, 2, "!! ", curses.color_pair(Colors.Warning))
                self.window.addstr(self.__warning)
                self.__warning = ""

            if self.__note:
                self.window.addstr(9, 2, "󱞁 ", curses.color_pair(Colors.Note))
                self.window.addstr(self.__note)
                self.__note = ""

            self.window.addstr(10 + self.__list_pad_height, 2, "***Commands***", curses.A_BOLD)
            self.window.attron(curses.color_pair(Colors.Help))
            self.window.addstr(11 + self.__list_pad_height, 2,
                               "q -> quit viewer; j/k -> move up/down; "+
                               "v -> select; " +
                               "/ -> filter; " +
                               ": -> enter command")

            self.window.addstr(12 + self.__list_pad_height, 2,
                               self.__help_line.rstrip())
            self.window.attroff(curses.color_pair(Colors.Help))
            self.window.refresh()

            self.list_pad.clear()
            # TODO: pad big enough?
            for i, entry in enumerate(self.__view_list):
                self.list_pad.move(i, 0)
                print_callback(self, entry, i)
            self.list_pad.refresh(self.list_pad_top, 0,
                                    5, 0, 5 + self.__list_pad_height, self.__list_pad_width)

            cmd = self.window.getch()

            # ENTER, SPACE
            if cmd in (10, 13, curses.KEY_ENTER) or cmd == 32:
                self.select_entry(self.cur_line, flip=True)

            # ESCAPE
            elif cmd == 27:
                self.normal_mode()

            elif cmd == ord('/'):
                # TODO: Fuzzy matching
                self.mode = FileViewerMode.Filter

            elif cmd == ord(':'):
                # TODO: command mode
                self.mode = FileViewerMode.Command

            else:
                pos = 0
                cmd_list = list(self.commands.keys())
                while True:
                    cmd_list = [
                        str(c) for c in cmd_list
                        if pos < len(c) and chr(cmd) == c[pos]
                    ]
                    if len(cmd_list) < 2:
                        break
                    pos += 1
                    cmd = self.window.getch()

                if cmd_list:
                    self.commands[cmd_list[0]].callback(self)


    def quit_view(self):
        self.__running = False

    def note(self, msg: str):
        self.__note = msg

    def warn(self, msg: str):
        self.__warning = msg

    def set_cur_line(self, idx: int):
        if idx >= len(self.__file_list):
            idx = 0

        self.cur_line = idx
        if idx < self.list_pad_top or idx > self.list_pad_top + self.__list_pad_height:
            self.list_pad_top = idx



def main(scr: curses.window):
    theme = ViewerTheme.load()
    file_list = [FileEntry(p) for p in Path('~/.config/').expanduser().iterdir()]
    FileViewer("Test Viewer", file_list, scr).show()


if __name__ == "__main__":
    curses.wrapper(main)



