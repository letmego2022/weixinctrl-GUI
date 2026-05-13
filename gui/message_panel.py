"""
message_panel.py - 消息日志面板
基于 customtkinter，支持 markdown 渲染
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from customtkinter import CTkTextbox
import mistune


class MessagePanel(ctk.CTkFrame):
    COLOR_RECV = "#7289da"
    COLOR_SENT = "#3ba55c"
    COLOR_ERROR = "#f14c4c"
    COLOR_SYSTEM = "#72767d"
    COLOR_TIME = "#72767d"

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self._md = mistune.create_markdown(plugins=["table"])
        self._history_loaded = False
        self._at_bottom = True

        self._setup_ui()

        from v2.bridge import bridge
        bridge.on_message_received(self._on_message_received)
        bridge.on_message_sent(self._on_message_sent)
        bridge.on_polling_status(self._on_polling_started)

    def _setup_ui(self):
        self._textbox = CTkTextbox(self, font=("Cascadia Code", 12), wrap="word",
                                    corner_radius=8)
        self._textbox.configure(state="disabled")
        self._textbox.pack(fill="both", expand=True, padx=4, pady=4)
        self._textbox.tag_config("recv", foreground=self.COLOR_RECV)
        self._textbox.tag_config("sent", foreground=self.COLOR_SENT)
        self._textbox.tag_config("system", foreground=self.COLOR_SYSTEM)
        self._textbox.tag_config("time", foreground=self.COLOR_TIME)

        # 绑定滚动事件
        self._textbox.bind("<Configure>", self._on_configure)

        self._append_system("消息日志已就绪，等待连接...")

    def _on_configure(self, event):
        # 检测是否在底部
        self._at_bottom = (
            self._textbox.yview()[1] >= 0.999
        )

    def _render_markdown(self, text: str) -> str:
        return self._md(text)

    def _escape(self, text):
        return (str(text)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))

    def _append_system(self, text):
        self._textbox.configure(state="normal")
        ts = self._now()
        self._textbox.insert("end", f"[{ts}] ", "time")
        self._textbox.insert("end", f"--- {self._escape(text)} ---", "system")
        self._textbox.insert("end", "\n")
        self._textbox.configure(state="disabled")
        if self._at_bottom:
            self._textbox.see("end")

    def _append_received(self, from_user: str, content: str, timestamp: str):
        self._textbox.configure(state="normal")
        self._textbox.insert("end", f"[{timestamp}] ", "time")
        self._textbox.insert("end", f"◀ {from_user}\n", "recv")
        # markdown 内容
        md_html = self._render_markdown(content)
        # customtkinter 的 CTkTextbox 不支持 HTML，用纯文本
        self._textbox.insert("end", content + "\n", "recv")
        self._textbox.insert("end", "\n")
        self._textbox.configure(state="disabled")
        if self._at_bottom:
            self._textbox.see("end")

    def _append_sent(self, content: str, timestamp: str):
        self._textbox.configure(state="normal")
        self._textbox.insert("end", f"[{timestamp}] ", "time")
        self._textbox.insert("end", "发送 ▶\n", "sent")
        self._textbox.insert("end", content + "\n", "sent")
        self._textbox.insert("end", "\n")
        self._textbox.configure(state="disabled")
        if self._at_bottom:
            self._textbox.see("end")

    @staticmethod
    def _now():
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

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
        self.after(0, lambda: self._append_received(
            data.get("from_user", ""),
            data.get("content", ""),
            data.get("timestamp", self._now())
        ))

    def _on_message_sent(self, content: str):
        self.after(0, lambda: self._append_sent(content, self._now()))