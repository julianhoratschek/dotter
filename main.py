from dotter import Dotter

from pathlib import Path
import argparse
import curses


DB_FILE : Path   = Path("~/.cache/dotter/files.json").expanduser().absolute()
DB_DIR  : Path    = (DB_FILE.parent / "dots/").expanduser().absolute() 
THEME_FILE  : Path  = (DB_FILE.parent / "theme.toml").expanduser().absolute()


def main(scr: curses.window):
    parser = argparse.ArgumentParser("dotter")
    parser.add_argument("-d", "--json-db", nargs=1, default=DB_FILE, type=Path, dest="db_file")
    parser.add_argument("-t", "--theme", nargs=1, default=THEME_FILE, type=str, dest="theme_file")
    args = parser.parse_args()

    Dotter(scr, db_file=args.db_file, theme_file=args.theme_file).main_view()


if __name__ == "__main__":
    curses.wrapper(main)

