"""
daily_summary.py - 每日总结插件
每天晚上8点自动总结当日聊天记录
"""
import time
import datetime
from typing import Optional
from . import PluginBase


class DailySummaryPlugin(PluginBase):
    """每日总结插件"""

    name = "daily_summary"
    interval = 300  # 每5分钟检查一次
    enabled = True

    def __init__(self):
        super().__init__()
        self._sent_date: Optional[str] = None  # 今天是否已推送过

    def on_start(self, account, user_id: str) -> Optional[str]:
        return None

    def on_interval(self, account, user_id: str) -> Optional[str]:
        now = time.localtime()
        today = datetime.date.today().isoformat()

        if now.tm_hour == 20 and now.tm_min < 5:
            if self._sent_date == today:
                return None  # 今天已推送过
            self._sent_date = today
            return self._do_summary(account)
        return None

    def _do_summary(self, account) -> Optional[str]:
        from v2.client import load_chat_log, ai_chat

        today = datetime.date.today().strftime("%Y-%m-%d")
        log = load_chat_log()
        msgs = log.get("messages", [])

        # 只取当天的 非system 消息，最多15条
        today_msgs = [
            m for m in msgs
            if m.get("timestamp", "").startswith(today)
            and m.get("role") != "system"
        ][-15:]

        if not today_msgs:
            return None

        # 构建精简上下文
        lines = []
        for m in today_msgs:
            ts = m.get("timestamp", "")[11:]  # HH:MM:SS
            role = "用户" if m.get("role") == "user" else "助手"

            content = m.get("content", "")
            if isinstance(content, list):
                text = next((b.get("text", "") for b in content if b.get("type") == "text"), "")
            else:
                text = str(content)

            # 截断超长内容（AI上下文有限）
            if len(text) > 150:
                text = text[:150] + "..."
            if not text:
                continue

            lines.append(f"[{ts}] {role}: {text}")

        if not lines:
            return None

        history_text = "\n".join(lines)
        prompt = (
            f"今天共 {len(today_msgs)} 条对话记录，"
            f"请用精简的markdown格式总结（不超过5个要点）：\n\n{history_text}\n\n"
            "回复格式：\n## 📋 今日聊天总结\n\n"
            "- **要点1**：...\n- **要点2**：...\n"
            "（如无实质内容则写「今天主要是一次普通闲聊」）"
        )

        summary = ai_chat(prompt)
        return summary if summary else None
