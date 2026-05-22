# -*- mode: python ; coding: utf-8 -*-
"""跨平台 PyInstaller 配置文件。

在 macOS 上：pyinstaller cs2_quote.spec   → 产出 dist/CS2行情.app
在 Windows 上：pyinstaller cs2_quote.spec → 产出 dist/CS2行情.exe（单文件）
"""

import sys
from pathlib import Path

block_cipher = None
APP_NAME = "CS2行情"
ROOT = Path(SPECPATH)

# 把 39k 饰品字典随构建产物一起带走（运行时通过 sys._MEIPASS 读取）
datas = [
    (str(ROOT / "base_dict.json"), "."),
]

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)


if sys.platform == "darwin":
    # macOS：先生成 onedir，再包装 .app
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APP_NAME,
    )
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=None,
        bundle_identifier="com.floatinz.cs2quote",
        info_plist={
            "CFBundleDisplayName": APP_NAME,
            "CFBundleName": APP_NAME,
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
            # 不在 Dock 显示也不进 Cmd+Tab；想显示的话改成 0 或删掉
            # "LSUIElement": True,
        },
    )

else:
    # Windows / Linux：单文件 onefile 模式
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
