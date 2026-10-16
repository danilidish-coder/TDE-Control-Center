"""Compatibility import; implementation lives in app.features.receipts.page."""
import sys as _sys
from importlib import import_module as _import_module
_sys.modules[__name__] = _import_module("app.features.receipts.page")
