"""
plugin_panel.py - 插件管理面板
基于 customtkinter
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from customtkinter import CTkFrame, CTkLabel, CTkButton
from datetime import datetime


class PluginRow(ctk.CTkFrame):
    def __init__(self, parent, name: str, interval: int, enabled: bool, last_run: float, **kwargs):
        super().__init__(parent, height=36, corner_radius=6, fg_color="#161b22", **kwargs)
        self._name = name
        self._enabled = enabled
        self.pack(fill="x", pady=1)

        CTkLabel(self, text=name, text_color="#c9d1d9", font=("Segoe UI", 11))\
            .pack(side="left", padx=(6, 0))

        color = "#3ba55c" if enabled else "#f14c4c"
        btn = CTkButton(self, text="启用" if enabled else "禁用", width=44, height=20,
                            command=self._toggle, fg_color=color, hover_color=color,
                            text_color="#fff", font=("Segoe UI", 9))
        btn.pack(side="right", padx=4)
        self._btn = btn

        ts = datetime.fromtimestamp(last_run).strftime("%H:%M:%S") if last_run else "未运行"
        CTkLabel(self, text=ts, text_color="#484f58", font=("Segoe UI", 9))\
            .pack(side="right", padx=(0, 4))

    def _toggle(self):
        from v2.bridge import bridge
        poller = bridge.get_poller()
        if poller:
            plugin = poller.plugin_manager.get_plugin(self._name)
            if plugin:
                plugin.enabled = not plugin.enabled
                self._enabled = plugin.enabled
                color = "#3ba55c" if self._enabled else "#f14c4c"
                self._btn.configure(text="启用" if self._enabled else "禁用", fg_color=color)


class PluginPanel(CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._setup_ui()

        from v2.bridge import bridge
        bridge.on_plugin_update(self._on_plugin_update)

        self.after(500, self._start_refresh_timer)

    def _setup_ui(self):
        title = CTkFrame(self, fg_color="transparent")
        title.pack(fill="x", padx=4, pady=(4, 2))

        CTkLabel(title, text="插件管理", font=("Segoe UI", 13, "bold")).pack(side="left")

        CTkButton(title, text="↻", width=30, height=24,
                  command=self._refresh_plugins, fg_color="#21262d", hover_color="#30363d",
                  text_color="#c9d1d9").pack(side="right")

        self._list_frame = CTkFrame(self, fg_color="transparent")
        self._list_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))

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
            CTkLabel(self._list_frame, text="无插件", text_color="#484f58").pack(pady=10)
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