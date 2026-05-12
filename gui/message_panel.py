"""
message_panel.py - 消息日志面板
支持 markdown 渲染，简单左对齐布局
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QMenu, QApplication, QAction
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QTextCursor, QFont, QColor
import mistune


class MessagePanel(QWidget):
    COLOR_RECV = '#7289da'
    COLOR_SENT = '#3ba55c'
    COLOR_ERROR = '#f14c4c'
    COLOR_SYSTEM = '#72767d'
    COLOR_TIME = '#72767d'

    FONT_MONO = "Cascadia Code, Consolas, Courier New, monospace"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.timeout.connect(self._scroll_to_bottom)

        self._md = mistune.create_markdown(plugins=['table'])
        self._history_loaded = False

        self._setup_ui()

        from v2.bridge import bridge
        bridge.signal_message_received.connect(self._on_message_received)
        bridge.signal_message_sent.connect(self._on_message_sent)
        bridge.signal_polling_status.connect(self._on_polling_started)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFont(QFont(self.FONT_MONO, 12))
        self._text_edit.setStyleSheet("background: #1e1e1e; border: none; padding: 4px;")
        self._text_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self._text_edit.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self._text_edit)

        self._append_system("消息日志已就绪，等待连接...")

    def _render_markdown(self, text: str) -> str:
        return self._md(text)

    def _append_system(self, text):
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(
            f'<span style="color: {self.COLOR_SYSTEM}">--- {self._escape(text)} ---</span><br>'
        )
        self._schedule_scroll()

    def _append_received(self, from_user: str, content: str, timestamp: str):
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        md_html = self._render_markdown(content)
        cursor.insertHtml(
            f'<span style="color: {self.COLOR_TIME}">[{timestamp}]</span> '
            f'<span style="color: {self.COLOR_RECV}">&#x25B6; {self._escape(from_user)}</span><br>'
            f'<div style="color: {self.COLOR_RECV}; font-size: 13px; line-height: 1.5; margin: 2px 0 8px 0;">{md_html}</div>'
        )
        self._schedule_scroll()

    def _append_sent(self, content: str, timestamp: str):
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        md_html = self._render_markdown(content)
        cursor.insertHtml(
            f'<span style="color: {self.COLOR_TIME}">[{timestamp}]</span> '
            f'<span style="color: {self.COLOR_SENT}">发送 &#x25B6;</span><br>'
            f'<div style="color: {self.COLOR_SENT}; font-size: 13px; line-height: 1.5; margin: 2px 0 8px 0;">{md_html}</div>'
        )
        self._schedule_scroll()

    @staticmethod
    def _time():
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def _escape(text):
        return (str(text)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))

    def _schedule_scroll(self):
        self._scroll_timer.start(50)

    def _scroll_to_bottom(self):
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._text_edit.setTextCursor(cursor)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        copy_action = QAction("复制", self)
        copy_action.triggered.connect(self._copy)
        clear_action = QAction("清空日志", self)
        clear_action.triggered.connect(self._text_edit.clear)
        menu.addAction(copy_action)
        menu.addAction(clear_action)
        menu.exec(self._text_edit.mapToGlobal(pos))

    def _copy(self):
        cursor = self._text_edit.textCursor()
        if cursor.hasSelection():
            QApplication.instance().clipboard().setText(cursor.selectedText())

    def _on_polling_started(self, running: bool):
        if not running or self._history_loaded:
            return
        self._history_loaded = True

        from v2.client import load_chat_log
        log = load_chat_log()
        for m in log.get("messages", []):
            role = m.get("role", "")
            content = m.get("content", "")
            ts = m.get("timestamp", "")[11:]
            name = m.get("name", "")
            text = ""
            if isinstance(content, list):
                text = next((b.get("text", "") for b in content if b.get("type") == "text"), "")
            else:
                text = str(content)
            if not text:
                continue
            if role == "user":
                self._append_received(name, text, ts)
            else:
                self._append_sent(text, ts)

    def _on_message_received(self, data: dict):
        self._append_received(data.get("from_user", ""), data.get("content", ""),
                               data.get("timestamp", self._time()))

    def _on_message_sent(self, content: str):
        self._append_sent(content, self._time())