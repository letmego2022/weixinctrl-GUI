#!/usr/bin/env python3
"""
招商银行外汇牌价插件 - 每天早上8点推送汇率报告
"""
import requests
import time
import datetime
from typing import Optional

from . import PluginBase


class CMBExchangePlugin(PluginBase):
    """招商银行美元汇率监控插件"""

    name = "cmb_exchange"
    interval = 300  # 5分钟检查一次
    enabled = True
    MAX_RETRIES = 3

    API_URL = "https://m.cmbchina.com/api/rate/fx-rate"
    PUSH_HOUR = 8

    def __init__(self):
        super().__init__()
        self._last_buy_rate = None
        self._last_sell_rate = None
        self._sent_date = None  # 成功推送的日期
        self._retry_count = 0

    def _fetch_rate(self) -> Optional[dict]:
        """获取招行美元汇率"""
        try:
            resp = requests.get(self.API_URL, timeout=10)
            if resp.status_code != 200:
                self.log_warning(f"API 返回 {resp.status_code}")
                return None
            data = resp.json()
            for item in data.get("body", {}).get("data", []):
                if item.get("ccyNbr") == "美元":
                    return {
                        "buy": float(item["rtbBid"]),
                        "sell": float(item["rthBid"]),
                        "time": item.get("ratTim", ""),
                        "date": item.get("ratDat", ""),
                    }
            self.log_warning("API 返回数据中未找到美元")
            return None
        except Exception as e:
            self.log_error(f"获取汇率失败: {e}")
            return None

    def _should_push_now(self) -> bool:
        """判断是否应该推送（20:00-21:00窗口，每天最多一次）"""
        now = time.localtime()
        today = datetime.date.today().isoformat()

        # 已成功推送
        if self._sent_date == today:
            return False

        # 跨天重置
        if self._sent_date and self._sent_date != today:
            self._retry_count = 0

        # 未到时间
        if now.tm_hour < self.PUSH_HOUR:
            return False

        # 超过1小时放弃
        if now.tm_hour >= self.PUSH_HOUR + 1:
            if self._sent_date != today:
                self.log_info(f"已超过{self.PUSH_HOUR + 1}点，放弃今日推送")
            self._sent_date = today
            return False

        # 达最大重试次数
        if self._retry_count >= self.MAX_RETRIES:
            self._sent_date = today
            self.log_error(f"已达最大重试次数 ({self.MAX_RETRIES})，放弃今日推送")
            return False

        return True

    def _get_trend_emoji(self, rate: float) -> str:
        """根据汇率变化判断趋势"""
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
        spread = buy - sell
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

    def _do_push(self) -> Optional[str]:
        """执行推送，成功返回消息文本，失败返回 None"""
        rate = self._fetch_rate()
        if not rate:
            return None
        self._last_buy_rate = rate["buy"]
        self._last_sell_rate = rate["sell"]
        self._sent_date = datetime.date.today().isoformat()
        self._retry_count = 0
        self.log_info("汇率推送成功")
        return self._format_rate_markdown(rate)

    def on_start(self, account, user_id: str) -> Optional[str]:
        if self._should_push_now():
            return self._do_push()
        return None

    def on_interval(self, account, user_id: str) -> Optional[str]:
        if not self._should_push_now():
            return None

        self._retry_count += 1
        if self._retry_count > 1:
            self.log_info(f"第 {self._retry_count - 1} 次重试...")

        result = self._do_push()
        if result:
            return result

        if self._retry_count >= self.MAX_RETRIES:
            self.log_error("已达最大重试次数，放弃今日推送")
        else:
            self.log_warning(f"获取失败，下个周期重试 ({self._retry_count}/{self.MAX_RETRIES})")
        return None

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        """收到消息时立即查询汇率"""
        from v2.client import extract_text
        text = extract_text(msg)
        if not text:
            return None

        keywords = ["汇率", "换汇", "美元", "外汇", "购汇", "结汇", "币", "外汇牌价", "换成美元", "换成人民币"]
        if not any(k in text for k in keywords):
            return None

        rate = self._fetch_rate()
        if not rate:
            self.log_warning("用户查询汇率失败")
            return "❌ 汇率查询失败，请稍后重试"

        # 更新缓存以保持趋势准确
        if self._last_buy_rate is None:
            self._last_buy_rate = rate["buy"]
            self._last_sell_rate = rate["sell"]

        return self._format_rate_markdown(rate)


if __name__ == "__main__":
    plugin = CMBExchangePlugin()
    rate = plugin._fetch_rate()
    if rate:
        print(plugin._format_rate_markdown(rate))
    else:
        print("获取汇率失败")
