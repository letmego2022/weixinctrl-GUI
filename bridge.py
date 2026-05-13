"""
bridge.py - 信号中心，单例模式
基于回调的观察者模式，支持任意 GUI 框架
"""

import threading


class Bridge:
    """
    Signal center using callback-based observer pattern.
    GUI components register callbacks, poller emits events.
    """
    _instance = None

    def __init__(self):
        self._poller = None
        self._callbacks = {
            "message_received": [],
            "message_sent": [],
            "log": [],
            "plugin_update": [],
            "polling_status": [],
        }
        self._lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "Bridge":
        return cls()

    # ── 发送信号 ──────────────────────────────────────────────────────────────

    def emit_message_received(self, data: dict):
        with self._lock:
            for cb in self._callbacks["message_received"]:
                try:
                    cb(data)
                except Exception:
                    pass

    def emit_message_sent(self, text: str):
        with self._lock:
            for cb in self._callbacks["message_sent"]:
                try:
                    cb(text)
                except Exception:
                    pass

    def emit_log(self, text: str, level: int = 1):
        with self._lock:
            for cb in self._callbacks["log"]:
                try:
                    cb(text, level)
                except Exception:
                    pass

    def emit_plugin_update(self, plugins: list):
        with self._lock:
            for cb in self._callbacks["plugin_update"]:
                try:
                    cb(plugins)
                except Exception:
                    pass

    def emit_polling_status(self, running: bool):
        with self._lock:
            for cb in self._callbacks["polling_status"]:
                try:
                    cb(running)
                except Exception:
                    pass

    # ── 注册回调 ──────────────────────────────────────────────────────────────

    def on_message_received(self, cb):
        self._callbacks["message_received"].append(cb)
        return cb

    def on_message_sent(self, cb):
        self._callbacks["message_sent"].append(cb)
        return cb

    def on_log(self, cb):
        self._callbacks["log"].append(cb)
        return cb

    def on_plugin_update(self, cb):
        self._callbacks["plugin_update"].append(cb)
        return cb

    def on_polling_status(self, cb):
        self._callbacks["polling_status"].append(cb)
        return cb

    # ── Poller 管理 ───────────────────────────────────────────────────────────

    def set_poller(self, poller):
        self._poller = poller
        if poller:
            self.emit_plugin_update(poller.plugin_manager.list_plugins())

    def get_poller(self):
        return self._poller


bridge = Bridge.get_instance()