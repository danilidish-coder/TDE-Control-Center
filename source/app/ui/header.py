from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer, Qt, QSize
from PySide6.QtGui import QColor, QIcon, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QToolButton, QVBoxLayout, QWidget
)

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


