from pathlib import Path
import tomllib
from typing import Callable, Self
import curses
from enum import IntEnum
import re


# Define types for readability

type CommandCallback    = Callable[[FileViewer], None]
type PrintCallback      = Callable[[FileViewer, FileEntry, int], None]
type FileList           = list[FileEntry]


class FileEntry:
    """
    Describes one database- or directory-entry to display with FileViewer

    :ivar path:     Path    Absolute path to the location of the file
    :ivar name:     str     Name describing the file, for Database-files md5-sum of
                            their absolute path
    :ivar selected: bool    True, if the file is currenly selected
    """

    def __init__(self, path: Path, name: str = "", selected: bool = False):
        self.path       : Path  = path.expanduser().absolute()
        self.name       : str   = name
        self.selected   : bool  = selected


    def to_dict(self) -> dict[str, str]:
        """
        Returns the object as JSON-writeable format
        """
        return { "path": str(self.path.expanduser().absolute()), "name": self.name }


class ViewerCommand:
    """
    Describes a callback and help text for a custom command for FileViewer

    :ivar callback:     CommandCallback     Callback for this command in form
                                            (FileViewer) -> None
    :ivar help_text:    str                 Text to display as help for this
                                            Command
    """

    def __init__(self, callback: CommandCallback, help_text: str):
        self.callback   : CommandCallback = callback
        self.help_text  : str             = help_text


class Colors(IntEnum):
    """Colors defined by this theme"""
    Directory   = 1
    Selected    = 2
    Warning     = 3
    Note        = 4
    Help        = 5
    HelpShort   = 6
    PreSelect   = 7


class ViewerTheme:
    """Simple Theme manager. Should not be istanciated directly, only called
    via ViewerTheme.load"""

    Instance: Self | None = None

    ColorMapping: dict[str, Colors] = {
        "Directory" : Colors.Directory,
        "Selected"  : Colors.Selected,
        "Warning"   : Colors.Warning,
        "Note"      : Colors.Note,
        "Help"      : Colors.Help,
        "HelpShort" : Colors.HelpShort,
        "PreSelect" : Colors.PreSelect }

    @staticmethod
    def __read_theme(
            theme_data: dict[str, list[int]],
            default: dict[str, list[int]]):
        """
        Reads theme from the provided dictionary, falls back to defaults
        if theme is malformed """

        for name, cl in ViewerTheme.ColorMapping.items():
            vals = default[name]
            if name in theme_data and len(theme_data[name]) == 2:
                try:
                    vals = list(map(int, theme_data[name]))
                except ValueError as e:
                    # TODO: handle
                    pass
            curses.init_pair(cl, vals[0], vals[1])


    def __init__(self):
        ViewerTheme.Instance = self


    @classmethod
    def load(cls, theme_file: Path | str | None):
        """
        Loads defaults for FileViewer Theme or reads color data from `theme_file`
        if provided. Falls back to defaults, if `theme_file` is malformed or
        missing.
        :ivar theme_file:   Path|str|None   Optional, Path to a toml-file providing
                                            the theme to display
        """

        if ViewerTheme.Instance:
            return

        curses.curs_set(0)

        curses.start_color()
        curses.use_default_colors()

        default_theme_file = Path(__file__).parent / "theme.toml"
        if not default_theme_file.exists():
            return

        with default_theme_file.open("rb") as fl:
            default_theme = tomllib.load(fl)
        theme_data = default_theme

        if theme_file and (theme_file := Path(theme_file)).exists():
            with theme_file.open("rb") as fl:
                try:
                    theme_data = tomllib.load(fl)
                except tomllib.TOMLDecodeError as e:
                    # TODO: handle
                    pass
        ViewerTheme.__read_theme(theme_data, default_theme)
        return cls()


class FileViewerMode(IntEnum):
    """Vim-like file modes for FileViewer"""

    Normal  = 0
    Select  = 1
    Command = 2     # TODO: do we need this?
    Filter  = 3     # TODO: implement?


def fliprange(a: int, b: int) -> range:
    """Wrapper for range-builtin that does not care about signs"""
    return range(min(a, b), max(a, b) + 1)


class FileViewer:
    """
    Display files and enables user to traverse lists with vim-like key bindings
    Highly extendable via commands

    :ivar __window           : curses.window     Main window to display files

    :ivar __list_pad_height  : int               nlines of __window used to display files
    :ivar __list_pad_width   : int               ncols of __window used to displa files
    :ivar list_pad           : curses.window     Window to show and scroll file list

    :ivar cur_line           : int               Current line (cursor)
    :ivar selection_start    : int               In Selection-Mode: Start of Selection
    :ivar list_pad_top       : int               Topmost displayed line of list_pad
    :ivar mode               : FileViewerMode    Mode of Viewer (Normal, Select, Filter, Command)

    :ivar __file_list        : FileList          Pointer to list to display (no copy)
    :ivar __view_list        : FileList          Actual (e.g. filtered) list displayed
    :ivar commands           :                   List of commands and callbacks
    :ivar name               : str               Name of the Viewer (for display only)

    :ivar __running          : bool              If False, Viewer will quit
    :ivar __help_line        : str               Line to display beneath filelist
    :ivar __note             : str               Note to display for one cycle
    :ivar __warning          : str               Warning to display for one cycle
    """

    # TODO: Notification system?

    @staticmethod
    def __default_print(viewer: FileViewer, entry: FileEntry, i: int):
        """
        Default per-line printing for entries in the current list
        :ivar viewer    :   FileViewer  The calling instance of FileViewer
        :ivar entry     :   FileEntry   The current entry of the list
        :ivar i         :   int         The ID (position) of entry (zero based)
        """

        # Pad is the area to display files
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
            if entry.path.is_symlink():
                icon = ''

            sel_str = "[ ]"
            if entry.selected:
                pad.attron(curses.color_pair(Colors.Selected))
                sel_str = "[]"

        arrl = arrr = ' '
        if viewer.cur_line == i:
            arrl = '󰁔'
            arrr = '󰁍'

        pad.addstr(f"{arrl} {icon} {sel_str} {i:3d} {entry.path} {arrr}")
        pad.attroff(curses.color_pair(Colors.Directory) |
                    curses.color_pair(Colors.Selected))


    def __draw_window(self):
        """Structuring method to draw everything but the list"""

        self.__window.clear()
        self.__window.hline(0, 2, '-', 60)
        self.__window.addstr(1, 2, self.name, curses.A_BOLD)
        self.__window.hline(6 + self.__list_pad_height, 2, '-', 60)

        # TODO: roper notifications-system
        if self.__warning:
            self.__window.addstr(7 + self.__list_pad_height, 2, "!! ", curses.color_pair(Colors.Warning))
            self.__window.addstr(self.__warning)
            self.__warning = ""

        if self.__note:
            self.__window.addstr(8 + self.__list_pad_height, 2, "󱞁 ", curses.color_pair(Colors.Note))
            self.__window.addstr(self.__note)
            self.__note = ""

        self.__window.addstr(9 + self.__list_pad_height, 2, "***Commands***", curses.A_BOLD)
        self.__window.attron(curses.color_pair(Colors.Help))
        self.__window.addstr(10 + self.__list_pad_height, 2,
                           "q -> quit viewer; j/k -> move up/down; "+
                           "v -> select; " +
                           "/ -> filter; " +
                           ": -> enter command")

        self.__window.addstr(11 + self.__list_pad_height, 2,
                           self.__help_line.rstrip())
        self.__window.attroff(curses.color_pair(Colors.Help))
        self.__window.refresh()


    def __init__(self, viewer_name: str, file_list: FileList, main_window: curses.window):
        self.__window           : curses.window     = main_window.derwin(2, 0)

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
        """Returns the entry currently under the cursor"""

        return self.__view_list[self.cur_line - self.list_pad_top]


    def line_down(self):
        """Moves cursor one line down, scrolls window if necessary"""

        if self.cur_line < len(self.__view_list) - 1:
            self.cur_line += 1

        if self.cur_line - self.list_pad_top >= self.__list_pad_height:
            self.list_pad_top += 1


    def line_up(self):
        """Moves cursor up one line, scrolls window if necessary"""

        if self.cur_line > 0:
            self.cur_line -= 1

        if self.cur_line < self.list_pad_top:
            self.list_pad_top -= 1


    def goto_top(self):
        """Move cursor to the top of the list"""

        self.cur_line = 0
        self.list_pad_top = 0


    def goto_bottom(self):
        """Move cursor to the bottom of the list"""

        self.cur_line = len(self.__view_list) - 1
        self.list_pad_top = len(self.__view_list) - self.__list_pad_height
        if self.list_pad_top < 0:
            self.list_pad_top = 0


    def normal_mode(self):
        """Switch to normal mode, executing changing-code if necessary"""

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
        """Switch from or to select-mode. If `exit_only` is True, this will
        only exit select mode but not enable it. On exiting select mode, this
        method selects all pre-selected files"""

        if self.mode == FileViewerMode.Select:
            self.mode = FileViewerMode.Normal
            for i in fliprange(self.selection_start, self.cur_line):
                self.select_entry(i, flip=False)

        elif not exit_only:
            self.mode = FileViewerMode.Select
            self.selection_start = self.cur_line


    def add_command(self, cmd: str | list[str], callback: CommandCallback, help_text: str = ""):
        """Add a command-callback to this FileViewer, registering one or multiple
        shortcuts for it.
        :param cmd      :   str | list[str]     String or list of Strings as keyboard shortcuts
        :param callback :   CommandCallback     Method to call when the shortcut is pressed
        :param help_text:   str                 Optional, text to display for help screen
        """

        if not isinstance(cmd, list):
            cmd = [cmd]

        for c in cmd:
            self.commands[c] = ViewerCommand(callback, help_text)


    def set_help_line(self, line: str):
        """Displays a textline beneath the list"""
        self.__help_line = line.rstrip() + "\n"


    def select_entry(self, i: int, flip: bool = True):
        """Selects entry with index `i` in the list, if `flip` is false, it will
        only be selected, otherwise selection will be toggled.
        :param i    :   int     Index of the entry in the file list
        :param flip :   bool    (Optional) whether to toggle selection (default: True)
        """
        if 0 < i or i >= len(self.__view_list):
            return
        e = self.__view_list[i]
        if e.path.is_dir():
            return
        e.selected = not e.selected if flip else True


    def prompt(self, msg: str) -> str:
        """
        Displays a window for the user to input text.
        :param msg: str Text to be displayed in front of the input window
        :returns:   str Text the user has typed into the window
        """

        curses.echo()
        curses.curs_set(1)

        height, width = self.__window.getmaxyx()
        win = self.__window.derwin(3, width - 2, height - 3, 2)
        win.box()

        win.addstr(1, 2, msg)
        win.refresh()

        ret = win.getstr(1, len(msg) + 2).decode("utf-8").strip()

        curses.noecho()
        curses.curs_set(0)
        del win

        return ret


    def show(self, print_callback: PrintCallback = __default_print):
        """
        Shows this FileViewer and executes main loop until the user presses 'q'
        :param print_callback:  PrintCallback   (Optional), function to execute to display lines of entries
        """

        while self.__running:
            self.__draw_window()

            # Make sure, list_pad is big enough
            if (h := self.list_pad.getmaxyx()[0]) >= len(self.__view_list):
                del self.list_pad
                self.list_pad = curses.newpad(int(h * 1.5), self.__list_pad_width)

            self.list_pad.clear()

            for i, entry in enumerate(self.__view_list):
                self.list_pad.move(i, 0)
                print_callback(self, entry, i)

            self.list_pad.refresh(
                self.list_pad_top, 0, 5, 0, 5 + self.__list_pad_height, self.__list_pad_width)

            cmd = self.__window.getch()

            # ENTER, SPACE
            if cmd in (10, 13, curses.KEY_ENTER) or cmd == 32:
                self.select_entry(self.cur_line, flip=True)

            # ESCAPE
            elif cmd == 27:
                self.normal_mode()

            elif cmd == ord('/'):
                # TODO: Fuzzy matching
                # self.mode = FileViewerMode.Filter
                filter_str = self.prompt("Test: ")
                self.__view_list = [
                    e for e in self.__file_list
                    if re.search(filter_str, str(e.path))]

            elif cmd == ord(':'):
                # TODO: command mode
                # self.mode = FileViewerMode.Command
                pass

            # Look for registered commands
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
                    cmd = self.__window.getch()

                if cmd_list:
                    self.commands[cmd_list[0]].callback(self)


    def quit_view(self):
        self.__running = False


    def note(self, msg: str):
        self.__note = msg


    def warn(self, msg: str):
        self.__warning = msg


    def set_cur_line(self, idx: int):
        """Jump cursor to line `idx` in the view window"""
        if idx >= len(self.__file_list):
            idx = 0

        self.cur_line = idx
        if idx < self.list_pad_top or idx > self.list_pad_top + self.__list_pad_height:
            self.list_pad_top = idx

    def refresh(self):
        """Reset displayed list to original list"""
        self.__view_list = self.__file_list



# def main(scr: curses.window):
#     theme = ViewerTheme.load()
#     file_list = [FileEntry(p) for p in Path('~/.config/').expanduser().iterdir()]
#     FileViewer("Test Viewer", file_list, scr).show()
#
#
# if __name__ == "__main__":
#     curses.wrapper(main)



