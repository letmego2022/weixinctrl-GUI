#!/usr/bin/env python3
"""
天气监控插件
- 每3小时检查一次天气
- 如果3小时内有降雨，主动发送提醒
"""
import time
import requests
from typing import Optional

from . import PluginBase


class WeatherPlugin(PluginBase):
    """天气监控插件"""

    name = "weather"
    interval = 3 * 3600  # 每3小时
    enabled = True

    # 降雨天气码
    BAD_WEATHER_CODES = {
        51, 53, 55, 56, 57,   # 毛毛雨
        61, 63, 65, 66, 67,   # 雨
        71, 73, 75, 77,       # 雪
        80, 81, 82,           # 阵雨
        85, 86,               # 阵雪
        95, 96, 99,           # 雷暴
    }
    PRECIP_THRESHOLD = 50  # 降水概率阈值

    def __init__(self):
        super().__init__()
        self._cached_location = None

    def _get_location(self):
        """获取位置（带缓存）"""
        if self._cached_location:
            return self._cached_location

        # 固定上海浦东新区
        self._cached_location = (31.2304, 121.4737, "上海浦东新区")
        return self._cached_location

    def _query_weather(self, lat, lon):
        """查询天气（Open-Meteo API），返回 (data, error_msg)"""
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "hourly": "temperature_2m,precipitation_probability,weather_code",
            "forecast_days": 1,
            "timezone": "auto",
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                self.log_warning(f"Open-Meteo API 返回 {resp.status_code}")
                return None, f"API 返回错误状态 {resp.status_code}"
            return resp.json(), None
        except requests.exceptions.ConnectionError:
            self.log_error("天气查询失败：无法连接 Open-Meteo API")
            return None, "网络连接失败，无法访问天气服务"
        except requests.exceptions.Timeout:
            self.log_error("天气查询超时")
            return None, "天气服务响应超时，请稍后重试"
        except Exception as e:
            self.log_error(f"天气查询失败: {e}")
            return None, f"天气查询异常: {e}"

    def _get_description(self, code):
        """天气码转中文"""
        descriptions = {
            0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
            45: "雾", 48: "雾凇",
            51: "毛毛雨(小)", 53: "毛毛雨(中)", 55: "毛毛雨(大)",
            56: "冻毛毛雨(小)", 57: "冻毛毛雨(大)",
            61: "小雨", 63: "中雨", 65: "大雨",
            66: "冻雨(小)", 67: "冻雨(大)",
            71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
            80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
            85: "小阵雪", 86: "大阵雪",
            95: "雷暴", 96: "雷暴+冰雹", 99: "雷暴+大冰雹",
        }
        return descriptions.get(code, f"未知({code})")

    def _check_rain(self, data):
        """检查是否有降雨"""
        hourly = data.get("hourly", {})
        weather_codes = hourly.get("weather_code", [])
        precip_probs = hourly.get("precipitation_probability", [])
        temps = hourly.get("temperature_2m", [])

        current_hour = time.localtime().tm_hour
        alerts = []

        for i in range(current_hour, min(current_hour + 3, len(weather_codes))):
            code = weather_codes[i] if i < len(weather_codes) else 0
            precip = precip_probs[i] if i < len(precip_probs) else 0
            temp = temps[i] if i < len(temps) else 0

            # 晴天=0, 晴间多云=1, 多云=2, 阴=3 - 这些单纯因为降水概率高就提醒不合理
            CLEAR_CODES = {0, 1, 2, 3}
            if (code in self.BAD_WEATHER_CODES) or (code not in CLEAR_CODES and precip >= self.PRECIP_THRESHOLD):
                desc = self._get_description(code)
                alerts.append(f"| {i}:00 | {desc} | {precip}% | {temp}°C |")

        return alerts

    def on_start(self, account, user_id: str) -> Optional[str]:
        """启动时检查天气"""
        return self._check_and_alert()

    def on_interval(self, account, user_id: str) -> Optional[str]:
        """定时检查天气"""
        return self._check_and_alert()

    def _check_and_alert(self) -> Optional[str]:
        """检查天气并返回提醒"""
        lat, lon, city = self._get_location()
        data, _err = self._query_weather(lat, lon)
        if not data:
            return None

        alerts = self._check_rain(data)
        if not alerts:
            return None

        return f"## 🌧️ {city} 天气提醒\n\n未来3小时有降雨：\n\n| 时间 | 天气 | 降水概率 | 温度 |\n|------|------|----------|------|\n" + "\n".join(alerts)

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        """处理用户消息"""
        from v2.client import extract_text
        text = extract_text(msg)

        # 处理天气相关命令
        if text and ("天气" in text or "下雨" in text or "雨" in text):
            # 立即查询天气
            lat, lon, city = self._get_location()
            data, err = self._query_weather(lat, lon)
            if not data:
                self.log_warning(f"用户查询天气失败: {err}")
                return f"❌ {err}"

            current = data.get("current", {})
            temp = current.get("temperature_2m")
            humidity = current.get("relative_humidity_2m")
            weather_code = current.get("weather_code")
            desc = self._get_description(weather_code) if weather_code is not None else "未知"

            alerts = self._check_rain(data)
            rain_rows = ""
            if alerts:
                rain_rows = "| 🌧️ 未来3小时 | 天气 | 降水概率 | 温度 |\n" + \
                            "|------|--------|----------|------|\n" + \
                            "\n".join(alerts)

            return (
                f"## 📍 {city} 当前天气\n\n"
                f"| 项目 | 数值 |\n"
                f"|------|------|\n"
                f"| 🌡️ 温度 | {temp}°C |\n"
                f"| 💧 湿度 | {humidity}% |\n"
                f"| ☁️ 天气 | {desc} |\n"
                + (f"\n{rain_rows}\n" if rain_rows else "")
            )

        return None
