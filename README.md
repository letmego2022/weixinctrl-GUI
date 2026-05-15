# weixinctrl v2

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows_10%2B-blue.svg)](https://github.com/letmego2022/weixinctrl-GUI)

> 一个 sci-fi 风格的微信机器人桌面客户端 —— 在电脑上收发微信消息，用本地 AI 自动回复，插件扩展天气/股市/汇率/号码查询。

## 截图

| 桌面端 | 移动端 |
|:---:|:---:|
| ![电脑端](pic/电脑端.png) | ![微信端](pic/微信端.png) |

## 为什么做这个

出门不带手机时在电脑上回微信；让 AI 帮忙处理重复性的聊天任务；下班前收到今天的聊天总结；随时查天气、股市、汇率不用打开 App。

**所有数据存在本地，不上传云端。**

## 功能

### 消息引擎
- 收发文本、图片、文件、语音、视频 — 基于微信 iLink Bot API
- 媒体文件自动下载，CDN + AES-128 解密
- 聊天记录按天存为 OpenAI 兼容 JSON，可喂给任意 AI 训练

### AI 对话
- 接入 **Ollama** 本地模型，消息来了自动回复
- 自动加载最近 6 条上下文，对话有记忆
- 插件优先：先匹配插件，没命中才走 AI

### 插件系统

| 插件 | 怎么做 | 触发 |
|------|--------|------|
| `weather` | Open-Meteo 实时预报 | 问「天气」或「下雨了吗」；每 3h 降雨预警 |
| `market` | 腾讯财经 + akshare，10 个全球指数 | 问「股市」或「纳斯达克怎么样」；收盘自动推送 |
| `cmb_exchange` | 招行官方 API 美元牌价 | 问「汇率」或「换美元」；每天 8:00 推送 |
| `phone` | MongoDB 索引反查 | `/phone 13800138000` |
| `cmd` | Claude Code CLI 异步执行 | `/cmd 帮我把桌面整理一下` |
| `cc` | Claude Code 读写 Obsidian 知识库 | `/cc 搜索关于微服务的笔记` |
| `daily_summary` | AI 生成结构化总结 | 每天 20:00 自动推送，4 大分类 |
| `minimax_music` | MiniMax AI 音乐创作 | `/music 一首关于夏天的轻快歌曲` |
| `web_search` | 联网搜索 + AI 总结 | `/search 2026年AI最新动态` |

### AI 引擎

全部 AI 调用使用 **MiniMax M2.7**（Anthropic 兼容接口），无需本地 GPU：
- 普通对话、每日总结、命令计划生成
- 音乐歌词创作、搜索结果总结

在 `.env` 中配置 API Key 即可使用。

在聊天框输入 `/help` 查看所有命令：

- **系统信息** — CPU、内存、磁盘、网络状态
- **进程管理** — 搜索 / 结束进程
- **文件搜索** — 集成 Everything (es.exe)
- **网络诊断** — ping、nslookup、netstat、ipconfig
- **窗口管理** — 列出 / 关闭窗口
- **截图** — 截取屏幕发送到微信
- **剪贴板** — 读 / 写剪贴板内容

## 快速开始

```bash
cp .env.example .env               # 编辑 .env 填入 MiniMax API Key
pip install -r requirements.txt    # Python 依赖
python main.py                     # 启动（未登录自动弹扫码页）
```

**前置条件：**

| 软件 | 用途 | 必须 |
|------|------|:---:|
| Python 3.10+ | 运行环境 | ✓ |
| Node.js | 媒体加密 | ✓ |
| MiniMax API | AI 对话 / 音乐 / 搜索（`.env` 配置） | ✓ |
| MongoDB | phone 插件反查 | 可选 |
| Everything (es.exe) | 文件搜索命令 | 可选 |

## 架构

```
┌─────────────────────────────────────────────────┐
│                main.py (GUI)                     │
│  ┌───────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ 消息面板   │  │ 插件面板  │  │  日志面板     │  │
│  │ sci-fi主题 │  │ 一键开关  │  │  按级过滤     │  │
│  └───────────┘  └──────────┘  └──────────────┘  │
└───────────────────┬─────────────────────────────┘
                    │ bridge.py  观察者模式（线程安全）
┌───────────────────▼─────────────────────────────┐
│           worker/poller.py  (后台轮询)            │
│                                                   │
│   get_updates ──► 消息分类 ──► PluginManager       │
│                      │           ├ 关键词/命令匹配  │
│                      │           ├ 定时推送         │
│                      └─ 未命中 ──► AI 兜底回复     │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│              client.py  (核心引擎)                 │
│  微信 API  │  Ollama AI  │  聊天记录  │  媒体处理   │
└─────────────────────────────────────────────────┘
```

## 项目结构

```
v2/
├── main.py                 # GUI 入口
├── client.py               # 微信 API / AI / 聊天记录 / 媒体
├── bridge.py               # 事件总线（观察者模式，线程安全）
├── commands.py             # 内置系统命令注册表
├── standalone-login.mjs    # Node.js 扫码登录
├── encrypt-image.mjs       # 媒体文件 AES-128-ECB 加密
├── gui/
│   ├── main_window.py      # 主窗口 + 工具栏
│   ├── message_panel.py    # 消息日志（终端风格排版）
│   ├── plugin_panel.py     # 插件管理（启用/禁用/上次运行）
│   └── log_panel.py        # 日志面板（ALL/INFO/WARN/ERROR）
├── plugins/
│   ├── __init__.py          # PluginBase（ABC）+ PluginManager
│   ├── weather.py           # Open-Meteo 天气
│   ├── market.py            # 全球股市
│   ├── cmb_exchange.py      # 招行汇率
│   ├── phone.py             # 号码反查
│   ├── cmd.py               # Claude Code CLI
│   ├── cc.py                # Claude Code 知识库
│   ├── daily_summary.py     # 每日总结
│   ├── minimax_music.py     # MiniMax 音乐生成
│   └── web_search.py         # MiniMax 联网搜索
└── worker/
    └── poller.py            # 消息轮询线程
```

## 写插件

继承 `PluginBase`，放在 `plugins/` 目录即可：

```python
from v2.plugins import PluginBase
from typing import Optional

class MyPlugin(PluginBase):
    name = "my_plugin"
    interval = 0        # 定时秒数，0 = 仅消息触发
    enabled = True

    def on_start(self, account, user_id: str) -> Optional[str]:
        return None     # 启动时执行

    def on_interval(self, account, user_id: str) -> Optional[str]:
        return None     # 定时执行，返回要发送的消息

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        from v2.client import extract_text
        text = extract_text(msg)
        if text and "关键词" in text:
            return "匹配到关键词的回复"
        return None     # 不处理则交给下一个插件或 AI
```

## 聊天记录格式

按天分文件在 `chat_logs/`，OpenAI SDK 兼容：

```json
{
  "messages": [
    {"role": "user", "content": "今天天气怎么样", "timestamp": "2026-05-14 10:30:00"},
    {"role": "assistant", "content": "## 📍 上海浦东新区 当前天气\n\n...", "timestamp": "2026-05-14 10:30:05"}
  ]
}
```

## 许可证

MIT — [LICENSE](LICENSE)
