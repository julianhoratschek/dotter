from dotter import Dotter

from pathlib import Path
import argparse
import curses


DB_FILE : Path   = Path("~/.cache/dotter/files.json").expanduser().absolute()
DB_DIR  : Path    = (DB_FILE.parent / "dots/").expanduser().absolute() 


def main(scr: curses.window):
    parser = argparse.ArgumentParser("dotter")
    parser.add_argument("-y", "--all-yes", action="store_false", dest="ask")
    parser.add_argument("-d", "--json-db", nargs=1, default=DB_FILE, type=Path, dest="db_file")
    args = parser.parse_args()

    Dotter(scr, db_file=args.db_file, ask_actions=args.ask).main_view()


if __name__ == "__main__":
    curses.wrapper(main)

