"""
cmd.py - Claude Code 命令插件
用户发送 /cmd <需求>，通过 Claude Code CLI 执行
"""
import subprocess
from typing import Optional
from v2.plugins import PluginBase


class CmdPlugin(PluginBase):
    """拦截 /cmd 消息，调用 Claude Code CLI 执行"""

    name = "cmd"
    interval = 0
    enabled = True

    def on_start(self, account, user_id: str) -> Optional[str]:
        return None

    def on_interval(self, account, user_id: str) -> Optional[str]:
        return None

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        """收到 /cmd 开头消息时调用 Claude Code CLI"""
        from v2.client import extract_text
        text = extract_text(msg)
        if not text or not text.startswith("/cmd "):
            return None

        request = text[5:].strip()
        if not request:
            return "用法: /cmd <需求>\n例如: /cmd 查看系统占用情况"

        try:
            result = subprocess.run(
                ["claude", "-p", request],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return f"Claude Code 执行失败: {result.stderr}"
            output = result.stdout.strip()
            return output if output else "执行完成，无输出"
        except subprocess.TimeoutExpired:
            return "执行超时（60秒）"
        except FileNotFoundError:
            return "未找到 claude 命令，请确认 Claude CLI 已安装并加入 PATH"
        except Exception as e:
            return f"执行错误: {e}"
