"""
message_panel.py - 消息日志面板 (sci-fi 终端风格)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from customtkinter import CTkTextbox

# 配色
CLR_RECV  = "#00e5ff"
CLR_SENT  = "#00e676"
CLR_ERR   = "#ff5252"
CLR_SYS   = "#626278"
CLR_TIME  = "#484860"
CLR_BAR   = "#1e1e30"
FONT      = ("Cascadia Code", 11)
SEP_W     = 56


class MessagePanel(ctk.CTkFrame):

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="#12121c", **kwargs)

        self._history_loaded = False
        self._at_bottom = True

        self._setup_ui()

        from v2.bridge import bridge
        bridge.on_message_received(self._on_message_received)
        bridge.on_message_sent(self._on_message_sent)
        bridge.on_polling_status(self._on_polling_started)

    def _setup_ui(self):
        self._textbox = CTkTextbox(self, font=FONT, wrap="word",
                                    fg_color="#12121c", text_color="#c8ccd4",
                                    corner_radius=0, border_width=0,
                                    spacing1=2, spacing2=2, spacing3=4)
        self._textbox.configure(state="disabled")
        self._textbox.pack(fill="both", expand=True)

        for tag, fg in [
            ("recv",  CLR_RECV),
            ("sent",  CLR_SENT),
            ("err",   CLR_ERR),
            ("sys",   CLR_SYS),
            ("time",  CLR_TIME),
            ("bar",   CLR_BAR),
        ]:
            self._textbox.tag_config(tag, foreground=fg)

        self._textbox.bind("<Configure>", self._on_configure)
        self._append_system("等待连接…")

    def _on_configure(self, event):
        self._at_bottom = self._textbox.yview()[1] >= 0.999

    @staticmethod
    def _now():
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    # ── 写入原语 ─────────────────────────────────────────────────────────

    def _ins(self, s, tag=None):
        if tag:
            self._textbox.insert("end", s, tag)
        else:
            self._textbox.insert("end", s)

    def _insl(self, s="", tag=None):
        self._ins(s, tag)
        self._ins("\n")

    def _sep(self):
        self._insl("▌" + "─" * SEP_W, "bar")

    # ── 消息渲染 ──────────────────────────────────────────────────────────

    def _check_bottom(self):
        """实时检查是否在底部（每次插入前调用）"""
        self._at_bottom = self._textbox.yview()[1] >= 0.99

    def _scroll_if_bottom(self):
        if self._at_bottom:
            self._textbox.see("end")

    def _append_system(self, text):
        self._textbox.configure(state="normal")
        self._check_bottom()
        self._insl("· " + text, "sys")
        self._insl()
        self._textbox.configure(state="disabled")
        self._scroll_if_bottom()

    def _append_received(self, from_user: str, content: str, timestamp: str):
        self._textbox.configure(state="normal")
        self._check_bottom()

        # 头行：▌ ◀ user · HH:MM:SS
        self._ins("▌", "bar")
        self._ins(" ◀ " + from_user, "recv")
        self._ins("  ·  " + timestamp, "time")
        self._insl()
        self._insl()
        for line in content.split("\n"):
            self._insl("   " + line)
        self._insl()
        self._sep()
        self._insl()
        self._textbox.configure(state="disabled")
        self._scroll_if_bottom()

    def _append_sent(self, content: str, timestamp: str):
        self._textbox.configure(state="normal")
        self._check_bottom()

        # 头行：▌ ▶ HH:MM:SS
        self._ins("▌", "bar")
        self._ins(" ▶ 发送", "sent")
        self._ins("  ·  " + timestamp, "time")
        self._insl()
        self._insl()
        for line in content.split("\n"):
            self._insl("   " + line)
        self._insl()
        self._sep()
        self._insl()
        self._textbox.configure(state="disabled")
        self._scroll_if_bottom()

    # ── 历史加载 ──────────────────────────────────────────────────────────

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

    # ── bridge 回调 ──────────────────────────────────────────────────────

    def _on_message_received(self, data: dict):
        self.after(0, lambda: self._append_received(
            data.get("from_user", ""),
            data.get("content", ""),
            data.get("timestamp", self._now())
        ))

    def _on_message_sent(self, content: str):
        self.after(0, lambda: self._append_sent(content, self._now()))
