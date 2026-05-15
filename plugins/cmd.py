"""
cmd.py - Claude Code 命令插件
用户发送 /cmd <需求>，通过 Claude Code CLI 异步执行
"""
import threading
import subprocess
from typing import Optional
from v2.plugins import PluginBase


MAX_OUTPUT_LENGTH = 3000


class CmdPlugin(PluginBase):
    """拦截 /cmd 消息，异步调用 Claude Code CLI 执行"""

    name = "cmd"
    interval = 0
    enabled = True

    def on_start(self, account, user_id: str) -> Optional[str]:
        return None

    def on_interval(self, account, user_id: str) -> Optional[str]:
        return None

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        """收到 /cmd 开头消息时异步调用 Claude Code CLI"""
        from v2.client import extract_text, send_message, log_message
        from v2.bridge import bridge

        text = extract_text(msg)
        if not text or not text.startswith("/cmd "):
            return None

        request = text[5:].strip()
        if not request:
            return "用法: /cmd <需求>\n例如: /cmd 查看系统占用情况"

        context_token = msg.get("context_token", "")

        def run():
            try:
                result = subprocess.run(
                    ["claude", "-p", request],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0:
                    reply = f"Claude Code 执行失败: {result.stderr[:500]}"
                else:
                    reply = result.stdout.strip()
                    if len(reply) > MAX_OUTPUT_LENGTH:
                        reply = reply[:MAX_OUTPUT_LENGTH] + "\n…（输出过长已截断）"
                    if not reply:
                        reply = "执行完成，无输出"

                send_result = send_message(account, from_user, reply, context_token)
                ret = send_result.get("ret") if send_result else -1
                if ret == 0 or ret is None or ret == 200:
                    bridge.emit_message_sent(reply)
                    log_message("sent", account.get("user_id", ""), from_user, "text", reply, context_token=context_token)
                else:
                    self.log_error(f"发送失败: {send_result.get('errmsg', '')}")

            except subprocess.TimeoutExpired:
                reply = "执行超时（120秒）"
                send_message(account, from_user, reply, context_token)
            except FileNotFoundError:
                reply = "未找到 claude 命令，请确认 Claude CLI 已安装并加入 PATH"
                send_message(account, from_user, reply, context_token)
            except Exception as e:
                self.log_error(f"执行错误: {e}")
                reply = f"执行错误: {e}"
                send_message(account, from_user, reply, context_token)

        threading.Thread(target=run, daemon=True).start()
        self.log_info(f"开始异步执行: {request[:40]}...")
        return None  # 不阻塞 poller，结果由子线程发送
