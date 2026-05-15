"""
plugin_panel.py - 插件管理面板 (sci-fi 主题)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from customtkinter import CTkFrame, CTkLabel, CTkButton
from datetime import datetime

CLR_BG    = "#12121c"
CLR_ROW   = "#181825"
CLR_DIM   = "#626278"
CLR_TEXT  = "#c8ccd4"
CLR_ON    = "#00e676"
CLR_OFF   = "#ff5252"
CLR_CYAN  = "#00e5ff"
FONT      = ("Cascadia Code", 10)
FONT_SM   = ("Cascadia Code", 9)
FONT_BOLD = ("Cascadia Code", 11, "bold")


class PluginRow(ctk.CTkFrame):
    def __init__(self, parent, name: str, interval: int, enabled: bool, last_run: float, **kwargs):
        super().__init__(parent, height=32, corner_radius=2,
                         fg_color=CLR_ROW, border_width=0, **kwargs)
        self._name = name
        self._enabled = enabled
        self.pack(fill="x", pady=1)

        dot = "●" if enabled else "○"
        color = CLR_ON if enabled else CLR_DIM
        CTkLabel(self, text=dot, font=("Consolas", 14), text_color=color,
                 width=16).pack(side="left", padx=(6, 0))

        CTkLabel(self, text=name, text_color=CLR_TEXT, font=FONT,
                 width=90, anchor="w").pack(side="left", padx=(2, 0))

        ts = datetime.fromtimestamp(last_run).strftime("%H:%M") if last_run else "-"
        CTkLabel(self, text=ts, text_color=CLR_DIM, font=FONT_SM).pack(side="right", padx=(0, 6))

        btn_text = "ON" if enabled else "OFF"
        btn_color = CLR_ON if enabled else CLR_OFF
        btn = CTkButton(self, text=btn_text, width=32, height=18,
                         command=self._toggle, corner_radius=2, font=FONT_SM,
                         fg_color=btn_color, hover_color=btn_color,
                         text_color="#0b0b10")
        btn.pack(side="right", padx=4)
        self._btn = btn

    def _toggle(self):
        from v2.bridge import bridge
        poller = bridge.get_poller()
        if poller:
            plugin = poller.plugin_manager.get_plugin(self._name)
            if plugin:
                plugin.enabled = not plugin.enabled
                self._enabled = plugin.enabled
                color = CLR_ON if self._enabled else CLR_OFF
                btn_text = "ON" if self._enabled else "OFF"
                self._btn.configure(text=btn_text, fg_color=color)


class PluginPanel(CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=CLR_BG, border_width=1,
                         border_color="#1e1e30", **kwargs)
        self._setup_ui()

        from v2.bridge import bridge
        bridge.on_plugin_update(self._on_plugin_update)
        self.after(500, self._start_refresh_timer)

    def _setup_ui(self):
        head = CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=6, pady=(6, 2))

        CTkLabel(head, text="PLUGINS", text_color=CLR_CYAN, font=FONT_BOLD).pack(side="left")

        CTkButton(head, text="↻", width=24, height=20,
                  command=self._refresh_plugins, corner_radius=2, font=FONT_SM,
                  fg_color="transparent", hover_color="#1e1e30",
                  text_color=CLR_DIM, border_width=0).pack(side="right")

        self._list_frame = CTkFrame(self, fg_color="transparent")
        self._list_frame.pack(fill="both", expand=True, padx=4, pady=(0, 6))

    def _refresh_plugins(self):
        from v2.bridge import bridge
        poller = bridge.get_poller()
        if poller:
            bridge.emit_plugin_update(poller.plugin_manager.list_plugins())

    def _start_refresh_timer(self):
        import threading
        def tick():
            while True:
                threading.Event().wait(30)
                self._refresh_plugins()
        t = threading.Thread(target=tick, daemon=True)
        t.start()

    def _on_plugin_update(self, plugins: list):
        self.after(0, lambda: self._do_update(plugins))

    def _do_update(self, plugins: list):
        for w in self._list_frame.winfo_children():
            w.destroy()
        if not plugins:
            CTkLabel(self._list_frame, text="无插件", text_color=CLR_DIM,
                     font=FONT_SM).pack(pady=10)
            return
        for p in plugins:
            if isinstance(p, dict):
                name = p.get("name", "")
                interval = p.get("interval", 0)
                enabled = p.get("enabled", True)
                last_run = p.get("last_run", 0)
            else:
                name, interval, enabled, last_run = p
            PluginRow(self._list_frame, name, interval, enabled, last_run)

    def update_plugins(self, plugins: list):
        self._do_update(plugins)
