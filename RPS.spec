# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Results Processing System (RPS)
Builds a standalone Windows executable with all dependencies.
"""

import sys
from pathlib import Path

# Get project root directory
project_root = Path(SPECPATH)
src_path = project_root / 'src'

block_cipher = None

a = Analysis(
    [str(src_path / 'main.py')],
    pathex=[str(src_path)],
    binaries=[],
    datas=[
        # Include resources (icons, etc.)
        (str(project_root / 'resources'), 'resources'),
        # Include alembic migrations
        (str(project_root / 'alembic'), 'alembic'),
        (str(project_root / 'alembic.ini'), '.'),
    ],
    hiddenimports=[
        # SQLAlchemy dialects
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.sql.default_comparator',
        # Alembic
        'alembic',
        'alembic.script',
        'alembic.runtime',
        'alembic.operations',
        # PyQt6 modules
        'PyQt6.QtPrintSupport',
        'PyQt6.sip',
        # Pandas/NumPy backends
        'pandas._libs.tslibs.timedeltas',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.skiplist',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
        'tkinter',
        'PIL',
        'PIL.Image',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RPS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed application (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Note: Icon must be .ico format for Windows. Convert PNG to ICO if needed.
    icon=None,  # TODO: Convert RPS_Logo.png to .ico format
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RPS',
)
