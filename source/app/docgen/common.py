"""Compatibility import; implementation lives in app.shared.documents.common."""
import sys as _sys
from importlib import import_module as _import_module
_sys.modules[__name__] = _import_module("app.shared.documents.common")
