from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer, Qt, QSize
from PySide6.QtGui import QColor, QIcon, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QToolButton, QVBoxLayout, QWidget
)

from app.core.db import Database
from app.core.paths import db_path, resource_path
from app.services.backup import backup_database
from app.services.receipts import ReceiptService
from app.services.fines import FineService
from app.services.refusals import RefusalService
from app.services.daily_activity import DailyActivityService
from app.services.periodicals import PeriodicalsService
from app.services.pending import PendingService
from app.ui.dialogs import StartShiftDialog
from app.ui.person_archive import PersonArchivePage
from app.ui.receipts_page import ReceiptsPage
from app.ui.fines_page import FinesPage
from app.ui.refusals_page import RefusalsPage
from app.ui.daily_activity import DailyActivityPage
from app.ui.periodicals_page import PeriodicalsPage
from app.ui.shift_reports import ShiftReportsPage
from app.ui.theme import DARK, LIGHT, stylesheet
from app.ui.widgets import Card


def _lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _metallic_emblem_image(path) -> QImage:
    """Keep the official emblem geometry, but map all visible colours to metallic olive-grey."""
    image = QImage(str(path)).convertToFormat(QImage.Format.Format_ARGB32)
    if image.isNull():
        return image
    stops = (
        (0.0, (26, 27, 22)),
        (0.28, (58, 59, 42)),
        (0.62, (108, 106, 81)),
        (1.0, (178, 180, 168)),
    )
    for y in range(image.height()):
        for x in range(image.width()):
            c = image.pixelColor(x, y)
            if c.alpha() == 0:
                continue
            lum = (0.2126 * c.red() + 0.7152 * c.green() + 0.0722 * c.blue()) / 255.0
            lum = max(0.0, min(1.0, (lum - 0.5) * 1.16 + 0.5))
            for i in range(len(stops) - 1):
                x0, c0 = stops[i]
                x1, c1 = stops[i + 1]
                if lum <= x1:
                    rgb = _lerp_color(c0, c1, (lum - x0) / max(1e-6, x1 - x0))
                    break
            else:
                rgb = stops[-1][1]
            # Subtle top-left illumination makes the badge itself look raised.
            light = 1.0 + 0.055 * ((1.0 - x / max(1, image.width() - 1)) + (1.0 - y / max(1, image.height() - 1)) - 1.0)
            rgb = tuple(max(0, min(205, round(v * light))) for v in rgb)
            image.setPixelColor(x, y, QColor(*rgb, c.alpha()))
    return image


class FloatingHeaderLabel(QLabel):
    """Metallic WordArt-style title: grey bevel, visible extrusion and floating shadow."""
    def __init__(self, text: str, object_name: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName(object_name)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setContentsMargins(8, 2, 18, 9)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 178))
        self.setGraphicsEffect(shadow)

    def sizeHint(self) -> QSize:
        base = super().sizeHint()
        return QSize(base.width() + 28, base.height() + 14)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        fm = self.fontMetrics()
        baseline = (self.height() - fm.height()) / 2 + fm.ascent() - 1
        path = QPainterPath()
        path.addText(8, baseline, self.font(), self.text())

        # Visible grey extrusion: the letters project above the panel instead of lying flat.
        for dx, dy, shade in ((6, 6, 34), (5, 5, 41), (4, 4, 50), (3, 3, 60), (2, 2, 70)):
            painter.save()
            painter.translate(dx, dy)
            painter.fillPath(path, QColor(shade, shade + 1, max(26, shade - 10), 238))
            painter.restore()

        bounds = path.boundingRect()
        metal = QLinearGradient(0, bounds.top(), 0, bounds.bottom())
        metal.setColorAt(0.00, QColor(242, 245, 246))
        metal.setColorAt(0.24, QColor(188, 195, 199))
        metal.setColorAt(0.52, QColor(98, 108, 116))
        metal.setColorAt(0.76, QColor(156, 164, 169))
        metal.setColorAt(1.00, QColor(222, 226, 228))
        painter.fillPath(path, metal)
        painter.strokePath(path, QPen(QColor(52, 54, 47), 1.35))

        painter.save()
        painter.translate(-0.8, -0.8)
        painter.strokePath(path, QPen(QColor(232, 233, 225, 160), 0.7))
        painter.restore()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        backup_database(db_path())
        self.receipts = ReceiptService(self.db)
        self.fines = FineService(self.db)
        self.refusals = RefusalService(self.db)
        self.daily = DailyActivityService(self.db)
        self.periodicals = PeriodicalsService()
        self.pending = PendingService(self.db, self.fines, self.refusals, self.daily)
        self.setWindowTitle("ΕΛΛΗΝΙΚΗ ΑΣΤΥΝΟΜΙΑ — Τ.Δ.Ε. ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ")
        self.resize(1540, 900)
        self.setMinimumSize(1180, 780)
        self.theme_name = self.db.get_preference("theme", "dark")

        root = QWidget(); root.setObjectName("Root"); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(7,7,7,7); outer.setSpacing(8)

        top = QFrame(); top.setObjectName("TopBar"); top.setMinimumHeight(148)
        top_shadow = QGraphicsDropShadowEffect(top); top_shadow.setBlurRadius(34); top_shadow.setOffset(0, 7); top_shadow.setColor(Qt.black); top.setGraphicsEffect(top_shadow)
        tl = QHBoxLayout(top); tl.setContentsMargins(24,16,24,16)
        self.police_emblem = QLabel(); self.police_emblem.setObjectName("PoliceEmblem"); self.police_emblem.setFixedSize(138,138)
        emblem_pixmap = QPixmap(str(resource_path("police_emblem_user.png")))
        if not emblem_pixmap.isNull():
            self.police_emblem.setPixmap(emblem_pixmap.scaled(130,130,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        self.police_emblem.setAlignment(Qt.AlignCenter)
        emblem_shadow = QGraphicsDropShadowEffect(self.police_emblem); emblem_shadow.setBlurRadius(26); emblem_shadow.setOffset(2,8); emblem_shadow.setColor(QColor(0,0,0,185)); self.police_emblem.setGraphicsEffect(emblem_shadow)
        tl.addWidget(self.police_emblem); tl.addSpacing(18)
        titlebox = QVBoxLayout(); titlebox.setSpacing(3)
        title = self._raised_header_label("ΔΙΕΥΘΥΝΣΗ ΑΣΤΥΝΟΜΙΑΣ ΦΛΩΡΙΝΑΣ", "HeaderLine1")
        unit = self._raised_header_label("ΤΜΗΜΑ ΔΙΑΒΑΤΗΡΙΑΚΟΥ ΕΛΕΓΧΟΥ ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ", "HeaderLine2")
        center = self._raised_header_label("ΚΕΝΤΡΟ ΕΛΕΓΧΟΥ ΑΞΙΩΜΑΤΙΚΟΥ ΥΠΗΡΕΣΙΑΣ", "HeaderLine3")
        titlebox.addWidget(title); titlebox.addWidget(unit); titlebox.addWidget(center)
        tl.addLayout(titlebox,1)
        self.greece_watermark = QLabel(); self.greece_watermark.setObjectName("GreeceWatermark"); self.greece_watermark.setFixedSize(175,125)
        gp = QPixmap(str(resource_path("skin_greece.svg")))
        if not gp.isNull(): self.greece_watermark.setPixmap(gp.scaled(168,120,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        self.greece_watermark.setAlignment(Qt.AlignCenter); tl.addWidget(self.greece_watermark)
        self.clock = QLabel(); tl.addWidget(self.clock)
        self.theme_btn = QToolButton(); self.theme_btn.clicked.connect(self.toggle_theme); tl.addWidget(self.theme_btn)
        outer.addWidget(top)
        header_glow = QFrame(); header_glow.setObjectName("HeaderGlow"); header_glow.setFixedHeight(3); outer.addWidget(header_glow)

        body = QHBoxLayout(); body.setSpacing(10); outer.addLayout(body,1)
        side = QFrame(); side.setObjectName("SidePanel"); side.setFixedWidth(350)
        side_shadow = QGraphicsDropShadowEffect(side); side_shadow.setBlurRadius(30); side_shadow.setOffset(5, 6); side_shadow.setColor(Qt.black); side.setGraphicsEffect(side_shadow)
        sl = QVBoxLayout(side); sl.setContentsMargins(16,16,16,16); sl.setSpacing(10)
        self.shift_status = QLabel(); sl.addWidget(self.shift_status)
        self.shift_detail = QLabel(); self.shift_detail.setWordWrap(True); sl.addWidget(self.shift_detail)
        self.start_btn = QPushButton("ΕΝΑΡΞΗ ΒΑΡΔΙΑΣ"); self.start_btn.setObjectName("Primary"); self.start_btn.clicked.connect(self.start_shift); sl.addWidget(self.start_btn)
        self.close_btn = QPushButton("ΚΛΕΙΣΙΜΟ ΒΑΡΔΙΑΣ"); self.close_btn.setObjectName("Danger"); self.close_btn.clicked.connect(self.close_shift); sl.addWidget(self.close_btn)
        sl.addSpacing(8)
        self.nav_buttons = {}
        nav_icons = {
"fines":"skin_nav_fines.svg", "refusals":"skin_refusals.svg",
            "daily":"skin_nav_daily.svg", "periodics":"skin_periodics.svg",
            "people":"skin_people.svg", "receipts":"skin_nav_receipts.svg"
        }
        for text, page in [
            ("ΠΡΟΣΤΙΜΑ", "fines"), ("ΑΡΝΗΣΕΙΣ", "refusals"), ("ΗΜΕΡΗΣΙΑ ΔΡΑΣΤΗΡΙΟΤΗΤΑ", "daily"),
            ("ΠΕΡΙΟΔΙΚΑ", "periodics"),
            ("ΑΡΧΕΙΟ - ΑΝΑΖΗΤΗΣΗ ΠΡΟΣΩΠΟΥ", "people"),
            ("ΕΙΣΠΡΑΞΕΙΣ ΠΡΟΣΤΙΜΩΝ", "receipts")]:
            b=QPushButton(text)
            b.setProperty("navButton", True)
            b.setIcon(QIcon(str(resource_path(nav_icons[page])))); b.setIconSize(QSize(40,40) if page == "fines" else QSize(35,35))
            b.setCheckable(True)
            b.setAutoExclusive(True)
            self.nav_buttons[page] = b
            b.clicked.connect(lambda checked=False,p=page:self.show_page(p))
            sl.addWidget(b)
        sl.addStretch(1)
        self.pending_btn = QPushButton("ΕΝΗΜΕΡΩΣΗ ΕΚΚΡΕΜΩΝ"); self.pending_btn.setIcon(QIcon(str(resource_path("skin_refresh.svg")))); self.pending_btn.setIconSize(QSize(34,34)); self.pending_btn.clicked.connect(self.retry_pending); sl.addWidget(self.pending_btn)
        self.version_label = QLabel("ΕΚΔΟΣΗ 1.0.13"); self.version_label.setObjectName("VersionLabel"); self.version_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter); sl.addWidget(self.version_label)
        body.addWidget(side)

        self.stack = QStackedWidget(); body.addWidget(self.stack,1)
        self.pages = {}
        self.pages["fines"] = FinesPage(self.fines)
        self.pages["refusals"] = RefusalsPage(self.refusals)
        self.pages["daily"] = DailyActivityPage(self.daily)
        self.pages["periodics"] = PeriodicalsPage(self.periodicals)
        self.pages["reports"] = ShiftReportsPage(self.db, self.fines, self.refusals, self.daily)
        self.pages["people"] = PersonArchivePage(self.db)
        self.pages["receipts"] = ReceiptsPage(self.receipts)
        self.pages["people"].useInFines.connect(lambda x: (self.pages["fines"].apply_person(x), self.stack.setCurrentWidget(self.pages["fines"])))
        self.pages["people"].useInRefusals.connect(lambda x: (self.pages["refusals"].apply_person(x), self.stack.setCurrentWidget(self.pages["refusals"])))
        for p in self.pages.values(): self.stack.addWidget(p)
        self.stack.currentChanged.connect(self._sync_active_nav)
        self._sync_active_nav(self.stack.currentIndex())

        self.timer=QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(1000)
        self.apply_theme(); self.refresh_shift(); self.refresh_pending(); self.tick()

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

    def refresh_shift(self):
        row=self.db.get_open_shift()
        if row:
            self.shift_status.setText("● ΕΝΕΡΓΗ ΒΑΡΔΙΑ"); self.shift_status.setObjectName("StatusOpen")
            identity = " · ".join(x for x in (row["officer_rank_full"], row["officer_agms"], row["officer_name"]) if x)
            self.shift_detail.setText(f"{identity}\nΈναρξη: {row['started_at'].replace('T',' ')}")
        else:
            self.shift_status.setText("○ ΧΩΡΙΣ ΕΝΕΡΓΗ ΒΑΡΔΙΑ"); self.shift_status.setObjectName("StatusClosed")
            self.shift_detail.setText("Δεν έχει ξεκινήσει βάρδια.")
        self.start_btn.setEnabled(row is None)
        self.close_btn.setEnabled(row is not None)
        self.shift_status.style().unpolish(self.shift_status); self.shift_status.style().polish(self.shift_status)

    def start_shift(self):
        dlg=StartShiftDialog(self)
        if dlg.exec():
            try:
                officer_name = f"{dlg.surname.text().strip()} {dlg.name.text().strip()}".strip()
                self.db.start_shift(
                    officer_name,
                    officer_agms=dlg.agms.text(),
                    officer_rank_short=dlg.rank.text(),
                    officer_rank_full=dlg.rank.text(),
                ); self.refresh_shift()
                for name in ("fines","refusals","daily"): self.pages[name].refresh()
            except Exception as e: QMessageBox.warning(self,"Έναρξη βάρδιας",str(e))

    def close_shift(self):
        if QMessageBox.question(self,"Κλείσιμο βάρδιας","Να κλείσει η ενεργή βάρδια;") != QMessageBox.Yes: return
        try:
            shift = self.db.get_open_shift()
            if not shift:
                raise ValueError("Δεν υπάρχει ενεργή βάρδια.")
            if not self.pages["daily"].save_current(quiet=True):
                return
            shift_id = self.db.close_shift()
            result = self.pending.archive_shift(shift_id)
            backup_database(db_path())
            self.refresh_shift()
            self.refresh_pending()
            self.pages["fines"].refresh()
            self.pages["refusals"].refresh()
            self.pages["daily"].refresh()
            if result.failed:
                details = "\n".join(f"• {self.pending.label(t)}: {err}" for t, err in result.failed)
                QMessageBox.warning(
                    self, "Κλείσιμο βάρδιας",
                    "Η βάρδια έκλεισε και τα δεδομένα αποθηκεύτηκαν. "
                    "Οι παρακάτω ενημερώσεις έμειναν σε εκκρεμότητα:\n\n" + details
                )
            else:
                QMessageBox.information(
                    self, "Κλείσιμο βάρδιας",
                    "Η βάρδια έκλεισε και οι αναφορές αρχειοθετήθηκαν.\n\n"
                    "Πρόστιμα: ΑΡΧΕΙΟ ΑΝΑΦΟΡΩΝ ΠΡΟΣΤΙΜΩΝ\n"
                    "Αρνήσεις: ΑΡΧΕΙΟ ΒΑΣ\n"
                    "Ημερήσια: ΣΤΑΤΙΣΤΙΚΑ / ΑΡΧΕΙΟ ΗΜΕΡΗΣΙΑΣ."
                )
        except Exception as e: QMessageBox.warning(self,"Κλείσιμο βάρδιας",str(e))

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
