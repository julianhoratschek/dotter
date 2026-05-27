# Dotter 🐔

## Intended Use 🛠️

Dotter is a pure Python TUI (Terminal User Interface) dotfile management application with zero external dependencies. 

The core philosophy is to keep all your dotfiles in a single location so that a version control system (like Git) can easily track them, while your system references them via symlinks at their original locations.

Furthermore, Dotter allows you to seamlessly back up and deploy your configurations across different machines by making it easy to adapt the home directory paths of your saved dotfiles.

Lastly, Dotter is built to be non-destructive. Even if you choose to remove a file from the database, it is never permanently deleted; instead, it is moved to a dedicated sub-folder for safe keeping and further inspection.

## Dependencies 📦

- Python >= 3.14
- Nerd Fonts (Optional, for icon support)

## Command Line Parameters 📣

| Command | Full Command | Parameter | Description |
| :--- | :--- | :--- | :--- |
| `-d` | `--json-db` | `Path to json file` | Path to a custom JSON database file. |
| `-t` | `--theme` | `Path to theme toml`| Path to a TOML file containing custom theme options. |

### JSON DB

Dotter uses a simple JSON database format to track managed files and their target locations. If no custom database is specified, Dotter defaults to `~/.cache/dotter/db.json`.

All dotfiles managed or read by Dotter are stored in `<path-to-json>/dots/`.

### Custom Themes

Dotter is fully customizable. You can apply a custom theme by passing the `-t` or `--theme` flag, which expects a [TOML file](https://toml.io/en/v1.1.0) containing some or all of the following color options:

```toml
# Default Values

Directory = [105,  -1]
Selected  = [ -1,  34]
Warning   = [124,  -1]
Note      = [220,  -1]
Help      = [ -1, 240]
HelpShort = [105, 240]
PreSelect = [ -1,  34]

```

The arrays represent [ANSI Escape Colors](https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797) formatted as `[foreground, background]`. Use `-1` to inherit your terminal's default colors.

## Commands ⌨️

### General Commands 🌐

Dotter utilizes Vim-like keybindings and modal navigation where applicable. The following commands are globally accessible:

| Key | Description | Modes |
| --- | --- | --- |
| `gg`, `g0` | Move to the top of the list | Normal, Select |
| `G` | Move to the bottom of the list | Normal, Select |
| `j` | Move one line down | Normal, Select |
| `k` | Move one line up | Normal, Select |
| `q` | Quit the application | Normal, Select |
| `v` | Enter / Exit Select Mode | Normal, Select |
| `/` | Enter Filter Mode | Normal, Select |

#### Select Mode

Press `v` to toggle Select Mode. In this mode, you can select multiple files simultaneously by moving the cursor over them. A visual highlighter indicates which files are queued. Upon exiting Select Mode (via `v` or `ESC`), the highlighted files will be formally selected.

#### Filter Mode

Press `/` to enter Filter Mode, and `ESC` to exit. In this mode, you can type Python-style regular expressions to filter the visible list. The filter automatically resets when you change directories, or it can be manually cleared by leaving the filter prompt empty.

### File Browser 📂

This is Dotter's main interface. Here, you can traverse directories, select files, and add them to your database.

| Key | Description |
| --- | --- |
| `a` | [Add selected files to Dotter](https://www.google.com/search?q=%23register-files) |
| `h` | [Move to parent directory](https://www.google.com/search?q=%23traversing-directories) |
| `l` | [Enter selected directory](https://www.google.com/search?q=%23traversing-directories) |
| `t` | [Show and edit registered files](https://www.google.com/search?q=%23list-registered-files) |

#### Register Files

Pressing `a` with files selected will add them to Dotter's internal database. The original file will be moved to `~/.cache/dotter/dots/`, and a symlink pointing to this new location will be generated at the file's original path.

* If a file is already registered, no action is taken.
* If a file is registered but its state has drifted (e.g., it is no longer a symlink, or it points elsewhere), the existing file in the database is safely moved to `~/.cache/dotter/dots/remove/`, and the new file takes its place.

> ⚠️ **Note:** Dotter does not support adding raw directories. You must select and add individual files.

#### Traversing Directories

Press `l` to enter the currently highlighted directory, or press `h` at any time to move up to the parent directory. If the current selection is a file, these commands will have no effect.

#### List Registered Files

Press `t` to open List Mode, which displays all registered files. From this view, you can edit, remove, restore, or deploy your dotfiles. See the [Dotter View](https://www.google.com/search?q=%23dotter-view) section below for the complete command mapping.

### Dotter View 🗒️

The Dotter View lists every registered file currently tracked in your database. From here, you can modify target paths, restore or remove files, and clean up your database. It is also the starting point for deploying your dotfiles onto a newly formatted system.

| Key | Description |
| --- | --- |
| `cl`, `cc` | [Clean Database](https://www.google.com/search?q=%23clean-database) |
| `r` | [Restore files](https://www.google.com/search?q=%23restore-files) |
| `d` | [Delete files](https://www.google.com/search?q=%23delete-files) |
| `eh` | [Edit Home Path](https://www.google.com/search?q=%23edit-home-path) |
| `s` | [Setup Files](https://www.google.com/search?q=%23setup-files) |

#### Clean Database

Pressing `cl` or `cc` syncs your database with your physical storage. Any database entry lacking a corresponding physical file in `~/.cache/dotter/dots` will be purged. Conversely, any untracked files found within the `dots` directory will be moved to `~/.cache/dotter/dots/remove/`.

#### Restore Files

Pressing `r` restores all selected entries. This removes them from the Dotter database and returns the physical files from `~/.cache/dotter/dots/` back to their original system locations.

#### Delete Files

Pressing `d` removes the selected entries from the database. True to Dotter's non-destructive design, no data is erased: the corresponding files are safely relocated to `~/.cache/dotter/dots/remove/`, and their active system symlinks are severed.

#### Edit Home Path

Pressing `eh` updates the target home directory path for all selected entries. You will be prompted to enter a new username; leaving the prompt empty aborts the operation. Otherwise, the username context within the file paths is updated, and the corresponding files in the `dots` directory are duplicated to reflect the new user profile.

This process is entirely non-destructive—your original files and entries remain untouched.

#### Setup Files

Pressing `s` deploys the selected dotfiles onto your current system.

> ⚠️ **Warning:** Symlinks will be created **exactly** at the literal paths stored in the database. The operation will fail if you lack the necessary write permissions or if the paths reference a non-existent home directory.
> Dotter **will not** overwrite existing files. If a file already occupies a path where Dotter attempts to drop a symlink, that file is skipped. Please back up and clear conflicting files before running this command.
