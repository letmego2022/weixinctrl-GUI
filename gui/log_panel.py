"""
log_panel.py - 控制台日志面板
基于 customtkinter，支持等级过滤
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from customtkinter import CTkTextbox, CTkComboBox, CTkButton, CTkLabel, CTkFrame


class LogPanel(CTkFrame):
    COLOR_DEBUG = "#808080"
    COLOR_INFO = "#d4d4d4"
    COLOR_WARN = "#dcdcaa"
    COLOR_ERROR = "#f14c4c"

    LEVEL_ALL = 0
    LEVEL_INFO = 1
    LEVEL_WARN = 2
    LEVEL_ERROR = 3

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._level_filter = self.LEVEL_ALL
        self._setup_ui()

        from v2.bridge import bridge
        bridge.on_log(self._on_log)

    def _setup_ui(self):
        # 工具栏
        toolbar = CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=4, pady=(4, 2))

        CTkLabel(toolbar, text="日志等级:", text_color="#8b949e").pack(side="left", padx=(0, 4))

        self._level_combo = CTkComboBox(toolbar, values=["全部", "信息", "警告", "错误"],
                                          width=90, state="readonly")
        self._level_combo.set("全部")
        self._level_combo.pack(side="left")
        self._level_combo.bind("<<ComboboxSelected>>", self._on_level_changed)

        CTkButton(toolbar, text="清空", width=50, height=24,
                  command=self._clear, fg_color="#21262d", hover_color="#30363d",
                  text_color="#c9d1d9").pack(side="right")

        # 日志文本区
        self._textbox = CTkTextbox(self, font=("Cascadia Code", 10), wrap="word",
                                    corner_radius=8)
        self._textbox.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._textbox.configure(state="disabled")

    def _on_level_changed(self, event=None):
        level_map = {"全部": 0, "信息": 1, "警告": 2, "错误": 3}
        self._level_filter = level_map.get(self._level_combo.get(), 0)

    def _clear(self):
        self._textbox.configure(state="normal")
        self._textbox.delete("0.0", "end")
        self._textbox.configure(state="disabled")

    def append(self, text: str, level: int = 1):
        if level < self._level_filter:
            return

        color = {
            0: self.COLOR_DEBUG,
            1: self.COLOR_INFO,
            2: self.COLOR_WARN,
            3: self.COLOR_ERROR,
        }.get(level, self.COLOR_INFO)

        self._textbox.configure(state="normal")
        ts = self._now()
        self._textbox.insert("end", f"[{ts}] ", "#72767d")
        self._textbox.insert("end", text + "\n", color)
        self._textbox.configure(state="disabled")
        self._textbox.see("end")

    @staticmethod
    def _now():
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def _on_log(self, text: str, level: int):
        self.after(0, lambda: self.append(text, level))