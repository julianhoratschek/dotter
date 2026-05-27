import curses
import difflib
from typing import override, Protocol
from enum import IntEnum
from util import fliprange
from pathlib import Path

from file_viewer_theme import Colors

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


class FileViewerContext(Protocol):
    def select_entry(self, i: int, flip: bool = True):
        ...

    def set_mode(self, new_mode: FileViewerModeType):
        ...

    @property
    def window(self) -> curses.window:
        ...

    @property
    def cur_line(self) -> int:
        ...

    @property
    def file_list(self) -> list[FileEntry]:
        ...

    @property
    def view_list(self) -> list[FileEntry]:
        ...

    @view_list.setter
    def view_list(self, value: list[FileEntry]):
        ...
    
    @property
    def list_pad(self) -> curses.window:
        ...


class FileViewerModeType(IntEnum):
    """Vim-like file modes for FileViewer"""
    Normal  = 0
    Select  = 1
    Command = 2     # TODO: do we need this?
    Filter  = 3     # TODO: implement?


class FileViewerMode:
    def __init__(self, parent: FileViewerContext, mode_type: FileViewerModeType):
        self.parent: FileViewerContext = parent
        self.mode_type: FileViewerModeType = mode_type

    def enter(self):
        pass

    def exit(self):
        pass

    def exec(self, cmd: int) -> bool:
        return False

    def draw(self, window: curses.window):
        pass


class NormalMode(FileViewerMode):
    def __init__(self, parent: FileViewerContext):
        super().__init__(parent, FileViewerModeType.Normal)

    @override
    def exec(self, cmd: int) -> bool:
        # ENTER, SPACE
        if cmd in (10, 13, curses.KEY_ENTER) or cmd == 32:
            self.parent.select_entry(self.parent.cur_line, flip=True)

        elif cmd == ord('/'):
            self.parent.set_mode(FileViewerModeType.Filter)

        elif cmd == ord(':'):
            # TODO: command mode
            pass

        # Look for registered commands
        else:
            return False

        return True


class SelectMode(FileViewerMode):
    def __init__(self, parent: FileViewerContext):
        super().__init__(parent, FileViewerModeType.Select)
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
        if cmd == 27:
            self.parent.set_mode(FileViewerModeType.Normal)
        return super().exec(cmd)

    @override
    def draw(self, window: curses.window):
        pad = self.parent.list_pad
        for y in fliprange(self.selection_start, self.parent.cur_line):
            pad.addch(y, 1, ' ', curses.color_pair(Colors.PreSelect))



class FilterMode(FileViewerMode):
    def __init__(self, parent: FileViewerContext):
        super().__init__(parent, FileViewerModeType.Filter)

        self.filter_string: str = ""
        self.overlay_win: curses.window | None = None

    @override
    def enter(self):
        curses.echo()
        curses.curs_set(1)

        y, x = self.parent.window.getmaxyx()
        self.overlay_win = self.parent.window.derwin(3, x - 4, y - 3, 2)
        self.overlay_win.bkgd(' ', curses.color_pair(Colors.Help))
        self.overlay_win.box()

        self.overlay_win.move(1, 3)

        return super().enter()

    @override
    def exit(self):
        curses.noecho()
        curses.curs_set(0)

        del self.overlay_win
        self.overlay_win = None

        return super().exit()

    @override
    def exec(self, cmd: int) -> bool:
        # ENTER, SPACE, ESC
        if cmd in (10, 13, curses.KEY_ENTER) or cmd == 32 or cmd == 27:
            self.parent.set_mode(FileViewerModeType.Normal)
            return True

        elif cmd in (8, 127, curses.KEY_BACKSPACE):
            self.filter_string = self.filter_string[:-1]

        else:
            self.filter_string += chr(cmd)

        path_list = difflib.get_close_matches(
            self.filter_string,
            map(lambda p: str(p.path), self.parent.file_list),
            len(self.parent.file_list))
        self.parent.view_list = [
            e for e in self.parent.file_list if str(e.path) in path_list]

        return True

    @override
    def draw(self, window: curses.window):
        self.overlay_win.addstr(1, 2, '/ ', curses.color_pair(Colors.HelpShort))
        self.overlay_win.addstr(self.filter_string)
        return super().draw(window)

