from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QGroupBox, QCheckBox, QSpinBox, QComboBox,
    QFrame, QPlainTextEdit, QTabWidget, QTableWidget,
    QTableWidgetItem, QLineEdit, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QPalette, QTextCursor, QTextCharFormat, QCursor, QDesktopServices

from datetime import datetime

def build_palette():
    pal = QPalette()
    bg      = QColor(28, 28, 30)
    surface = QColor(22, 22, 24)
    txt     = QColor(224, 224, 224)
    acc     = QColor(58, 123, 213)

    pal.setColor(QPalette.Window,          bg)
    pal.setColor(QPalette.WindowText,      txt)
    pal.setColor(QPalette.Base,            surface)
    pal.setColor(QPalette.AlternateBase,   QColor(34, 34, 36))
    pal.setColor(QPalette.ToolTipBase,     surface)
    pal.setColor(QPalette.ToolTipText,     txt)
    pal.setColor(QPalette.Text,            txt)
    pal.setColor(QPalette.Button,          QColor(42, 42, 44))
    pal.setColor(QPalette.ButtonText,      txt)
    pal.setColor(QPalette.BrightText,      QColor(255, 255, 255))
    pal.setColor(QPalette.Link,            acc)
    pal.setColor(QPalette.Highlight,       acc)
    pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    return pal

MAIN_STYLESHEET = """
/* Base */
QMainWindow, QWidget {
    background-color: #1c1c1e;
    color: #e0e0e0;
    font-family: 'Segoe UI', 'Inter', 'Arial', sans-serif;
    font-size: 10pt;
}

/* GroupBox cards */
QGroupBox {
    border: 1px solid #2e2e30;
    border-radius: 6px;
    margin-top: 18px;
    padding: 12px 10px 10px 10px;
    background-color: #232325;
    font-size: 8.5pt;
    font-weight: 600;
    color: #888;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    background-color: #232325;
}

/* Buttons */
QPushButton {
    background-color: #2a2a2c;
    color: #d0d0d0;
    border: 1px solid #3a3a3c;
    border-radius: 5px;
    padding: 7px 14px;
    font-size: 9.5pt;
}
QPushButton:hover {
    background-color: #333335;
    border-color: #555558;
    color: #f0f0f0;
}
QPushButton:pressed  { background-color: #222224; }
QPushButton:disabled {
    background-color: #222224;
    color: #484848;
    border-color: #2a2a2c;
}

/* Primary button */
QPushButton[primary="true"] {
    background-color: #1faa59;
    color: #ffffff;
    border: 1px solid #2fd06f;
    font-weight: 700;
}
QPushButton[primary="true"]:hover {
    background-color: #27c765;
    border-color: #43ea83;
}
QPushButton[primary="true"]:pressed  { background-color: #168547; }
QPushButton[primary="true"]:disabled {
    background-color: #243428;
    border-color: #243428;
    color: #6b8c74;
}

/* Danger button */
QPushButton[danger="true"] {
    background-color: #8f2424;
    color: #ffffff;
    border: 1px solid #d94b4b;
    font-weight: 700;
}
QPushButton[danger="true"]:hover {
    background-color: #b12f2f;
    border-color: #ff6666;
    color: #ffffff;
}
QPushButton[danger="true"]:pressed  { background-color: #721b1b; }
QPushButton[danger="true"]:disabled {
    color: #8f6f6f;
    border-color: #473030;
    background-color: #2c2020;
}

/* ComboBox */
QComboBox {
    background-color: #2a2a2c;
    color: #d8d8d8;
    border: 1px solid #3a3a3c;
    border-radius: 5px;
    padding: 5px 10px;
    min-height: 26px;
}
QComboBox:hover  { border-color: #555558; }
QComboBox:focus  { border-color: #3a7bd5; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background-color: #252527;
    color: #d8d8d8;
    selection-background-color: #3a7bd5;
    border: 1px solid #3a3a3c;
    outline: none;
    padding: 2px;
}

/* SpinBox */
QSpinBox {
    background-color: #2a2a2c;
    color: #d8d8d8;
    border: 1px solid #3a3a3c;
    border-radius: 5px;
    padding: 5px 8px;
    min-height: 26px;
}
QSpinBox:hover { border-color: #555558; }
QSpinBox:focus { border-color: #3a7bd5; }
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #333335;
    border: none;
    width: 16px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #3a7bd5;
}

/* LineEdit */
QLineEdit {
    background-color: #2a2a2c;
    color: #d8d8d8;
    border: 1px solid #3a3a3c;
    border-radius: 5px;
    padding: 5px 10px;
    min-height: 26px;
    selection-background-color: #3a7bd5;
}
QLineEdit:hover { border-color: #555558; }
QLineEdit:focus { border-color: #3a7bd5; }

/* CheckBox */
QCheckBox {
    color: #c8c8c8;
    font-size: 9.5pt;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    border-radius: 3px;
    border: 1px solid #4a4a4c;
    background-color: #2a2a2c;
}
QCheckBox::indicator:hover   { border-color: #3a7bd5; }
QCheckBox::indicator:checked {
    background-color: #3a7bd5;
    border-color: #3a7bd5;
}

/* ProgressBar */
QProgressBar {
    border: 1px solid #333335;
    border-radius: 4px;
    background-color: #252527;
    color: #888;
    text-align: center;
    font-size: 8pt;
    height: 14px;
}
QProgressBar::chunk {
    background-color: #3a7bd5;
    border-radius: 3px;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #2e2e30;
    border-radius: 6px;
    background-color: #1e1e20;
    top: -1px;
}
QTabBar::tab {
    background-color: #1c1c1e;
    color: #666;
    padding: 8px 18px;
    margin-right: 2px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    font-size: 9pt;
    font-weight: 500;
    border: 1px solid #252527;
    border-bottom: none;
}
QTabBar::tab:selected {
    background-color: #1e1e20;
    color: #e0e0e0;
    border-color: #2e2e30;
    border-bottom: 1px solid #1e1e20;
}
QTabBar::tab:hover:!selected {
    background-color: #252527;
    color: #aaa;
}

/* Table */
QTableWidget {
    background-color: #1e1e20;
    color: #d0d0d0;
    gridline-color: #2a2a2c;
    border: 1px solid #2e2e30;
    border-radius: 4px;
    font-size: 9pt;
    alternate-background-color: #222224;
    selection-background-color: #2d4a70;
}
QTableWidget::item { padding: 5px 8px; }
QTableWidget::item:selected {
    background-color: #2d4a70;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #232325;
    color: #888;
    padding: 6px 10px;
    border: none;
    border-right: 1px solid #2e2e30;
    border-bottom: 1px solid #2e2e30;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* Terminal (QPlainTextEdit) */
QPlainTextEdit {
    background-color: #161618;
    color: #c8c8c8;
    font-family: 'Consolas', 'Cascadia Code', 'Courier New', monospace;
    font-size: 10px;
    border: none;
    padding: 8px;
    selection-background-color: #2d4a70;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #1c1c1e; width: 6px; border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #3a3a3c; border-radius: 3px; min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #4a4a4c; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #1c1c1e; height: 6px; border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #3a3a3c; border-radius: 3px; min-width: 20px;
}
QScrollBar::handle:horizontal:hover { background: #4a4a4c; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* Splitter */
QSplitter::handle { background-color: #2e2e30; }

/* Tooltips */
QToolTip {
    background-color: #2a2a2c;
    color: #d0d0d0;
    border: 1px solid #3a3a3c;
    padding: 4px 8px;
    border-radius: 4px;
}

/* Label misc */
QLabel { background: transparent; border: none; }
"""

# Status badge styles
STATUS_READY_STYLE = """
QLabel {
    color: #888;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 2px;
    border: 1px solid #333;
    border-radius: 4px;
    background-color: #222224;
}
"""

STATUS_ACTIVE_STYLE = """
QLabel {
    color: #c0a030;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 2px;
    border: 1px solid #3a3010;
    border-radius: 4px;
    background-color: #282410;
}
"""

# File label no file selected
FILE_LABEL_EMPTY_STYLE = """
QLabel {
    color: #888;
    font-size: 9pt;
    padding: 6px 10px;
    border: 1px solid #2e2e30;
    border-radius: 4px;
    background-color: #1e1e20;
}
"""

# File label file chosen
FILE_LABEL_SELECTED_STYLE = """
QLabel {
    color: #d0d0d0;
    font-size: 9pt;
    padding: 6px 10px;
    border: 1px solid #2e2e30;
    border-radius: 4px;
    background-color: #1e1e20;
}
"""

# High-contrast terminal stylesheet (always active)
TERMINAL_HC_STYLE = """
QPlainTextEdit {
    background-color: #000000;
    color: #ffffff;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    border: 1px solid #2e2e30;
    border-radius: 4px;
    padding: 8px;
    selection-background-color: #335577;
}
"""

class HoverLinkLabel(QLabel):
    def __init__(self, text, url, parent=None):
        super().__init__(text, parent)
        self.url = url
        self._base_style = "color: #6a6a6a; font-size: 9pt; padding-left: 10px;"
        self._hover_style = "color: #b8b8b8; font-size: 9pt; padding-left: 10px; text-decoration: underline;"
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.setToolTip("")
        self.setStyleSheet(self._base_style)

    def enterEvent(self, event):
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(self._hover_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.setStyleSheet(self._base_style)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl(self.url))
        super().mousePressEvent(event)

class ModernTerminal(QPlainTextEdit):

    def __init__(self):
        super().__init__()
        self._apply_style()
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setMaximumBlockCount(1000)

    def _apply_style(self):
        self.setStyleSheet(TERMINAL_HC_STYLE)

    def add_line(self, text, color="#ffffff"):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.insertText(f"{timestamp} {text}\n", fmt)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

def build_ui(main_window):

    refs = {}   # collects all named references to return

    root = QWidget()
    main_window.setCentralWidget(root)
    root_layout = QVBoxLayout(root)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

    # Titlebar
    titlebar = QFrame()
    titlebar.setFixedHeight(48)
    titlebar.setStyleSheet("""
QFrame {
    background-color: #161618;
    border-bottom: 1px solid #2a2a2c;
}
""")
    tb_layout = QHBoxLayout(titlebar)
    tb_layout.setContentsMargins(20, 0, 20, 0)

    app_name = QLabel("BRUTEFORCER")
    app_name.setStyleSheet("""
QLabel {
    color: #e8e8e8;
    font-size: 12pt;
    font-weight: 700;
    letter-spacing: 3px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}
""")

    author_lbl = HoverLinkLabel("by Medvedeff", "https://github.com/medvedeff-true")
    author_lbl.setStyleSheet("color: #6a6a6a; font-size: 9pt; padding-left: 10px;")

    tb_layout.addWidget(app_name)
    tb_layout.addWidget(author_lbl)
    tb_layout.addStretch()

    status_badge = QLabel("READY")
    status_badge.setFixedSize(72, 24)
    status_badge.setAlignment(Qt.AlignCenter)
    status_badge.setStyleSheet(STATUS_READY_STYLE)
    tb_layout.addWidget(status_badge)
    refs["status_badge"] = status_badge

    root_layout.addWidget(titlebar)

    # Content area
    content = QWidget()
    content.setStyleSheet("QWidget { background-color: #1c1c1e; }")
    content_layout = QHBoxLayout(content)
    content_layout.setContentsMargins(16, 16, 16, 16)
    content_layout.setSpacing(14)

    # LEFT COLUMN
    left_col = QWidget()
    left_col.setFixedWidth(340)
    left_layout = QVBoxLayout(left_col)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(12)

    # File card
    file_card = QGroupBox("Target File")
    fc_layout = QVBoxLayout(file_card)
    fc_layout.setSpacing(6)

    file_row = QHBoxLayout()
    file_label = QLabel("No file selected")
    file_label.setStyleSheet(FILE_LABEL_EMPTY_STYLE)
    file_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    refs["file_label"] = file_label

    browse_btn = QPushButton("Browse")
    browse_btn.setFixedWidth(80)
    browse_btn.clicked.connect(main_window.select_file)
    file_row.addWidget(file_label)
    file_row.addWidget(browse_btn)

    file_info_label = QLabel("Type: —  |  Protection: —")
    file_info_label.setStyleSheet("color: #505050; font-size: 8.5pt; padding: 2px 2px;")
    refs["file_info_label"] = file_info_label

    fc_layout.addLayout(file_row)
    fc_layout.addWidget(file_info_label)
    left_layout.addWidget(file_card)

    # Attack method card
    method_card = QGroupBox("Attack Method")
    mc_layout = QVBoxLayout(method_card)
    mc_layout.setSpacing(8)

    attack_combo = QComboBox()
    attack_combo.addItems(["Dictionary Attack", "Brute-Force", "Mask Attack"])
    attack_combo.currentIndexChanged.connect(main_window.update_attack_method)
    refs["attack_combo"] = attack_combo
    mc_layout.addWidget(attack_combo)

    method_stack = QWidget()
    method_stack.setStyleSheet("QWidget { background-color: transparent; }")
    method_stack_layout = QVBoxLayout(method_stack)
    method_stack_layout.setContentsMargins(0, 0, 0, 0)
    method_stack_layout.setSpacing(0)

    # Dictionary sub-widget
    dict_widget = QWidget()
    dict_widget.setStyleSheet("QWidget { background-color: transparent; }")
    dw_layout = QHBoxLayout(dict_widget)
    dw_layout.setContentsMargins(0, 0, 0, 0)
    dw_layout.setSpacing(6)

    dict_lbl = QLabel("Wordlist:")
    dict_lbl.setStyleSheet("color: #666; font-size: 9pt;")
    dict_lbl.setFixedWidth(58)

    dict_combo = QComboBox()
    refs["dict_combo"] = dict_combo

    dict_browse = QPushButton("…")
    dict_browse.setFixedWidth(34)
    dict_browse.setToolTip("Browse for wordlist file")
    dict_browse.clicked.connect(main_window.browse_custom_dict)

    dw_layout.addWidget(dict_lbl)
    dw_layout.addWidget(dict_combo, 1)
    dw_layout.addWidget(dict_browse)
    refs["dict_widget"] = dict_widget

    # Brute-force sub-widget
    bruteforce_widget = QWidget()
    bruteforce_widget.setStyleSheet("QWidget { background-color: transparent; }")
    bfw = QVBoxLayout(bruteforce_widget)
    bfw.setContentsMargins(0, 0, 0, 0)
    bfw.setSpacing(6)

    len_row = QHBoxLayout()
    len_lbl = QLabel("Length:")
    len_lbl.setStyleSheet("color: #666; font-size: 9pt;")
    len_lbl.setFixedWidth(50)

    min_length = QSpinBox()
    min_length.setRange(1, 20)
    min_length.setValue(1)
    min_length.setFixedWidth(62)
    refs["min_length"] = min_length

    dash_lbl = QLabel("–")
    dash_lbl.setStyleSheet("color: #555; font-size: 10pt;")
    dash_lbl.setAlignment(Qt.AlignCenter)
    dash_lbl.setFixedWidth(14)

    max_length = QSpinBox()
    max_length.setRange(1, 20)
    max_length.setValue(6)
    max_length.setFixedWidth(62)
    refs["max_length"] = max_length

    len_row.addWidget(len_lbl)
    len_row.addWidget(min_length)
    len_row.addWidget(dash_lbl)
    len_row.addWidget(max_length)
    len_row.addStretch()

    cs_row = QHBoxLayout()
    cs_lbl = QLabel("Charset:")
    cs_lbl.setStyleSheet("color: #666; font-size: 9pt;")
    cs_lbl.setFixedWidth(50)

    charset_combo = QComboBox()
    charset_combo.addItems([
        "Lowercase (a–z)",
        "Uppercase (A–Z)",
        "Digits (0–9)",
        "Alphanumeric",
        "All printable",
        "Hex lowercase",
        "Hex uppercase",
        "Custom…",
    ])
    charset_combo.currentIndexChanged.connect(main_window.update_charset_widget)
    refs["charset_combo"] = charset_combo
    cs_row.addWidget(cs_lbl)
    cs_row.addWidget(charset_combo, 1)

    custom_charset_widget = QWidget()
    custom_charset_widget.setStyleSheet("QWidget { background-color: transparent; }")
    ccw = QHBoxLayout(custom_charset_widget)
    ccw.setContentsMargins(0, 0, 0, 0)
    ccw.setSpacing(6)
    cc_lbl = QLabel("Chars:")
    cc_lbl.setStyleSheet("color: #666; font-size: 9pt;")
    cc_lbl.setFixedWidth(50)
    custom_charset_edit = QLineEdit()
    custom_charset_edit.setPlaceholderText("e.g.  abcdef123!@#")
    refs["custom_charset_edit"] = custom_charset_edit
    ccw.addWidget(cc_lbl)
    ccw.addWidget(custom_charset_edit, 1)
    custom_charset_widget.hide()
    refs["custom_charset_widget"] = custom_charset_widget

    bfw.addLayout(len_row)
    bfw.addLayout(cs_row)
    bfw.addWidget(custom_charset_widget)
    refs["bruteforce_widget"] = bruteforce_widget

    # Mask sub-widget
    mask_widget = QWidget()
    mask_widget.setStyleSheet("QWidget { background-color: transparent; }")
    mwl = QVBoxLayout(mask_widget)
    mwl.setContentsMargins(0, 0, 0, 0)
    mwl.setSpacing(6)

    mask_hint = QLabel("?l  ?u  ?d  ?s  ?a  ?h  ?H")
    mask_hint.setStyleSheet("""
QLabel {
    color: #484848;
    font-size: 8pt;
    font-family: 'Consolas', monospace;
    padding: 4px 6px;
    border-left: 2px solid #2e2e30;
}
""")

    mask_row = QHBoxLayout()
    mask_lbl = QLabel("Mask:")
    mask_lbl.setStyleSheet("color: #666; font-size: 9pt;")
    mask_lbl.setFixedWidth(50)
    mask_edit = QLineEdit()
    mask_edit.setPlaceholderText("e.g.  ?u?l?l?d?d?s")
    refs["mask_edit"] = mask_edit
    mask_row.addWidget(mask_lbl)
    mask_row.addWidget(mask_edit, 1)

    mwl.addWidget(mask_hint)
    mwl.addLayout(mask_row)
    refs["mask_widget"] = mask_widget

    for w in [dict_widget, bruteforce_widget, mask_widget]:
        method_stack_layout.addWidget(w)

    mc_layout.addWidget(method_stack)
    left_layout.addWidget(method_card)

    # Statistics card
    stats_card = QGroupBox("Statistics")
    stats_grid = QGridLayout(stats_card)
    stats_grid.setContentsMargins(10, 14, 10, 10)
    stats_grid.setSpacing(5)
    stats_grid.setColumnStretch(1, 1)

    stat_defs = [
        ("Attempts",  "passwords_tried",  "0"),
        ("Speed",     "speed",            "0 pwd/s"),
        ("Elapsed",   "elapsed",          "0 s"),
        ("Current",   "current_password", "—"),
        ("ETA",       "estimated_time",   "Calculating…"),
    ]

    stats_labels = {}
    for i, (name, key, default) in enumerate(stat_defs):
        k_lbl = QLabel(name)
        k_lbl.setStyleSheet(
            "color: #505050; font-size: 8pt; font-weight: 600; letter-spacing: 0.5px;")

        v_lbl = QLabel(default)
        v_lbl.setStyleSheet("""
QLabel {
    color: #d0d0d0;
    font-size: 9pt;
    font-family: 'Consolas', monospace;
    font-weight: 500;
}
""")
        stats_grid.addWidget(k_lbl, i, 0)
        stats_grid.addWidget(v_lbl, i, 1)
        stats_labels[key] = v_lbl

    refs["stats_labels"] = stats_labels
    left_layout.addWidget(stats_card)

    # Progress
    progress_bar = QProgressBar()
    progress_bar.setFixedHeight(14)
    progress_bar.setTextVisible(False)
    refs["progress_bar"] = progress_bar
    left_layout.addWidget(progress_bar)

    # Action buttons
    btn_row = QHBoxLayout()
    btn_row.setSpacing(8)

    start_btn = QPushButton("Start Attack")
    start_btn.setProperty("primary", True)
    start_btn.setFixedHeight(36)
    start_btn.clicked.connect(main_window.start_attack)
    start_btn.setEnabled(False)
    refs["start_btn"] = start_btn

    stop_btn = QPushButton("Stop")
    stop_btn.setProperty("danger", True)
    stop_btn.setFixedHeight(36)
    stop_btn.setFixedWidth(90)
    stop_btn.clicked.connect(main_window.stop_attack)
    stop_btn.setEnabled(False)
    refs["stop_btn"] = stop_btn

    btn_row.addWidget(start_btn)
    btn_row.addWidget(stop_btn)
    left_layout.addLayout(btn_row)
    left_layout.addStretch()

    # RIGHT COLUMN
    right_col = QWidget()
    right_layout = QVBoxLayout(right_col)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(0)

    tab_widget = QTabWidget()
    tab_widget.setDocumentMode(True)
    refs["tab_widget"] = tab_widget

    # Log tab
    terminal = ModernTerminal()
    terminal.setStyleSheet("""
QPlainTextEdit {
    background-color: #000000;
    color: #ffffff;
    font-family: 'Consolas', 'Cascadia Code', 'Courier New', monospace;
    font-size: 16px;
    border: 1px solid #2e2e30;
    border-radius: 4px;
    padding: 10px;
    selection-background-color: #335577;
}
""")
    tab_widget.addTab(terminal, "Log")
    refs["terminal"] = terminal

    # Results tab
    results_outer = QWidget()
    results_outer.setStyleSheet("QWidget { background-color: #1e1e20; }")
    ro_layout = QVBoxLayout(results_outer)
    ro_layout.setContentsMargins(6, 6, 6, 6)

    results_table = QTableWidget()
    results_table.setColumnCount(5)
    results_table.setHorizontalHeaderLabels(["Time", "File", "Type", "Password", "Status"])
    results_table.horizontalHeader().setStretchLastSection(True)
    results_table.setAlternatingRowColors(True)
    results_table.verticalHeader().setVisible(False)
    results_table.setShowGrid(False)
    results_table.setSelectionBehavior(QTableWidget.SelectRows)
    results_table.setEditTriggers(QTableWidget.NoEditTriggers)
    refs["results_table"] = results_table

    ro_layout.addWidget(results_table)
    tab_widget.addTab(results_outer, "Results")

    # Settings tab
    settings_outer = QWidget()
    settings_outer.setStyleSheet("QWidget { background-color: #1e1e20; }")
    so_layout = QVBoxLayout(settings_outer)
    so_layout.setContentsMargins(16, 16, 16, 16)
    so_layout.setSpacing(16)

    perf_section = QGroupBox("Performance")
    ps_layout = QVBoxLayout(perf_section)
    ps_layout.setSpacing(4)

    performant_checkbox = QCheckBox("Multi-core mode (use all CPU threads)")
    performant_checkbox.setChecked(True)
    refs["performant_checkbox"] = performant_checkbox
    ps_layout.addWidget(performant_checkbox)

    perf_hint = QLabel(
        "Maximises throughput by parallelising across all available cores.\n"
        "Increases CPU load significantly."
    )
    perf_hint.setStyleSheet(
        "color: #484848; font-size: 8.5pt; padding-left: 24px; line-height: 160%;")
    perf_hint.setWordWrap(True)
    ps_layout.addWidget(perf_hint)

    so_layout.addWidget(perf_section)
    so_layout.addStretch()

    tab_widget.addTab(settings_outer, "Settings")

    right_layout.addWidget(tab_widget)

    # Assemble
    content_layout.addWidget(left_col)
    content_layout.addWidget(right_col, 1)
    root_layout.addWidget(content)

    # UI refresh timer
    ui_timer = QTimer()
    ui_timer.timeout.connect(main_window.update_ui)
    ui_timer.start(500)
    refs["ui_timer"] = ui_timer

    return refs
