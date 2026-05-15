"""
minimax_music.py — MiniMax 音乐生成 / 翻唱 / 歌词 独立测试脚本
用法:
  python minimax_music.py music "E小调, 90BPM, 钢琴抒情, 男声" --lyrics "歌词内容"
  python minimax_music.py music "流行摇滚, 快节奏" --auto-lyrics
  python minimax_music.py cover <audio_url> "爵士风格, 慵懒"
  python minimax_music.py lyric "赛博朋克风格的失恋"
"""
import os
import sys
import time
import json
import requests
from pathlib import Path

# ── 加载 .env ──────────────────────────────────────────────────────────────
def load_env():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print("❌ 未找到 .env 文件")
        sys.exit(1)
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

load_env()

API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# 音乐生成用 minimax 原生 API
BASE = "https://api.minimaxi.com"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

OUTPUT_DIR = Path(__file__).parent / "minimax_output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── 音乐生成 ───────────────────────────────────────────────────────────────

def generate_music(prompt: str, lyrics: str = None, instrumental: bool = False,
                   auto_lyrics: bool = False, model: str = "music-2.6",
                   sample_rate: int = 44100, bitrate: int = 256000):
    """生成音乐，返回输出文件路径"""
    print(f"\n🎵 生成音乐: {prompt[:60]}...")

    payload = {
        "model": model,
        "prompt": prompt,
        "audio_setting": {
            "sample_rate": sample_rate,
            "bitrate": bitrate,
            "format": "mp3",
        },
        "output_format": "url",
    }

    if auto_lyrics:
        payload["lyrics_optimizer"] = True
        print("   📝 自动生成歌词模式")
    elif instrumental:
        payload["is_instrumental"] = True
        print("   🎹 纯音乐模式")
    elif lyrics:
        payload["lyrics"] = lyrics
        print(f"   📝 歌词: {lyrics[:60]}...")

    # 1. 提交任务
    print("   ⏳ 提交生成任务...")
    resp = requests.post(f"{BASE}/v1/music_generation", headers=HEADERS,
                         json=payload, timeout=120)

    if resp.status_code != 200:
        print(f"   ❌ 提交失败 HTTP {resp.status_code}: {resp.text[:300]}")
        return None

    data = resp.json()
    base = data.get("base_resp", {})
    if base.get("status_code") not in (0, None):
        print(f"   ❌ API 错误 {base.get('status_code')}: {base.get('status_msg', '')}")
        return None

    # 同步返回：data.audio 直接有 URL
    inner = data.get("data", {})
    audio_url = inner.get("audio") or data.get("audio_file", {}).get("url") or data.get("audio_url")
    if audio_url:
        return _download(audio_url, "music")

    # 异步模式：有 task_id
    task_id = inner.get("id") or data.get("id") or data.get("generation_id")
    if task_id:
        print(f"   📋 任务ID: {task_id}")
        return _poll(task_id, "music")

    print(f"   ❌ 未获取到结果: {json.dumps(data, ensure_ascii=False)[:300]}")
    return None

# ── 翻唱 ───────────────────────────────────────────────────────────────────

def generate_cover(audio_url: str, prompt: str, lyrics: str = None):
    """音乐翻唱：传入原曲 URL + 风格描述"""
    print(f"\n🎤 翻唱: {prompt[:60]}...")
    print(f"   🎧 原曲: {audio_url[:60]}...")

    payload = {
        "model": "music-cover",
        "audio_url": audio_url,
        "prompt": prompt,
        "audio_setting": {
            "sample_rate": 44100,
            "bitrate": 256000,
            "format": "mp3",
        },
        "output_format": "url",
    }

    if lyrics:
        payload["lyrics"] = lyrics

    print("   ⏳ 提交翻唱任务...")
    resp = requests.post(f"{BASE}/v1/music_generation", headers=HEADERS,
                         json=payload, timeout=120)

    if resp.status_code != 200:
        print(f"   ❌ 提交失败 HTTP {resp.status_code}: {resp.text[:300]}")
        return None

    data = resp.json()
    base = data.get("base_resp", {})
    if base.get("status_code") not in (0, None):
        print(f"   ❌ API 错误 {base.get('status_code')}: {base.get('status_msg', '')}")
        return None

    # 同步返回
    inner = data.get("data", {})
    audio_url_out = inner.get("audio") or data.get("audio_file", {}).get("url") or data.get("audio_url")
    if audio_url_out:
        return _download(audio_url_out, "cover")

    # 异步模式
    task_id = inner.get("id") or data.get("id") or data.get("generation_id")
    if task_id:
        print(f"   📋 任务ID: {task_id}")
        return _poll(task_id, "cover")

    print(f"   ❌ 未获取到结果: {json.dumps(data, ensure_ascii=False)[:300]}")
    return None

# ── 歌词生成 ───────────────────────────────────────────────────────────────

def generate_lyrics(topic: str):
    """通过 Anthropic 兼容接口生成歌词"""
    print(f"\n📝 生成歌词: {topic}")

    prompt = f"""请根据以下主题创作一首歌的歌词，要求：
- 包含 [Verse]、[Chorus]、[Bridge] 等结构标签
- 符合音乐韵律，适合演唱
- 中文歌词，有画面感和情感
- 每个段落 4-8 行

主题：{topic}

直接输出歌词，不要额外解释。"""

    resp = requests.post(
        f"{BASE}/anthropic/v1/messages",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "MiniMax-M2.7",
            "max_tokens": 2000,
            "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )

    if resp.status_code != 200:
        print(f"   ❌ HTTP {resp.status_code}: {resp.text[:300]}")
        return None

    data = resp.json()
    content = data.get("content") or ""
    # Anthropic 格式：content 是 list
    if isinstance(content, list):
        content = "".join(
            b.get("text", "") for b in content if b.get("type") == "text"
        )
    # OpenAI 兼容格式
    if not content:
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    if content:
        # 保存
        path = OUTPUT_DIR / f"lyrics_{_ts()}.txt"
        path.write_text(content, encoding="utf-8")
        print(f"   ✅ 歌词已保存: {path}")
        print(f"\n{content}\n")
        return str(path)

    print(f"   ❌ 未获取到内容: {json.dumps(data, ensure_ascii=False)[:500]}")
    return None

# ── 工具函数 ───────────────────────────────────────────────────────────────

def _poll(task_id: str, tag: str, max_wait: int = 180):
    """轮询异步任务直到完成"""
    start = time.time()
    while time.time() - start < max_wait:
        time.sleep(8)
        elapsed = int(time.time() - start)
        print(f"   ⏳ 等待中... ({elapsed}s)")

        resp = requests.get(
            f"{BASE}/v1/music_generation",
            headers=HEADERS,
            params={"id": task_id},
            timeout=15,
        )

        if resp.status_code != 200:
            continue

        data = resp.json()
        status = data.get("status") or data.get("state") or ""

        if status in ("completed", "success", "done"):
            audio_url = data.get("audio_file", {}).get("url") or data.get("audio_url")
            if audio_url:
                return _download(audio_url, tag)
            print(f"   ❌ 完成但无音频URL: {json.dumps(data, ensure_ascii=False)[:300]}")
            return None

        if status in ("failed", "error"):
            err = data.get("base_resp", {}).get("status_msg", str(data)[:200])
            print(f"   ❌ 生成失败: {err}")
            return None

    print(f"   ❌ 超时（{max_wait}s）")
    return None


def _download(url: str, tag: str):
    """下载音频文件"""
    print(f"   📥 下载中...")
    resp = requests.get(url, timeout=60)
    if resp.status_code != 200:
        print(f"   ❌ 下载失败 HTTP {resp.status_code}")
        return None

    path = OUTPUT_DIR / f"{tag}_{_ts()}.mp3"
    path.write_bytes(resp.content)
    size_kb = len(resp.content) / 1024
    print(f"   ✅ 已保存: {path} ({size_kb:.1f} KB)")
    return str(path)


def _ts():
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("命令: music | cover | lyric")
        return

    cmd = sys.argv[1]

    if cmd == "music":
        if len(sys.argv) < 3:
            print("用法: python minimax_music.py music <风格描述> [--lyrics <歌词>] [--auto-lyrics] [--instrumental]")
            return

        prompt = sys.argv[2]
        lyrics = None
        auto_lyrics = False
        instrumental = False

        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--lyrics" and i + 1 < len(sys.argv):
                lyrics = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--auto-lyrics":
                auto_lyrics = True
                i += 1
            elif sys.argv[i] == "--instrumental":
                instrumental = True
                i += 1
            else:
                i += 1

        generate_music(prompt, lyrics, instrumental, auto_lyrics)

    elif cmd == "cover":
        if len(sys.argv) < 4:
            print("用法: python minimax_music.py cover <音频URL> <风格描述> [--lyrics <歌词>]")
            return

        audio_url = sys.argv[2]
        prompt = sys.argv[3]
        lyrics = None

        i = 4
        while i < len(sys.argv):
            if sys.argv[i] == "--lyrics" and i + 1 < len(sys.argv):
                lyrics = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        generate_cover(audio_url, prompt, lyrics)

    elif cmd == "lyric":
        if len(sys.argv) < 3:
            print("用法: python minimax_music.py lyric <主题>")
            return

        topic = sys.argv[2]
        generate_lyrics(topic)

    else:
        print(f"未知命令: {cmd}")
        print("可用命令: music | cover | lyric")


if __name__ == "__main__":
    main()
