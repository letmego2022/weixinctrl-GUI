"""
fetch_url.py - 网页抓取插件
触发: 消息中包含 http(s):// 链接时自动抓取，或 /fetch <url>
用代理访问 URL，将网页内容转为 Markdown 回复
"""
import re
import threading
from typing import Optional

from v2.plugins import PluginBase

URL_RE = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def _get_proxy() -> str:
    from v2.utils import env
    return env("PROXY_URL")


def _html_to_md(html: str) -> str:
    """HTML → Markdown，优先用 html2text，否则简单提取文本"""
    try:
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0
        return h.handle(html).strip()
    except ImportError:
        pass
    # 回退：简单去标签
    import html.parser

    class Stripper(html.parser.HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
            self._skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style", "noscript"):
                self._skip = True
            elif tag in ("br", "p", "div", "li", "tr"):
                self.parts.append("\n")
            elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                self.parts.append("\n## ")

        def handle_endtag(self, tag):
            if tag in ("script", "style", "noscript"):
                self._skip = False
            elif tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
                self.parts.append("\n")

        def handle_data(self, data):
            if not self._skip:
                self.parts.append(data)

    s = Stripper()
    s.feed(html)
    lines = [l.strip() for l in "".join(s.parts).splitlines()]
    return "\n\n".join(l for l in lines if l)


def _http_get_curl_cffi(url: str, proxy: str, timeout: int) -> str:
    """用 curl_cffi 模拟 Chrome/Safari TLS 指纹抓取，逐个尝试"""

    # 按成功率排序的 impersonate 目标，chrome124 过大部分 Cloudflare
    impersonate_targets = ["chrome124", "safari17_0", "chrome120", "edge101", "firefox116"]

    from curl_cffi import requests as curl_requests

    proxies = {"http": proxy, "https": proxy} if proxy else None
    last_error = None

    for target in impersonate_targets:
        try:
            resp = curl_requests.get(
                url, headers=BROWSER_HEADERS, proxies=proxies,
                timeout=timeout, allow_redirects=True, max_redirects=5,
                impersonate=target,
            )
            resp.raise_for_status()
            _set_encoding(resp)
            return resp.text
        except Exception as e:
            last_error = e
            if "not supported" in str(e).lower():
                continue
            if getattr(e, "response", None) is not None:
                code = e.response.status_code if hasattr(e.response, "status_code") else 0
                if code == 403:
                    continue  # 403 = 被拦截，换下一个目标
            raise  # 其他异常（超时等）直接抛出

    raise last_error


def _set_encoding(resp):
    """设置 response 编码，兼容 curl_cffi 和 requests"""
    try:
        resp.encoding = resp.apparent_encoding or "utf-8"
    except AttributeError:
        # curl_cffi 没有 apparent_encoding，根据 Content-Type 推断
        ct = resp.headers.get("Content-Type", "")
        if "charset=" in ct:
            resp.encoding = ct.split("charset=")[-1].split(";")[0].strip()
        else:
            resp.encoding = "utf-8"


def _http_get_requests(url: str, proxy: str, timeout: int) -> str:
    """requests 降级方案"""
    import requests

    proxies = {"http": proxy, "https": proxy} if proxy else None
    resp = requests.get(
        url, headers=BROWSER_HEADERS, proxies=proxies,
        timeout=timeout, allow_redirects=True,
    )
    resp.raise_for_status()
    _set_encoding(resp)
    return resp.text


def fetch_url_content(url: str, timeout: int = 20) -> Optional[str]:
    """抓取网页并转为 Markdown。
    Tier 1: curl_cffi 模拟 Chrome TLS 指纹（过反爬）
    Tier 2: requests 降级
    """
    proxy = _get_proxy()

    html = None
    errors = []

    # Tier 1: curl_cffi
    try:
        html = _http_get_curl_cffi(url, proxy, timeout)
    except Exception as e:
        errors.append(f"curl_cffi: {e}")

    # Tier 2: requests 降级
    if html is None:
        try:
            html = _http_get_requests(url, proxy, timeout)
        except Exception as e:
            errors.append(f"requests: {e}")

    if html is None:
        return f"❌ 抓取失败（{'；'.join(errors)}）"

    if len(html) > 500_000:
        return "页面过大（超过 500KB），无法抓取"

    md = _html_to_md(html)
    limit = 6000
    if len(md) > limit:
        md = md[:limit] + f"\n\n…（内容已截断，原文 {len(md)} 字符）"
    return md


def _format_error(e: Exception) -> str:
    """格式化异常消息"""
    msg = str(e)
    # 精简常见的超长异常消息
    if len(msg) > 200:
        msg = msg[:200] + "…"
    return msg


class FetchUrlPlugin(PluginBase):
    """网页抓取插件"""

    name = "fetch_url"
    interval = 0
    enabled = True

    def on_start(self, account, user_id: str) -> Optional[str]:
        return None

    def on_interval(self, account, user_id: str) -> Optional[str]:
        return None

    def on_query(self, text: str, account=None, from_user=None, context_token=None) -> Optional[str]:
        """被 AI 路由调用，异步抓取，先返回占位提示"""
        from v2.client import send_message, log_message
        from v2.bridge import bridge

        urls = URL_RE.findall(text)
        if not urls:
            return "未在消息中找到有效链接"

        context_token = context_token or ""
        account_id = account.get("user_id", "") if account else ""

        for url in urls[:3]:
            def run(u=url):
                self.log_info(f"抓取: {u[:60]}")
                try:
                    md = fetch_url_content(u)
                    preview = md if md else f"⚠️ 无法抓取: {u}"
                    send_message(account, from_user, f"## 📄 {u}\n\n{preview}" if md else preview, context_token)
                    if md:
                        bridge.emit_message_sent(f"抓取: {u}")
                        log_message("sent", account_id, from_user, "text", md,
                                    context_token=context_token, sent_via="fetch_url")
                        self.log_info(f"抓取完成: {u[:40]}")
                except Exception as e:
                    self.log_error(f"抓取异常: {e}")
                    send_message(account, from_user, f"❌ 抓取失败: {u}\n{_format_error(e)}", context_token)

            threading.Thread(target=run, daemon=True).start()

        return f"⏳ 正在抓取 {len(urls)} 个链接…" if len(urls) > 1 else "⏳ 正在抓取链接…"

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        """命令路径：/fetch <url>"""
        from v2.client import extract_text, send_message, log_message
        from v2.bridge import bridge

        text = extract_text(msg)
        if not text:
            return None

        if not text.startswith("/fetch"):
            return None

        parts = text[len("/fetch"):].strip().split()
        if not parts:
            return "用法: /fetch <url>\n例如: /fetch https://example.com"
        urls = [u for u in parts if URL_RE.match(u)]
        if not urls:
            return "未识别到有效 URL，请以 http:// 或 https:// 开头"

        context_token = msg.get("context_token", "")
        account_id = account.get("user_id", "")

        for url in urls[:3]:
            def run(u=url):
                self.log_info(f"抓取: {u[:60]}")
                try:
                    md = fetch_url_content(u)
                    preview = md if md else f"⚠️ 无法抓取: {u}"
                    send_message(account, from_user, f"## 📄 {u}\n\n{preview}" if md else preview, context_token)
                    if md:
                        bridge.emit_message_sent(f"抓取: {u}")
                        log_message("sent", account_id, from_user, "text", md,
                                    context_token=context_token, sent_via="fetch_url")
                        self.log_info(f"抓取完成: {u[:40]}")
                except Exception as e:
                    self.log_error(f"抓取异常: {e}")
                    send_message(account, from_user, f"❌ 抓取失败: {u}\n{_format_error(e)}", context_token)

            threading.Thread(target=run, daemon=True).start()

        return f"⏳ 正在抓取 {len(urls)} 个链接…" if len(urls) > 1 else "⏳ 正在抓取链接…"
