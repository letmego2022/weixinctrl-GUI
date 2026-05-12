"""
cc.py - Claude Code 知识库插件
用户发送 /cc <需求>，通过 Claude Code CLI 操作 Obsidian 知识库
"""
import os
import subprocess
from typing import Optional
from v2.plugins import PluginBase


class CcPlugin(PluginBase):
    """拦截 /cc 消息，操作 Obsidian 知识库"""

    name = "cc"
    interval = 0
    enabled = True

    def on_start(self, account, user_id: str) -> Optional[str]:
        return None

    def on_interval(self, account, user_id: str) -> Optional[str]:
        return None

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        """收到 /cc 开头消息时调用 Claude Code 操作知识库"""
        from v2.client import extract_text, run_claude_code_knowledge, _auto_send_output, _extract_output_file
        text = extract_text(msg)
        if not text:
            return None

        lower_text = text.lower()
        if not lower_text.startswith("/cc "):
            return None

        prompt = text[len("/cc "):].strip()
        if not prompt:
            return "用法: /cc <需求>\n例如: /cc 帮我整理今天的笔记"

        try:
            raw_text, output_file = run_claude_code_knowledge(prompt)
            clean_text, _ = _extract_output_file(raw_text)
            if output_file and os.path.exists(output_file):
                send_desc = _auto_send_output(account, from_user, None, output_file)
                clean_text = f"{clean_text}\n{send_desc}".strip()
            return clean_text if clean_text else "执行完成，无输出"
        except Exception as e:
            return f"执行错误: {e}"
