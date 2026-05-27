from typing import Callable
import curses

from file_viewer_theme import Colors
from file_viewer_modes import FileEntry, FileViewerModeType, FileViewerMode, NormalMode, FilterMode, SelectMode

# Define types for readability

type CommandCallback    = Callable[[FileViewer], None]
type PrintCallback      = Callable[[FileViewer, FileEntry, int], None]
type FileList           = list[FileEntry]

# TODO: Size of window big enough?


class ViewerCommand:
    """
    Describes a callback and help text for a custom command for FileViewer

    :ivar callback:     CommandCallback     Callback for this command in form
                                            (FileViewer) -> None
    :ivar help_text:    str                 Text to display as help for this
                                            Command
    """

    def __init__(self, callback: CommandCallback, help_text: str, modes: set[FileViewerModeType]):
        self.callback   : CommandCallback = callback
        self.help_text  : str             = help_text
        self.modes      : set[FileViewerModeType] = modes


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

        win = self.__window

        win.erase()
        win.hline(0, 2, '-', 60)
        win.addstr(1, 2, self.name, curses.A_BOLD)
        win.hline(4 + self.__list_pad_height, 2, '-', 60)

        if self.__warning:
            win.addstr(5 + self.__list_pad_height, 2, "!! ", curses.color_pair(Colors.Warning))
            win.addstr(self.__warning)
            self.__warning = ""

        if self.__note:
            win.addstr(6 + self.__list_pad_height, 2, "󱞁 ", curses.color_pair(Colors.Note))
            win.addstr(self.__note)
            self.__note = ""

        win.addstr(7 + self.__list_pad_height, 2, "***Commands***", curses.A_BOLD)
        win.attron(curses.color_pair(Colors.Help))
        # TODO only display mode valid commands
        win.addstr(8 + self.__list_pad_height, 2,
                           "q -> quit viewer; j/k -> move up/down; "+
                           "v -> select; " +
                           "/ -> filter; " +
                           ": -> enter command")

        win.addstr(9 + self.__list_pad_height, 2,
                           self.__help_line.rstrip())
        win.attroff(curses.color_pair(Colors.Help))
        win.noutrefresh()


    def __init__(self, viewer_name: str, file_list: FileList, main_window: curses.window):
        self.__window           : curses.window     = main_window.derwin(2, 0)
        h, w = self.__window.getmaxyx()

        self.__list_pad_height  : int               = h - 11 
        self.__list_pad_width   : int               = w
        self.__list_pad           : curses.window     = curses.newpad(1024, self.__list_pad_width)

        self.__file_list        : FileList          = file_list
        self.view_list        : FileList          = file_list

        self.__cur_line           : int               = 0
        self.__list_pad_top       : int               = 0
        self.__current_mode       : FileViewerModeType = FileViewerModeType.Normal
        self.__modes            : dict[FileViewerModeType, FileViewerMode] = {
            FileViewerModeType.Normal: NormalMode(self),
            FileViewerModeType.Select: SelectMode(self),
            FileViewerModeType.Filter: FilterMode(self) }

        self.__commands           : dict[str, ViewerCommand] = {}
        self.name               : str               = viewer_name

        self.__running          : bool              = True
        self.__help_line        : str               = ""
        self.__note             : str               = ""
        self.__warning          : str               = ""

        self.add_command('j',FileViewer.line_down,
                         modes={FileViewerModeType.Normal, FileViewerModeType.Select})
        self.add_command('k', FileViewer.line_up,
                         modes={FileViewerModeType.Normal, FileViewerModeType.Select})
        self.add_command(["gg", "g0"], FileViewer.goto_top,
                         modes={FileViewerModeType.Normal, FileViewerModeType.Select})
        self.add_command('G', FileViewer.goto_bottom,
                         modes={FileViewerModeType.Normal, FileViewerModeType.Select})
        self.add_command('v', FileViewer.toggle_select_mode,
                         modes={FileViewerModeType.Normal, FileViewerModeType.Select})

        self.add_command('q', FileViewer.quit_view,
            """Quits this viewer and returns either to the last Viewer or the shell""")


    @property
    def file_list(self) -> FileList:
        return self.__file_list

    @property
    def window(self) -> curses.window:
        return self.__window

    @property
    def list_pad(self) -> curses.window:
        return self.__list_pad

    @property
    def cur_line(self) -> int:
        return self.__cur_line

    @cur_line.setter
    def cur_line(self, value: int):
        """Jump cursor to line `idx` in the view window"""
        if value >= len(self.__file_list):
            value = 0

        self.__cur_line = value
        if value < self.__list_pad_top \
        or value > self.__list_pad_top + self.__list_pad_height:
            self.__list_pad_top = value
    

    @property
    def current_entry(self) -> FileEntry:
        """Returns the entry currently under the cursor"""
        return self.view_list[self.__cur_line]

    @property
    def mode(self) -> FileViewerMode:
        return self.__modes[self.__current_mode]


    def line_down(self):
        """Moves cursor one line down, scrolls window if necessary"""
        if self.__cur_line < len(self.view_list) - 1:
            self.__cur_line += 1

        if self.__cur_line - self.__list_pad_top >= self.__list_pad_height:
            self.__list_pad_top += 1


    def line_up(self):
        """Moves cursor up one line, scrolls window if necessary"""
        if self.__cur_line > 0:
            self.__cur_line -= 1

        if self.__cur_line < self.__list_pad_top:
            self.__list_pad_top -= 1


    def goto_top(self):
        """Move cursor to the top of the list"""
        self.__cur_line = 0
        self.__list_pad_top = 0


    def goto_bottom(self):
        """Move cursor to the bottom of the list"""
        self.__cur_line = len(self.view_list) - 1
        self.__list_pad_top = len(self.view_list) - self.__list_pad_height
        if self.__list_pad_top < 0:
            self.__list_pad_top = 0


    def toggle_select_mode(self):
        new_mode = FileViewerModeType.Select
        if self.__current_mode == FileViewerModeType.Select:
            new_mode = FileViewerModeType.Normal
        self.set_mode(new_mode)


    def add_command(
        self, cmd: str | list[str],
        callback: CommandCallback,
        help_text: str = "",
        modes: set[FileViewerModeType] | None = None ):
        """Add a command-callback to this FileViewer, registering one or multiple
        shortcuts for it.
        :param cmd      :   str | list[str]     String or list of Strings as keyboard shortcuts
        :param callback :   CommandCallback     Method to call when the shortcut is pressed
        :param help_text:   str                 Optional, text to display for help screen
        """

        if not isinstance(cmd, list):
            cmd = [cmd]

        for c in cmd:
            self.__commands[c] = ViewerCommand(callback, help_text, modes or { 
                FileViewerModeType.Normal,
                FileViewerModeType.Select,
                FileViewerModeType.Filter})


    def set_help_line(self, line: str):
        """Displays a textline beneath the list"""
        self.__help_line = line.rstrip() + "\n"


    def select_entry(self, i: int, flip: bool = True):
        """Selects entry with index `i` in the list, if `flip` is false, it will
        only be selected, otherwise selection will be toggled.
        :param i    :   int     Index of the entry in the file list
        :param flip :   bool    (Optional) whether to toggle selection (default: True)
        """
        if i < 0 or i >= len(self.view_list):
            return
        e = self.view_list[i]
        if e.path.is_dir():
            return
        e.selected = not e.selected if flip else True


    def __exec_user_commands(self, cmd: int) -> bool:
        cmd_list = [
            k for k, e in self.__commands.items()
            if self.__current_mode in e.modes]
        inp = chr(cmd)
        while True:
            cmd_list = list(filter(lambda c: c.startswith(inp), cmd_list))
            if len(cmd_list) < 2:
                break
            cmd = self.__window.getch()
            inp += chr(cmd)

        if cmd_list:
            self.__commands[cmd_list[0]].callback(self)
            return True

        return False


    def set_mode(self, new_mode: FileViewerModeType):
        self.mode.exit()
        self.__current_mode = new_mode
        self.mode.enter()


    def show(self, print_callback: PrintCallback = default_print):
        """
        Shows this FileViewer and executes main loop until the user presses 'q'
        :param print_callback:  PrintCallback   (Optional), function to execute to display lines of entries
        """

        while self.__running:
            self.__draw_window()

            # Make sure, list_pad is big enough
            if (h := self.__list_pad.getmaxyx()[0]) <= len(self.view_list):
                del self.__list_pad
                self.__list_pad = curses.newpad(int(h * 1.5), self.__list_pad_width)

            self.__list_pad.erase()

            for i, entry in enumerate(self.view_list):
                self.__list_pad.move(i, 0)
                print_callback(self, entry, i)

            self.mode.draw(self.window)

            self.__list_pad.noutrefresh(
                self.__list_pad_top, 0, 5, 0, 5 + self.__list_pad_height, self.__list_pad_width)

            curses.doupdate()

            cmd = self.__window.getch()
            processed = self.mode.exec(cmd)

            if not processed and not self.__exec_user_commands(cmd):
                # TODO: Do anything here??
                pass


    def quit_view(self):
        self.__running = False


    def note(self, msg: str):
        self.__note = msg


    def warn(self, msg: str):
        self.__warning = msg




    def refresh(self):
        """Reset displayed list to original list"""
        self.view_list = self.__file_list



# def main(scr: curses.window):
#     theme = ViewerTheme.load()
#     file_list = [FileEntry(p) for p in Path('~/.config/').expanduser().iterdir()]
#     FileViewer("Test Viewer", file_list, scr).show()
#
#
# if __name__ == "__main__":
#     curses.wrapper(main)



