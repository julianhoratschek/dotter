from enum import IntEnum

# String formatting functions for logging

class CM(IntEnum):
    """Describes ANSI-Color for Foreground or Background"""
    FG      = 38
    BG      = 48


class AC(IntEnum): 
    """Describes ANSI-Color Scheme"""
    BLUE    = 105
    GREEN   = 34
    GREY    = 240
    RED     = 124
    YELLOW  = 220


def cl(msg: str, color: AC, mode: CM = CM.FG, close: bool = True) -> str:
    """
    Set color for text

    :param msg:     String to color with ANSI-Colors
    :param color:   Ansi-Color code as AC-Enum
    :param mode:    Ansi-Code for foreground or background as CM-Enum
    :param close:   Close Ansi-Code at end of msg
    :returns:       str, `msg` enclosed in corresponding ANSI-Codes
    """

    reset = f"\x1b[{mode + 1}m" if close else ""
    return f"\x1b[{mode};5;{color}m{msg}{reset}"


def fg(msg: str, color: AC, close: bool = True) -> str:
    return cl(msg, color, CM.FG, close)


def bg(msg: str, color: AC, close: bool = True) -> str:
    return cl(msg, color, CM.BG, close)


def err(msg: str) -> str:
    return f"  \x1b[91m!!\x1b[0m {msg}"


def warn(msg: str) -> str:
    return f"  \x1b[38;5;220m󱞁\x1b[0m {msg}"


def bold(msg: str) -> str:
    return f"\x1b[1m{msg}\x1b[22m"



