# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

hidden_imports = [
    'pandas',
    'matplotlib',
    'scikit-learn',
    'scipy',
    'seaborn',
    'geopandas',
    'contextily',
    'duckdb',
    'sqlalchemy',
    'pyarrow',
    'PyQt6.QtSvg'
]
hidden_imports += collect_submodules('scipy')

app_datas = [
    ('resources', 'resources'),
    ('icons', 'icons'),
    ('src/ui/styles', 'ui/styles'),
]

spatial_datas = (
    collect_data_files('fiona') +
    collect_data_files('pyproj') +
    collect_data_files('geopandas') +
    collect_data_files('contextily')
)

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=app_datas + spatial_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5'],
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
    name='Aletheia',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='DataPlotStudio.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Aletheia',
)
