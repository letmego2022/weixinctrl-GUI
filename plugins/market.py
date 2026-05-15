#!/usr/bin/env python3
"""
全球股市监控插件
- 监控全球主要市场指数
- 收盘后推送涨跌信息
- 数据来源：腾讯财经（美国/香港/A股）+ 东方财富（亚洲/欧洲）
"""
import time
from typing import Optional, Dict

import requests

from . import PluginBase


# 腾讯财经代码（美国/香港/A股）
TENCENT_CODES = {
    "US_NASDAQ": "usIXIC",
    "US_SP500": "usINX",
    "US_DOW": "usDJI",
    "HK": "hkHSI",
    "CN": "sh000001",
}

# 东方财富 secid（亚太/欧洲指数）
# secid格式：市场ID.指数代码
# 市场ID：1=上海，100=全球指数(含日本/韩国/香港/英国/德国/法国等)
EM_SECIDS = {
    "JP_N225": "100.N225",
    "KR_KS11": "100.KS11",
    "HK_HSI": "100.HSI",
    "GB_FTSE": "100.FTSE",
    "DE_GDAXI": "100.GDAXI",
    "FR_FCHI": "100.FCHI",
}

# 合并所有市场配置
# tencent: 腾讯财经代码（美国/香港/A股）
# akshare: akshare中文名称（亚太/欧洲指数，新浪财经源）
MARKETS = [
    {"name": "🇺🇸 纳斯达克", "tencent": "usIXIC", "akshare": None, "region": "US"},
    {"name": "🇺🇸 标普500", "tencent": "usINX", "akshare": None, "region": "US"},
    {"name": "🇺🇸 道琼斯", "tencent": "usDJI", "akshare": None, "region": "US"},
    {"name": "🇯🇵 日经225", "tencent": None, "akshare": "日经225指数", "region": "JP"},
    {"name": "🇰🇷 KOSPI", "tencent": None, "akshare": "首尔综合指数", "region": "KR"},
    {"name": "🇭🇰 恒生指数", "tencent": "hkHSI", "akshare": None, "region": "HK"},
    {"name": "🇨🇳 上证指数", "tencent": "sh000001", "akshare": None, "region": "CN"},
    {"name": "🇬🇧 富时100", "tencent": None, "akshare": "英国富时100指数", "region": "GB"},
    {"name": "🇩🇪 DAX", "tencent": None, "akshare": "德国DAX 30种股价指数", "region": "DE"},
    {"name": "🇫🇷 CAC40", "tencent": None, "akshare": "法CAC40指数", "region": "FR"},
]

# 各市场大致收盘时间（北京时间）
MARKET_CLOSE_TIME = {
    "CN": {"hour": 15, "minute": 0},
    "HK": {"hour": 16, "minute": 0},
    "JP": {"hour": 15, "minute": 0},
    "KR": {"hour": 15, "minute": 30},
    "GB": {"hour": 16, "minute": 30},
    "DE": {"hour": 17, "minute": 30},
    "FR": {"hour": 17, "minute": 30},
    "US": {"hour": 4, "minute": 0},  # 北京时间次日
}


def _fetch_tencent(code: str) -> Optional[Dict]:
    """通过腾讯财经获取指数数据"""
    try:
        url = f"https://qt.gtimg.cn/q={code}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        parts = resp.text.split("~")
        if len(parts) < 33:
            return None
        # parts[3]=当前价, parts[4]=昨日收盘, parts[31]=涨跌额, parts[32]=涨跌幅%, parts[30]=时间
        current = float(parts[3])
        prev_close = float(parts[4])
        change = float(parts[31])
        change_pct = float(parts[32])
        update_time = parts[30]
        return {
            "current": current,
            "prev": prev_close,
            "change": change,
            "change_pct": change_pct,
            "update_time": update_time,
        }
    except Exception:
        return None


def _fetch_eastmoney(secid: str) -> Optional[Dict]:
    """通过东方财富获取指数数据（已弃用，保留备用）"""
    try:
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f44,f57,f58,f60"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        d = data.get("data")
        if not d:
            return None
        current = d["f43"] / 100
        prev_close = d["f44"] / 100
        change = current - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        return {
            "current": current,
            "prev": prev_close,
            "change": change,
            "change_pct": change_pct,
            "update_time": str(d.get("f60", "")),
        }
    except Exception:
        return None


def _fetch_akshare(symbol_zh: str) -> Optional[Dict]:
    """通过akshare获取全球指数数据（新浪财经源）"""
    try:
        import akshare as ak
        df = ak.index_global_hist_sina(symbol=symbol_zh)
        if df is None or df.empty:
            return None
        latest = df.iloc[-1]
        current = float(latest["close"])
        prev = float(latest["open"])  # 用开盘价作昨日收盘的近似
        change = current - prev
        change_pct = (change / prev * 100) if prev else 0
        update_time = str(latest.get("date", ""))
        return {
            "current": current,
            "prev": prev,
            "change": change,
            "change_pct": change_pct,
            "update_time": update_time,
        }
    except Exception:
        return None


def _judge_trend(change_pct: float) -> str:
    """根据涨跌幅判断短期情绪"""
    if change_pct >= 1.5:
        return "📈 强势上涨"
    elif change_pct >= 0.5:
        return "🟢 小幅上涨"
    elif change_pct <= -1.5:
        return "📉 强势下跌"
    elif change_pct <= -0.5:
        return "🔴 小幅下跌"
    elif change_pct >= 0:
        return "➡️ 窄幅震荡"
    else:
        return "➡️ 窄幅震荡"


class MarketPlugin(PluginBase):
    """全球股市监控插件"""

    name = "market"
    interval = 300  # 每5分钟检查一次
    enabled = True

    def __init__(self):
        super().__init__()
        self._pending_close: Dict[str, str] = {}  # region -> date（今天已推送过）
        self._msg_cache: Dict[str, tuple] = {}  # code -> (data, timestamp)

    def _fetch_one(self, market: Dict) -> Optional[Dict]:
        """获取单个指数数据"""
        tencent_code = market.get("tencent")
        akshare_symbol = market.get("akshare")

        if tencent_code:
            data = _fetch_tencent(tencent_code)
            if data:
                data["trend"] = _judge_trend(data["change_pct"])
                return data

        if akshare_symbol:
            data = _fetch_akshare(akshare_symbol)
            if data:
                data["trend"] = _judge_trend(data["change_pct"])
                return data

        return None

    def _fetch_one_cached(self, market: Dict) -> Optional[Dict]:
        """获取单个指数数据（有5分钟缓存，用于用户查询）"""
        code = market.get("tencent") or market.get("akshare")
        now = time.time()

        if code in self._msg_cache:
            data, ts = self._msg_cache[code]
            if now - ts < 300:
                return data

        data = self._fetch_one(market)
        if data:
            self._msg_cache[code] = (data, now)
        return data

    def _should_push_for_region(self, region: str) -> bool:
        """判断某个区域是否应该推送（只在收盘时间点触发一次）"""
        close_info = MARKET_CLOSE_TIME.get(region)
        if not close_info:
            return False

        now = time.localtime()
        close_hour = close_info["hour"]
        close_min = close_info["minute"]

        if region == "US":
            # 美股收盘是北京时间次日04:00
            now_mins = now.tm_hour * 60 + now.tm_min
            close_mins = close_hour * 60 + close_min
            if now.tm_hour < 12:
                now_mins += 24 * 60
            close_mins += 24 * 60
        else:
            now_mins = now.tm_hour * 60 + now.tm_min
            close_mins = close_hour * 60 + close_min

        # 是否在收盘时间点+10分钟窗口内
        in_window = close_mins <= now_mins < close_mins + 10
        if not in_window:
            return False

        # 每天只推送一次
        import datetime
        date_key = datetime.date.today().isoformat()

        if self._pending_close.get(region) == date_key:
            return False

        self._pending_close[region] = date_key
        return True

    def _format_markdown(self, market: Dict, data: Dict) -> str:
        """格式化单个市场信息（表格行格式）"""
        name = market["name"]
        current = data["current"]
        change = data["change"]
        change_pct = data["change_pct"]
        trend = data["trend"]
        sign = "+" if change >= 0 else ""
        return f"| {name} | {current:,.2f} | {sign}{change:,.2f}（{change_pct:+.2f}%） | {trend} |"

    def _do_push(self) -> Optional[str]:
        """执行推送：检查每个区域是否到点，到点则推送对应市场的收盘数据"""
        pushed_any = False
        lines = ["## 🌍 全球股市收盘播报\n"]

        for m in MARKETS:
            region = m["region"]
            if not self._should_push_for_region(region):
                continue

            data = self._fetch_one(m)
            if not data:
                continue

            lines.append(self._format_markdown(m, data))
            pushed_any = True

        if not pushed_any:
            return None

        # 补上表格头
        header = "| 市场 | 点位 | 涨跌 | 趋势 |\n|:---|---:|---:|:---:|\n"
        title = lines[0]  # "## 🌍 全球股市收盘播报\n"
        rows = "\n".join(lines[1:])
        return title + header + rows

    def on_start(self, account, user_id: str) -> Optional[str]:
        return None  # 启动时不推送

    def on_interval(self, account, user_id: str) -> Optional[str]:
        return self._do_push()

    def on_query(self, text: str, account=None, from_user=None, context_token=None) -> Optional[str]:
        """被 AI 意图分类路由调用"""
        results = []
        for m in MARKETS:
            data = self._fetch_one_cached(m)
            if data:
                results.append((m, data))

        if not results:
            self.log_warning("行情查询失败：全部指数获取失败")
            return "❌ 行情查询失败，请稍后重试"

        lines = ["## 📊 全球股市实时行情\n",
                 "| 市场 | 点位 | 涨跌 | 趋势 |",
                 "|:---|---:|---:|:---:|"]
        for m, data in results:
            lines.append(self._format_markdown(m, data))

        return "\n".join(lines)

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        """收到消息时查询股市（关键词匹配，保留兼容）"""
        from v2.client import extract_text
        text = extract_text(msg)
        if not text:
            return None

        keywords = ["股市", "指数", "行情", "纳指", "日经", "恒生", "上证", "大盘"]
        if not any(k in text for k in keywords):
            return None

        return self.on_query(text)


if __name__ == "__main__":
    plugin = MarketPlugin()
    for m in MARKETS:
        data = plugin._fetch_one(m)
        if data:
            print(plugin._format_markdown(m, data))
        else:
            print(f"{m['name']}: 获取失败")
