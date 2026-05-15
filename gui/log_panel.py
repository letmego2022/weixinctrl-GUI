"""
log_panel.py - 控制台日志面板 (sci-fi 主题)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from customtkinter import CTkTextbox, CTkComboBox, CTkButton, CTkLabel, CTkFrame

CLR_BG    = "#0e0e18"
CLR_DEBUG = "#484860"
CLR_INFO  = "#c8ccd4"
CLR_WARN  = "#ffd740"
CLR_ERROR = "#ff5252"
CLR_TIME  = "#484860"
CLR_DIM   = "#626278"
FONT      = ("Cascadia Code", 10)
FONT_SM   = ("Cascadia Code", 9)


class LogPanel(CTkFrame):
    LEVEL_ALL   = 0
    LEVEL_INFO  = 1
    LEVEL_WARN  = 2
    LEVEL_ERROR = 3

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=CLR_BG, border_width=1,
                         border_color="#1e1e30", **kwargs)
        self._level_filter = self.LEVEL_ALL
        self._setup_ui()

        from v2.bridge import bridge
        bridge.on_log(self._on_log)

    def _setup_ui(self):
        bar = CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=6, pady=(4, 2))

        CTkLabel(bar, text="LOG", text_color=CLR_DIM, font=FONT_SM).pack(side="left")

        self._level_combo = CTkComboBox(
            bar, values=["ALL", "INFO", "WARN", "ERROR"],
            width=80, state="readonly", font=FONT_SM,
            fg_color="#12121c", border_color="#1e1e30",
            button_color="#1e1e30", text_color=CLR_DIM,
            dropdown_fg_color="#12121c", dropdown_text_color=CLR_INFO,
            dropdown_hover_color="#1e1e30"
        )
        self._level_combo.set("ALL")
        self._level_combo.pack(side="left", padx=(8, 0))
        self._level_combo.bind("<<ComboboxSelected>>", self._on_level_changed)

        CTkButton(bar, text="×", width=26, height=20, command=self._clear,
                  corner_radius=2, font=FONT_SM,
                  fg_color="transparent", hover_color="#1e1e30",
                  text_color=CLR_DIM).pack(side="right")

        self._textbox = CTkTextbox(self, font=FONT, wrap="word",
                                    fg_color=CLR_BG, corner_radius=0,
                                    border_width=0)
        self._textbox.pack(fill="both", expand=True, padx=2, pady=(0, 4))
        self._textbox.configure(state="disabled")

    def _on_level_changed(self, event=None):
        m = {"ALL": 0, "INFO": 1, "WARN": 2, "ERROR": 3}
        self._level_filter = m.get(self._level_combo.get(), 0)

    def _clear(self):
        self._textbox.configure(state="normal")
        self._textbox.delete("0.0", "end")
        self._textbox.configure(state="disabled")

    def append(self, text: str, level: int = 1):
        if level < self._level_filter:
            return
        color = {0: CLR_DEBUG, 1: CLR_INFO, 2: CLR_WARN, 3: CLR_ERROR}.get(level, CLR_INFO)
        self._textbox.configure(state="normal")
        self._textbox.insert("end", f"[{self._now()}] ", CLR_TIME)
        self._textbox.insert("end", text + "\n", color)
        self._textbox.configure(state="disabled")
        self._textbox.see("end")

    @staticmethod
    def _now():
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def _on_log(self, text: str, level: int):
        self.after(0, lambda: self.append(text, level))
