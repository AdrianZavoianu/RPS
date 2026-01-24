# RPS Deployment Guide

This guide explains how to build and deploy the Results Processing System (RPS) as a standalone Windows executable.

---

## Quick Start (For Users)

### System Requirements
- **Operating System**: Windows 10 (build 19041+) or Windows 11
- **Architecture**: 64-bit (x64)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB for application + space for project databases

### Installation
1. Download the latest RPS release (ZIP file)
2. Extract the ZIP file to a folder on your computer (e.g., `C:\Programs\RPS\`)
3. Navigate to the extracted folder
4. Double-click `RPS.exe` to launch the application

**Note**: No installation required! The application is fully portable.

### First Launch
On first launch, RPS will:
- Create a `data/` folder alongside the application for project storage
- Initialize the project catalog database
- Show the main project management window

---

## Building from Source (For Developers)

### Prerequisites
- **Python**: 3.11.x (3.11+ supported)
- **Pipenv**: For dependency management
- **Git**: For version control (optional)

### Build Steps

#### Option 1: Using the Build Script (Recommended)
```batch
# Clone or navigate to the project directory
cd C:\SoftDev\RPS

# Run the automated build script
build.bat
```

The script will:
1. Clean previous builds
2. Install dependencies via pipenv
3. Verify database migrations
4. Build the executable with PyInstaller
5. Create a timestamped ZIP package

**Output**:
- Executable: `dist\RPS\RPS.exe`
- Distribution ZIP: `dist\RPS_Build_YYYYMMDD_HHMM.zip`

#### Option 2: Manual Build
```batch
# Install dependencies
pipenv install --dev

# Clean previous builds (optional)
rmdir /s /q build dist

# Build with PyInstaller
pipenv run python -m PyInstaller --clean RPS.spec

# The executable will be in dist\RPS\RPS.exe
```

### Build Configuration

The build process is controlled by `RPS.spec`. Key configurations:

**Included Resources**:
- `resources/` - Application icons and assets
- `alembic/` - Database migration scripts
- `alembic.ini` - Migration configuration

**Hidden Imports** (required for PyInstaller):
- SQLAlchemy dialects (sqlite)
- Alembic migration tools
- PyQt6 modules (QtPrintSupport, sip)
- Pandas/NumPy internals

**Excluded Modules** (to reduce size):
- matplotlib, IPython, jupyter, tkinter, PIL

**Executable Settings**:
- **Name**: RPS.exe
- **Console**: Disabled (windowed application)
- **UPX Compression**: Enabled
- **Icon**: Currently disabled (requires .ico format)

---

## Distribution

### Creating a Release Package

**Automated** (via build.bat):
```batch
build.bat
# Creates dist\RPS_Build_YYYYMMDD_HHMM.zip
```

**Manual**:
```batch
# Compress the entire RPS folder
powershell -command "Compress-Archive -Path 'dist\RPS\*' -DestinationPath 'RPS_v2.22.0.zip'"
```

### Package Contents
```
RPS/
├── RPS.exe                  # Main executable (18MB)
└── _internal/               # Dependencies and libraries
    ├── alembic/             # Database migrations
    ├── resources/           # Icons and assets
    ├── *.pyd                # Python extension modules
    ├── *.dll                # PyQt6, NumPy, Pandas libraries
    └── base_library.zip     # Python standard library
```

**Total Size**: ~200-300MB (compressed: ~100-150MB)

### Distribution Methods

#### 1. GitHub Releases (Recommended)
```bash
# Tag the release
git tag v2.22.0
git push origin v2.22.0

# Upload ZIP file to GitHub Releases
# Add release notes from internal tracker or PR description
```

#### 2. Network Share (Enterprise)
```
\\fileserver\software\RPS\
├── v2.22.0\
│   └── RPS_v2.22.0.zip
├── latest\              # Symlink to current version
└── README.txt
```

#### 3. Cloud Storage
- Upload to Azure Blob Storage / AWS S3
- Generate shareable download link
- Set appropriate access permissions

---

## Deployment Checklist

### Pre-Deployment
- [ ] Update version number in `pyproject.toml`
- [ ] Capture release notes in internal tracker or PR description
- [ ] Run full test suite: `pipenv run pytest tests/`
- [ ] Verify database migrations: `pipenv run alembic upgrade head`
- [ ] Test application on clean dev machine

### Build
- [ ] Clean previous builds: `rmdir /s /q build dist`
- [ ] Run build script: `build.bat`
- [ ] Verify executable launches: `dist\RPS\RPS.exe`
- [ ] Test core functionality:
  - [ ] Create new project
  - [ ] Import Excel file
  - [ ] View results (table + plot)
  - [ ] Close and reopen project

### Post-Build
- [ ] Generate SHA256 checksum
- [ ] Create distribution ZIP
- [ ] Write release notes
- [ ] Upload to distribution platform
- [ ] Notify users of new release

---

## Troubleshooting

### Build Issues

**Error: "pyinstaller not found"**
```batch
pipenv install --dev
# Ensures PyInstaller is installed
```

**Error: "ModuleNotFoundError" during build**
- Check `hiddenimports` in `RPS.spec`
- Add missing module to the list
- Rebuild

**Error: "Icon must be .ico format"**
- Currently, icon is disabled in `RPS.spec`
- To enable: Convert `resources/icons/RPS_Logo.png` to `.ico`
- Update line 83 in `RPS.spec` with icon path

**Build succeeds but .exe crashes**
- Check `build\RPS\warn-RPS.txt` for warnings
- Run in console mode to see error messages:
  - Change `console=False` to `console=True` in `RPS.spec`
  - Rebuild and check console output

### Deployment Issues

**"Windows protected your PC" warning**
- This is normal for unsigned executables
- Click "More info" → "Run anyway"
- For enterprise: Code-sign the executable

**Application won't start**
- Verify Windows 10/11 (64-bit)
- Check antivirus hasn't quarantined files
- Ensure entire `RPS/` folder is extracted (not just .exe)

**Database errors on launch**
- RPS will auto-create databases
- Verify user has write permissions to `%APPDATA%\RPS\data\`

**Missing DLLs**
- Ensure `_internal/` folder is present next to RPS.exe
- Don't move .exe outside its folder

---

## File Structure

### Source
```
RPS/
├── src/                     # Application source code
├── alembic/                 # Database migrations
├── resources/               # Icons and assets
├── RPS.spec                 # PyInstaller configuration
└── build.bat                # Build script
```

### Build Output
```
dist/
├── RPS/                     # Distributable application
│   ├── RPS.exe              # Main executable
│   └── _internal/           # Dependencies
└── RPS_Build_*.zip          # Distribution package
```

---

## Advanced Topics

### Customizing the Build

**Change executable name**:
Edit `RPS.spec` line 69:
```python
name='RPS',  # Change to desired name
```

**Enable console window** (for debugging):
Edit `RPS.spec` line 76:
```python
console=True,  # Shows console output
```

**Add application icon**:
1. Convert PNG to ICO format (256x256 recommended)
2. Edit `RPS.spec` line 83:
```python
icon='resources/icons/RPS_Logo.ico',
```

**Reduce file size**:
- Remove unused dependencies from `Pipfile`
- Add more modules to `excludes` in `RPS.spec`
- Disable UPX compression (paradoxically can be smaller)

### Code Signing (Optional)

For enterprise deployment, sign the executable:
```batch
# Using Windows SDK signtool
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist\RPS\RPS.exe
```

### Auto-Update Framework (Future)

To implement auto-updates:
1. Add version checker in `src/main.py`
2. Query update server for latest version
3. Download and extract new version
4. Restart application

**Libraries**: PyUpdater, winsparkle, or custom solution

---

## Version History

### v2.22.0 (Current)
- Production-ready release with expanded export/reporting features
- Standalone executable with PyInstaller

### Build Details
- **PyInstaller**: See `Pipfile.lock` for pinned version
- **Python**: 3.11.x
- **Platform**: Windows 10/11 x64
- **Compression**: UPX enabled
- **Size**: ~200-300MB uncompressed

---

## Support

**Build Issues**: Check `build\RPS\warn-RPS.txt` for warnings

**Deployment Questions**: See project documentation:
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Technical details
- [CLAUDE.md](../CLAUDE.md) - Development guide
- [README.md](../README.md) - Project overview

**Bug Reports**: File issues in project tracker

---

**Last Updated**: November 2025
**Status**: Production-ready for internal deployment
