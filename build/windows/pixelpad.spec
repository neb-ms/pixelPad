# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None

spec_dir = Path(globals().get("SPECPATH", ".")).resolve()
project_root = (spec_dir / ".." / "..").resolve()

fonts_dir = project_root / "fonts"
pics_dir = project_root / "pics"

datas = []
if fonts_dir.exists():
    datas.append((str(fonts_dir), "fonts"))
if pics_dir.exists():
    datas.append((str(pics_dir), "pics"))


a = Analysis(
    [str(project_root / 'main.py')],
    pathex=[str(project_root)],
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
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PixelPad',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
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
    upx=True,
    upx_exclude=[],
    name='PixelPad',
)
