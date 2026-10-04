from app.core.paths import resource_path

DARK = {
    "window": "#05111d",
    "panel": "#081a2a",
    "card": "#0b263a",
    "card2": "#173d59",
    "text": "#f5f9ff",
    "muted": "#9eb7ca",
    "accent": "#2c9ce8",
    "accent2": "#0b578d",
    "border": "#367fad",
    "danger": "#a92f43",
    "ok": "#16825f",
    "input": "#061621",
}

LIGHT = {
    "window": "#e7eef5",
    "panel": "#f5f8fb",
    "card": "#ffffff",
    "card2": "#eaf2f8",
    "text": "#0b2035",
    "muted": "#587086",
    "accent": "#1269b5",
    "accent2": "#084b84",
    "border": "#b9ccdc",
    "danger": "#a92f43",
    "ok": "#16795a",
    "input": "#ffffff",
}


def stylesheet(t: dict[str, str]) -> str:
    is_dark = t["window"].lower() == "#05111d"
    arrow_name = "combo_arrow_white.svg" if is_dark else "combo_arrow_dark.svg"
    arrow_path = resource_path(arrow_name).as_posix()

    # Side navigation must remain readable in both themes. The old stylesheet
    # used a permanently dark sidebar while inheriting dark text in light mode.
    side_top = "#0d2c43" if is_dark else "#edf4f9"
    side_mid = "#0a2236" if is_dark else "#e4eef5"
    side_bottom = "#071724" if is_dark else "#d8e7f1"
    side_border = "#326f9c" if is_dark else "#7ca7c4"
    nav_top = "#173b56" if is_dark else "#e7f1f7"
    nav_mid = "#102d43" if is_dark else "#d9e8f2"
    nav_bottom = "#0a2032" if is_dark else "#cbdfea"
    nav_text = "#f5f9ff" if is_dark else "#0b2035"
    nav_border = "#3b82b0" if is_dark else "#779fba"
    nav_bottom_border = "#04111c" if is_dark else "#9eb9ca"
    nav_hover_top = "#205174" if is_dark else "#2c9ce8"
    nav_hover_mid = "#15405e" if is_dark else "#187fc7"
    nav_hover_bottom = "#0d2c44" if is_dark else "#0b578d"
    return f"""
    QMainWindow, QWidget#Root {{ background: {t['window']}; color: {t['text']}; }}
    QWidget {{ color: {t['text']}; font-family: 'Segoe UI'; font-size: 10.5pt; }}
    QDialog {{ background: {t['window']}; color: {t['text']}; }}
    QDialog QLabel {{ color: {t['text']}; font-weight: 700; }}

    QFrame#TopBar {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #173c56, stop:0.22 #102d43, stop:0.58 #091c2b, stop:1 #071521);
        border: 1px solid #3d7ba5; border-radius: 16px;
    }}
    QFrame#HeaderGlow {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 transparent, stop:.18 #27a8ef, stop:.55 #87d8ff, stop:.82 #2195dc, stop:1 transparent); border: none; }}
    QLabel#GreeceWatermark {{ background: transparent; border: none; }}
    QFrame#SidePanel {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {side_top}, stop:.15 {side_mid}, stop:1 {side_bottom});
        border: 1px solid {side_border}; border-radius: 16px;
    }}
    QFrame#Card {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {t['card2']}, stop:0.10 {t['card']}, stop:1 {t['card']});
        border: 1px solid {t['border']}; border-radius: 16px;
    }}


    QWidget#HomeDashboard {{ background: transparent; }}
    QLabel#DashboardHeading {{
        color: {t['text']}; font-family: 'Bahnschrift SemiCondensed', 'Segoe UI Semibold';
        font-size: 17pt; font-weight: 900; letter-spacing: .9px; padding: 6px 0 10px 0;
    }}
    QFrame#DashboardCard {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #193f5b, stop:.24 #112f47, stop:.62 #0a2234, stop:1 #071824);
        border: 1px solid #4aa1d7; border-bottom: 3px solid #03101a; border-radius: 16px;
    }}
    QFrame#DashboardCard:hover {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #183d5c, stop:0.52 #102d46, stop:1 #0b2034);
        border: 2px solid #57b5f3; border-bottom: 3px solid {t['window']};
    }}
    QLabel#DashboardIcon {{
        background: transparent; border: none; font-family: 'Segoe UI Symbol', 'Segoe UI';
        font-size: 48pt; font-weight: 900; padding: 0; min-height: 122px;
    }}
    QLabel#DashboardTitle {{
        background: transparent; border: none; color: {t['text']};
        font-family: 'Bahnschrift SemiCondensed', 'Segoe UI Semibold';
        font-size: 21pt; font-weight: 900; letter-spacing: .8px;
    }}
    QLabel#DashboardDetail {{
        background: transparent; border: none; color: {t['text']};
        font-size: 11pt; font-weight: 520;
    }}

    QLabel#HeaderLine1, QLabel#HeaderLine2, QLabel#HeaderLine3 {{ font-family: 'Bahnschrift SemiCondensed', 'Segoe UI Semibold'; background: transparent; font-weight: 900; letter-spacing: .8px; }}
    QLabel#HeaderLine1 {{ font-size: 22pt; }}
    QLabel#HeaderLine2 {{ font-size: 17pt; }}
    QLabel#HeaderLine3 {{ font-size: 14.5pt; }}
    QLabel#VersionLabel {{ color: {t['muted']}; font-size: 8.5pt; font-weight: 700; letter-spacing: .6px; padding: 3px 2px 0 2px; }}
    QLabel#Title {{ font-size: 20pt; font-weight: 850; }}
    QLabel#SubTitle {{ color: {t['muted']}; font-size: 9.5pt; font-weight: 650; letter-spacing: .4px; }}
    QLabel[fieldLabel="true"] {{ font-weight: 800; color: {t['text']}; min-width: 145px; }}
    QLabel#StatusOpen {{ background: {t['ok']}; color: white; padding: 7px 11px; border: 1px solid {t['border']}; border-radius: 10px; font-weight: 800; }}
    QLabel#StatusClosed {{ background: {t['card2']}; color: {t['muted']}; padding: 7px 11px; border: 1px solid {t['border']}; border-radius: 10px; font-weight: 800; }}

    QPushButton {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {t['card2']}, stop:1 {t['panel']});
        border: 1px solid {t['border']}; border-bottom: 3px solid {t['window']}; border-radius: 12px;
        min-height: 43px; padding: 7px 14px; font-weight: 750; text-align: left;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {t['accent']}, stop:1 {t['accent2']});
        color: white; border-color: {t['accent']}; border-bottom-color: {t['window']};
    }}
    QPushButton:pressed {{ background: {t['accent2']}; border-bottom-width: 1px; padding-top: 9px; }}

    QPushButton[navButton="true"] {{
        min-height: 48px; padding: 5px 14px; font-size: 11.5pt; font-weight: 850;
        color: {nav_text};
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {nav_top}, stop:.48 {nav_mid}, stop:1 {nav_bottom});
        border: 1px solid {nav_border}; border-bottom: 3px solid {nav_bottom_border}; border-radius: 11px;
    }}
    QPushButton[navButton="true"]:hover {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {nav_hover_top}, stop:.48 {nav_hover_mid}, stop:1 {nav_hover_bottom});
        color: white; border-color: #65b8eb;
    }}
    QPushButton[navButton="true"]:checked {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2ebd70, stop:1 #11683f);
        color: white; border: 1px solid #42d982; border-bottom: 3px solid #06351f;
        font-weight: 850;
    }}
    QPushButton[navButton="true"]:checked:hover {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #34c97a, stop:1 #14764a);
        color: white; border-color: #53e391;
    }}
    QPushButton#Primary {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {t['accent']}, stop:1 {t['accent2']});
        color: white; border-color: {t['accent']}; border-bottom: 3px solid {t['window']}; text-align: center;
    }}
    QPushButton#Danger {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {t['danger']}, stop:1 #6f1f2d);
        color: white; border-color: {t['danger']}; border-bottom: 3px solid {t['window']}; text-align: center;
    }}
    QPushButton:disabled {{ color: {t['muted']}; background: {t['panel']}; border-color: {t['border']}; }}

    QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QTextEdit {{
        background: {t['input']}; color: {t['text']}; border: 2px solid {t['border']};
        border-radius: 10px; min-height: 36px; padding: 4px 9px;
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QTextEdit:focus {{
        border: 2px solid {t['accent']}; background: {t['card']};
    }}
    QComboBox {{ padding-right: 34px; }}
    QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 32px; border-left: 1px solid {t['border']}; background: {t['card2']}; border-top-right-radius: 8px; border-bottom-right-radius: 8px; }}
    QComboBox::down-arrow {{ image: url("{arrow_path}"); width: 14px; height: 9px; }}
    QComboBox QAbstractItemView {{
        background: {t['card']}; color: {t['text']}; border: 2px solid {t['accent']};
        selection-background-color: {t['accent']}; selection-color: white; outline: 0; padding: 4px;
    }}
    QComboBox QAbstractItemView::item {{
        color: {t['text']}; background: {t['card']}; min-height: 30px; padding: 4px 8px;
    }}
    QComboBox QAbstractItemView::item:selected {{
        color: white; background: {t['accent']};
    }}

    /* Lists and popup views were previously left to the native Windows
       palette. In dark mode that could produce light text on a light list. */
    QListWidget, QListView, QTreeView, QAbstractItemView {{
        background: {t['card']}; color: {t['text']};
        alternate-background-color: {t['card2']};
        border: 1px solid {t['border']}; border-radius: 8px;
        selection-background-color: {t['accent']}; selection-color: white;
        outline: 0;
    }}
    QListWidget::item, QListView::item, QTreeView::item {{
        color: {t['text']}; min-height: 28px; padding: 4px 7px;
    }}
    QListWidget::item:hover, QListView::item:hover, QTreeView::item:hover {{
        background: {t['card2']}; color: {t['text']};
    }}
    QListWidget::item:selected, QListView::item:selected, QTreeView::item:selected {{
        background: {t['accent']}; color: white;
    }}
    QMenu {{
        background: {t['card']}; color: {t['text']};
        border: 1px solid {t['border']}; padding: 5px;
    }}
    QMenu::item {{ color: {t['text']}; padding: 6px 22px 6px 10px; }}
    QMenu::item:selected {{ background: {t['accent']}; color: white; }}
    QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled, QTextEdit:disabled {{
        background: {t['panel']}; color: {t['muted']}; border-color: {t['border']};
    }}

    QTableWidget {{
        background: {t['card']}; alternate-background-color: {t['card2']}; border: 1px solid {t['border']};
        gridline-color: {t['border']}; border-radius: 10px; selection-background-color: {t['accent']}; selection-color: white;
    }}
    QHeaderView::section {{
        background: {t['panel']}; color: {t['text']}; padding: 8px; border: none;
        border-bottom: 2px solid {t['border']}; font-weight: 800;
    }}
    QToolButton {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {t['card2']}, stop:1 {t['panel']});
        border: 1px solid {t['border']}; border-bottom: 3px solid {t['window']}; border-radius: 11px; padding: 8px 12px; font-weight: 700;
    }}
    QToolButton:hover {{ background: {t['accent']}; color: white; }}

    QTabWidget::pane {{
        border: 1px solid {t['border']}; border-radius: 13px; background: {t['panel']}; top: -1px;
    }}
    QTabBar::tab {{
        background: {t['card2']}; color: {t['muted']}; border: 1px solid {t['border']};
        padding: 10px 18px; min-width: 210px; font-weight: 800; margin-right: 3px;
        border-top-left-radius: 10px; border-top-right-radius: 10px;
    }}
    QTabBar::tab:selected {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {t['accent']}, stop:1 {t['accent2']});
        color: white; border-color: {t['accent']};
    }}
    QTabBar::tab:hover {{ color: white; border-color: {t['accent']}; }}
    """
