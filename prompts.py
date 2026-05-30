import curses
from enum import IntEnum

from file_viewer_theme import Colors


class DialogResult(IntEnum):
    No      = 0
    Yes     = 1


def prompt(window: curses.window, msg: str) -> str:
    curses.echo()
    curses.curs_set(1)

    height, width = window.getmaxyx()
    win = window.derwin(3, width - 2, height - 3, 2)
    win.bkgd(' ', curses.color_pair(Colors.Help))
    win.box()

    win.addstr(1, 2, msg)
    win.refresh()

    ret = win.getstr(1, len(msg) + 2).decode("utf-8").strip()

    curses.noecho()
    curses.curs_set(0)
    del win

    return ret


def yesno_prompt(window: curses.window, msg: str) -> DialogResult:
    curses.curs_set(1)

    _, width = window.getmaxyx()
    win = window.derwin(12, 50, 4, width // 2 - 25)
    win.bkgd(' ', curses.color_pair(Colors.Help))
    win.box()

    for i, line in enumerate(msg.splitlines()):
        win.addstr(2 + i, 2, line)

    win.addch(8, 15, 'Y', curses.color_pair(Colors.Accent))
    win.addstr("es")
    win.addch(8, 30, 'N', curses.color_pair(Colors.Accent))
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
