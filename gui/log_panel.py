"""
log_panel.py - 控制台日志面板
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QComboBox, QLabel, QPushButton
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QTextCursor, QFont


class LogPanel(QWidget):
    """
    控制台日志面板。
    显示 poller 的 DEBUG/INFO/WARN/ERROR 日志，支持等级过滤。
    """

    COLOR_DEBUG = '#808080'   # 灰色
    COLOR_INFO = '#d4d4d4'   # 白色
    COLOR_WARN = '#dcdcaa'   # 黄色
    COLOR_ERROR = '#f14c4c'  # 红色

    LEVEL_ALL = 0
    LEVEL_INFO = 1
    LEVEL_WARN = 2
    LEVEL_ERROR = 3

    FONT_MONO = "Cascadia Code, Consolas, Courier New, monospace"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level_filter = self.LEVEL_ALL
        self._setup_ui()

        # 连接信号
        from v2.bridge import bridge
        bridge.signal_log.connect(self._on_log)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("日志等级:"))
        self._level_combo = QComboBox()
        self._level_combo.addItems(["全部", "信息", "警告", "错误"])
        self._level_combo.setCurrentIndex(0)
        self._level_combo.currentIndexChanged.connect(self._on_level_changed)
        self._level_combo.setFixedWidth(80)
        toolbar.addWidget(self._level_combo)
        toolbar.addStretch()

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._clear)
        clear_btn.setFixedSize(50, 24)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        # 日志文本区
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFont(QFont(self.FONT_MONO, 10))
        self._text_edit.setObjectName("logViewer")
        layout.addWidget(self._text_edit)

    def _on_level_changed(self, index):
        self._level_filter = index

    def _clear(self):
        self._text_edit.clear()

    def _append(self, text: str, level: int):
        if level < self._level_filter:
            return

        color = {
            0: self.COLOR_DEBUG,
            1: self.COLOR_INFO,
            2: self.COLOR_WARN,
            3: self.COLOR_ERROR,
        }.get(level, self.COLOR_INFO)

        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(
            f'<span style="color: {color}">[{self._time()}] {self._escape(text)}</span><br>'
        )
        # 自动滚动
        cursor.movePosition(QTextCursor.End)
        self._text_edit.setTextCursor(cursor)

    @staticmethod
    def _time():
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def _escape(text):
        return (str(text)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>"))

    # ── Qt 槽函数 ────────────────────────────────────────────────────────────

    def _on_log(self, text: str, level: int):
        self._append(text, level)
