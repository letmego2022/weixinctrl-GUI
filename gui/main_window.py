"""
main_window.py - 主窗口 (sci-fi 主题)
基于 customtkinter 的科幻风 GUI
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
from customtkinter import CTkFrame, CTkLabel, CTkButton, CTkEntry

from v2.gui.message_panel import MessagePanel
from v2.gui.plugin_panel import PluginPanel
from v2.gui.log_panel import LogPanel
from v2.bridge import bridge

# ── Sci-fi 调色板 ──────────────────────────────────────────────────────────
C = {
    "bg":       "#0b0b10",
    "surface":  "#12121c",
    "elevated": "#181825",
    "border":   "#1e1e30",
    "cyan":     "#00e5ff",
    "green":    "#00e676",
    "purple":   "#bb86fc",
    "red":      "#ff5252",
    "amber":    "#ffd740",
    "text":     "#c8ccd4",
    "dim":      "#626278",
    "white":    "#ffffff",
}
FONT = ("Cascadia Code", 12)
FONT_SM = ("Cascadia Code", 10)
FONT_BOLD = ("Cascadia Code", 12, "bold")


class MainWindow(ctk.CTkFrame):
    def __init__(self, master=None, auto_login=False):
        super().__init__(master, fg_color=C["bg"])

        self._poller = None
        self._running = False

        self._setup_ui()
        self._bind_bridge()

        if auto_login:
            self.after(500, self._open_login)

    def _bind_bridge(self):
        bridge.on_message_received(self._on_message_received)
        bridge.on_message_sent(self._on_message_sent)
        bridge.on_plugin_update(self._on_plugin_update)
        bridge.on_polling_status(self._on_polling_status)

    # ── UI 构建 ─────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self._build_toolbar()
        self._build_main_area()
        self._build_bottom_area()

    def _build_toolbar(self):
        bar = CTkFrame(self, height=42, corner_radius=0,
                       fg_color=C["surface"], border_width=1, border_color=C["border"])
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # 左侧：状态指示灯 + 标题
        left = CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", padx=(10, 0))

        self._status_dot = CTkLabel(left, text="●", font=("Consolas", 16),
                                    text_color=C["dim"])
        self._status_dot.pack(side="left")

        self._status_label = CTkLabel(left, text=" 待机", font=FONT_BOLD,
                                      text_color=C["text"])
        self._status_label.pack(side="left", padx=(2, 0))

        ver = CTkLabel(bar, text="v2.0", font=FONT_SM, text_color=C["dim"])
        ver.pack(side="left", padx=(6, 0))

        # 右侧：快捷按钮
        right = CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=6)

        for text, cmd, w in [
            ("≡ 插件", self._toggle_plugin, 68),
            ("◷ 日志", self._toggle_log, 68),
        ]:
            CTkButton(right, text=text, width=w, height=26, command=cmd,
                      corner_radius=3, font=FONT_SM,
                      fg_color="transparent", hover_color=C["elevated"],
                      text_color=C["dim"], border_width=0
                      ).pack(side="left", padx=1)

        # 登录
        CTkButton(right, text="🔐 登录", width=64, height=26,
                  command=self._open_login, corner_radius=3, font=FONT_SM,
                  fg_color="transparent", hover_color=C["elevated"],
                  text_color=C["dim"], border_width=0
                  ).pack(side="left", padx=1)

        # 电源按钮
        self._power_btn = CTkButton(
            right, text="▶ 启动", width=68, height=26, command=self._toggle_polling,
            corner_radius=3, font=FONT_SM,
            fg_color="transparent", hover_color=C["elevated"],
            text_color=C["cyan"], border_width=1, border_color=C["cyan"]
        )
        self._power_btn.pack(side="left", padx=(4, 2))

        # 退出
        CTkButton(right, text="✕", width=30, height=26, command=self._quit,
                  corner_radius=3, font=FONT_SM,
                  fg_color="transparent", hover_color="#2a1515",
                  text_color=C["red"], border_width=0
                  ).pack(side="left", padx=1)

    def _build_main_area(self):
        body = CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=6, pady=(6, 2))

        # 消息面板：细边框发光效果
        msg_frame = CTkFrame(body, fg_color=C["surface"],
                             border_width=1, border_color=C["border"])
        msg_frame.pack(side="left", fill="both", expand=True, padx=(0, 3))

        self._message_panel = MessagePanel(master=msg_frame)
        self._message_panel.pack(fill="both", expand=True)

        # 插件面板
        self._plugin_panel = PluginPanel(master=body, width=250)
        self._plugin_panel.pack(side="right", fill="y", padx=(3, 0))
        self._plugin_panel.pack_forget()

    def _build_bottom_area(self):
        bottom = CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=6, pady=(2, 6))

        # 输入栏
        input_frame = CTkFrame(bottom, height=44, corner_radius=4,
                               fg_color=C["surface"],
                               border_width=1, border_color=C["border"])
        input_frame.pack(fill="x", pady=(0, 2))
        input_frame.pack_propagate(False)

        self._input_entry = CTkEntry(
            input_frame, placeholder_text="输入消息，Enter 发送…",
            font=FONT, corner_radius=0,
            fg_color="transparent", border_width=0,
            placeholder_text_color=C["dim"]
        )
        self._input_entry.pack(side="left", fill="x", expand=True, padx=(10, 4), pady=6)
        self._input_entry.bind("<Return>", lambda e: self._send_message())

        self._send_btn = CTkButton(
            input_frame, text="↵", width=40, height=30,
            command=self._send_message, corner_radius=3, font=("Consolas", 14),
            fg_color=C["cyan"], hover_color="#00c8e0", text_color=C["bg"]
        )
        self._send_btn.pack(side="right", padx=4, pady=6)

        # 日志面板
        self._log_panel = LogPanel(master=bottom, height=140, corner_radius=4)
        self._log_panel.pack(fill="x", pady=0)
        self._log_panel.pack_forget()

    # ── bridge 回调 ─────────────────────────────────────────────────────────

    def _on_message_received(self, data: dict):
        pass

    def _on_message_sent(self, text: str):
        pass

    def _on_plugin_update(self, plugins: list):
        self.after(0, lambda: self._plugin_panel.update_plugins(plugins))

    def _on_polling_status(self, running: bool):
        self.after(0, lambda: self._update_power_ui(running))

    def _update_power_ui(self, running: bool):
        self._running = running
        if running:
            self._status_dot.configure(text="●", text_color=C["green"])
            self._status_label.configure(text=" 运行中")
            self._power_btn.configure(text="■ 停止", text_color=C["red"],
                                      border_color=C["red"])
        else:
            self._status_dot.configure(text="●", text_color=C["dim"])
            self._status_label.configure(text=" 待机")
            self._power_btn.configure(text="▶ 启动", text_color=C["cyan"],
                                      border_color=C["cyan"])

    # ── 操作 ─────────────────────────────────────────────────────────────────

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
        self._update_power_ui(True)

    def _stop_polling(self):
        if self._poller:
            self._poller._running = False
            self._poller.join(timeout=3)
        self._running = False
        self._update_power_ui(False)

    def _send_message(self):
        text = self._input_entry.get().strip()
        if not text:
            return
        if not self._running:
            self._input_entry.delete(0, "end")
            return

        self._input_entry.delete(0, "end")
        self._send_btn.configure(state="disabled")

        def do_send():
            from v2.client import send_message
            account = self._poller._account
            user_id = self._poller._user_id
            result = send_message(account, user_id, text, "")
            ret = result.get("ret")
            self.after(0, lambda: self._send_btn.configure(state="normal"))
            if ret == 0 or ret is None:
                bridge.emit_message_sent(text)
            else:
                self.after(0, lambda: self._log_panel.append(
                    f"发送失败: {result.get('errmsg', '未知')}", 3))

        threading.Thread(target=do_send, daemon=True).start()

    def _toggle_plugin(self):
        if self._plugin_panel.winfo_viewable():
            self._plugin_panel.pack_forget()
        else:
            self._plugin_panel.pack(side="right", fill="y", padx=(3, 0))

    def _toggle_log(self):
        if self._log_panel.winfo_viewable():
            self._log_panel.pack_forget()
        else:
            self._log_panel.pack(fill="x")

    def _quit(self):
        import os
        self._stop_polling()
        os._exit(0)

    def _open_login(self):
        import http.client

        FIXED_BASE_URL = "https://ilinkai.weixin.qq.com"
        ILINK_APP_ID = "bot"

        def build_client_version(version):
            parts = list(map(int, version.split(".")))
            return ((parts[0] & 0xff) << 16) | ((parts[1] & 0xff) << 8) | (parts[2] & 0xff)

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

        try:
            url = f"{FIXED_BASE_URL}/ilink/bot/get_bot_qrcode?bot_type=3"
            resp = http_get(url, {"X-WECHAT-UIN": base64.b64encode(str(random.getrandbits(32)).encode()).decode()})
            qr_url = resp.get("qrcode_img_content") or resp.get("qrcode")
            if qr_url:
                webbrowser.open(qr_url)
                self._log_panel.append("已打开扫码登录页面", 1)
            else:
                self._log_panel.append("获取登录链接失败", 2)
        except Exception as e:
            self._log_panel.append(f"登录异常: {e}", 3)
