## Recycle bin content viewer

This tools `scanner.py` and `gui.py` can read Windows 10 recycle bin files.

Recycle bin files - files in folders like `C:\$Recycle.Bin\S-1-5-21-429418970-3681832759-2535186036-1003`

## gui.py

Python script that can load generated json file using `scanner.py`.
It can:
- restore files
- Open them
- Delete them
- Copy to clipboard
- Restoring and deleting in batch to original locations or one folder

### Note
- To access that hidden folders all scripts must be run with admin rights.
- Tested only on Windows 10