from dotter import Dotter

from pathlib import Path
import argparse


DB_FILE : Path   = Path("~/.cache/dotter/files.json").expanduser().absolute()
DB_DIR  : Path    = (DB_FILE.parent / "dots/").expanduser().absolute() 


if __name__ == "__main__":
    parser = argparse.ArgumentParser("dotter")
    parser.add_argument("-y", "--all-yes", action="store_false", dest="ask")
    parser.add_argument("-d", "--json-db", nargs=1, default=DB_FILE, type=Path, dest="db_file")
    args = parser.parse_args()

    Dotter(db_file=args.db_file, ask_actions=args.ask).main_view()
