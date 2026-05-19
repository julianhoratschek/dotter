# Dotter :chicken:

Cross-Platform Dot-File Manager for configuration files in pure python without
external dependencies.


## Intended Use :thought_balloon:

:inbox_tray: Bundle config (and other) files in one location

:paperclip: Automatic management of symlinks on your system to have all programs always
  find their respective config-files

:blue_heart: Non-Destructive. None of the original files are deleted or removed

:recycle: Use a version-management system of your choice to manage all of your
  config-files in one place

:leftwards_arrow_with_hook: Easily reset changes: removing a file from Dotter will move it back to its original location


## Background :bomb:

- Dotter Allows the user to select files from the system
- Each selected file will be moved to ~/.cache/dotter/dots/ (dots-folder)
- For each file a symlink will be created at its original location
- This allows for:
    - Managing of the dots-folder with a version management system
    - Easily setup your dots-files on a new system using dotters setup-function


## Dependencies :package:

- python >= 13.14
- (optional) NerdFonts for Icons


## Usage :wrench:

Dotter has two main-views:

- [File-Manager](#file-manager-view-open_file_folder) (for traversing directories and adding files)
- [Dotter-View](#dotter-view-egg) (for managing registered files: edit, delete, or setup system)

Execution:

```bash
python main.py
```

### Command Line Options 🚀

|Command|Alias(es)|Description|Parameters|Default|
|-------|---------|-----------|----------|-------|
|-d     |--json-db|Location of a user defined JSON-File. Must be in a directory with a /dots/ folder|<file>.json|~/.cache/dotter/db.json|
|-y     |--all-yes|Don't ask before executing actions||False|


### All Views :cyclone:

All managers expose these commands:


| Command          | Alias(es)  | Description                                       | Parameters                            |
| ---------------- | ---------- | ------------------------------------------------- | ------------------------------------- |
| quit             | q, exit    | Closes current View                               |                                       |
| /                |            | Filters current View by regex                     | Regex-String or empty to reset filter |
| !                |            | Switches selection mode to 'select' or 'deselect' |                                       |
| Selection-Syntax |            | See [Selection-Syntax](#selection-syntax)         |                                       |



#### Selection-Syntax

- Selects files by ID from the current View
- Comma-Separated list of numbers or ranges
- An asterisk (*) at any place will select all visible files

Example:
```
1, 2,43 5       # Selects files 1, 2, 43 and 5
3, 4 - 8, 9 11  # Selects files 3, 4, 5, 6, 7, 8, 9 and 11
```


### File-Manager-View :open_file_folder:

Displays files of the current working directory.

Exposes the following commands:

- **cd \<ID\>|..|\<name\>**
  
  Changes working directory to a file indicated by an ID of the current view, a name in the current list or the parent directory ('..')

- **add|a**

  Adds all selected files to the database and moves the respective files from their location to DB_DIR/dots/. A symlink to the moves
  file will be created at the old location.

- **list|l**

  Enters [Dotter-View](#dotter-view-egg) to work with already registered files


### Dotter-View :egg:

Displays all registered config-files.

Exposes the following commands:

- **delete|d|remove|r \[trash\]**

  Removes all selected entries from the database, removes associated symlinks and moves corresponding files back to their original location.
  This will fail, if the symlink was changed or replaced by another file.
  
  If you don't wish to move files back to their original place, use parameter ```trash```, which will move them to DB_DIR/dots/remove/ instead.
  
- **edit|e \[user|usr \[\<new_name>\]\]**

  Edits all selected entries according to respective subcommands:
  
  - **user|usr \[\<new_name>\]**
  
    Changes home directory of the selected entries either to <new_name>, if given, or to the current users home-directory, if omitted
    
- **setup|s|create|c**

  Creates Symlinks to all selected entries in your file system. This will not overwrite existing files or symlinks.
  
  Be cautious: This will create symlinks at **exactly** the path indicated by the entry. If you want them e.g. in another users home
  directory (e.g. your own), you should use ```edit``` to apply changes first
  
- **cleanup**

  Removes all entries in the JSON-Database without corresponding files in DB_DIR/dots/.
  
  This will also move all files from DB_DIR/dots/ without entries in the JSON-Database to DB_DIR/dots/remove/
