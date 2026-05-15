#!/usr/bin/env python3
"""
插件系统 - 提供插件化扩展机制
"""
import logging
import time
import threading
from abc import ABC, abstractmethod
from typing import Optional, List

logger = logging.getLogger("weixin.plugins")


class PluginBase(ABC):
    """插件基类"""

    # 插件名称
    name: str = "base"
    # 运行间隔（秒），0=仅启动时运行一次
    interval: int = 0
    # 是否启用
    enabled: bool = True

    def __init__(self):
        self._last_run = 0
        self._lock = threading.Lock()
        self._log = logging.getLogger(f"weixin.plugins.{self.name}")

    def log_info(self, msg: str):
        self._log.info(msg)

    def log_error(self, msg: str):
        self._log.error(msg)

    def log_warning(self, msg: str):
        self._log.warning(msg)

    def should_run(self) -> bool:
        """检查是否应该运行"""
        if not self.enabled:
            return False
        if self.interval == 0:
            # 仅启动时运行
            if self._last_run > 0:
                return False
        elif time.time() - self._last_run < self.interval:
            return False
        return True

    def mark_run(self):
        """标记已运行"""
        with self._lock:
            self._last_run = time.time()

    @abstractmethod
    def on_start(self, account, user_id: str) -> Optional[str]:
        """
        启动时执行（仅当 enabled=True 时调用）
        返回: 消息文本，None 表示不需要发送
        """
        pass

    @abstractmethod
    def on_interval(self, account, user_id: str) -> Optional[str]:
        """
        定时执行（当 interval > 0 时，按间隔执行）
        返回: 消息文本，None 表示不需要发送
        """
        pass

    def on_query(self, text: str, account=None, from_user=None, context_token=None) -> Optional[str]:
        """
        被 AI 意图分类路由调用（默认不处理）
        返回: 消息文本，None 表示不处理
        """
        return None

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        """
        收到消息时执行（默认不处理）
        返回: 消息文本，None 表示不回复
        """
        return None

    def _log_push(self, msg_preview: str, success: bool = True):
        """标准化插件推送日志"""
        prefix = "✓" if success else "✗"
        emoji = "📤" if success else "⚠️"
        self._log.info(f"推送 {'成功' if success else '失败'}: {msg_preview[:50]}...")


class PluginManager:
    """插件管理器"""

    def __init__(self):
        self._plugins: List[PluginBase] = []

    def register(self, plugin: PluginBase):
        """注册插件"""
        self._plugins.append(plugin)
        logging.getLogger("weixin.plugins").info(f"插件已注册: {plugin.name}")

    def unregister(self, name: str):
        """卸载插件"""
        self._plugins = [p for p in self._plugins if p.name != name]

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """获取插件"""
        for p in self._plugins:
            if p.name == name:
                return p
        return None

    def on_start(self, account, user_id: str) -> List[tuple[str, str]]:
        """
        启动时执行所有插件
        返回: [(plugin_name, message), ...]
        """
        results = []
        for plugin in self._plugins:
            if not plugin.enabled:
                continue
            try:
                msg = plugin.on_start(account, user_id)
                plugin.mark_run()
                if msg:
                    results.append((plugin.name, msg))
                    plugin._log_push(msg, success=True)
            except Exception as e:
                plugin._log.error(f"启动执行失败: {e}")
        return results

    def on_interval(self, account, user_id: str) -> List[tuple[str, str]]:
        """
        检查并执行需要运行的插件
        返回: [(plugin_name, message), ...]
        """
        results = []
        for plugin in self._plugins:
            if not plugin.should_run():
                continue
            try:
                msg = plugin.on_interval(account, user_id)
                plugin.mark_run()
                if msg:
                    results.append((plugin.name, msg))
                    plugin._log_push(msg, success=True)
            except Exception as e:
                plugin._log.error(f"定时执行失败: {e}")
        return results

    def on_message(self, msg, account, from_user: str) -> List[tuple[str, str]]:
        """
        消息到达时触发插件
        返回: [(plugin_name, message), ...]
        """
        results = []
        for plugin in self._plugins:
            if not plugin.enabled:
                continue
            try:
                msg_text = plugin.on_message(msg, account, from_user)
                if msg_text:
                    results.append((plugin.name, msg_text))
                    plugin._log_push(msg_text, success=True)
            except Exception as e:
                plugin._log.error(f"消息处理失败: {e}")
        return results

    def list_plugins(self) -> List[dict]:
        """列出所有插件"""
        return [
            {
                "name": p.name,
                "interval": p.interval,
                "enabled": p.enabled,
                "last_run": p._last_run,
            }
            for p in self._plugins
        ]
