# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import runpy

root = Path(SPECPATH)
resources = root / 'resources'
identity = runpy.run_path(str(root / 'app' / 'version.py'))
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=identity['WINDOWS_VERSION'], prodvers=identity['WINDOWS_VERSION'], mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
    kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('FileVersion', identity['APP_VERSION']),
        StringStruct('ProductVersion', identity['APP_VERSION']),
        StringStruct('ProductName', 'TDE CONTROL CENTER'),
        StringStruct('FileDescription', 'CONTROL CENTER candidate validation build'),
        StringStruct('OriginalFilename', identity['EXE_NAME'] + '.exe'),
    ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])],
)

datas = [
    (str(resources / 'Anafora_base.docx'), 'resources'),
    (str(resources / 'Fine_Protocol_Base.xlsx'), 'resources'),
    (str(resources / 'Master_Template_Arnisi.docx'), 'resources'),
    (str(resources / 'VAS_base.docx'), 'resources'),
    (str(resources / 'police_emblem.jpeg'), 'resources'),
    (str(resources / 'police_emblem_official.png'), 'resources'),
    (str(resources / 'police_emblem_user.png'), 'resources'),
    (str(resources / 'skin_home.svg'), 'resources'),
    (str(resources / 'skin_fines.svg'), 'resources'),
    (str(resources / 'skin_refusals.svg'), 'resources'),
    (str(resources / 'skin_periodics.svg'), 'resources'),
    (str(resources / 'skin_people.svg'), 'resources'),
    (str(resources / 'skin_reports.svg'), 'resources'),
    (str(resources / 'skin_nav_fines.svg'), 'resources'),
    (str(resources / 'skin_nav_receipts.svg'), 'resources'),
    (str(resources / 'skin_nav_daily.svg'), 'resources'),
    (str(resources / 'skin_nav_reports.svg'), 'resources'),
    (str(resources / 'skin_refresh.svg'), 'resources'),
    (str(resources / 'skin_greece.svg'), 'resources'),
    (str(resources / 'police_emblem.ico'), 'resources'),
    (str(resources / 'periodicals_profile.json'), 'resources'),
    (str(resources / 'combo_arrow_white.svg'), 'resources'),
    (str(resources / 'combo_arrow_dark.svg'), 'resources'),
]

a = Analysis(
    ['main.py'],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=['pythoncom', 'pywintypes', 'win32com', 'win32com.client'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name=identity['EXE_NAME'],
    version=version_info,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(resources / 'police_emblem.ico'),
)
