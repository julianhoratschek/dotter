# Dotter :chicken:

Linux/Unix Dot-file manager for configuration files

## Intended Use :thought_balloon:

- Bundle config (and other) files in one location :inbox_tray:
- Automatic management of symlinks on your system to have all programs always
  find their respective config-files :paperclip:
- Use a version-management system of your choice to manage all of your
  config-files in one place :recycle:
- Easily reset changes: removing a file from Dotter will move it back to its
  original location :leftwards_arrow_with_hook:


## Usage :wrench:

Dotter has two main-views:

- [File-Manager](#file-manager) (for traversing directories and adding files)
- [Dotter-View](#dotter-view) (for managing registered files: edit, delete, or setup system)


### All Managers :package:

All managers expose these commands:


| Command          | Alias(es)  | Description                                       | Parameters                            |
| ---------------- | ---------- | ------------------------------------------------- | ------------------------------------- |
| quit             | q, exit, e | Closes current View                               |                                       |
| /                |            | Filters current View by regex                     | Regex-String or empty to reset filter |
| !                |            | Switches selection mode to 'select' or 'deselect' |                                       |
| Selection-Syntax |            | See [Selection-Syntax](#selection-syntax)         |                                       |



#### Selection-Syntax :magnet:

- Selects files by ID from the current View
- Comma-Separated list of numbers or ranges
- An asterisk (*) at any place will select all visible files

Example:
```
1, 2,43 5       # Selects files 1, 2, 43 and 5
3, 4 - 8, 9 11  # Selects files 3, 4, 5, 6, 7, 8, 9 and 11
```


### File-Manager :open_file_folder:

Displays files of the current working directory.

Exposes the following commands:


| Command | Alias(es) | Description                                                                                                                                  | Parameters |
| ------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| cd      |           | Changes working directory either to file indicated by ID or to parent directory when '..' is given as parameter                              | ID or '..' |
| add     | a         | Adds all selected files to the database, moves files from their current location to Dotters collection directory and links them via symlinks |            |
| list    | l         | Enters [Dotter-View](#dotter-view)                                                                                                           |            |



### Dotter-View :egg:

Displays all registered config-files.

Exposes the following commands:


| Command | Alias(es)    | Description                                                                                                                                                                                                                                  | Parameters |
| ------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| delete  | d, remove, r | Removes all selected files from the database, removes files from collection directory and moves them back to their original directories                                                                                                      |            |
| edit    | e            | Not implemented yet                                                                                                                                                                                                                          |            |
| setup   | s, create, c | Inserts symlinks to all selected registered files at the locations the files were taken from                                                                                                                                                 |            |
| cleanup |             | Removes all entries in the JSON-database without files in the collection directory and moves all files from the collection directory without correlated entry in the JSON-database into a "remove"-directory inside the collection directory |            |


