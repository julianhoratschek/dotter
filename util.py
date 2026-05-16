from pathlib import Path
from enum import StrEnum

DB_DIR  : Path    = Path("~/.cache/dotter/dots/").expanduser().absolute()
DB_FILE : Path   = Path("~/.cache/dotter/files.json").expanduser().absolute()


def err(msg: str) -> str:
    return f"\x1b[1;91m!!\x1b[0m {msg}"

def warn(msg: str) -> str:
    return f"\x1b[38;5;220m󱞁\x1b[0m {msg}"

def bold(msg: str) -> str:
    return f"\x1b[1m{msg}\x1b[22m"

class CM(StrEnum):
    FG = "38;5;"
    BG = "48;5;"

class AC(StrEnum):
    RED = "124"
    GREEN = "34"
    GREY = "240"
    BLUE = "105"


def cl(msg: str, color: AC, mode: CM = CM.FG, close: bool = True) -> str:
    reset = ""
    if close:
        reset = "\x1b[39m" if mode == CM.FG else "\x1b[49m"
    return f"\x1b[{mode}{color}m{msg}{reset}"

def fg(msg: str, color: AC, close: bool = True) -> str:
    return cl(msg, color, CM.FG, close)

def bg(msg: str, color: AC, close: bool = True) -> str:
    return cl(msg, color, CM.BG, close)




