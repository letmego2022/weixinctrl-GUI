"""
poller.py - 消息轮询线程
独立重写，底层复用 client.py API
"""
import sys
import os
import time
import logging

# 将项目根目录加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import QThread

# 复用 client.py 的核心 API
from v2.client import (
    load_account,
    get_updates,
    send_message,
    log_message,
    extract_text,
    is_image_message,
    is_voice_message,
    is_file_message,
    is_video_message,
    save_image,
    save_voice,
    save_file,
    save_video,
    handle_message as client_handle_message,
    is_user_message,
    CURSOR_FILE,
)

# 插件系统
from v2.plugins import PluginManager
from v2.plugins.weather import WeatherPlugin
from v2.plugins.cmb_exchange import CMBExchangePlugin
from v2.plugins.market import MarketPlugin
from v2.plugins.phone import PhonePlugin
from v2.plugins.cmd import CmdPlugin
from v2.plugins.cc import CcPlugin
from v2.plugins.daily_summary import DailySummaryPlugin

logger = logging.getLogger("weixin.poller")


class PollerThread(QThread):
    """
    QThread: 消息轮询主循环。
    运行独立线程中，通过 bridge 信号与 GUI 通信。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._account = None
        self._cursor = ""
        self._user_id = ""

        # 初始化插件管理器
        self.plugin_manager = PluginManager()
        self.plugin_manager.register(WeatherPlugin())
        self.plugin_manager.register(CMBExchangePlugin())
        self.plugin_manager.register(MarketPlugin())
        self.plugin_manager.register(PhonePlugin())
        self.plugin_manager.register(CmdPlugin())
        self.plugin_manager.register(CcPlugin())
        self.plugin_manager.register(DailySummaryPlugin())

    def _load_account(self):
        """加载账号，失败则退出"""
        try:
            self._account = load_account()
            self._user_id = self._account.get("user_id", "")
            return True
        except SystemExit:
            self._emit_log("未登录，请先运行 login.bat", 3)
            return False

    def _load_cursor(self):
        """从文件恢复 cursor"""
        try:
            if os.path.exists(CURSOR_FILE):
                with open(CURSOR_FILE, "r") as f:
                    saved = f.read().strip()
                if saved:
                    self._cursor = saved
                    self._emit_log(f"已恢复 cursor", 1)
        except Exception:
            pass

    def _save_cursor(self, cursor):
        """持久化 cursor"""
        try:
            with open(CURSOR_FILE, "w") as f:
                f.write(cursor)
        except Exception:
            pass

    def _emit_log(self, msg, level=1):
        """发送日志信号"""
        from v2.bridge import bridge
        bridge.signal_log.emit(msg, level)

    def _classify_message(self, msg):
        """分类消息，返回 (type, content, file_path)"""
        from_user = msg.get("from_user_id", "")

        if is_image_message(msg):
            filepath = save_image(self._account, msg, from_user)
            return ("image", f"[图片] {filepath}", filepath)
        elif is_voice_message(msg):
            filepath, voice_text = save_voice(self._account, msg, from_user)
            content = f"[语音] {filepath}" + (f" (转文字: {voice_text})" if voice_text else "")
            return ("voice", content, filepath)
        elif is_file_message(msg):
            filepath = save_file(self._account, msg, from_user)
            return ("file", f"[文件] {filepath}", filepath)
        elif is_video_message(msg):
            filepath = save_video(self._account, msg, from_user)
            return ("video", f"[视频] {filepath}", filepath)
        else:
            text = extract_text(msg)
            return ("text", text, None)

    def _process_message(self, msg):
        """处理单条消息，发送到 GUI"""
        if not is_user_message(msg):
            return

        from_user = msg.get("from_user_id", "")
        context_token = msg.get("context_token", "")

        # 分类消息
        msg_type, content, file_path = self._classify_message(msg)

        # 记录到聊天日志
        log_message(
            "received", from_user, self._user_id, msg_type,
            content, context_token=context_token, file_path=file_path
        )

        # 发送到 GUI
        from v2.bridge import bridge
        bridge.signal_message_received.emit({
            "type": msg_type,
            "from_user": from_user,
            "content": content,
            "timestamp": time.strftime("%H:%M:%S"),
            "file_path": file_path,
            "context_token": context_token,
        })

        # 插件处理
        plugin_responses = self.plugin_manager.on_message(msg, self._account, from_user)
        if plugin_responses:
            for plugin_name, plugin_text in plugin_responses:
                result = send_message(self._account, from_user, plugin_text, context_token)
                ret = result.get("ret")
                if ret == 0 or ret is None or ret == 200:
                    self._emit_log(f"插件 {plugin_name} 已回复", 1)
                    bridge.signal_message_sent.emit(plugin_text)
                    log_message("sent", self._user_id, from_user, "text", plugin_text, context_token=context_token)
            return  # 插件已处理，跳过 AI

        # AI / 命令处理（复用 client.py 的 handle_message 逻辑）
        text = extract_text(msg)
        if not text:
            return

        response = client_handle_message(text, self._account, from_user, context_token)
        if response:
            if isinstance(response, tuple):
                response_text, output_file = response
            else:
                response_text, output_file = response, None

            if response_text:
                result = send_message(self._account, from_user, response_text, context_token)
                ret = result.get("ret")
                if ret == 0 or ret is None or ret == 200:
                    bridge.signal_message_sent.emit(response_text)
                    self._emit_log(f"已回复: {response_text[:40]}...", 1)
                    log_message("sent", self._user_id, from_user, "text", response_text, context_token=context_token)

    def _check_plugins(self):
        """检查并执行定时插件"""
        from v2.bridge import bridge
        results = self.plugin_manager.on_interval(self._account, self._user_id)
        for plugin_name, msg_text in results:
            result = send_message(self._account, self._user_id, msg_text)
            ret = result.get("ret")
            if ret == 0 or ret is None or ret == 200:
                self._emit_log(f"插件 {plugin_name} 已发送提醒", 1)
                bridge.signal_message_sent.emit(msg_text)
                log_message("sent", self._user_id, self._user_id, "text", msg_text)

    def run(self):
        """主循环"""
        if not self._load_account():
            return

        self._running = True
        self._load_cursor()
        self._emit_log("轮询线程已启动", 1)

        # 启动时执行所有插件
        start_results = self.plugin_manager.on_start(self._account, self._user_id)
        for plugin_name, msg_text in start_results:
            result = send_message(self._account, self._user_id, msg_text)
            ret = result.get("ret")
            if ret == 0 or ret is None or ret == 200:
                self._emit_log(f"插件 {plugin_name} 已发送启动提醒", 1)

        from v2.bridge import bridge
        bridge.signal_polling_status.emit(True)

        while self._running:
            try:
                # 定时插件检查
                self._check_plugins()

                # 消息轮询
                msgs, self._cursor = get_updates(self._account, self._cursor)
                if self._cursor:
                    self._save_cursor(self._cursor)

                for msg in msgs:
                    self._process_message(msg)

                time.sleep(1 if msgs else 0.5)

            except Exception as e:
                self._emit_log(f"轮询异常: {e}", 3)
                time.sleep(5)

        bridge.signal_polling_status.emit(False)
        self._emit_log("轮询线程已停止", 1)

    def stop(self):
        """停止轮询"""
        self._running = False
