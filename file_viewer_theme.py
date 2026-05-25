from enum import IntEnum
import curses
from typing import override
from pathlib import Path
import tomllib


class Colors(IntEnum):
    """Colors defined by this theme"""
    Directory   = 1
    Selected    = 2
    Warning     = 3
    Note        = 4
    Help        = 5
    HelpShort   = 6
    PreSelect   = 7

    @override
    def __str__(self) -> str:
        match self:
            case Colors.Directory:
                return "Directory"
            case Colors.Selected:
                return "Selected"
            case Colors.Warning:
                return "Warning"
            case Colors.Note:
                return "Note"
            case Colors.Help:
                return "Help"
            case Colors.HelpShort:
                return "HelpShort"
            case Colors.PreSelect:
                return "PreSelect"

ColorDefaults: dict[Colors, list[int]] = {
	Colors.Directory: [105, -1],
	Colors.Selected: [-1,  34],
	Colors.Warning: [124, -1],
	Colors.Note: [220, -1],
	Colors.Help: [-1,  240],
	Colors.HelpShort: [105, 240],
	Colors.PreSelect: [-1,  34]
}


class ViewerTheme:
    InitDone: bool = False

    def __init__(self, theme_file: Path | str = ""):
        """
        Loads defaults for FileViewer Theme or reads color data from `theme_file`
        if provided. Falls back to defaults, if `theme_file` is malformed or
        missing.
        :ivar theme_file:   Path|str    Optional, Path to a toml-file providing
                                        the theme to display
        """

        if not ViewerTheme.InitDone:
            curses.curs_set(0)

            curses.start_color()
            curses.use_default_colors()
            ViewerTheme.InitDone = True

        theme_data: dict[str, list[int]] = {}
        if theme_file and (theme_file := Path(theme_file)).exists():
            with theme_file.open("rb") as fl:
                try:
                    theme_data = tomllib.load(fl)
                except tomllib.TOMLDecodeError:
                    # TODO: handle
                    pass

        for cl, vals in ColorDefaults.items():
            name = str(cl)

            try:
                if name in theme_data and len(theme_data[name]) == 2:
                    vals = list(map(int, theme_data[name]))
            except ValueError:
                # TODO: handle correctly
                pass
            curses.init_pair(cl, *vals)

