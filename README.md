# Dotter

A pure Python TUI dotfile manager — zero external dependencies, vim-like navigation, and strictly non-destructive operations.

Dotter keeps all your dotfiles in one versioned directory and places symlinks at their original system paths. When you move to a new machine, point Dotter at your repo and deploy everything in seconds.

---

## Features

- **Zero dependencies** — only the Python standard library (≥ 3.14) and curses
- **Non-destructive** — files are never deleted; displaced entries move to a `remove/` staging folder
- **Cross-machine deployment** — update username paths in bulk to deploy configs for a different user
- **Vim-like navigation** — Normal, Select, and Filter modes
- **Fully themeable** — override any color via a TOML file
- **Regex filtering** — live filter the file list with Python regular expressions

---

## Requirements

| Requirement | Notes |
|---|---|
| Python ≥ 3.14 | Uses `Path.move()` and `tomllib` from stdlib |
| Nerd Fonts | Optional — enables file-status icons in the browser |

---

## Installation

No install step is required. Clone the repo and run `main.py` directly:

```sh
git clone https://github.com/julianhoratschek/dotter.git
cd dotter
python main.py
```

---

## Usage

```
python main.py [-d <db.json>] [-t <theme.toml>]
```

| Flag | Long form | Description |
|---|---|---|
| `-d PATH` | `--json-db` | Path to a custom JSON database file (default: `~/.cache/dotter/files.json`) |
| `-t PATH` | `--theme` | Path to a TOML theme file (default: `~/.cache/dotter/theme.toml`) |

### Quick start

```sh
# Use the default database location
python main.py

# Use a custom database (e.g. inside your dotfiles repo)
python main.py -d ~/dotfiles/db.json

# Apply a custom color theme
python main.py -t ~/dotfiles/mytheme.toml
```

---

## Storage layout

Dotter stores everything relative to the database file location:

```
~/.cache/dotter/
├── files.json          ← database (tracks path → md5-name mappings)
└── dots/
    ├── a3f8c2...       ← managed dotfile (named by md5 of original path)
    ├── 9e1bd4...
    └── remove/         ← staging area for displaced/deleted files
        └── .config/
            └── nvim/
                └── init.lua
```

All managed files live inside `dots/`. Symlinks at their original paths point here. The `remove/` subdirectory is the non-destructive trash — nothing Dotter does permanently erases data.

---

## Workflow

### 1. Add dotfiles

Open Dotter and navigate to a config file. Select it and press `a`:

```
Dotter moves:  ~/.config/nvim/init.lua  →  ~/.cache/dotter/dots/9e1bd4...
Creates link:  ~/.config/nvim/init.lua  →  ~/.cache/dotter/dots/9e1bd4...
```

The file now lives in one place and is tracked in `files.json`.

### 2. Put the database directory under version control

```sh
cd ~/.cache/dotter
git init
git add dots/ files.json
git commit -m "add dotfiles"
```

### 3. Deploy to a new machine

Clone your repo, open Dotter with `-d` pointing at the database, switch to the Registered Files view (`t`), select all entries, and press `s`:

```sh
# On the new machine
git clone git@github.com:you/dotfiles.git ~/dotfiles
python main.py -d ~/dotfiles/files.json
# → press t → select all → press s
```

Dotter creates symlinks at the exact paths stored in the database.

---

## Key bindings

### Global (all modes)

| Key | Action |
|---|---|
| `j` / `k` | Move cursor down / up |
| `gg`, `g0` | Jump to top |
| `G` | Jump to bottom |
| `v` | Toggle Select Mode |
| `/` or `f` | Enter Filter Mode |
| `x` | Clear filter |
| `q` | Quit |

### File Browser

Navigate the filesystem and add files to the database.

| Key | Action |
|---|---|
| `l` | Enter highlighted directory |
| `h` | Go to parent directory |
| `Space` / `Enter` | Toggle selection on current entry |
| `a` | Add selected files to database |
| `t` | Open Registered Files view |

Files already tracked in the database are marked with a `󰃁` icon (requires Nerd Fonts).

> Dotter only accepts individual files — directories cannot be added directly.

### Registered Files view

Manage your tracked dotfiles.

| Key | Action |
|---|---|
| `Space` / `Enter` | Toggle selection on current entry |
| `r` | Restore selected files to their original paths |
| `d` | Delete selected files (moves to `remove/`, non-destructive) |
| `eh` | Edit home username for selected entries |
| `s` | Deploy (setup) selected files on the current system |
| `cl` / `cc` | Clean database — sync entries with physical files |
| `t` | Return to File Browser |

---

## Modes

### Normal Mode

The default mode. Navigate, toggle selections, and run commands.

### Select Mode (`v`)

Activates a visual range selector. Moving the cursor while in Select Mode highlights a range of files. Pressing `v` or `ESC` to exit commits the highlighted range as the current selection.

### Filter Mode (`/`)

A live regex filter overlaid at the bottom of the screen. Type a Python regular expression; the list updates in real time. Press `ESC`, `Enter`, or `Space` to return to Normal Mode. The filter clears automatically when you change directories, or manually with `x`.

---

## Operations reference

### Add files (`a`)

Moves the selected file from its current location into `dots/` and places a symlink back at the original path. If the file was already registered but has drifted (e.g. the symlink was removed), the existing database copy is moved to `remove/` before the new file takes its place.

### Restore (`r`)

Removes entries from the database and moves the physical files back to their original system paths. The symlink is replaced by the real file.

### Delete (`d`)

Removes entries from the database and moves the corresponding files to `remove/`. The symlink at the original path is severed. No data is lost.

### Edit home path (`eh`)

Prompts for a new username and duplicates the selected entries under the new home path. Useful for deploying the same configs for a different user. The original entries are left untouched.

### Setup (`s`)

Creates symlinks on the system at the exact paths stored in the database. Skips any path where a file already exists — clear conflicts manually before running. Paths must point to a home directory that exists on the current machine.

### Clean database (`cl` / `cc`)

Reconciles the database with physical storage:
- Entries with no matching file in `dots/` are purged from the database.
- Files in `dots/` not tracked in the database are moved to `remove/`.

---

## Theming

Pass a TOML file with `-t` to customize colors. Each key maps to `[foreground, background]` using [ANSI 256 color codes](https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797). Use `-1` to inherit the terminal default.

```toml
# theme.toml — all values are optional, unset keys fall back to defaults

Directory = [105,  -1]   # color of directory entries
Selected  = [ -1,  34]   # selected file highlight
Warning   = [124,  -1]   # warning messages
Note      = [220,  -1]   # informational messages
Help      = [ -1, 240]   # help bar background
Accent    = [105, 240]   # accented text in help bar
PreSelect = [ -1,  34]   # visual range highlight (before committing selection)
NormalMod = [ -1, 240]   # mode indicator: Normal
VisualMod = [ -1, 124]   # mode indicator: Select
FilterMod = [ -1,  34]   # mode indicator: Filter
```

Any key you omit stays at the default value. A malformed TOML file causes Dotter to silently fall back to all defaults.
