"""
cc.py - Claude Code 知识库插件
用户发送 /cc <需求>，异步通过 Claude Code CLI 操作 Obsidian 知识库
"""
import os
import threading
import subprocess
from typing import Optional
from v2.plugins import PluginBase


class CcPlugin(PluginBase):
    """拦截 /cc 消息，异步操作 Obsidian 知识库"""

    name = "cc"
    interval = 0
    enabled = True

    def on_start(self, account, user_id: str) -> Optional[str]:
        return None

    def on_interval(self, account, user_id: str) -> Optional[str]:
        return None

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        """收到 /cc 消息时异步调用 Claude Code 操作知识库"""
        from v2.client import (
            extract_text, send_message, log_message,
            run_claude_code_knowledge, _auto_send_output, _extract_output_file,
        )
        from v2.bridge import bridge

        text = extract_text(msg)
        if not text or not text.lower().startswith("/cc "):
            return None

        prompt = text[len("/cc "):].strip()
        if not prompt:
            return "用法: /cc <需求>\n例如: /cc 帮我整理今天的笔记"

        context_token = msg.get("context_token", "")

        def run():
            try:
                raw_text, output_file = run_claude_code_knowledge(prompt)
                clean_text, _ = _extract_output_file(raw_text)
                if output_file and os.path.exists(output_file):
                    send_desc = _auto_send_output(account, from_user, None, output_file)
                    clean_text = f"{clean_text}\n{send_desc}".strip()
                reply = clean_text if clean_text else "执行完成，无输出"

                send_result = send_message(account, from_user, reply, context_token)
                ret = send_result.get("ret") if send_result else -1
                if ret == 0 or ret is None or ret == 200:
                    bridge.emit_message_sent(reply)
                    log_message("sent", account.get("user_id", ""), from_user, "text", reply, context_token=context_token)
                else:
                    self.log_error(f"发送失败: {send_result.get('errmsg', '')}")

            except Exception as e:
                self.log_error(f"执行错误: {e}")
                reply = f"执行错误: {e}"
                send_message(account, from_user, reply, context_token)

        threading.Thread(target=run, daemon=True).start()
        self.log_info(f"开始异步执行 /cc: {prompt[:40]}...")
        return None  # 不阻塞 poller
