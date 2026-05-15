"""
utils.py - 共享工具函数
"""
import os
from pathlib import Path

_ENV_PATH = Path(__file__).parent / ".env"


def _read_env():
    """读取 .env 为 dict（带缓存）"""
    if not hasattr(_read_env, "_cache"):
        _read_env._cache = {}
        if _ENV_PATH.exists():
            for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    _read_env._cache[k.strip()] = v.strip()
    return _read_env._cache


def env(key, default=""):
    """读取 .env 中的配置项"""
    return _read_env().get(key, default)


def minimax_key():
    """MiniMax API Key"""
    return env("ANTHROPIC_API_KEY")


def minimax_base():
    """MiniMax API 纯 host（去掉 /anthropic 路径后缀）"""
    url = env("ANTHROPIC_BASE_URL", "https://api.minimaxi.com/anthropic")
    return url.split("/anthropic")[0] if "/anthropic" in url else url


def minimax_url():
    """MiniMax Anthropic 兼容接口完整 URL"""
    return minimax_base() + "/anthropic/v1/messages"
