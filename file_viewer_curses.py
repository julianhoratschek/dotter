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

    :ivar keys     :    Set of keys this command reacts to
    :ivar callback :    Callback for this command in form
                        (FileViewer) -> None
    :ivar help_text:    Text to display as help for this
                        Command
    :ivar modes    :    Modes this command should be active in

    """

    def __init__(self, keys: list[str] | str,
                 callback: CommandCallback, help_text: str,
                 modes: set[FileViewerModeType]):
        self.callback   : CommandCallback = callback
        self.help_text  : str             = help_text
        self.modes      : set[FileViewerModeType] = modes
        self.keys       : list[str]          = keys if isinstance(keys, list) else [keys]


class FileViewer:
    """
    Display files and enables user to traverse lists with vim-like key bindings
    Highly extendable via commands

    :ivar name             :    Name to display for this viewer
    :ivar view_list        :    List displayed in the viewer. Can be reset with
                                `viewer.refresh()`

    :ivar __window         :    Main curses window to draw UI

    :ivar __list_pad_height:    Height of file list display
    :ivar __list_pad_width :    Width of file list display
    :ivar __list_pad       :    curses window for file list display

    :ivar __file_list      :    Pointer to external file-list, default for `view_list`

    :ivar __cur_line       :    Current line in file list display
    :ivar __list_pad_top   :    Internal use: Top line of `__list_pad` to display

    :ivar __current_mode   :    Currently active editor mode
    :ivar __modes          :    Dictionary of registered modes

    :ivar __commands       :    Dictionary of registered user commands. Can be
                                extended by `add_command`
    :ivar __current_commands:   List of commands in the current mode

    :ivar __running        :    Internal use: Controls main Loop
    """

    # TODO: Notification system?

    @staticmethod
    def default_print(viewer: FileViewer, entry: FileEntry, i: int, /, **kwargs):
        """
        Default per-line printing for entries in the current list

        :param viewer:  The calling instance of FileViewer
        :param entry :  The current entry of the list
        :param i     :  The ID (position) of entry (zero based)
        :param kwargs:  Further optional arguments:
                        prepend_icon: Icon to display before line
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

        win.addstr(5 + self.__list_pad_height, 2, "***Commands***", curses.A_BOLD)
        win.attron(curses.color_pair(Colors.Help))

        win.move(6 + self.__list_pad_height, 2)

        for cmd in filter(lambda x: x.help_text, self.__current_commands):
            win.addstr(cmd.keys[0], curses.color_pair(Colors.HelpShort))
            win.addstr(f" -> {cmd.help_text}; ")

        # win.addstr(6 + self.__list_pad_height, 2,
        #                    "q -> quit viewer; j/k -> move up/down; "+
        #                    "v -> select block; " +
        #                    "/ -> filter; " + 
        #                    "x -> reset filter; ")

        win.attroff(curses.color_pair(Colors.Help))

    def __exec_user_commands(self, cmd: int) -> bool:
        """
        Looks for commands defined by add_command for the currently active
        mode and executes them.
        :param cmd  :   int     First keypress of the user
        :returns    :   bool    True if a command was found, False otherwise
        """

        cmd_list = [
            (e.keys, e) for e in self.__current_commands
        ]

        inp = chr(cmd)

        while True:
            cmd_list = [
                (e[0], e[1]) for e in cmd_list
                if any(s.startswith(inp) for s in e[0])
            ]

            if len(cmd_list) < 2:
                break

            cmd = self.__window.getch()
            inp += chr(cmd)

        if cmd_list:
            cmd_list[0][1].callback(self)
            return True

        return False


    def __get_mode_commands(self) -> list[ViewerCommand]:
        return [e for e in self.__commands
            if self.__current_mode in e.modes]


    def __init__(self, viewer_name: str, file_list: FileList, main_window: curses.window):
        self.name               : str                       = viewer_name
        self.__window           : curses.window             = main_window.derwin(2, 0)

        h, w = self.__window.getmaxyx()

        self.__list_pad_height  : int                       = h - 12
        self.__list_pad_width   : int                       = w
        self.__list_pad         : curses.window             = curses.newpad(1024, self.__list_pad_width)

        self.__file_list        : FileList                  = file_list
        self.view_list          : FileList                  = file_list

        self.__cur_line         : int                       = 0
        self.__list_pad_top     : int                       = 0
        self.__current_mode     : FileViewerModeType        = FileViewerModeType.Normal
        self.__modes            : dict[FileViewerModeType, FileViewerMode] = {
            FileViewerModeType.Normal: NormalMode(self),
            FileViewerModeType.Select: SelectMode(self),
            FileViewerModeType.Filter: FilterMode(self) }

        self.__commands         : list[ViewerCommand]  = []

        self.__running          : bool                      = True

        modes = {
            FileViewerModeType.Normal,
            FileViewerModeType.Select
        }

        self.add_command('j',FileViewer.line_down,
                         help_text="move up", modes=modes)

        self.add_command('k', FileViewer.line_up,
                         help_text="move down", modes=modes)

        self.add_command(["gg", "g0"], FileViewer.goto_top,
                         help_text="move to top", modes=modes)

        self.add_command('G', FileViewer.goto_bottom,
                         help_text="move to bottom", modes=modes)

        self.add_command('v', 
                         lambda x: x.toggle_mode(FileViewerModeType.Select),
                         help_text="toggle select", modes=modes)

        self.add_command('/',
                         lambda x: x.toggle_mode(FileViewerModeType.Filter),
                         help_text="filter", modes={FileViewerModeType.Normal})

        self.add_command('x', FileViewer.reset_filter,
                         help_text="reset filter")

        self.add_command('q', FileViewer.quit_view,
                         help_text="quit viewer")

        self.__current_commands : list[ViewerCommand]       = self.__get_mode_commands()


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

    def toggle_mode(self, new_mode: FileViewerModeType):
        """Enter or exit `new_mode`"""

        if self.__current_mode == new_mode:
            new_mode = FileViewerModeType.Normal
        self.set_mode(new_mode)

    def reset_filter(self):
        self.__modes[FileViewerModeType.Filter].filter_string = ""
        self.refresh()

    def add_command(self, cmd: str | list[str],
                    callback: CommandCallback,
                    help_text: str = "",
                    modes: set[FileViewerModeType] | None = None ):
        """
        Add a command-callback to this FileViewer, registering one or multiple
        shortcuts for it.

        :param cmd      :   String or list of Strings as keyboard shortcuts
        :param callback :   Method to call when the shortcut is pressed
        :param help_text:   Optional, text to display for help screen
        :param modes    :   Set of modes this command should be
                            activated for. If left empty, command will be active
                            for all modes.
        """

        self.__commands.append(
            ViewerCommand(cmd, callback, help_text, modes or { 
                FileViewerModeType.Normal,
                FileViewerModeType.Select,
                FileViewerModeType.Filter}))


    def select_entry(self, i: int, flip: bool = True):
        """
        Selects entry with index `i` in the list, if `flip` is false, it will
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

    def set_mode(self, new_mode: FileViewerModeType):
        """
        Sets the mode of FileViewer to `new_mode`. Calls exit-method of the old
        mode and enter-method of the new mode.
        :param new_mode:    FileViewerModeType  New Mode to enter
        """

        self.mode.exit()
        self.__current_mode = new_mode
        self.mode.enter()
        self.__current_commands = self.__get_mode_commands()

    def show(self, print_callback: PrintCallback = default_print):
        """
        Shows this FileViewer and executes main loop until the user presses 'q'
        :param print_callback:  PrintCallback   (Optional), function to execute to display lines of entries
        """

        self.__current_commands = self.__get_mode_commands()

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

            self.mode.draw_pad(self.__list_pad)

            self.__window.noutrefresh()

            self.__list_pad.noutrefresh(
                self.__list_pad_top, 0, 5, 0, 5 + self.__list_pad_height, self.__list_pad_width)

            self.mode.draw(self.window)

            curses.doupdate()

            cmd = self.__window.getch()
            processed = self.mode.exec(cmd)

            if not processed and not self.__exec_user_commands(cmd):
                # Do anything here?
                ...

    def quit_view(self):
        self.__running = False

    def refresh(self):
        """Reset displayed list to original list"""
        self.view_list = self.__file_list


