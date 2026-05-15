"""
MiniMax Token Plan — 网络搜索 + 图片理解 测试脚本
用法:
  python minimax_search_test.py search "搜索关键词"
  python minimax_search_test.py image "图片URL" "提问"
  python minimax_search_test.py usage
"""
import os
import sys
import json
import requests
from pathlib import Path

# ── 加载 .env ──
def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()

# 优先从 .env 直接读取，避免系统环境变量覆盖
def _env(key, default=""):
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return os.getenv(key, default)

API_KEY = _env("ANTHROPIC_API_KEY")
API_HOST = _env("ANTHROPIC_BASE_URL", "https://api.minimaxi.com/anthropic")
# 提取 base host
if "/anthropic" in API_HOST:
    BASE = API_HOST.split("/anthropic")[0]
else:
    BASE = "https://api.minimaxi.com"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

print(f"API Host: {BASE}")
print(f"API Key:  {API_KEY[:20]}...\n")


def web_search(query: str):
    """网络搜索"""
    print(f"🔍 搜索: {query}\n")

    resp = requests.post(
        f"{BASE}/v1/coding_plan/search",
        headers=HEADERS,
        json={"q": query},
        timeout=30,
    )

    print(f"HTTP {resp.status_code}")

    if resp.status_code != 200:
        print(f"❌ {resp.text[:500]}")
        return

    data = resp.json()
    organic = data.get("organic", [])
    related = data.get("related_searches", [])

    print(f"\n=== 搜索结果 ({len(organic)} 条) ===\n")
    for i, r in enumerate(organic[:8], 1):
        print(f"{i}. {r.get('title', '')}")
        print(f"   🔗 {r.get('link', '')}")
        print(f"   📝 {r.get('snippet', '')[:150]}")
        if r.get("date"):
            print(f"   📅 {r['date']}")
        print()

    if related:
        print(f"=== 相关搜索 ===\n")
        for s in related:
            print(f"  · {s}")


def understand_image(image_url: str, prompt: str):
    """图片理解"""
    print(f"🖼️  图片: {image_url[:80]}...")
    print(f"   提问: {prompt}\n")

    resp = requests.post(
        f"{BASE}/v1/coding_plan/vlm",
        headers=HEADERS,
        json={"image_url": image_url, "prompt": prompt},
        timeout=60,
    )

    print(f"HTTP {resp.status_code}")

    if resp.status_code != 200:
        print(f"❌ {resp.text[:500]}")
        return

    data = resp.json()
    print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])


def check_usage():
    """查询 Token Plan 剩余用量"""
    print("📊 查询用量...\n")

    resp = requests.get(
        f"{BASE}/v1/token_plan/remains",
        headers=HEADERS,
        timeout=10,
    )

    print(f"HTTP {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(json.dumps(data, ensure_ascii=False, indent=2)[:1000])
    else:
        print(f"❌ {resp.text[:500]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else "MiniMax M2.7 最新动态"
        web_search(query)

    elif cmd == "image":
        if len(sys.argv) < 4:
            print("用法: python minimax_search_test.py image <图片URL> <提问>")
            sys.exit(1)
        understand_image(sys.argv[2], sys.argv[3])

    elif cmd == "usage":
        check_usage()

    else:
        print(f"未知命令: {cmd}")
