"""
web_search.py - MiniMax 联网搜索插件
触发: /search <关键词> → 搜索 + AI 总结回答
"""
import threading
import requests
from pathlib import Path
from typing import Optional

from v2.plugins import PluginBase


def do_search(query: str) -> Optional[str]:
    """执行搜索并返回 AI 总结"""
    from v2.utils import minimax_key, minimax_base, minimax_url
    api_key = minimax_key()
    base = minimax_base()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Step 1: 搜索
    search_resp = requests.post(
        f"{base}/v1/coding_plan/search",
        headers=headers,
        json={"q": query},
        timeout=30,
    )
    if search_resp.status_code != 200:
        return None

    results = search_resp.json().get("organic", [])
    if not results:
        return "未找到相关结果。"

    # Step 2: 构建上下文
    snippets = []
    for i, r in enumerate(results[:8], 1):
        snippets.append(f"[{i}] {r.get('title', '')}\n{r.get('snippet', '')[:300]}")

    context = "\n\n".join(snippets)

    # Step 3: AI 总结
    prompt = f"""用户问题：{query}

以下是最新的网络搜索结果：
{context}

请根据搜索结果回答用户问题。要求：
- 简洁直接，不超过 300 字
- 引用具体来源（用 [N] 标注）
- 如果搜索结果不足，诚实说明"""

    ai_resp = requests.post(
        minimax_url(),
        headers=headers,
        json={
            "model": "MiniMax-M2.7",
            "max_tokens": 800,
            "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )

    if ai_resp.status_code != 200:
        return "AI 总结失败，请稍后重试。"

    data = ai_resp.json()
    content = data.get("content", "")
    if isinstance(content, list):
        content = "".join(b.get("text", "") for b in content if b.get("type") == "text")

    return content.strip() if content else "AI 未生成有效回答。"


# ── 插件 ───────────────────────────────────────────────────────────────────

class WebSearchPlugin(PluginBase):
    """联网搜索插件"""

    name = "web_search"
    interval = 0
    enabled = True

    def on_start(self, account, user_id: str) -> Optional[str]:
        return None

    def on_interval(self, account, user_id: str) -> Optional[str]:
        return None

    def on_query(self, text: str, account=None, from_user=None, context_token=None) -> Optional[str]:
        """被 AI 意图分类路由调用"""
        return do_search(text)

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        from v2.client import extract_text, send_message, log_message
        from v2.bridge import bridge

        text = extract_text(msg)
        if not text or not text.startswith("/search"):
            return None

        query = text[len("/search"):].strip()
        if not query:
            return "用法: /search <关键词>\n例如: /search 2026年5月 AI 最新动态"

        context_token = msg.get("context_token", "")
        account_id = account.get("user_id", "")

        def run():
            self.log_info(f"搜索: {query[:40]}...")
            answer = do_search(query)
            if answer:
                send_message(account, from_user, f"🔍 {query}\n\n{answer}", context_token)
                bridge.emit_message_sent(f"🔍 {query}")
                log_message("sent", account_id, from_user, "text", answer, context_token=context_token)
                self.log_info("搜索完成")
            else:
                send_message(account, from_user, "❌ 搜索失败，请稍后重试", context_token)
                self.log_error("搜索失败")

        threading.Thread(target=run, daemon=True).start()
        return f"⏳ 正在搜索并分析…\n关键词: {query}"
