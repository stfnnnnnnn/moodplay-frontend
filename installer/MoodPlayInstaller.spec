# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for MoodPlay Installer
# Build with: pyinstaller MoodPlayInstaller.spec

import sys
from PyInstaller.utils.hooks import collect_all

# Collect all pywebview data/binaries/hiddenimports
pywebview_datas, pywebview_binaries, pywebview_hiddenimports = collect_all("webview")

a = Analysis(
    ["installer.py"],
    pathex=[],
    binaries=pywebview_binaries,
    datas=pywebview_datas,
    hiddenimports=pywebview_hiddenimports + [
        "pywebview",
        "pywebview.platforms",
        "pywebview.platforms.edgechromium",
        "pywebview.platforms.winforms",
        "clr",
        "System",
        "System.Windows.Forms",
        "System.Drawing",
        "pythonnet",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MoodPlayInstaller",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # no console window — UI is pywebview
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="icon.ico",  # uncomment and provide an .ico to set a custom icon
    uac_admin=True,     # embed UAC manifest — triggers elevation on launch
)
