import curses
import re
from typing import override, Protocol
from enum import IntEnum
from pathlib import Path

from util import fliprange
from file_viewer_theme import Colors


class FileEntry:
    """
    Describes one database- or directory-entry to display with FileViewer

    :ivar path    :     Absolute path to the location of the file
    :ivar name    :     Name describing the file, for Database-files md5-sum of
                        their absolute path
    :ivar selected:     True, if the file is currently selected
    """

    def __init__(self, path: Path, name: str = "", selected: bool = False):
        self.path       : Path  = path.expanduser().absolute()
        self.name       : str   = name
        self.selected   : bool  = selected

    def to_dict(self) -> dict[str, str]:
        """ Returns the object as JSON-writeable format """
        return { "path": str(self.path.expanduser().absolute()), "name": self.name }


class FileViewerContext(Protocol):
    """Context as forward-declaration for FileViewer"""

    def select_entry(self, i: int, flip: bool = True): ...

    def set_mode(self, new_mode: FileViewerModeType): ...

    @property
    def window(self) -> curses.window: ...

    @property
    def cur_line(self) -> int: ...

    @cur_line.setter
    def cur_line(self, value: int): ...

    @property
    def file_list(self) -> list[FileEntry]: ...

    @property
    def view_list(self) -> list[FileEntry]: ...

    @view_list.setter
    def view_list(self, value: list[FileEntry]): ...
    
    @property
    def list_pad(self) -> curses.window: ...


class FileViewerModeType(IntEnum):
    """Vim-like file modes for FileViewer"""
    Normal      = 0
    Select      = 1
    Filter      = 2


class FileViewerMode:
    """
    Base class for File viewer modes. Exposes functionality for entering, exiting
    and processing as well as drawing within this mode.
    :ivar parent   :    FileViewer owning this mode
    :ivar mode_type:    FileViewerModeType describing this mode
    """

    def __init__(self, parent: FileViewerContext,
                 mode_type: FileViewerModeType, color: Colors):
        self.parent     : FileViewerContext     = parent
        self.mode_type  : FileViewerModeType    = mode_type
        self.color      : Colors                = color

    def enter(self):
        """Called when entering this mode"""
        pass

    def exit(self):
        """Called when exiting this mode"""
        pass

    def exec(self, cmd: int) -> bool:
        """
        Called on every input while this mode is active
        :param cmd: First input caught from the user
        :returns:   True, if the input was handled by exec, otherwise return
                    False to indicate that `cmd` should be compared to
                    registered FileViewerCommands of `parent`
        """
        return False

    def draw(self, window: curses.window):
        """Called after drawing windows while this mode is active"""
        pass

    def draw_pad(self, pad: curses.window):
        """Called after drawing but before refreshing the list pad"""
        pass


class NormalMode(FileViewerMode):
    def __init__(self, parent: FileViewerContext):
        super().__init__(parent, FileViewerModeType.Normal,
                         Colors.NormalMod)

    @override
    def exec(self, cmd: int) -> bool:
        # ENTER, SPACE
        if cmd in (10, 13, curses.KEY_ENTER) or cmd == 32:
            self.parent.select_entry(self.parent.cur_line, flip=True)
            return True

        # Look for registered commands
        return False


class SelectMode(FileViewerMode):
    def __init__(self, parent: FileViewerContext):
        super().__init__(parent, FileViewerModeType.Select,
                         Colors.VisualMod)

        self.selection_start: int = 0

    @override
    def enter(self):
        self.selection_start = self.parent.cur_line
        return super().enter()

    @override
    def exit(self):
        for i in fliprange(self.selection_start, self.parent.cur_line):
            self.parent.select_entry(i, flip=False)
        return super().exit()

    @override
    def exec(self, cmd: int) -> bool:
        # ESC
        if cmd == 27:
            self.parent.set_mode(FileViewerModeType.Normal)
        return super().exec(cmd)

    @override
    def draw_pad(self, pad: curses.window):
        for y in fliprange(self.selection_start, self.parent.cur_line):
            pad.addch(y, 1, ' ', curses.color_pair(Colors.PreSelect))


class FilterMode(FileViewerMode):
    def __init__(self, parent: FileViewerContext):
        super().__init__(parent, FileViewerModeType.Filter,
                         Colors.FilterMod)

        y, x = self.parent.window.getmaxyx()

        self.filter_string  : str           = ""
        self.overlay_win    : curses.window = curses.newwin(3, x, y - 3, 2)

    @override
    def enter(self):
        curses.echo()
        curses.curs_set(1)

        y, x = self.parent.window.getmaxyx()
        self.overlay_win = curses.newwin(3, x, y - 3, 2)

        return super().enter()

    @override
    def exit(self):
        curses.noecho()
        curses.curs_set(0)

        del self.overlay_win

        return super().exit()

    @override
    def exec(self, cmd: int) -> bool:
        self.parent.cur_line = 0

        # ENTER, SPACE, ESC
        if cmd in (10, 13, curses.KEY_ENTER) or cmd == 32 or cmd == 27:
            self.parent.set_mode(FileViewerModeType.Normal)
            return True

        # BACKSPACE
        elif cmd in (8, 127, curses.KEY_BACKSPACE):
            self.filter_string = self.filter_string[:-1]

        else:
            self.filter_string += chr(cmd)

        try:
            pattern = re.compile(self.filter_string)
            self.parent.view_list = [e for e in self.parent.file_list
                if pattern.search(str(e.path))] 
        except re.PatternError:
            pass

        return True


    @override
    def draw(self, window: curses.window):
        self.overlay_win.erase()
        self.overlay_win.bkgd(' ', curses.color_pair(Colors.Help))
        self.overlay_win.box()

        self.overlay_win.addstr(1, 2, '/', curses.color_pair(Colors.Accent))
        self.overlay_win.addstr(self.filter_string)
        self.overlay_win.move(1, 3 + len(self.filter_string))

        self.overlay_win.noutrefresh()

        return super().draw(window)

