from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QVBoxLayout


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setAttribute(Qt.WA_StyledBackground, True)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(Qt.black)
        self.setGraphicsEffect(shadow)
        self.layout_box = QVBoxLayout(self)
        self.layout_box.setContentsMargins(18, 18, 18, 18)
        self.layout_box.setSpacing(10)
