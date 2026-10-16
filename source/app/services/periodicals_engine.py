"""Compatibility import; implementation lives in app.features.periodicals.engine."""
import sys as _sys
from importlib import import_module as _import_module
_sys.modules[__name__] = _import_module("app.features.periodicals.engine")
