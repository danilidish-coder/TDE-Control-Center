# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
resources = root / 'resources'

datas = [
    (str(resources / 'Anafora_base.docx'), 'resources'),
    (str(resources / 'Fine_Protocol_Base.xlsx'), 'resources'),
    (str(resources / 'Master_Template_Arnisi.docx'), 'resources'),
    (str(resources / 'VAS_base.docx'), 'resources'),
    (str(resources / 'periodicals_profile.json'), 'resources'),
    (str(resources / 'police_emblem.jpeg'), 'resources'),
    (str(resources / 'police_emblem.ico'), 'resources'),
]

a = Analysis(
    ['control_center_autonomous.py'],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=['pythoncom','pywintypes','win32com','win32com.client'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='TDE_Control_Center',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    console=False,
    icon=str(resources / 'police_emblem.ico'),
)
