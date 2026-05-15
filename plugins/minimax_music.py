"""
minimax_music.py - MiniMax 音乐插件
触发: /music <需求描述>
AI 自动理解需求，生成歌词 + 音乐，或仅歌词
"""
import os
import json
import threading
import requests
from pathlib import Path
from typing import Optional

from v2.plugins import PluginBase

API_BASE = "https://api.minimaxi.com"
OUTPUT_DIR = Path(__file__).parent.parent / "minimax_output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _ts():
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _get_api_key():
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def _ai(prompt: str) -> Optional[str]:
    """调用 MiniMax 文本 API"""
    api_key = _get_api_key()
    if not api_key:
        return None

    resp = requests.post(
        f"{API_BASE}/anthropic/v1/messages",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "MiniMax-M2.7",
            "max_tokens": 2000,
            "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    if resp.status_code != 200:
        return None

    data = resp.json()
    content = data.get("content", "")
    if isinstance(content, list):
        content = "".join(b.get("text", "") for b in content if b.get("type") == "text")
    return content.strip() if content else None


def _call_music_api(payload: dict) -> Optional[str]:
    """调用 MiniMax 音乐生成 API，返回下载后的本地文件路径"""
    api_key = _get_api_key()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    resp = requests.post(f"{API_BASE}/v1/music_generation",
                         headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        return None

    data = resp.json()
    base = data.get("base_resp", {})
    if base.get("status_code") not in (0, None):
        return None

    audio_url = data.get("data", {}).get("audio") or data.get("audio_file", {}).get("url")
    if not audio_url:
        return None

    dl = requests.get(audio_url, timeout=60)
    if dl.status_code != 200:
        return None

    path = OUTPUT_DIR / f"music_{_ts()}.mp3"
    path.write_bytes(dl.content)
    return str(path)


# ── 核心：AI 理解需求 → 生成音乐 ──────────────────────────────────────────

def create_music(request: str) -> Optional[str]:
    """
    AI 分析用户需求，自动生成合适的歌词和音乐。
    返回本地 MP3 文件路径，失败返回 None。
    """
    # Step 1: AI 分析意图并创作
    analyze_prompt = f"""用户说：「{request}」

请根据用户需求，做以下事情：
1. 判断用户是只要歌词，还是要一首完整的歌（歌词+音乐）。默认生成完整歌曲。
2. 为音乐生成写一个英文风格描述（如 "upbeat pop, 120BPM, piano, warm vocal"），不超过60词。
3. 如果用户要歌曲，同时创作中文歌词，带 [Verse][Chorus][Bridge] 等结构标签。

请按以下 JSON 格式输出，不要输出其他内容：
{{"type": "song", "style": "英文风格描述", "lyrics": "中文歌词（带结构标签）"}}

如果用户只要歌词，type 为 "lyrics"，不需要 style 字段：
{{"type": "lyrics", "lyrics": "中文歌词（带结构标签）"}}"""

    result = _ai(analyze_prompt)
    if not result:
        return None

    # 解析 AI 返回的 JSON
    try:
        # 提取 JSON 块
        if "```" in result:
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        parsed = json.loads(result.strip())
    except json.JSONDecodeError:
        return None

    req_type = parsed.get("type", "song")
    lyrics = parsed.get("lyrics", "")
    style = parsed.get("style", "pop")

    if req_type == "lyrics":
        # 只要歌词，返回特殊标记
        return "__LYRICS_ONLY__:" + lyrics

    # Step 2: 生成音乐
    payload = {
        "model": "music-2.6",
        "prompt": style,
        "audio_setting": {"sample_rate": 44100, "bitrate": 256000, "format": "mp3"},
        "output_format": "url",
    }
    if lyrics:
        payload["lyrics"] = lyrics
    else:
        payload["lyrics_optimizer"] = True

    return _call_music_api(payload)


# ── 插件 ───────────────────────────────────────────────────────────────────

class MiniMaxMusicPlugin(PluginBase):
    """MiniMax 音乐插件"""

    name = "minimax_music"
    interval = 0
    enabled = True

    def on_start(self, account, user_id: str) -> Optional[str]:
        return None

    def on_interval(self, account, user_id: str) -> Optional[str]:
        return None

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        from v2.client import extract_text, send_message, send_file_message, log_message
        from v2.bridge import bridge

        text = extract_text(msg)
        if not text or not text.startswith("/music"):
            return None

        request = text[len("/music"):].strip()
        if not request:
            return "用法: /music <需求>\n例如:\n/music 一首关于夏天的轻快歌曲\n/music 写一首失恋的歌词"

        context_token = msg.get("context_token", "")
        account_id = account.get("user_id", "")

        def run():
            self.log_info(f"音乐请求: {request[:40]}...")
            result = create_music(request)

            if not result:
                send_message(account, from_user, "❌ 音乐生成失败，请稍后重试", context_token)
                self.log_error("音乐生成失败")
                return

            if result.startswith("__LYRICS_ONLY__:"):
                lyrics = result[len("__LYRICS_ONLY__:"):]
                send_message(account, from_user, f"📝 {request}\n\n{lyrics}", context_token)
                bridge.emit_message_sent(f"📝 {request}")
                log_message("sent", account_id, from_user, "text", lyrics, context_token=context_token)
                self.log_info("歌词已发送")
                return

            # 发送音乐文件
            size_kb = os.path.getsize(result) / 1024
            send_message(account, from_user, f"🎵 {request}", context_token)
            send_result = send_file_message(account, from_user, result, context_token)
            ret = send_result.get("ret") if send_result else -1
            if ret == 0 or ret is None or ret == 200:
                bridge.emit_message_sent(f"🎵 {os.path.basename(result)}")
                log_message("sent", account_id, from_user, "file", result, context_token=context_token)
                self.log_info(f"音乐已发送: {os.path.basename(result)} ({size_kb:.0f} KB)")
            else:
                send_message(account, from_user, "❌ 文件发送失败", context_token)

        threading.Thread(target=run, daemon=True).start()
        return "⏳ 正在创作中，稍候…"
