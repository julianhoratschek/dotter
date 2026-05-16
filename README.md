# Dotter :chicken:

Linux/Unix Dot-file manager for configuration files in pure python without
external dependencies.


## Intended Use :thought_balloon:

:inbox_tray: Bundle config (and other) files in one location

:paperclip: Automatic management of symlinks on your system to have all programs always
  find their respective config-files

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

- python >= 13.14 (probably also earlier versions)


## Usage :wrench:

Dotter has two main-views:

- [File-Manager](#file-manager-view-open_file_folder) (for traversing directories and adding files)
- [Dotter-View](#dotter-view-egg) (for managing registered files: edit, delete, or setup system)

Execution:

```bash
python main.py
```


### All Views :letter:

All managers expose these commands:


| Command          | Alias(es)  | Description                                       | Parameters                            |
| ---------------- | ---------- | ------------------------------------------------- | ------------------------------------- |
| quit             | q, exit, e | Closes current View                               |                                       |
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


| Command | Alias(es) | Description                                                                                                                                  | Parameters |
| ------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| cd      |           | Changes working directory either to file indicated by ID or to parent directory when '..' is given as parameter                              | ID or '..' |
| add     | a         | Adds all selected files to the database, moves files from their current location to Dotters collection directory and links them via symlinks |            |
| list    | l         | Enters [Dotter-View](#dotter-view-egg)                                                                                                       |            |



### Dotter-View :egg:

Displays all registered config-files.

Exposes the following commands:


| Command | Alias(es)    | Description                                                                                                                                                                                                                                  | Parameters |
| ------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| delete  | d, remove, r | Removes all selected files from the database, removes files from collection directory and moves them back to their original directories                                                                                                      |            |
| edit    | e            | Not implemented yet                                                                                                                                                                                                                          |            |
| setup   | s, create, c | Inserts symlinks to all selected registered files at the locations the files were taken from                                                                                                                                                 |            |
| cleanup |             | Removes all entries in the JSON-database without files in the collection directory and moves all files from the collection directory without correlated entry in the JSON-database into a "remove"-directory inside the collection directory |            |


