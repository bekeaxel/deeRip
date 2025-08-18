# -*- mode: python ; coding: utf-8 -*-
import sys
import shutil
import os

datas = [
    ("images/song_icon.png", "images"),
    ("config/config_default.yml", "config"),
    ("config/tokens_default.env", "config"),
    ("src/frontend/styles/global.tcss", "src/frontend/styles"),
    ("src/frontend/styles/screens.tcss", "src/frontend/styles"),
    ("src/frontend/styles/widgets.tcss", "src/frontend/styles"),
    ("assets/terminal-launcher", ".")
]

hiddenimports = [
    "textual.widgets._markdown_viewer",
    "textual.widgets._tab",
    "textual.widgets._tab_pane",
    "textual.widgets._collapsible_title",
]

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=["hooks"],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# Detect platform
is_macos = sys.platform == "darwin"
is_windows = sys.platform == "win32"

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="deeRip",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=is_windows,
    disable_windowed_traceback=False,
    argv_emulation=is_macos,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/deeRip.icns" if is_macos else None,
    target_name="deeRip",
)

# macOS app bundle
if is_macos:
    app = BUNDLE(
        exe,
        name="deeRip.app",
        icon="assets/deeRip.icns",
        info_plist={
            'CFBundleName': 'deeRip',
            'CFBundleDisplayName': 'deeRip',
            'CFBundleExecutable': 'terminal-launcher',
            'CFBundleIdentifier': 'com.yourname.deerip',
            'CFBundleShortVersionString': '0.3.0',
            'NSHighResolutionCapable': True,
        },
    )

    # Copy launcher into .app after EXE build
    app_path = os.path.join("dist", "deeRip.app", "Contents", "MacOS", "terminal-launcher")
    shutil.copy("assets/terminal-launcher", app_path)
    os.chmod(app_path, 0o755)