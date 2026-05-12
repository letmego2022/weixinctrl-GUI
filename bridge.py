"""
bridge.py - 信号中心，单例模式
负责 PollerThread 和 GUI 之间的通信
"""
from PyQt5.QtCore import QObject, pyqtSignal


class Bridge(QObject):
    """
    PyQt 信号中心。
    所有后台线程通过这里向 GUI 推送信号。
    """
    # 新消息到达 (dict: type, from_user, content, timestamp, file_path)
    signal_message_received = pyqtSignal(dict)
    # 消息发送成功 (str: 发送的文本)
    signal_message_sent = pyqtSignal(str)
    # 日志输出 (str: 内容, int: 等级 0=DEBUG 1=INFO 2=WARN 3=ERROR)
    signal_log = pyqtSignal(str, int)
    # 插件状态更新 (list: [(name, interval, enabled, last_run), ...])
    signal_plugin_update = pyqtSignal(list)
    # 轮询状态变化 (bool: True=运行中, False=已停止)
    signal_polling_status = pyqtSignal(bool)

    # 单例
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._poller = None
        return cls._instance

    @classmethod
    def get_instance(cls) -> "Bridge":
        return cls()

    def set_poller(self, poller):
        """poller 启动时注册自己"""
        self._poller = poller
        # 立即触发一次插件列表刷新
        if poller:
            self.signal_plugin_update.emit(poller.plugin_manager.list_plugins())

    def get_poller(self):
        return self._poller


# 全局快捷访问
bridge = Bridge.get_instance()
