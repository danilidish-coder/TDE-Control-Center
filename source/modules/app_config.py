from __future__ import annotations
import json, os, sys
from dataclasses import dataclass, asdict
from pathlib import Path


def app_dir() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]


def default_settings_path() -> Path:
    # Prefer a writable file beside the EXE so a copied folder keeps its station settings.
    local = app_dir() / 'tde_autonomous.settings.json'
    try:
        local.parent.mkdir(parents=True, exist_ok=True)
        t=local.parent/'.write_test'; t.write_text('1',encoding='utf-8'); t.unlink(missing_ok=True)
        return local
    except Exception:
        base=Path(os.environ.get('PROGRAMDATA') or os.environ.get('APPDATA') or Path.home())/'TDE_Krystallopigis'
        return base/'tde_autonomous.settings.json'

@dataclass
class AppConfig:
    data_root: str = ''
    fines_archive_root: str = ''
    activity_workbook: str = ''
    officer_name: str = ''
    officer_agms: str = ''
    officer_rank_short: str = 'Ανθ/μου'
    officer_rank_full: str = 'ΑΝΘΥΠΑΣΤΥΝΟΜΟΣ'
    refusal_aa: str = ''
    refusal_year: str = ''
    refusal_protocol_prefix: str = ''
    refusal_protocol_no: str = ''
    periodicals_profile: str = ''

    @classmethod
    def load(cls, path: str|Path|None=None):
        p=Path(path) if path else default_settings_path()
        try:
            raw=json.loads(p.read_text(encoding='utf-8'))
            vals={k:raw.get(k,getattr(cls(),k)) for k in asdict(cls()).keys()}
            return cls(**vals)
        except Exception:
            return cls()

    def save(self,path: str|Path|None=None)->Path:
        p=Path(path) if path else default_settings_path();p.parent.mkdir(parents=True,exist_ok=True)
        tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(asdict(self),ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,p)
        return p
