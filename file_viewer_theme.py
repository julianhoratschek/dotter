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
    Accent      = 6
    PreSelect   = 7
    NormalMod   = 8
    VisualMod   = 9
    FilterMod   = 10


ColorDefaults: dict[Colors, list[int]] = {
	Colors.Directory: [105,  -1],
	Colors.Selected : [ -1,  34],
	Colors.Warning  : [124,  -1],
	Colors.Note     : [220,  -1],
	Colors.Help     : [ -1, 240],
	Colors.Accent   : [105, 240],
	Colors.PreSelect: [ -1,  34],
    Colors.NormalMod: [ -1, 240],
    Colors.VisualMod: [ -1, 124],
    Colors.FilterMod: [ -1,  34]
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

        # Load user theme if defined
        if theme_file and (theme_file := Path(theme_file)).exists():
            with theme_file.open("rb") as fl:
                try:
                    theme_data = tomllib.load(fl)
                except tomllib.TOMLDecodeError:
                    # TODO: handle
                    pass

        # Setup colors
        for cl, vals in ColorDefaults.items():
            name = cl.name

            try:
                if name in theme_data and len(theme_data[name]) == 2:
                    vals = list(map(int, theme_data[name]))
            except ValueError:
                # TODO: handle correctly
                pass
            curses.init_pair(cl, *vals)

