"""
main_window.py - 主窗口
基于 customtkinter 的现代化 GUI
"""
import sys
import os
import threading
import base64
import random
import json
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from customtkinter import CTkFrame, CTkLabel, CTkButton, CTkEntry, CTkTextbox

from v2.gui.message_panel import MessagePanel
from v2.gui.plugin_panel import PluginPanel
from v2.gui.log_panel import LogPanel
from v2.bridge import bridge


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("微信控制台 v2")
        self.geometry("1100x700")
        self.minsize(900, 600)

        self._poller = None
        self._running = False

        self._setup_ui()

        # 注册 bridge 回调
        bridge.on_message_received(self._on_message_received)
        bridge.on_message_sent(self._on_message_sent)
        bridge.on_log(self._on_log)
        bridge.on_plugin_update(self._on_plugin_update)
        bridge.on_polling_status(self._on_polling_status)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        # ── 顶部工具栏 ──────────────────────────────────────────────────────
        toolbar = CTkFrame(self, height=48, corner_radius=0, fg_color="#161b22")
        toolbar.pack(fill="x", padx=0, pady=0)
        toolbar.pack_propagate(False)

        # 状态标签
        self._status_label = CTkLabel(toolbar, text="⚫ 未启动", font=("Segoe UI", 13, "bold"))
        self._status_label.pack(side="left", padx=(12, 0))

        # 右侧按钮组
        btn_frame = CTkFrame(toolbar, fg_color="transparent")
        btn_frame.pack(side="right", padx=8)

        self._login_btn = CTkButton(
            btn_frame, text="🔐 登录微信", width=110, height=28,
            command=self._open_login, corner_radius=6,
            fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9"
        )
        self._login_btn.pack(side="left", padx=2)

        self._plugin_btn = CTkButton(
            btn_frame, text="📦 插件", width=80, height=28,
            command=self._toggle_plugin, corner_radius=6,
            fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9"
        )
        self._plugin_btn.pack(side="left", padx=2)

        self._log_btn = CTkButton(
            btn_frame, text="📋 日志", width=80, height=28,
            command=self._toggle_log, corner_radius=6,
            fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9"
        )
        self._log_btn.pack(side="left", padx=2)

        self._toggle_btn = CTkButton(
            btn_frame, text="▶ 启动", width=80, height=28,
            command=self._toggle_polling, corner_radius=6,
            fg_color="#1f6feb", hover_color="#1669d4", text_color="#fff"
        )
        self._toggle_btn.pack(side="left", padx=2)

        # ── 中间主区域（消息面板 + 插件面板） ─────────────────────────────────
        main_area = CTkFrame(self, fg_color="#0d1117")
        main_area.pack(fill="both", expand=True, padx=4, pady=(4, 2))

        # 消息面板（始终显示）
        self._message_panel = MessagePanel(master=main_area)
        self._message_panel.pack(side="left", fill="both", expand=True, padx=(0, 2))

        # 插件面板（默认隐藏，右侧）
        self._plugin_panel = PluginPanel(master=main_area, width=260)
        self._plugin_panel.pack(side="right", fill="y", padx=(2, 0))
        self._plugin_panel.pack_forget()

        # ── 底部（输入框 + 日志面板） ────────────────────────────────────────
        bottom_area = CTkFrame(self, fg_color="#0d1117")
        bottom_area.pack(fill="x", padx=4, pady=(2, 4))

        # 输入框
        input_frame = CTkFrame(bottom_area, height=50, corner_radius=8, fg_color="#161b22")
        input_frame.pack(fill="x", pady=(0, 4))
        input_frame.pack_propagate(False)

        self._input_entry = CTkEntry(
            input_frame, placeholder_text="输入消息后按 Enter 发送...",
            font=("Segoe UI", 13), corner_radius=6,
            fg_color="#0d1117", border_width=0
        )
        self._input_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=6)
        self._input_entry.bind("<Return>", lambda e: self._send_message())

        self._send_btn = CTkButton(
            input_frame, text="发送", width=70, height=32,
            command=self._send_message, corner_radius=6,
            fg_color="#1f6feb", hover_color="#1669d4", text_color="#fff"
        )
        self._send_btn.pack(side="right", padx=6, pady=8)

        # 日志面板（默认隐藏）
        self._log_panel = LogPanel(master=bottom_area, height=150, corner_radius=8)
        self._log_panel.pack(fill="x", pady=0)
        self._log_panel.pack_forget()

    # ── 状态栏回调 ───────────────────────────────────────────────────────────

    def _on_message_received(self, data: dict):
        self.after(0, lambda: None)  # 已在 panel 处理

    def _on_message_sent(self, text: str):
        pass

    def _on_log(self, text: str, level: int):
        self.after(0, lambda: self._log_panel.append(text, level))

    def _on_plugin_update(self, plugins: list):
        self.after(0, lambda: self._plugin_panel.update_plugins(plugins))

    def _on_polling_status(self, running: bool):
        self.after(0, lambda: self._update_polling_ui(running))

    def _update_polling_ui(self, running: bool):
        self._running = running
        if running:
            self._status_label.configure(text="⚡ 运行中")
            self._toggle_btn.configure(text="■ 停止", fg_color="#c93c3c", hover_color="#a83232")
        else:
            self._status_label.configure(text="⚫ 已停止")
            self._toggle_btn.configure(text="▶ 启动", fg_color="#1f6feb", hover_color="#1669d4")

    # ── 控件回调 ─────────────────────────────────────────────────────────────

    def _toggle_polling(self):
        if self._running:
            self._stop_polling()
        else:
            self._start_polling()

    def _start_polling(self):
        if self._poller and self._poller.is_alive():
            return

        from v2.worker.poller import PollerThread
        self._poller = PollerThread()
        self._poller.start()
        bridge.set_poller(self._poller)
        self._running = True
        self._update_polling_ui(True)

    def _stop_polling(self):
        if self._poller:
            self._poller._running = False
        self._running = False
        self._update_polling_ui(False)

    def _send_message(self):
        text = self._input_entry.get().strip()
        if not text:
            return

        if not self._running:
            self._input_entry.delete(0, "end")
            return

        from v2.client import send_message
        account = self._poller._account
        user_id = self._poller._user_id

        result = send_message(account, user_id, text, "")
        ret = result.get("ret")

        if ret == 0 or ret is None:
            bridge.emit_message_sent(text)
            self._input_entry.delete(0, "end")
        else:
            self._log_panel.append(f"发送失败: {result.get('errmsg', '未知错误')}", 3)

    def _toggle_plugin(self):
        if self._plugin_panel.winfo_viewable():
            self._plugin_panel.pack_forget()
            self._plugin_btn.configure(text="📦 插件")
        else:
            self._plugin_panel.pack(side="right", fill="y", padx=(2, 0))
            self._plugin_btn.configure(text="📦 隐藏")

    def _toggle_log(self):
        if self._log_panel.winfo_viewable():
            self._log_panel.pack_forget()
            self._log_btn.configure(text="📋 日志")
        else:
            self._log_panel.pack(fill="x", pady=(0, 0))
            self._log_btn.configure(text="📋 隐藏")

    def _open_login(self):
        """用默认浏览器打开微信登录页面"""
        FIXED_BASE_URL = "https://ilinkai.weixin.qq.com"
        ILINK_APP_ID = "bot"

        def build_client_version(version):
            parts = list(map(int, version.split(".")))
            return ((parts[0] & 0xff) << 16) | ((parts[1] & 0xff) << 8) | (parts[2] & 0xff)

        import http.client

        def http_get(url, headers=None):
            u = __import__("urllib.parse", fromlist=["urlparse"]).urlparse(url)
            path = u.path if u.path else "/"
            if u.query:
                path += "?" + u.query
            conn = http.client.HTTPSConnection(u.hostname, timeout=40)
            h = {"iLink-App-Id": ILINK_APP_ID, "iLink-App-Client-Version": str(build_client_version("2.1.8"))}
            if headers:
                h.update(headers)
            conn.request("GET", path, headers=h)
            resp = conn.getresponse()
            data = resp.read()
            conn.close()
            if data:
                try:
                    return json.loads(data.decode("utf-8"))
                except json.JSONDecodeError:
                    pass
            return {}

        def random_uint32_base64():
            uint32 = random.getrandbits(32)
            return base64.b64encode(str(uint32).encode("utf-8")).decode("utf-8")

        try:
            url = f"{FIXED_BASE_URL}/ilink/bot/get_bot_qrcode?bot_type=3"
            headers = {"X-WECHAT-UIN": random_uint32_base64()}
            resp = http_get(url, headers)
            qr_url = resp.get("qrcode_img_content") or resp.get("qrcode")
            if qr_url:
                webbrowser.open(qr_url)
                self._log_panel.append("已用浏览器打开登录页面，请在浏览器中扫码登录", 1)
            else:
                self._log_panel.append("获取登录链接失败，请稍后重试", 2)
        except Exception as e:
            self._log_panel.append(f"打开登录页面失败: {e}", 3)

    def _on_close(self):
        self._stop_polling()
        self.destroy()