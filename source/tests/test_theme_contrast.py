from app.ui.theme import DARK, LIGHT, stylesheet


def test_dark_theme_explicitly_styles_lists_and_combo_popups():
    qss = stylesheet(DARK)
    assert "QListWidget, QListView, QTreeView, QAbstractItemView" in qss
    assert "background: #0b263a; color: #f5f9ff;" in qss
    assert "selection-background-color: #2c9ce8; selection-color: white;" in qss
    assert "QComboBox QAbstractItemView::item:selected" in qss
    assert "QMenu::item:selected" in qss


def test_light_theme_sidebar_has_real_contrast():
    qss = stylesheet(LIGHT)
    assert "stop:0 #edf4f9" in qss
    assert "stop:1 #d8e7f1" in qss
    assert "color: #0b2035;" in qss
    assert "stop:0 #e7f1f7" in qss
    assert "stop:1 #cbdfea" in qss
    assert "QPushButton[navButton=\"true\"]:checked" in qss
    assert "color: white;" in qss


def test_dark_sidebar_remains_high_contrast():
    qss = stylesheet(DARK)
    assert "stop:0 #0d2c43" in qss
    assert "stop:1 #071724" in qss
    assert "color: #f5f9ff;" in qss
