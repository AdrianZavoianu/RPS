========================================
  Results Processing System (RPS)
  Version 1.7.0
========================================

WHAT IS RPS?
------------
RPS is a desktop application for processing and visualizing structural
engineering results from ETABS/SAP2000 Excel exports.

Features:
- Import and process story drift, acceleration, and force results
- Interactive building profile plots
- Color-coded data tables
- Project management with database storage
- Modern dark theme interface


SYSTEM REQUIREMENTS
-------------------
- Windows 10 (build 19041+) or Windows 11
- 64-bit (x64) architecture
- 4GB RAM minimum (8GB recommended)
- 500MB disk space + project data storage


QUICK START
-----------
1. Extract this ZIP file to a folder (e.g., C:\Programs\RPS\)
2. Open the extracted folder
3. Double-click RPS.exe to launch
4. No installation needed - fully portable!


FIRST TIME SETUP
----------------
On first launch, RPS will automatically:
- Create a data folder for your projects
- Initialize the project database
- Display the main project window

To start using RPS:
1. Click "New Project" to create a project
2. Click "Import Folder" to batch import Excel files
   OR "Import File" for single file import
3. View results in the interactive table and plot panels


FOLDER STRUCTURE
----------------
RPS/
├── RPS.exe          - Main application (double-click to run)
└── _internal/       - Application libraries (do NOT move or delete)

IMPORTANT: Keep RPS.exe and _internal/ folder together!


TROUBLESHOOTING
---------------
Q: Windows says "Windows protected your PC"
A: This is normal for unsigned apps. Click "More info" → "Run anyway"

Q: Application won't start
A: - Ensure you extracted the ENTIRE folder (not just RPS.exe)
   - Check that _internal/ folder is present
   - Verify you're running Windows 10/11 64-bit

Q: "Missing DLL" errors
A: The _internal/ folder must be in the same location as RPS.exe

Q: Can't create or save projects
A: Ensure you have write permissions to your user folder

Q: Application crashes on startup
A: Try running as administrator (right-click RPS.exe → Run as admin)


SUPPORT
-------
For technical documentation and support:
- See included documentation files
- Contact your structural engineering team lead
- File bug reports through your project tracker


ABOUT
-----
Built with: PyQt6, PyQtGraph, SQLite, Pandas
License: Internal use only
Target: Structural engineering teams

========================================
Copyright (c) 2025 - Structural Engineering
All rights reserved
========================================
