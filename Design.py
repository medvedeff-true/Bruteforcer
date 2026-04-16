from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QGroupBox, QCheckBox, QSpinBox, QComboBox,
    QFrame, QPlainTextEdit, QTabWidget, QTableWidget,
    QTableWidgetItem, QLineEdit, QGridLayout, QSizePolicy,
    QAbstractSpinBox, QStyle,
)
from PySide6.QtCore import Qt, QTimer, QUrl, QPropertyAnimation, QEasingCurve, Property, QObject, QSize
from PySide6.QtGui import QColor, QPalette, QTextCursor, QTextCharFormat, QCursor, QDesktopServices, QPainter, QPen, QBrush

from datetime import datetime

TRANSLATIONS = {
    "en": {
        # Titlebar
        "status_ready": "READY",
        "status_running": "RUNNING",
        # Cards
        "card_target_file": "Target File",
        "card_attack_method": "Attack Method",
        "card_statistics": "Statistics",
        "card_performance": "Performance",
        "card_save": "Save Results",
        # File
        "no_file": "No file selected",
        "browse": "Browse",
        "file_info_default": "Type: —  |  Protection: —",
        # Attack methods
        "method_dictionary": "Dictionary Attack",
        "method_bruteforce": "Brute-Force",
        "method_mask": "Mask Attack",
        # Dictionary
        "lbl_wordlist": "Wordlist:",
        "select_wordlist": "Select wordlist…",
        "no_wordlists": "No wordlists found",
        "default_label": "  [default]",
        # Brute-force
        "lbl_length": "Length:",
        "lbl_charset": "Charset:",
        "lbl_chars": "Chars:",
        "charset_lower": "Lowercase (a–z)",
        "charset_upper": "Uppercase (A–Z)",
        "charset_digits": "Digits (0–9)",
        "charset_alnum": "Alphanumeric",
        "charset_all": "All printable",
        "charset_hex_l": "Hex lowercase",
        "charset_hex_u": "Hex uppercase",
        "charset_custom": "Custom…",
        "custom_placeholder": "e.g.  abcdef123!@#",
        # Mask
        "lbl_mask": "Mask:",
        "mask_placeholder": "e.g.  ?u?l?l?d?d?s",
        # Stats labels
        "stat_attempts": "Attempts",
        "stat_speed": "Speed",
        "stat_elapsed": "Elapsed",
        "stat_current": "Current",
        "stat_eta": "ETA",
        "stat_default_speed": "0 pwd/s",
        "stat_default_eta": "Calculating…",
        # Buttons
        "btn_start": "Start",
        "btn_stop": "Stop",
        # Tabs
        "tab_log": "Log",
        "tab_results": "Results",
        "tab_settings": "Settings",
        # Results table headers
        "col_time": "Time",
        "col_file": "File",
        "col_type": "Type",
        "col_protection": "Protection",
        "col_password": "Password",
        "col_duration": "Duration",
        "col_status": "Status",
        "status_found": "Found",
        "status_not_found": "Not found",
        "btn_clear_log": "Clear log",
        "btn_export": "Export",
        "btn_restore": "Restore",
        # Settings
        "perf_checkbox": "Multi-core mode (use all CPU threads)",
        "perf_hint": "Maximises throughput by parallelising across all available cores.\nIncreases CPU load significantly.",
        "backend_label": "Backend:",
        "backend_cpu": "CPU",
        "backend_gpu": "GPU",
        "backend_hint": "CPU mode is built in and now keeps some logical processors free for Windows.\nGPU mode is optional and may require an external runtime download.",
        "save_checkbox": "Save results to Results.txt",
        "save_hint": "Automatically writes each found password\nto Results.txt next to the program.",
        # Log messages
        "log_select_file": "Select a file first.",
        "log_select_wordlist": "Select a wordlist.",
        "log_enter_mask": "Enter a mask pattern.",
        "log_wordlist_not_found": "Wordlist not found: ",
        "log_attack_started": "Attack started",
        "log_file": "File: ",
        "log_mode_multicore": "Mode: multi-core",
        "log_stopped": "Attack stopped by user.",
        "log_not_found": "Attack completed. Password not found.",
        "log_password_found": "PASSWORD FOUND",
        "confirm_title": "Confirm",
        "confirm_msg": "This file has no password protection. Continue anyway?",
    },
    "ru": {
        # Titlebar
        "status_ready": "ГОТОВ",
        "status_running": "РАБОТАЕТ",
        # Cards
        "card_target_file": "Целевой файл",
        "card_attack_method": "Метод подбора",
        "card_statistics": "Статистика",
        "card_performance": "Производительность",
        "card_save": "Сохранение результатов",
        # File
        "no_file": "Файл не выбран",
        "browse": "Обзор",
        "file_info_default": "Тип: —  |  Защита: —",
        # Attack methods
        "method_dictionary": "Атака по словарю",
        "method_bruteforce": "Перебор",
        "method_mask": "Атака по маске",
        # Dictionary
        "lbl_wordlist": "Словарь:",
        "select_wordlist": "Выберите словарь…",
        "no_wordlists": "Словари не найдены",
        "default_label": "  [по умолч.]",
        # Brute-force
        "lbl_length": "Длина:",
        "lbl_charset": "Символы:",
        "lbl_chars": "Символы:",
        "charset_lower": "Строчные (a–z)",
        "charset_upper": "Заглавные (A–Z)",
        "charset_digits": "Цифры (0–9)",
        "charset_alnum": "Буквы и цифры",
        "charset_all": "Все печатные",
        "charset_hex_l": "Hex строчные",
        "charset_hex_u": "Hex заглавные",
        "charset_custom": "Свои…",
        "custom_placeholder": "напр.  abcdef123!@#",
        # Mask
        "lbl_mask": "Маска:",
        "mask_placeholder": "напр.  ?u?l?l?d?d?s",
        # Stats labels
        "stat_attempts": "Попытки",
        "stat_speed": "Скорость",
        "stat_elapsed": "Прошло",
        "stat_current": "Текущий",
        "stat_eta": "Осталось",
        "stat_default_speed": "0 пар/с",
        "stat_default_eta": "Вычисление…",
        # Buttons
        "btn_start": "Начать",
        "btn_stop": "Стоп",
        # Tabs
        "tab_log": "Журнал",
        "tab_results": "Результаты",
        "tab_settings": "Настройки",
        # Results table headers
        "col_time": "Время",
        "col_file": "Файл",
        "col_type": "Тип",
        "col_password": "Пароль",
        "col_duration": "Время",
        "col_status": "Статус",
        "status_found": "Найден",
        "status_not_found": "Не найден",
        # Settings
        "perf_checkbox": "Многоядерный режим (все потоки CPU)",
        "perf_hint": "Максимизирует производительность за счёт\nраспараллеливания по всем ядрам.\nЗначительно увеличивает нагрузку на CPU.",
        "save_checkbox": "Сохранять результаты в Results.txt",
        "save_hint": "Автоматически записывает каждый найденный\nпароль в файл Results.txt рядом с программой.",
        # Log messages
        "log_select_file": "Сначала выберите файл.",
        "log_select_wordlist": "Выберите словарь.",
        "log_enter_mask": "Введите маску.",
        "log_wordlist_not_found": "Словарь не найден: ",
        "log_attack_started": "Атака начата",
        "log_file": "Файл: ",
        "log_mode_multicore": "Режим: многоядерный",
        "log_stopped": "Атака остановлена пользователем.",
        "log_not_found": "Атака завершена. Пароль не найден.",
        "log_password_found": "ПАРОЛЬ НАЙДЕН",
        "confirm_title": "Подтверждение",
        "confirm_msg": "Файл не защищён паролем. Продолжить?",
    },
}

TRANSLATIONS["en"].update({
    "engine_label": "Engine:",
    "engine_cpu": "CPU",
    "engine_gpu": "GPU",
    "engine_gpu_fallback": "CPU fallback",
    "perf_checkbox": "Multi-core mode (leave system headroom)",
    "perf_hint": (
        "Uses almost all available CPU throughput while reserving some logical processors for Windows.\n"
        "This keeps the app responsive under heavy wordlists and masks."
    ),
    "backend_label": "Backend:",
    "backend_cpu": "CPU",
    "backend_gpu": "GPU",
    "backend_hint": (
        "CPU mode is built in and now keeps some logical processors free for Windows.\n"
        "GPU mode downloads an external backend into ~/Bruteforcer/lib/ when enabled."
    ),
    "gpu_device_label": "GPU device:",
    "gpu_device_placeholder": "Detect GPU devices",
})

TRANSLATIONS["ru"].update({
    "engine_label": "\u0414\u0432\u0438\u0436\u043e\u043a:",
    "engine_cpu": "CPU",
    "engine_gpu": "GPU",
    "engine_gpu_fallback": "CPU fallback",
    "col_protection": "\u0417\u0430\u0449\u0438\u0442\u0430",
    "btn_clear_log": "\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u0436\u0443\u0440\u043d\u0430\u043b",
    "btn_export": "\u042d\u043a\u0441\u043f\u043e\u0440\u0442",
    "btn_restore": "\u0412\u043e\u0441\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c",
    "perf_checkbox": "\u041c\u043d\u043e\u0433\u043e\u044f\u0434\u0435\u0440\u043d\u044b\u0439 \u0440\u0435\u0436\u0438\u043c (\u0441 \u0437\u0430\u043f\u0430\u0441\u043e\u043c \u0434\u043b\u044f \u0441\u0438\u0441\u0442\u0435\u043c\u044b)",
    "perf_hint": (
        "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442 \u043f\u043e\u0447\u0442\u0438 \u0432\u0441\u044e \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0443\u044e \u043c\u043e\u0449\u043d\u043e\u0441\u0442\u044c CPU, "
        "\u043d\u043e \u043e\u0441\u0442\u0430\u0432\u043b\u044f\u0435\u0442 \u0447\u0430\u0441\u0442\u044c \u043b\u043e\u0433\u0438\u0447\u0435\u0441\u043a\u0438\u0445 \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u043e\u0440\u043e\u0432 Windows.\n"
        "\u042d\u0442\u043e \u0441\u043d\u0438\u0436\u0430\u0435\u0442 \u0440\u0438\u0441\u043a \u043f\u0435\u0440\u0435\u0433\u0440\u0443\u0437\u043a\u0438 \u043d\u0430 \u0442\u044f\u0436\u0451\u043b\u044b\u0445 \u0441\u043b\u043e\u0432\u0430\u0440\u044f\u0445 \u0438 \u043c\u0430\u0441\u043a\u0430\u0445."
    ),
    "backend_label": "\u0411\u044d\u043a\u0435\u043d\u0434:",
    "backend_cpu": "CPU",
    "backend_gpu": "GPU",
    "backend_hint": (
        "CPU-\u0440\u0435\u0436\u0438\u043c \u0432\u0441\u0442\u0440\u043e\u0435\u043d \u0432 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0438 \u0442\u0435\u043f\u0435\u0440\u044c "
        "\u043e\u0441\u0442\u0430\u0432\u043b\u044f\u0435\u0442 \u0447\u0430\u0441\u0442\u044c \u043b\u043e\u0433\u0438\u0447\u0435\u0441\u043a\u0438\u0445 "
        "\u043f\u0440\u043e\u0446\u0435\u0441\u0441\u043e\u0440\u043e\u0432 \u0441\u0438\u0441\u0442\u0435\u043c\u0435.\n"
        "GPU-\u0440\u0435\u0436\u0438\u043c \u043f\u0440\u0438 \u0432\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0438 \u0441\u043a\u0430\u0447\u0438\u0432\u0430\u0435\u0442 \u0432\u043d\u0435\u0448\u043d\u0438\u0439 backend \u0432 ~/Bruteforcer/lib/."
    ),
    "gpu_device_label": "\u0412\u0438\u0434\u0435\u043e\u043a\u0430\u0440\u0442\u0430:",
    "gpu_device_placeholder": "\u041e\u0431\u043d\u0430\u0440\u0443\u0436\u0438\u0442\u044c GPU-\u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u0430",
})

# Global current language
_current_lang = "en"

def tr(key):
    """Get translation for key in current language."""
    return TRANSLATIONS.get(_current_lang, TRANSLATIONS["en"]).get(key, key)

def set_language(lang):
    global _current_lang
    _current_lang = lang

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
    color: #f0f0f0;
    font-size: 11pt;
    font-weight: 700;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #3a7bd5;
}
QSpinBox::up-arrow, QSpinBox::down-arrow {
    width: 8px;
    height: 8px;
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

/* CheckBox — overridden by custom widget, these are fallback */
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
QCheckBox::indicator:hover   { border-color: #c8963a; }
QCheckBox::indicator:checked {
    background-color: #c8963a;
    border-color: #c8963a;
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


class LanguageToggle(QWidget):

    def __init__(self, parent=None, on_change=None):
        super().__init__(parent)
        self._is_russian = False
        self._on_change = on_change
        self.setFixedSize(88, 30)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setToolTip("Switch language / Сменить язык")

        # Animation for knob
        self._knob_x = 4
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_step)
        self._anim_dir = 0
        self._anim_target = 4

    @property
    def is_russian(self):
        return self._is_russian

    def set_russian(self, val: bool):
        self._is_russian = val
        self._anim_target = 50 if val else 4
        self._anim_dir = 1 if val else -1
        self._anim_timer.start(10)
        self.update()

    def _animate_step(self):
        step = 4
        if self._anim_dir > 0:
            self._knob_x = min(self._knob_x + step, self._anim_target)
        else:
            self._knob_x = max(self._knob_x - step, self._anim_target)
        self.update()
        if self._knob_x == self._anim_target:
            self._anim_timer.stop()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_russian = not self._is_russian
            self._anim_target = 50 if self._is_russian else 4
            self._anim_dir = 1 if self._is_russian else -1
            self._anim_timer.start(10)
            if self._on_change:
                self._on_change(self._is_russian)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Track background
        track_color = QColor(42, 42, 44)
        p.setBrush(QBrush(track_color))
        p.setPen(QPen(QColor(60, 60, 62), 1))
        p.drawRoundedRect(0, 3, 88, 24, 12, 12)

        # Flag labels
        p.setFont(self.font())
        p.setPen(QColor(180, 180, 180))

        # 🇺🇸 left side
        p.drawText(6, 3, 34, 24, Qt.AlignCenter, "🇺🇸")
        # 🇷🇺 right side
        p.drawText(48, 3, 34, 24, Qt.AlignCenter, "🇷🇺")

        # Knob
        knob_color = QColor(58, 123, 213) if not self._is_russian else QColor(200, 60, 60)
        p.setBrush(QBrush(knob_color))
        p.setPen(QPen(QColor(80, 80, 82), 1))
        p.drawRoundedRect(self._knob_x, 5, 34, 20, 10, 10)

        # Active flag on knob
        p.setPen(QColor(255, 255, 255))
        flag = "🇷🇺" if self._is_russian else "🇺🇸"
        p.drawText(self._knob_x, 5, 34, 20, Qt.AlignCenter, flag)

        p.end()


class PulsingBrowseButton(QPushButton):

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._pulse_alpha = 0
        self._pulse_dir = 1
        self._file_selected = False

        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_step)
        self._pulse_timer.start(30)

    def set_file_selected(self, selected: bool):
        self._file_selected = selected
        if selected:
            self._pulse_timer.stop()
            self._pulse_alpha = 0
        else:
            self._pulse_timer.start(30)
        self.update()

    def _pulse_step(self):
        self._pulse_alpha += self._pulse_dir * 6
        if self._pulse_alpha >= 200:
            self._pulse_alpha = 200
            self._pulse_dir = -1
        elif self._pulse_alpha <= 0:
            self._pulse_alpha = 0
            self._pulse_dir = 1
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._file_selected and self._pulse_alpha > 0:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            glow_color = QColor(31, 170, 89, self._pulse_alpha)
            pen = QPen(glow_color, 2)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 5, 5)
            p.end()


class StyledCheckBox(QWidget):

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._checked = False
        self._hovered = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._indicator = QLabel()
        self._indicator.setFixedSize(18, 18)
        self._indicator.setAlignment(Qt.AlignCenter)

        self._label = QLabel(text)
        self._label.setStyleSheet("color: #c8c8c8; font-size: 9.5pt; background: transparent;")
        self._label.setWordWrap(False)

        layout.addWidget(self._indicator)
        layout.addWidget(self._label)
        layout.addStretch()

        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._update_style()

    def _update_style(self):
        if self._checked:
            style = """
QLabel {
    background-color: #c8843a;
    border: 1px solid #e8a050;
    border-radius: 4px;
    color: white;
    font-size: 9pt;
    font-weight: bold;
}"""
            self._indicator.setStyleSheet(style)
            self._indicator.setText("✓")
        else:
            border_col = "#c8843a" if self._hovered else "#4a4a4c"
            style = f"""
QLabel {{
    background-color: #2a2a2c;
    border: 1px solid {border_col};
    border-radius: 4px;
    color: transparent;
    font-size: 9pt;
}}"""
            self._indicator.setStyleSheet(style)
            self._indicator.setText("")

    def isChecked(self):
        return self._checked

    def setChecked(self, val: bool):
        self._checked = val
        self._update_style()

    def setText(self, text):
        self._label.setText(text)

    def text(self):
        return self._label.text()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._checked = not self._checked
            self._update_style()
            # emit stateChanged-like
            if hasattr(self, '_on_toggle') and self._on_toggle:
                self._on_toggle(self._checked)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        super().leaveEvent(event)

    def connect_toggle(self, fn):
        self._on_toggle = fn

    class _FakeSignal:
        def __init__(self, widget):
            self._widget = widget
            self._callbacks = []
        def connect(self, fn):
            self._callbacks.append(fn)
            self._widget._on_toggle = lambda v: [cb(2 if v else 0) for cb in self._callbacks]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @property
    def stateChanged(self):
        if not hasattr(self, '_fake_signal'):
            self._fake_signal = StyledCheckBox._FakeSignal(self)
            self._on_toggle = None
        return self._fake_signal


class VisibleStepSpinBox(QSpinBox):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.setStyleSheet("QSpinBox { padding-right: 20px; }")

        self._btn_plus = QPushButton("+", self)
        self._btn_plus.setCursor(Qt.PointingHandCursor)
        self._btn_plus.setFocusPolicy(Qt.NoFocus)
        self._btn_plus.clicked.connect(self.stepUp)

        self._btn_minus = QPushButton("-", self)
        self._btn_minus.setCursor(Qt.PointingHandCursor)
        self._btn_minus.setFocusPolicy(Qt.NoFocus)
        self._btn_minus.clicked.connect(self.stepDown)

        btn_style = """
            QPushButton {
                background-color: #333335;
                color: #f2f2f2;
                border: none;
                font-size: 10pt;
                font-weight: 700;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #3a7bd5;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #2f5ea4;
            }
        """
        self._btn_plus.setStyleSheet(btn_style)
        self._btn_minus.setStyleSheet(btn_style)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        btn_w = 16
        half_h = max(1, self.height() // 2)
        x = self.width() - btn_w - 1

        self._btn_plus.setGeometry(x, 1, btn_w, half_h - 1)
        self._btn_minus.setGeometry(x, half_h, btn_w, self.height() - half_h - 1)


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

    def add_separator(self, color="#2e2e30", char="-", width=56):
        self.add_line(char * width, color)

def build_ui(main_window):

    refs = {}

    root = QWidget()
    main_window.setCentralWidget(root)
    root_layout = QVBoxLayout(root)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

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

    author_lbl = HoverLinkLabel("info", "https://github.com/medvedeff-true/Bruteforcer")
    author_lbl.setStyleSheet("color: #6a6a6a; font-size: 9pt; padding-left: 10px;")

    tb_layout.addWidget(app_name)
    tb_layout.addWidget(author_lbl)
    tb_layout.addStretch()

    # Language toggle
    lang_toggle = LanguageToggle(on_change=lambda is_ru: main_window._on_language_change(is_ru))
    refs["lang_toggle"] = lang_toggle
    tb_layout.addWidget(lang_toggle)
    tb_layout.addSpacing(12)

    status_badge = QLabel(tr("status_ready"))
    status_badge.setFixedSize(86, 24)
    status_badge.setAlignment(Qt.AlignCenter)
    status_badge.setStyleSheet(STATUS_READY_STYLE)
    tb_layout.addWidget(status_badge)
    refs["status_badge"] = status_badge

    engine_label = QLabel(f"{tr('engine_label')} {tr('engine_cpu')}")
    engine_label.setStyleSheet(
        "color: #9a9a9a; font-size: 8.5pt; font-family: 'Consolas', monospace; padding-left: 10px;")
    tb_layout.addWidget(engine_label)
    refs["engine_label"] = engine_label

    root_layout.addWidget(titlebar)

    content = QWidget()
    content.setStyleSheet("QWidget { background-color: #1c1c1e; }")
    content_layout = QHBoxLayout(content)
    content_layout.setContentsMargins(16, 16, 16, 16)
    content_layout.setSpacing(14)

    left_col = QWidget()
    left_col.setFixedWidth(340)
    left_layout = QVBoxLayout(left_col)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(12)

    # File card
    file_card = QGroupBox(tr("card_target_file"))
    refs["file_card"] = file_card
    fc_layout = QVBoxLayout(file_card)
    fc_layout.setSpacing(6)

    file_row = QHBoxLayout()
    file_label = QLabel(tr("no_file"))
    file_label.setStyleSheet(FILE_LABEL_EMPTY_STYLE)
    file_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    refs["file_label"] = file_label

    browse_btn = PulsingBrowseButton(tr("browse"))
    browse_btn.setFixedWidth(80)
    browse_btn.clicked.connect(main_window.select_file)
    refs["browse_btn"] = browse_btn

    file_row.addWidget(file_label)
    file_row.addWidget(browse_btn)

    file_info_label = QLabel(tr("file_info_default"))
    file_info_label.setStyleSheet("color: #505050; font-size: 8.5pt; padding: 2px 2px;")
    refs["file_info_label"] = file_info_label

    fc_layout.addLayout(file_row)
    fc_layout.addWidget(file_info_label)
    left_layout.addWidget(file_card)

    # Attack method card
    method_card = QGroupBox(tr("card_attack_method"))
    refs["method_card"] = method_card
    mc_layout = QVBoxLayout(method_card)
    mc_layout.setSpacing(8)

    attack_combo = QComboBox()
    attack_combo.addItems([tr("method_dictionary"), tr("method_bruteforce"), tr("method_mask")])
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

    dict_lbl = QLabel(tr("lbl_wordlist"))
    dict_lbl.setStyleSheet("color: #666; font-size: 9pt;")
    dict_lbl.setFixedWidth(58)
    refs["dict_lbl"] = dict_lbl

    dict_combo = QComboBox()
    refs["dict_combo"] = dict_combo

    dict_browse = QPushButton("…")
    dict_browse.setText("+")
    dict_browse.setIcon(main_window.style().standardIcon(QStyle.SP_DirOpenIcon))
    dict_browse.setIconSize(QSize(14, 14))
    dict_browse.setFixedWidth(44)
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
    len_lbl = QLabel(tr("lbl_length"))
    len_lbl.setStyleSheet("color: #666; font-size: 9pt;")
    len_lbl.setFixedWidth(58)
    refs["len_lbl"] = len_lbl

    min_length = VisibleStepSpinBox()
    min_length.setRange(1, 20)
    min_length.setValue(1)
    min_length.setFixedWidth(62)
    refs["min_length"] = min_length

    dash_lbl = QLabel("–")
    dash_lbl.setStyleSheet("color: #555; font-size: 10pt;")
    dash_lbl.setAlignment(Qt.AlignCenter)
    dash_lbl.setFixedWidth(14)

    max_length = VisibleStepSpinBox()
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
    cs_lbl = QLabel(tr("lbl_charset"))
    cs_lbl.setStyleSheet("color: #666; font-size: 9pt;")
    cs_lbl.setFixedWidth(58)
    refs["cs_lbl"] = cs_lbl

    charset_combo = QComboBox()
    charset_combo.addItems([
        tr("charset_lower"), tr("charset_upper"), tr("charset_digits"),
        tr("charset_alnum"), tr("charset_all"), tr("charset_hex_l"),
        tr("charset_hex_u"), tr("charset_custom"),
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
    cc_lbl = QLabel(tr("lbl_chars"))
    cc_lbl.setStyleSheet("color: #666; font-size: 9pt;")
    cc_lbl.setFixedWidth(58)
    refs["cc_lbl"] = cc_lbl
    custom_charset_edit = QLineEdit()
    custom_charset_edit.setPlaceholderText(tr("custom_placeholder"))
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
    mask_lbl = QLabel(tr("lbl_mask"))
    mask_lbl.setStyleSheet("color: #666; font-size: 9pt;")
    mask_lbl.setFixedWidth(58)
    refs["mask_lbl"] = mask_lbl
    mask_edit = QLineEdit()
    mask_edit.setPlaceholderText(tr("mask_placeholder"))
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
    stats_card = QGroupBox(tr("card_statistics"))
    refs["stats_card"] = stats_card
    stats_grid = QGridLayout(stats_card)
    stats_grid.setContentsMargins(10, 14, 10, 10)
    stats_grid.setSpacing(5)
    stats_grid.setColumnStretch(1, 1)

    stat_defs = [
        ("stat_attempts",  "passwords_tried",  "0"),
        ("stat_speed",     "speed",            tr("stat_default_speed")),
        ("stat_elapsed",   "elapsed",          "0 s"),
        ("stat_current",   "current_password", "—"),
        ("stat_eta",       "estimated_time",   tr("stat_default_eta")),
    ]

    stats_labels = {}
    stats_key_labels = {}
    for i, (name_key, key, default) in enumerate(stat_defs):
        k_lbl = QLabel(tr(name_key))
        k_lbl.setStyleSheet(
            "color: #505050; font-size: 8pt; font-weight: 600; letter-spacing: 0.5px;")
        refs[f"stat_key_{name_key}"] = k_lbl
        stats_key_labels[name_key] = k_lbl

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
    refs["stats_key_labels"] = stats_key_labels
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

    start_btn = QPushButton(tr("btn_start"))
    start_btn.setProperty("primary", True)
    start_btn.setFixedHeight(36)
    start_btn.clicked.connect(main_window.start_attack)
    start_btn.setEnabled(False)
    refs["start_btn"] = start_btn

    stop_btn = QPushButton(tr("btn_stop"))
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

    right_col = QWidget()
    right_layout = QVBoxLayout(right_col)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(0)

    tab_widget = QTabWidget()
    tab_widget.setDocumentMode(True)
    refs["tab_widget"] = tab_widget

    # Log tab
    log_outer = QWidget()
    log_outer.setStyleSheet("QWidget { background-color: #1e1e20; }")
    log_layout = QVBoxLayout(log_outer)
    log_layout.setContentsMargins(6, 6, 6, 6)
    log_layout.setSpacing(6)

    log_toolbar = QHBoxLayout()
    log_toolbar.addStretch()
    clear_log_btn = QPushButton(tr("btn_clear_log"))
    clear_log_btn.setCursor(Qt.PointingHandCursor)
    clear_log_btn.setIcon(main_window.style().standardIcon(QStyle.SP_TrashIcon))
    refs["clear_log_btn"] = clear_log_btn
    log_layout.addLayout(log_toolbar)
    log_toolbar.addWidget(clear_log_btn)

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
    log_layout.addWidget(terminal)
    tab_widget.addTab(log_outer, tr("tab_log"))
    refs["terminal"] = terminal

    # Results tab
    results_outer = QWidget()
    results_outer.setStyleSheet("QWidget { background-color: #1e1e20; }")
    ro_layout = QVBoxLayout(results_outer)
    ro_layout.setContentsMargins(6, 6, 6, 6)

    results_table = QTableWidget()
    results_table.setColumnCount(7)
    results_table.setHorizontalHeaderLabels([
        tr("col_time"), tr("col_file"), tr("col_type"), tr("col_protection"),
        tr("col_password"), tr("col_duration"), tr("col_status"),
    ])
    results_table.horizontalHeader().setStretchLastSection(True)
    results_table.setAlternatingRowColors(True)
    results_table.verticalHeader().setVisible(False)
    results_table.setShowGrid(False)
    results_table.setSelectionBehavior(QTableWidget.SelectRows)
    results_table.setEditTriggers(QTableWidget.NoEditTriggers)
    refs["results_table"] = results_table

    ro_layout.addWidget(results_table)

    results_actions = QHBoxLayout()
    results_actions.addStretch()

    restore_results_btn = QPushButton(tr("btn_restore"))
    restore_results_btn.setCursor(Qt.PointingHandCursor)
    restore_results_btn.setIcon(main_window.style().standardIcon(QStyle.SP_BrowserReload))
    refs["restore_results_btn"] = restore_results_btn
    results_actions.addWidget(restore_results_btn)

    export_results_btn = QPushButton(tr("btn_export"))
    export_results_btn.setCursor(Qt.PointingHandCursor)
    export_results_btn.setIcon(main_window.style().standardIcon(QStyle.SP_DialogSaveButton))
    refs["export_results_btn"] = export_results_btn
    results_actions.addWidget(export_results_btn)

    ro_layout.addLayout(results_actions)
    tab_widget.addTab(results_outer, tr("tab_results"))

    # Settings tab
    settings_outer = QWidget()
    settings_outer.setStyleSheet("QWidget { background-color: #1e1e20; }")
    so_layout = QVBoxLayout(settings_outer)
    so_layout.setContentsMargins(16, 16, 16, 16)
    so_layout.setSpacing(16)

    # Performance section
    perf_section = QGroupBox(tr("card_performance"))
    refs["perf_section"] = perf_section
    ps_layout = QVBoxLayout(perf_section)
    ps_layout.setSpacing(6)

    performant_checkbox = StyledCheckBox(tr("perf_checkbox"))
    performant_checkbox.setChecked(True)
    refs["performant_checkbox"] = performant_checkbox
    ps_layout.addWidget(performant_checkbox)

    backend_row = QHBoxLayout()
    backend_label = QLabel(tr("backend_label"))
    backend_label.setStyleSheet("color: #666; font-size: 9pt;")
    refs["backend_label"] = backend_label
    backend_combo = QComboBox()
    backend_combo.addItems([tr("backend_cpu"), tr("backend_gpu")])
    refs["backend_combo"] = backend_combo
    backend_row.addWidget(backend_label)
    backend_row.addWidget(backend_combo, 1)
    ps_layout.addLayout(backend_row)

    gpu_device_row = QHBoxLayout()
    gpu_device_label = QLabel(tr("gpu_device_label"))
    gpu_device_label.setStyleSheet("color: #666; font-size: 9pt;")
    refs["gpu_device_label"] = gpu_device_label
    gpu_device_combo = QComboBox()
    gpu_device_combo.addItem(tr("gpu_device_placeholder"))
    refs["gpu_device_combo"] = gpu_device_combo
    gpu_device_row.addWidget(gpu_device_label)
    gpu_device_row.addWidget(gpu_device_combo, 1)
    refs["gpu_device_row"] = gpu_device_row
    ps_layout.addLayout(gpu_device_row)

    perf_hint = QLabel(tr("perf_hint"))
    refs["perf_hint"] = perf_hint
    perf_hint.setStyleSheet(
        "color: #484848; font-size: 8.5pt; padding-left: 26px; line-height: 160%;")
    perf_hint.setWordWrap(True)
    ps_layout.addWidget(perf_hint)

    backend_hint = QLabel(tr("backend_hint"))
    refs["backend_hint"] = backend_hint
    backend_hint.setStyleSheet(
        "color: #484848; font-size: 8.5pt; padding-left: 26px; line-height: 160%;")
    backend_hint.setWordWrap(True)
    ps_layout.addWidget(backend_hint)

    so_layout.addWidget(perf_section)

    # Save results section
    save_section = QGroupBox(tr("card_save"))
    refs["save_section"] = save_section
    sv_layout = QVBoxLayout(save_section)
    sv_layout.setSpacing(6)

    save_checkbox = StyledCheckBox(tr("save_checkbox"))
    save_checkbox.setChecked(True)
    refs["save_checkbox"] = save_checkbox
    sv_layout.addWidget(save_checkbox)

    save_hint = QLabel(tr("save_hint"))
    refs["save_hint"] = save_hint
    save_hint.setStyleSheet(
        "color: #484848; font-size: 8.5pt; padding-left: 26px; line-height: 160%;")
    save_hint.setWordWrap(True)
    sv_layout.addWidget(save_hint)

    so_layout.addWidget(save_section)
    so_layout.addStretch()

    tab_widget.addTab(settings_outer, tr("tab_settings"))

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
