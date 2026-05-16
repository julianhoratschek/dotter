# Dotter

Linux/Unix Dot-file manager for configurations

## Intended Use

- Bundle config (and other) files in one location
- Automatic management of symlinks on your system to have all programs always
  find their respective config-files
- Use a version-management system of your choice to manage all of your
  config-files in one place
- Completely non-destructive


## Usage

- Dotter has two main-views:
    - File-Manager (for traversing directories and adding files)
    - Dotter-View (for managing registered files: edit, delete, or setup system)

## All Managers

- All managers expose these commands:

| Command     | Alias(es)  | Description                                       | Parameters                            |
| ----------- | ---------- | ------------------------------------------------- | ------------------------------------- |
| quit        | q, exit, e | Closes current File View                          |                                       |
| /           |            | Filters current view by reges                     | Regex-String or empty to reset filter |
| !           |            | Switches selection mode to 'select' or 'deselect' |                                       |
| <selection> |            | See Selection-Syntax                              |                                       |


### Selection-Syntax

- Selects files by ID from the current view
- Comma-Separated list of numbers or ranges
- An asterisk (*) at any place will select all visible files

Example:
```
1, 2,43 5       # Selects files 1, 2, 43 and 5
3, 4 - 8, 9 11  # Selects files 3, 4, 5, 6, 7, 8, 9 and 11
```

## File-Manager

- Displays files of the current working directory
- Exposes the following commands:

| Command | Alias(es) | Description                                                                                                                                  | Parameters   |
| ------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| cd      | |         | Changes working directory either to file indicated by <id> or to parent directory when '..' is given as parameter                            | <id> or '..' |
| add     | a         | Adds all selected files to the database, moves files from their current location to Dotters collection directory and links them via symlinks |              |
| list    | l         | Enters Dotter View                                                                                                                           |              |


## Dotter-View

- Displays all registered config-files
- Exposes the following commands:

| Command | Alias(es)    | Description                                                                                                                                                                                                                                  | Parameters |
| ------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| delete  | d, remove, r | Removes all selected files from the database, removes files from collection directory and moves them back to their original directories                                                                                                      |            |
| edit    | e            | Not implemented yet                                                                                                                                                                                                                          |            |
| setup   | s, create, c | Inserts symlinks to all selected registered files at the locations the files were taken from                                                                                                                                                 |            |
| cleanup | |            | Removes all entries in the JSON-database without files in the collection directory and moves all files from the collection directory without correlated entry in the JSON-database into a "remove"-directory inside the collection directory |            |
