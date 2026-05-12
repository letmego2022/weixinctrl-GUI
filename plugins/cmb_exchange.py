#!/usr/bin/env python3
"""
招商银行外汇牌价插件 - 每天早上8点推送汇率报告
"""
import requests
import time
from typing import Optional

from . import PluginBase


class CMBExchangePlugin(PluginBase):
    """招商银行美元汇率监控插件"""

    name = "cmb_exchange"
    interval = 300  # 检查间隔（秒），每5分钟检查一次是否到8点
    enabled = True

    # 招行外汇 API
    API_URL = "https://m.cmbchina.com/api/rate/fx-rate"
    # 推送时间：每天早上8点
    PUSH_HOUR = 8
    PUSH_MINUTE = 0

    def __init__(self):
        super().__init__()
        self._last_buy_rate = None
        self._last_sell_rate = None
        self._last_push_date = None  # 上次推送日期，用于控制每天只发一次

    def _fetch_rate(self) -> Optional[dict]:
        """获取招行美元汇率"""
        try:
            resp = requests.get(self.API_URL, timeout=10)
            if resp.status_code != 200:
                return None
            data = resp.json()
            for item in data.get("body", {}).get("data", []):
                if item.get("ccyNbr") == "美元":
                    return {
                        "buy": float(item["rtbBid"]),    # 购汇汇率（银行卖美元）
                        "sell": float(item["rthBid"]),   # 结汇汇率（银行买美元）
                        "time": item.get("ratTim", ""),
                        "date": item.get("ratDat", ""),
                    }
            return None
        except Exception:
            return None

    def _should_push_now(self) -> bool:
        """判断是否应该推送（每天8点只发一次）"""
        now = time.localtime()
        if now.tm_hour == self.PUSH_HOUR and now.tm_min < self.PUSH_MINUTE + 10:
            today = f"{now.tm_year}-{now.tm_mon}-{now.tm_mday}"
            if self._last_push_date != today:
                self._last_push_date = today
                return True
        return False

    def _get_trend_emoji(self, rate: float) -> str:
        """根据汇率获取趋势表情（相对于近期均值判断）"""
        if self._last_buy_rate is None:
            return "➡️"
        diff = rate - self._last_buy_rate
        if diff > 0.3:
            return "📈"
        elif diff < -0.3:
            return "📉"
        return "➡️"

    def _format_rate_markdown(self, rate: dict) -> str:
        """格式化汇率信息为 Markdown"""
        buy = rate["buy"]
        sell = rate["sell"]
        trend = self._get_trend_emoji(buy)
        spread = buy - sell  # 买卖价差
        # 换算成 1 美元 = 多少人民币
        buy_per_usd = buy / 100
        sell_per_usd = sell / 100

        return f"""## 📊 招商银行 · 美元汇率

**日期**: {rate['date']} {rate['time']}

---

| 类型 | 汇率 |
|:---:|:---:|
| 💱 购汇（买美元） | **{buy}** 元/100美元 |
| 💰 结汇（卖美元） | **{sell}** 元/100美元 |

---

> 💡 1 USD ≈ **{buy_per_usd:.4f}** CNY（购汇）
> 💡 1 USD ≈ **{sell_per_usd:.4f}** CNY（结汇）
> 📊 买卖价差: **{spread:.2f}** 元/100美元

{trend} 数据来源: 招商银行官方牌价"""

    def on_start(self, account, user_id: str) -> Optional[str]:
        """启动时检查是否8点，直接推送"""
        if self._should_push_now():
            return self._do_push()
        return None

    def on_interval(self, account, user_id: str) -> Optional[str]:
        """定时检查是否到8点"""
        if self._should_push_now():
            return self._do_push()
        return None

    def _do_push(self) -> Optional[str]:
        """执行推送"""
        rate = self._fetch_rate()
        if not rate:
            return None
        self._last_buy_rate = rate["buy"]
        self._last_sell_rate = rate["sell"]
        return self._format_rate_markdown(rate)

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        """收到消息时，立即查询汇率"""
        from client import extract_text
        text = extract_text(msg)
        if not text:
            return None

        # 汇率查询关键词
        keywords = ["汇率", "换汇", "美元", "外汇", "购汇", "结汇", "币", "外汇牌价", "换成美元", "换成人民币"]
        if not any(k in text for k in keywords):
            return None

        rate = self._fetch_rate()
        if not rate:
            return "❌ 汇率查询失败，请稍后重试"

        return self._format_rate_markdown(rate)


if __name__ == "__main__":
    plugin = CMBExchangePlugin()
    rate = plugin._fetch_rate()
    if rate:
        print(plugin._format_rate_markdown(rate))
    else:
        print("获取汇率失败")