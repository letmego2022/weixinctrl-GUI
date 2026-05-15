"""
daily_summary.py - 每日总结插件
每天晚上8点自动总结当日聊天记录，失败自动重试（最多3次）
"""
import time
import datetime
from typing import Optional
from . import PluginBase


class DailySummaryPlugin(PluginBase):
    """每日总结插件"""

    name = "daily_summary"
    interval = 300  # 5分钟检查一次
    enabled = True
    MAX_RETRIES = 3

    def __init__(self):
        super().__init__()
        self._sent_date: Optional[str] = None
        self._retry_count = 0

    def on_start(self, account, user_id: str) -> Optional[str]:
        today = datetime.date.today().isoformat()
        if self._sent_date != today:
            self._sent_date = None
            self._retry_count = 0
        return None

    def on_interval(self, account, user_id: str) -> Optional[str]:
        now = time.localtime()
        today = datetime.date.today().isoformat()

        # 跨天重置重试计数
        if self._sent_date and self._sent_date != today:
            self._retry_count = 0

        # 今天已经成功推送
        if self._sent_date == today:
            return None

        # 未到20点
        if now.tm_hour < 20:
            return None

        # 超过21点放弃，避免深夜打扰
        if now.tm_hour >= 21:
            if self._sent_date != today:
                self.log_info("已超过21点，放弃今日总结")
            self._sent_date = today
            return None

        # 已达最大重试次数
        if self._retry_count >= self.MAX_RETRIES:
            self._sent_date = today
            self.log_error(f"已达最大重试次数 ({self.MAX_RETRIES})，放弃今日总结")
            return None

        if self._retry_count > 0:
            self.log_info(f"第 {self._retry_count} 次重试生成每日总结...")
        else:
            self.log_info("开始生成每日总结...")

        result = self._do_summary(account)

        if result and not self._is_error(result):
            self._sent_date = today
            self._retry_count = 0
            self.log_info("每日总结推送成功")
            return result

        self._retry_count += 1
        error_preview = (result or "无内容")[:40]
        if self._retry_count >= self.MAX_RETRIES:
            self.log_error(f"已达最大重试次数，放弃: {error_preview}")
        else:
            self.log_warning(f"失败，将在下个周期重试 ({self._retry_count}/{self.MAX_RETRIES}): {error_preview}")
        return None

    def _is_error(self, text: str) -> bool:
        """检测 ai_chat 是否返回了错误而非有效回复"""
        return text.strip().startswith((
            "AI 错误", "AI 异常", "超时了",
            "连接失败", "请求超时", "AI 服务",
        ))

    def _do_summary(self, account) -> Optional[str]:
        from v2.client import load_chat_log, ai_chat

        today = datetime.date.today().strftime("%Y-%m-%d")
        log = load_chat_log()
        msgs = log.get("messages", [])

        today_msgs = [
            m for m in msgs
            if m.get("timestamp", "").startswith(today)
            and m.get("role") != "system"
        ]

        if not today_msgs:
            self.log_info("今日无对话记录，跳过总结")
            return None

        user_count = sum(1 for m in today_msgs if m.get("role") == "user")
        total_count = len(today_msgs)

        lines = []
        for m in today_msgs:
            content = m.get("content", "")
            if isinstance(content, list):
                text = next((b.get("text", "") for b in content if b.get("type") == "text"), "")
            else:
                text = str(content)

            if len(text.strip()) < 2:
                continue
            # 超长内容截断（命令输出之类无总结价值的内容）
            if len(text) > 600:
                text = text[:200] + "…"

            ts = m.get("timestamp", "")[11:16]  # HH:MM
            role_label = "用户" if m.get("role") == "user" else "助手"
            lines.append(f"[{ts}] {role_label}: {text}")

        if not lines:
            return None

        # 智能采样：超过40条时保留最早8条 + 最近32条
        if len(lines) > 40:
            lines = lines[:8] + ["…（省略中间对话）"] + lines[-32:]

        history_text = "\n".join(lines)
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        weekday = weekdays[datetime.date.today().weekday()]

        prompt = (
            f"以下是今天（周{weekday}）的微信聊天记录，共 {total_count} 条消息（用户发言 {user_count} 条）。\n\n"
            f"请认真阅读全部聊天记录，整理一份结构化的每日总结。要求：\n"
            f"- 按主题分 3-5 个大类，每个大类下列 2-4 个具体要点\n"
            f"- 覆盖：重要讨论/决定、查询的信息（天气/股市/汇率）、待办事项、文件分享、有趣的内容\n"
            f"- 每个要点包含具体内容和大致时间\n"
            f"- 不要遗漏任何有信息量的对话\n"
            f"- 末尾用一段话总结今天的主题和节奏\n\n"
            f"聊天记录：\n{history_text}\n\n"
            f"输出格式（严格遵守）：\n"
            f"## 📋 {today} 聊天总结\n\n"
            f"### 🔑 重要讨论\n"
            f"- **14:30** 具体内容...\n\n"
            f"### 📊 信息查询\n"
            f"- **09:15** 具体内容...\n\n"
            f"### ✅ 待办事项\n"
            f"- **16:00** 具体内容...\n\n"
            f"### 📝 其他\n"
            f"- **11:20** 具体内容...\n\n"
            f"> 总结：..."
        )

        return ai_chat(prompt, max_tokens=2000)
