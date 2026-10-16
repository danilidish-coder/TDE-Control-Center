from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget, QMainWindow
from app.bootstrap import create_services
from app.contracts import PageActions
from app.registry import DEFAULT_MODULES, create_pages, validate_modules
from app.workflows import ApplicationWorkflow
from app.features.shifts.controller import ShiftController
from app.ui.header import FloatingHeaderLabel, _lerp_color, _metallic_emblem_image
from app.ui.shell import build_shell
from app.ui.theme import DARK, LIGHT, stylesheet
from app.ui.widgets import Card

APP_VERSION = "1.0.14"


class MainWindow(QMainWindow):
    def __init__(self, services=None, modules=DEFAULT_MODULES):
        super().__init__()
        self.modules = tuple(modules)
        validate_modules(self.modules)
        self.services = services if services is not None else create_services()
        for name in ("db", "receipts", "fines", "refusals", "daily", "periodicals", "pending"):
            setattr(self, name, getattr(self.services, name))
        self.workflow = ApplicationWorkflow(self.services)
        self.shift_controller = ShiftController(self, self.workflow)
        self.setWindowTitle(f"ΕΛΛΗΝΙΚΗ ΑΣΤΥΝΟΜΙΑ — Τ.Δ.Ε. ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ — v{APP_VERSION}")
        self.resize(1540, 900)
        self.setMinimumSize(1180, 780)
        self.theme_name = self.db.get_preference("theme", "dark")
        build_shell(self, APP_VERSION)
        self.pages = create_pages(self.services, self.modules)
        actions = PageActions(self.show_reports, self.refresh_pages, self.refresh_pending)
        for page in self.pages.values():
            page.actions = actions
        self.pages["people"].useInFines.connect(lambda x: (self.pages["fines"].apply_person(x), self.stack.setCurrentWidget(self.pages["fines"])))
        self.pages["people"].useInRefusals.connect(lambda x: (self.pages["refusals"].apply_person(x), self.stack.setCurrentWidget(self.pages["refusals"])))
        for p in self.pages.values(): self.stack.addWidget(p)
        self.stack.currentChanged.connect(self._sync_active_nav)
        self._sync_active_nav(self.stack.currentIndex())
        self.timer=QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(1000)
        self.apply_theme(); self.refresh_shift(); self.refresh_pending(); self.tick()

    def refresh_pages(self, names):
        for name in names:
            page = self.pages.get(name)
            if page is not None and hasattr(page, "refresh"):
                page.refresh()

    def refresh_shift(self):
        return self.shift_controller.refresh_shift()

    def start_shift(self):
        return self.shift_controller.start_shift()

    def close_shift(self):
        return self.shift_controller.close_shift()

    def _sync_active_nav(self, index: int = -1):
        current = self.stack.currentWidget() if hasattr(self, "stack") else None
        for name, button in getattr(self, "nav_buttons", {}).items():
            button.setChecked(self.pages.get(name) is current)

    def _raised_header_label(self, text: str, object_name: str) -> QLabel:
        return FloatingHeaderLabel(text, object_name)

    def _placeholder(self,title,text):
        page=QWidget(); lay=QVBoxLayout(page); c=Card();
        t=QLabel(title); t.setObjectName("Title"); c.layout_box.addWidget(t)
        x=QLabel(text); x.setWordWrap(True); c.layout_box.addWidget(x); lay.addWidget(c); lay.addStretch(1); return page

    def show_reports(self, report_type: str = ""):
        page = self.pages["reports"]
        page.set_report_type(report_type)
        self.stack.setCurrentWidget(page)

    def show_page(self,name):
        page = self.pages[name]
        if hasattr(page, "refresh"):
            try: page.refresh()
            except Exception: pass
        self.stack.setCurrentWidget(page)

    def tick(self): self.clock.setText(datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))

    def refresh_pending(self):
        count = self.pending.count()
        self.pending_btn.setEnabled(count > 0)
        self.pending_btn.setText("ΕΝΗΜΕΡΩΣΗ ΕΚΚΡΕΜΩΝ" if count == 0 else f"ΕΝΗΜΕΡΩΣΗ ΕΚΚΡΕΜΩΝ ({count})")
        self.pending_btn.setToolTip("" if count == 0 else f"Υπάρχουν {count} πραγματικές εκκρεμείς ενημερώσεις.")

    def retry_pending(self):
        if self.pending.count() == 0:
            self.refresh_pending()
            return
        result = self.pending.retry_pending()
        self.refresh_pending()
        if result.failed:
            details = "\n".join(f"• {self.pending.label(t)}: {err}" for t, err in result.failed)
            QMessageBox.warning(self, "Ενημέρωση εκκρεμών", "Παραμένουν εκκρεμότητες:\n\n" + details)
        else:
            QMessageBox.information(self, "Ενημέρωση εκκρεμών", "Οι εκκρεμείς ενημερώσεις ολοκληρώθηκαν.")

    def toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.db.set_preference("theme", self.theme_name); self.apply_theme()

    def apply_theme(self):
        t = DARK if self.theme_name == "dark" else LIGHT
        self.setStyleSheet(stylesheet(t))
        self.theme_btn.setText("☀ ΦΩΤΕΙΝΟ" if self.theme_name == "dark" else "☾ ΣΚΟΤΕΙΝΟ")
