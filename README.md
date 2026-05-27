# Dotter :chicken:

## Intended Use

Dotter is a TUI dots-file management software in pure python without external
dependencies. The main idea is to keep all your dot-files in one location
to let a versioning manager of your choice easily track changes on them,
while your system will find symlinks to the respective files at their
original location.
Furthermore, Dotter enables you to easily save and set up your configuration
on any new system, as it makes it easy to change home-directories of the
saved dot-files.
Lastly, Dotter is designed to work non-destructively. Even if you should choose
to remove a file from the database, it will not be destroyed but moved to a
special sub-folder for further inspection.


## Dependencies

- Python >= 3.14
- Nerd Fonts (Optional, for icons)

## Command Line Parameters


| .. | ..        | ..                 | ..                                           |
| -- | --------- | ------------------ | -------------------------------------------- |
| -d | --json-db | Path to json file  | Where to find a custom JSON file.            |
| -t | --theme   | Path to theme toml | File containing some or all themeing options |


### JSON DB

Dotter uses JSON as a simple database format to keep track of its managed files
and their locations. If the user does not define a custom JSON file, Dotter will
look for it in `~/.cache/dotter/db.json`.

All Files moved or read by Dotter will be searched for in `<path-to-json>/dots/`.

### Creating Theme

Dotter is customizable. You can point Dotter to a specific theme-file by passing
the command line argument `-t` or `--theme`.
This expects to find a [TOML-File](https://toml.io/en/v1.1.0) with all or some of the following options:

```toml
# Default-Values

Directory = [105,  -1]
Selected  = [ -1,  34]
Warning   = [124,  -1]
Note      = [220,  -1]
Help      = [ -1, 240]
HelpShort = [105, 240]
PreSelect = [ -1,  34]
```

The list represents [ANSI-ESCAPE-Colors](https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797) as \[foreground, background\]. Use `-1`
to signal to use default-colors.


## Commands

### General Commands

Dotter uses vim-like key-bindings wherever possible. Also, vim-like modes are
used to facilitate specific actions. The globally available commands are:

| Key     | Description            | Modes          |
| ------- | ---------------------- | -------------- |
| `gg g0` | Move to top of list    | Normal, Select |
| `G`     | Move to bottom of list | Normal, Select |
| `j`     | Move one line down     | Normal, Select |
| `k`     | Move one line up       | Normal, Select |
| `q`     | Quit Viewer            | Normal, Select |
| `v`     | Enter/Exit Select Mode | Normal, Select |
| `/`     | Enter Filter Mode      | Normal, Select |


#### Select Mode

Pressing `v` will enter/exit Select-Mode. In this mode, you can select multiple
files at once by moving over them. A highlighter will signal, which files will
be selected. When exiting Select-Mode (by pressing `v` or `ESC`), the highlightet
files will be selected.

#### Filter Mode

Pressing `/` will enter Filter-Mode. Press `ESC` to exit Filter-Mode.
In this mode, you can type in regular expressions (python-style) to filter
the displayed list. The filter resets when changing directories. To reset
the filter, simply leave the filter-prompt empty.

### File Browser

This is Dotters Main Screen. Here, you can traverse directories, select files
and add them to your database. Available commands are:


| ..  | ..                                                       |
| --- | -------------------------------------------------------- |
| `a` | [Add selected files to Dotter](#register-files)          |
| `h` | [Move to parent directory](#traversing-directories)      |
| `l` | [Enter Directory](#traversing-directories)               |
| `t` | [Show and edit registered files](#list-registered-files) |


#### Register files

Pressing `a` while having files selected in the file browser, will add those
files to Dotters internal database. The original file will be moved to `~/.cache/dotter/dots/`
and a symlink to that new location will be created at its original location.

If a file is already registered, nothing will happen. If a file is already registered,
but the added file seems to differ from it (e.g. is not a symlink or is a symlink
that links elsewhere), the old file from the database will be moved to `~/.cache/dotter/dots/remove/` and the new file will take its place.

Please note, that you cannot add directories. You will have to select all files
individually.


#### Traversing Directories

Pressing `l` will enter the currently selected directory, pressing `h` at any
time will move one directory up. If the selected entry is not a directory,
this command has no effect.


#### List Registered Files

Pressing `t` will open list-mode, where all registered files will be presented
and can be changed. Here, you can edit, remove, restore or setup your dots files.
See [Dotter View](#dotter-view) for a complete command list.


### Dotter View

This View lists all registered files in your database. You can edit the paths
of these files, restore or remove them and clean your database if needed.
Additionally, if you set up a new system, you can create symlinks to selected
files on your system to speed up dot-files setup.


| ..      | ..                                |
| ------- | --------------------------------- |
| `cl cc` | [Clean Database](#clean-database) |
| `r`     | [Restore files](#restore-files)   |
| `d`     | [Delete files](#delete-files)     |
| `eh`    | [Edit Home Path](#edit-home-path) |
| `s`     | [Setup Files](#setup-files)       |



#### Clean Database

Pressing `cl` or `cc` will clean up the database and saved files. All database
entries without a corresponding file in `~/.cache/dotter/dots` will be removed.
Also, all files in the `dots` directory without entries in the database will
be moved to `~/.cache/dotter/dots/remove/`.


#### Restore Files

Pressing `r` will restore all selected files. It will remove the selected entries
from the database and move the corresponding files from `~/.cache/dotter/dots/`
back to their original locations.


#### Delete Files

Pressing `d` will delete all selected entries. Dotter is designed to be non-destructive,
so no files will actually be deleted. The entries will be removed from the database,
the corresponding files are moved to `~/.cache/dotter/dots/remove/`, their symlinks
are removed from the system.


#### Edit Home path

Pressing `eh` will change the home path of all selected entries. The user will
be prompted to enter a new username, leaving this empty will abort the operation.
Otherwise, the usernames in all selected entries will be changed to the new
username and will be saved as new entries (respective files in the `dots`-directory
will be copied).

This operation is non-destructive, old files or entries will not be touched,
the new entries will link to separate, copied files.

#### Setup Files

Pressing `s` will setup the selected files on your system. Beware, the symlinks
will be created **exactly** at the locations their paths point to. If you don't
have the necessary permissions or try to create files in the wrong home directory,
the operation will fail.

This will **not** overwrite existing files. If you already have a dot file at
the location Dotter tries to insert a symlink, the operation will skip that file.
Please remove all unwanted dot-files before executing this command.
