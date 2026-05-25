from pathlib import Path
from typing import Callable
import curses
from enum import IntEnum
import re

from file_viewer_theme import Colors


# Define types for readability

type CommandCallback    = Callable[[FileViewer], None]
type PrintCallback      = Callable[[FileViewer, FileEntry, int], None]
type FileList           = list[FileEntry]

# TODO: Size of window big enough?

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
        """ Returns the object as JSON-writeable format """
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


class DialogResult(IntEnum):
    No      = 0
    Yes     = 1


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
    def default_print(viewer: FileViewer, entry: FileEntry, i: int, /, **kwargs):
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

        if "prepend_icon" in kwargs:
            icon = str(kwargs["prepend_icon"]) + icon

        pad.addstr(f"{arrl} {icon} {sel_str} {i:3d} {entry.path} {arrr}")
        pad.attroff(curses.color_pair(Colors.Directory) |
                    curses.color_pair(Colors.Selected))


    def __draw_window(self):
        """Structuring method to draw everything but the list"""

        self.__window.clear()
        self.__window.hline(0, 2, '-', 60)
        self.__window.addstr(1, 2, self.name, curses.A_BOLD)
        self.__window.hline(4 + self.__list_pad_height, 2, '-', 60)

        if self.__warning:
            self.__window.addstr(5 + self.__list_pad_height, 2, "!! ", curses.color_pair(Colors.Warning))
            self.__window.addstr(self.__warning)
            self.__warning = ""

        if self.__note:
            self.__window.addstr(6 + self.__list_pad_height, 2, "󱞁 ", curses.color_pair(Colors.Note))
            self.__window.addstr(self.__note)
            self.__note = ""

        self.__window.addstr(7 + self.__list_pad_height, 2, "***Commands***", curses.A_BOLD)
        self.__window.attron(curses.color_pair(Colors.Help))
        self.__window.addstr(8 + self.__list_pad_height, 2,
                           "q -> quit viewer; j/k -> move up/down; "+
                           "v -> select; " +
                           "/ -> filter; " +
                           ": -> enter command")

        self.__window.addstr(9 + self.__list_pad_height, 2,
                           self.__help_line.rstrip())
        self.__window.attroff(curses.color_pair(Colors.Help))
        self.__window.refresh()


    def __init__(self, viewer_name: str, file_list: FileList, main_window: curses.window):
        self.__window           : curses.window     = main_window.derwin(2, 0)
        h, w = self.__window.getmaxyx()

        self.__list_pad_height  : int               = h - 11 
        self.__list_pad_width   : int               = w
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
        return self.__view_list[self.cur_line]


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
        if i < 0 or i >= len(self.__view_list):
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
        win.bkgd(' ', curses.color_pair(Colors.Help))
        win.box()

        win.addstr(1, 2, msg)
        win.refresh()

        ret = win.getstr(1, len(msg) + 2).decode("utf-8").strip()

        curses.noecho()
        curses.curs_set(0)
        del win

        return ret


    def yesno_prompt(self, msg: str) -> DialogResult:
        curses.curs_set(1)

        _, width = self.__window.getmaxyx()
        win = self.__window.derwin(12, 50, 4, width // 2 - 25)
        win.bkgd(' ', curses.color_pair(Colors.Help))
        win.box()

        for i, line in enumerate(msg.splitlines()):
            win.addstr(2 + i, 2, line)

        win.addch(8, 15, 'Y', curses.color_pair(Colors.HelpShort))
        win.addstr("es")
        win.addch(8, 30, 'N', curses.color_pair(Colors.HelpShort))
        win.addch('o')
        win.refresh()

        res = DialogResult.Yes
        win.move(8, 15)

        while True:
            cmd = win.getch()
            if cmd == ord('l'):
                win.move(8, 30)
                res = DialogResult.No
            elif cmd == ord('n') or cmd == ord('N'):
                res = DialogResult.No
                break
            elif cmd == ord('h'):
                win.move(8, 15)
                res = DialogResult.Yes
            elif cmd == ord('y') or cmd == ord('Y'):
                res = DialogResult.Yes
                break
            elif cmd == ord('q') or cmd == 27:
                res = DialogResult.No
                break
            elif cmd in (10, 13, curses.KEY_ENTER) or cmd == 32:
                break

        curses.curs_set(0)
        del win

        return res


    def show(self, print_callback: PrintCallback = default_print):
        """
        Shows this FileViewer and executes main loop until the user presses 'q'
        :param print_callback:  PrintCallback   (Optional), function to execute to display lines of entries
        """

        while self.__running:
            self.__draw_window()

            # Make sure, list_pad is big enough
            if (h := self.list_pad.getmaxyx()[0]) <= len(self.__view_list):
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
                cmd_list = list(self.commands.keys())
                inp = chr(cmd)
                while True:
                    cmd_list = list(filter(lambda c: c.startswith(inp), cmd_list))
                    if len(cmd_list) < 2:
                        break
                    cmd = self.__window.getch()
                    inp += chr(cmd)

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



