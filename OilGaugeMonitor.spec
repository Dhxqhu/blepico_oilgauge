# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['client_gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['bleak.backends.winrt', 'bleak.backends.winrt.scanner', 'bleak.backends.winrt.client', 'matplotlib.backends.backend_tkagg', 'PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'scipy', 'pandas', 'notebook', 'IPython'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='OilGaugeMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
