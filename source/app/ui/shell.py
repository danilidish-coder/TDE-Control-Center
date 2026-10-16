"""The original widget layout, kept separate from application composition."""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QToolButton, QVBoxLayout, QWidget)
from app.core.paths import resource_path
from app.registry import navigation_modules


def build_shell(self, app_version):
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
    for module in navigation_modules(self.modules):
        text, page = module.title, module.key
        b=QPushButton(text)
        b.setProperty("navButton", True)
        b.setIcon(QIcon(str(resource_path(module.icon)))); b.setIconSize(QSize(40,40) if page == "fines" else QSize(35,35))
        b.setCheckable(True)
        b.setAutoExclusive(True)
        self.nav_buttons[page] = b
        b.clicked.connect(lambda checked=False,p=page:self.show_page(p))
        sl.addWidget(b)
    sl.addStretch(1)
    self.pending_btn = QPushButton("ΕΝΗΜΕΡΩΣΗ ΕΚΚΡΕΜΩΝ"); self.pending_btn.setIcon(QIcon(str(resource_path("skin_refresh.svg")))); self.pending_btn.setIconSize(QSize(34,34)); self.pending_btn.clicked.connect(self.retry_pending); sl.addWidget(self.pending_btn)
    self.version_label = QLabel(f"ΕΚΔΟΣΗ {app_version}"); self.version_label.setObjectName("VersionLabel"); self.version_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter); sl.addWidget(self.version_label)
    body.addWidget(side)

    self.stack = QStackedWidget(); body.addWidget(self.stack,1)
