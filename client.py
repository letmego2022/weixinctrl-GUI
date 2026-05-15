#!/usr/bin/env python3
"""
微信客户端 - 执行引擎
├─ /cmd <需求>  → Claude Code CLI
├─ /cc <需求>   → Claude Code 操作 Obsidian 知识库
└─ <其他文字>   → AI 对话
"""
import base64
import hashlib
import json
import logging
import os
import random
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import mss
import requests
from Crypto.Cipher import AES as _PyAES

# ── 日志配置 ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("weixin")

# ── 常量 ──────────────────────────────────────────────────────────────────────
CHANNEL_VERSION = "2.1.8"
POLL_INTERVAL = 1
POLL_INTERVAL_WITH_MSG = 0.5
MAX_RESPONSE_LEN = 2000
MAX_IMAGE_DIM = 1600
IMAGE_QUALITY = 80
CURSOR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".cursor")
PROCESSED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed")
RECEIVED_PICS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "received", "received_pics")
RECEIVED_FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "received", "received_files")
RECEIVED_VIDEOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "received", "received_videos")
PIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pic")

# ── 插件系统 ──────────────────────────────────────────────────────────────────
# ── Claude Code CLI 系统提示 ───────────────────────────────────────────────────
CC_SYSTEM_PROMPT = """\
你是一个文件处理助手，**不要分析当前项目代码**。

文件位置：
- 图片目录: {received_pics_dir}/
- 文件目录: {received_files_dir}/
- 视频目录: {received_videos_dir}/
- 你的输出目录: {processed_dir}/

**重要规则**：
1. 找图片就去 {received_pics_dir}/，找文件就去 {received_files_dir}/，按时间倒序取最新的
2. 处理完成后，必须把输出文件路径写成一行：[OUTPUT_FILE] /absolute/path/to/output.file
3. 图片处理用 Python + PIL，文档处理也写到 {processed_dir}/
4. 绝对不要只说"已保存"，必须标注 [OUTPUT_FILE] 才能发送
"""

# ── 配置 ──────────────────────────────────────────────────────────────────────

STATE_DIR = os.path.join(os.path.expanduser("~"), ".openclaw", "openclaw-weixin")
ACCOUNTS_DIR = os.path.join(STATE_DIR, "accounts")
CONFIG_FILE = os.path.join(STATE_DIR, "config.json")

# ── 聊天记录存储（OpenAI SDK 兼容格式）────────────────────────────────────────
CHAT_LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_logs")

def get_chat_log_path():
    """获取当天的聊天记录文件路径"""
    date_str = time.strftime("%Y-%m-%d")
    return os.path.join(CHAT_LOGS_DIR, f"chat_{date_str}.json")

def load_chat_log():
    """加载当天的聊天记录"""
    path = get_chat_log_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.warning("聊天记录加载失败，使用空记录")
            return {"messages": []}
    return {"messages": []}

def save_chat_log(log):
    """保存聊天记录到文件"""
    os.makedirs(CHAT_LOGS_DIR, exist_ok=True)
    path = get_chat_log_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def log_message(direction, from_user, to_user, message_type, content, context_token=None, file_path=None, sent_via=None):
    """
    记录一条消息到聊天记录，格式兼容 OpenAI SDK。

    direction: "received" -> role="user", "sent" -> role="assistant"
    content: 文本字符串 或 图片消息的 [{"type": "text", ...}, {"type": "image_url", ...}]
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    role = "user" if direction == "received" else "assistant"
    bot_id = "bot"

    # 构建 OpenAI 格式的消息
    if message_type == "image" and file_path:
        # 图片消息：content 为多模态数组
        # 本地文件用 file:// URI，AI 实际调用时需转换为 base64
        content_blocks = [{"type": "text", "text": content}]
        if os.path.exists(file_path):
            content_blocks.append({
                "type": "image_url",
                "image_url": {"url": f"file://{file_path}"}
            })
        msg_entry = {
            "role": role,
            "content": content_blocks,
            "name": from_user if direction == "received" else bot_id,
            "sent_via": sent_via,
            "timestamp": timestamp,
        }
    else:
        # 文本消息
        msg_entry = {
            "role": role,
            "content": content,
            "name": from_user if direction == "received" else bot_id,
            "sent_via": sent_via,
            "timestamp": timestamp,
        }

    if context_token:
        msg_entry["context_token"] = context_token

    log = load_chat_log()
    log["messages"].append(msg_entry)
    save_chat_log(log)

# ── 账号加载 ──────────────────────────────────────────────────────────────────
def load_account():
    if not os.path.exists(CONFIG_FILE):
        print("未登录，请先运行 standalone-login.mjs")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    account_id = config.get("current_account")
    if not account_id:
        sys.exit(1)
    account_file = os.path.join(ACCOUNTS_DIR, f"{account_id}.json")
    if not os.path.exists(account_file):
        sys.exit(1)
    with open(account_file, "r", encoding="utf-8") as f:
        return json.load(f)


def random_uint32_base64():
    # 官方方式：uint32数字 -> 字符串 -> base64（如 305419896 -> "MzA1NDE5ODk2"）
    uint32 = random.randint(0, 2**32 - 1)
    return base64.b64encode(str(uint32).encode("utf-8")).decode()


# ── 微信 API ──────────────────────────────────────────────────────────────────
def api_post(endpoint, account, data, timeout=40):
    base_url = account.get("base_url", "https://ilinkai.weixin.qq.com")
    url = f"{base_url}/{endpoint}"
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "X-WECHAT-UIN": random_uint32_base64(),
            "AuthorizationType": "ilink_bot_token",
            "Authorization": f"Bearer {account.get('bot_token', '')}",
            "iLink-App-Id": "bot",
            "iLink-App-ClientVersion": "131336",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            result = json.loads(raw) if raw.strip() else {}
            result["_http_status"] = resp.status
            return result
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except:
            return {"ret": -1, "errmsg": f"HTTP {e.code}"}
    except Exception as e:
        return {"ret": -1, "errmsg": str(e)}


def get_updates(account, cursor=""):
    """
    长轮询获取新消息。
    - 超时30秒，连续空消息8次后强制重置 cursor 重新建连
    - 每次失败自动清空 cursor 重试（最多3次）
    """
    # 用函数属性持久化连续空消息计数（跨调用保持）
    empty_count = getattr(get_updates, "_empty_count", 0)

    for attempt in range(3):
        try:
            resp = api_post("ilink/bot/getupdates", account, {"get_updates_buf": cursor}, timeout=30)
            ret = resp.get("ret")

            if ret is not None and ret != 0:
                if ret in (-1, 12002) or "timeout" in resp.get("errmsg", "").lower():
                    cursor = ""
                    empty_count = 0
                    get_updates._empty_count = 0
                    continue
                return [], cursor

            msgs = resp.get("msgs", [])
            new_cursor = resp.get("get_updates_buf", cursor)

            if not msgs:
                empty_count += 1
                get_updates._empty_count = empty_count
                # 连续8次空消息（约4分钟）说明连接可能已断，强制重置 cursor
                if empty_count >= 8:
                    cursor = ""
                    empty_count = 0
                    get_updates._empty_count = 0
                    continue
            else:
                # 有消息则重置计数
                empty_count = 0
                get_updates._empty_count = 0

            # 持久化 cursor 到文件
            try:
                with open(CURSOR_FILE, "w") as f:
                    f.write(new_cursor)
            except Exception:
                logger.debug("cursor 持久化失败")
            return msgs, new_cursor

        except Exception as e:
            cursor = ""
            empty_count = 0
            get_updates._empty_count = 0
            time.sleep(2)

    get_updates._empty_count = 0
    return [], cursor  # 3次都失败


def send_image_message(account, to_user_id, image_path, context_token=None):
    """发送图片消息（CDN 上传方式）"""
    result = subprocess.run(
        ["node", "encrypt-image.mjs", image_path],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        return {"ret": -1, "errmsg": f"加密脚本失败: {result.stderr}"}
    data = json.loads(result.stdout)

    filekey = data["filekey"]
    aeskey_hex = data["aeskey_hex"]
    aeskey_base64 = data["aeskey_base64"]
    ciphertext = base64.b64decode(data["ciphertext_base64"])
    filesize = data["filesize"]
    rawsize = data["rawsize"]
    rawfilemd5 = data["rawfilemd5"]

    # 获取上传 URL（官方需要 base_info 字段）
    req_data = {
        "filekey": filekey,
        "media_type": 1,
        "to_user_id": to_user_id,
        "rawsize": rawsize,
        "rawfilemd5": rawfilemd5,
        "filesize": filesize,
        "no_need_thumb": True,
        "aeskey": aeskey_hex,
        "base_info": {"channel_version": CHANNEL_VERSION},
    }
    upload_resp = api_post("ilink/bot/getuploadurl", account, req_data, timeout=15)
    upload_url = upload_resp.get("upload_full_url", "")
    if not upload_url:
        return {"ret": -1, "errmsg": f"获取上传URL失败: {upload_resp}"}

    # POST 上传加密数据到 CDN
    req = urllib.request.Request(
        upload_url,
        data=ciphertext,
        headers={"Content-Type": "application/octet-stream"},
        method="POST",
    )
    enc_param = None
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_headers = dict(resp.headers)
            enc_param = resp_headers.get("x-encrypted-param", "")
            if not enc_param:
                return {"ret": -1, "errmsg": "CDN响应缺少x-encrypted-param"}
    except Exception as e:
        return {"ret": -1, "errmsg": f"CDN上传失败: {e}"}

    # 发送图片消息
    msg = {
        "from_user_id": "",
        "to_user_id": to_user_id,
        "client_id": str(uuid.uuid4()),
        "message_type": 2,
        "message_state": 2,
        "item_list": [
            {
                "type": 2,  # IMAGE
                "image_item": {
                    "media": {
                        "encrypt_query_param": enc_param,
                        "aes_key": aeskey_base64,
                        "encrypt_type": 1,
                    },
                    "mid_size": filesize,
                },
            }
        ],
    }
    if context_token:
        msg["context_token"] = context_token

    return api_post("ilink/bot/sendmessage", account, {"msg": msg, "base_info": {"channel_version": CHANNEL_VERSION}}, timeout=15)


def send_file_message(account, to_user_id, file_path, context_token=None):
    """发送文件消息（CDN 上传方式）"""

    if not os.path.exists(file_path):
        return {"ret": -1, "errmsg": f"文件不存在: {file_path}"}

    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)

    # 读取文件内容并计算 hash
    with open(file_path, "rb") as f:
        file_data = f.read()
    rawfilemd5 = hashlib.md5(file_data).hexdigest()

    # 加密
    r = subprocess.run(
        ["node", "encrypt-image.mjs", file_path],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        return {"ret": -1, "errmsg": f"加密失败: {r.stderr}"}
    enc = json.loads(r.stdout)
    ciphertext = base64.b64decode(enc["ciphertext_base64"])

    # 获取上传 URL (media_type=3 for FILE)
    req_data = {
        "filekey": enc["filekey"],
        "media_type": 3,
        "to_user_id": to_user_id,
        "rawsize": enc["rawsize"],
        "rawfilemd5": enc["rawfilemd5"],
        "filesize": enc["filesize"],
        "no_need_thumb": True,
        "aeskey": enc["aeskey_hex"],
        "base_info": {"channel_version": CHANNEL_VERSION},
    }
    upload_resp = api_post("ilink/bot/getuploadurl", account, req_data, timeout=15)
    upload_url = upload_resp.get("upload_full_url", "")
    if not upload_url:
        return {"ret": -1, "errmsg": f"获取上传URL失败: {upload_resp}"}

    # 上传到 CDN
    req = urllib.request.Request(
        upload_url,
        data=ciphertext,
        headers={"Content-Type": "application/octet-stream"},
        method="POST",
    )
    enc_param = None
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            enc_param = dict(resp.headers).get("x-encrypted-param", "")
            if not enc_param:
                return {"ret": -1, "errmsg": "CDN响应缺少x-encrypted-param"}
    except Exception as e:
        return {"ret": -1, "errmsg": f"CDN上传失败: {e}"}

    # 发送文件消息
    msg = {
        "from_user_id": "",
        "to_user_id": to_user_id,
        "client_id": str(uuid.uuid4()),
        "message_type": 2,
        "message_state": 2,
        "item_list": [
            {
                "type": 4,  # FILE
                "file_item": {
                    "media": {
                        "encrypt_query_param": enc_param,
                        "aes_key": enc["aeskey_base64"],
                        "encrypt_type": 1,
                    },
                    "file_name": file_name,
                    "len": str(file_size),
                }
            }
        ],
    }
    if context_token:
        msg["context_token"] = context_token

    return api_post("ilink/bot/sendmessage", account, {"msg": msg, "base_info": {"channel_version": CHANNEL_VERSION}}, timeout=15)


def send_video_message(account, to_user_id, video_path, context_token=None):
    """发送视频消息（CDN 上传方式）"""

    if not os.path.exists(video_path):
        return {"ret": -1, "errmsg": f"视频不存在: {video_path}"}

    file_size = os.path.getsize(video_path)

    # 加密
    r = subprocess.run(
        ["node", "encrypt-image.mjs", video_path],
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        return {"ret": -1, "errmsg": f"加密失败: {r.stderr}"}
    enc = json.loads(r.stdout)
    ciphertext = base64.b64decode(enc["ciphertext_base64"])

    # 获取上传 URL (media_type=2 for VIDEO)
    req_data = {
        "filekey": enc["filekey"],
        "media_type": 2,
        "to_user_id": to_user_id,
        "rawsize": enc["rawsize"],
        "rawfilemd5": enc["rawfilemd5"],
        "filesize": enc["filesize"],
        "no_need_thumb": True,
        "aeskey": enc["aeskey_hex"],
        "base_info": {"channel_version": CHANNEL_VERSION},
    }
    upload_resp = api_post("ilink/bot/getuploadurl", account, req_data, timeout=15)
    upload_url = upload_resp.get("upload_full_url", "")
    if not upload_url:
        return {"ret": -1, "errmsg": f"获取上传URL失败: {upload_resp}"}

    # 上传到 CDN
    req = urllib.request.Request(
        upload_url,
        data=ciphertext,
        headers={"Content-Type": "application/octet-stream"},
        method="POST",
    )
    enc_param = None
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            enc_param = dict(resp.headers).get("x-encrypted-param", "")
            if not enc_param:
                return {"ret": -1, "errmsg": "CDN响应缺少x-encrypted-param"}
    except Exception as e:
        return {"ret": -1, "errmsg": f"CDN上传失败: {e}"}

    # 发送视频消息
    msg = {
        "from_user_id": "",
        "to_user_id": to_user_id,
        "client_id": str(uuid.uuid4()),
        "message_type": 2,
        "message_state": 2,
        "item_list": [
            {
                "type": 5,  # VIDEO
                "video_item": {
                    "media": {
                        "encrypt_query_param": enc_param,
                        "aes_key": enc["aeskey_base64"],
                        "encrypt_type": 1,
                    },
                    "video_size": enc["filesize"],
                }
            }
        ],
    }
    if context_token:
        msg["context_token"] = context_token

    return api_post("ilink/bot/sendmessage", account, {"msg": msg, "base_info": {"channel_version": CHANNEL_VERSION}}, timeout=15)


def send_message(account, to_user_id, text, context_token=None):
    msg = {
        "from_user_id": "",
        "to_user_id": to_user_id,
        "client_id": str(uuid.uuid4()),
        "message_type": 2,
        "message_state": 2,
        "item_list": [{"type": 1, "text_item": {"text": text}}],
    }
    if context_token:
        msg["context_token"] = context_token
    return api_post("ilink/bot/sendmessage", account, {"msg": msg, "base_info": {"channel_version": CHANNEL_VERSION}}, timeout=15)


def extract_text(msg):
    for item in msg.get("item_list", []):
        if item.get("type") == 1:
            return item.get("text_item", {}).get("text", "")
    return ""


def extract_image(msg):
    """提取图片消息，返回 (image_data, image_ext) 或 (None, None)"""
    for item in msg.get("item_list", []):
        if item.get("type") == 2:
            image_item = item.get("image_item", {})
            media = image_item.get("media", {})
            # 优先从 md5 获取图片数据（如果有的话）
            md5 = media.get("md5", "")
            if md5:
                return md5, "jpg"
            # 其他情况返回空
            return "", "jpg"
    return None, None


def is_image_message(msg):
    """判断是否为图片消息"""
    if msg.get("message_type") != 1:
        return False
    for item in msg.get("item_list", []):
        if item.get("type") == 2:
            return True
    return False


def save_image(account, msg, from_user):
    """下载并保存图片消息"""
    for item in msg.get("item_list", []):
        if item.get("type") != 2:
            continue
        image_item = item.get("image_item", {})
        media = image_item.get("media", {})

        aeskey_hex = image_item.get("aeskey", "")
        aeskey_base64 = media.get("aes_key", "")

        data, err = _cdn_download_and_decrypt(
            media.get("encrypt_query_param", ""), aeskey_hex, aeskey_base64
        )
        if err:
            logger.warning("图片消息处理失败: %s", err)
            return None

        received_pics_dir = RECEIVED_PICS_DIR
        os.makedirs(received_pics_dir, exist_ok=True)

        filename = f"img_{from_user}_{int(time.time() * 1000)}.jpg"
        filepath = os.path.join(received_pics_dir, filename)
        with open(filepath, "wb") as f:
            f.write(data)

        logger.info("图片已保存: %s (%d bytes)", filepath, len(data))
        return filepath
    return None


def _parse_aes_key(aeskey_hex, aeskey_base64):
    """解析 AES key，返回 16 字节 key 或 None"""
    try:
        import binascii
        if aeskey_hex and len(aeskey_hex) == 32:
            return binascii.unhexlify(aeskey_hex)
        elif aeskey_base64:
            decoded = base64.b64decode(aeskey_base64)
            if len(decoded) == 16:
                return decoded
            elif len(decoded) == 32:
                return binascii.unhexlify(decoded.decode("ascii"))
        return None
    except Exception:
        return None


def _cdn_download_and_decrypt(encrypt_query_param, aeskey_hex, aeskey_base64, timeout=30):
    """
    通用 CDN 下载 + AES-ECB 解密。
    返回 (decrypted_bytes, None) 或 (None, error_msg)
    """
    if not encrypt_query_param:
        return None, "缺少 encrypt_query_param"

    cdn_base_url = "https://novac2c.cdn.weixin.qq.com/c2c"
    download_url = f"{cdn_base_url}/download?encrypted_query_param={urllib.parse.quote(encrypt_query_param)}"

    try:
        req = urllib.request.Request(download_url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            encrypted_data = resp.read()
    except Exception as e:
        return None, f"CDN 下载失败: {e}"

    if not encrypted_data:
        return None, "CDN 返回空数据"

    key_bytes = _parse_aes_key(aeskey_hex, aeskey_base64)
    if not key_bytes:
        return None, "AES key 解析失败"

    try:
        cipher = _PyAES.new(key_bytes, _PyAES.MODE_ECB)
        decrypted = cipher.decrypt(encrypted_data)
        pad_len = decrypted[-1]
        if 1 <= pad_len <= 16:
            decrypted = decrypted[:-pad_len]
        return decrypted, None
    except Exception as e:
        return None, f"AES 解密失败: {e}"


def is_voice_message(msg):
    """判断是否为语音消息"""
    if msg.get("message_type") != 1:
        return False
    for item in msg.get("item_list", []):
        if item.get("type") == 3:
            return True
    return False


def save_voice(account, msg, from_user):
    """下载并保存语音消息（silk 格式）"""
    for item in msg.get("item_list", []):
        if item.get("type") != 3:
            continue
        voice_item = item.get("voice_item", {})
        media = voice_item.get("media", {})

        voice_text = voice_item.get("text", "")
        encode_type = voice_item.get("encode_type", 0)

        data, err = _cdn_download_and_decrypt(
            media.get("encrypt_query_param", ""),
            voice_item.get("aeskey", ""),
            media.get("aes_key", ""),
        )
        if err:
            logger.warning("语音消息处理失败: %s", err)
            return None, voice_text

        received_voices_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "received_voices")
        os.makedirs(received_voices_dir, exist_ok=True)

        ext = "silk" if encode_type == 6 else "audio"
        filename = f"voice_{from_user}_{int(time.time() * 1000)}.{ext}"
        filepath = os.path.join(received_voices_dir, filename)
        with open(filepath, "wb") as f:
            f.write(data)

        extra = f" (转文字: {voice_text})" if voice_text else ""
        logger.info("语音已保存: %s (%d bytes)%s", filepath, len(data), extra)
        return filepath, voice_text
    return None, ""


def is_file_message(msg):
    """判断是否为文件消息"""
    if msg.get("message_type") != 1:
        return False
    for item in msg.get("item_list", []):
        if item.get("type") == 4:
            return True
    return False


def save_file(account, msg, from_user):
    """下载并保存文件消息"""
    for item in msg.get("item_list", []):
        if item.get("type") != 4:
            continue
        file_item = item.get("file_item", {})
        media = file_item.get("media", {})

        file_name = file_item.get("file_name", "file.bin")

        data, err = _cdn_download_and_decrypt(
            media.get("encrypt_query_param", ""),
            file_item.get("aeskey", ""),
            media.get("aes_key", ""),
        )
        if err:
            logger.warning("文件消息处理失败: %s", err)
            return None

        received_files_dir = RECEIVED_FILES_DIR
        os.makedirs(received_files_dir, exist_ok=True)

        filename = f"file_{from_user}_{int(time.time() * 1000)}_{file_name}"
        filepath = os.path.join(received_files_dir, filename)
        with open(filepath, "wb") as f:
            f.write(data)

        logger.info("文件已保存: %s (%d bytes) - %s", filepath, len(data), file_name)
        return filepath
    return None


def is_video_message(msg):
    """判断是否为视频消息"""
    if msg.get("message_type") != 1:
        return False
    for item in msg.get("item_list", []):
        if item.get("type") == 5:
            return True
    return False


def save_video(account, msg, from_user):
    """下载并保存视频消息"""
    for item in msg.get("item_list", []):
        if item.get("type") != 5:
            continue
        video_item = item.get("video_item", {})
        media = video_item.get("media", {})
        play_length = video_item.get("play_length", 0)

        data, err = _cdn_download_and_decrypt(
            media.get("encrypt_query_param", ""),
            video_item.get("aeskey", ""),
            media.get("aes_key", ""),
            timeout=60,
        )
        if err:
            logger.warning("视频消息处理失败: %s", err)
            return None

        received_videos_dir = RECEIVED_VIDEOS_DIR
        os.makedirs(received_videos_dir, exist_ok=True)

        filename = f"video_{from_user}_{int(time.time() * 1000)}.mp4"
        filepath = os.path.join(received_videos_dir, filename)
        with open(filepath, "wb") as f:
            f.write(data)

        extra = f" (时长: {play_length}ms)" if play_length else ""
        logger.info("视频已保存: %s (%d bytes)%s", filepath, len(data), extra)
        return filepath
    return None


def is_user_message(msg):
    return msg.get("message_type") == 1


def _load_recent_history(limit=6):
    """加载最近 limit 条历史消息，转换为 Ollama 格式"""
    log = load_chat_log()
    msgs = log.get("messages", [])
    history = []
    for m in msgs[-limit:]:
        c = m.get("content", "")
        if not c:
            continue
        role = "user" if m.get("role") == "user" else "assistant"
        sent_via = m.get("sent_via")
        if isinstance(c, list):
            text = next((block.get("text", "") for block in c if block.get("type") == "text"), "")
        else:
            text = c
        if text:
            # 插件生成的消息加提示，让 AI 知道这是插件输出，后续可据此再次调用插件
            if role == "assistant" and sent_via:
                text = f"[via plugin:{sent_via}]\n{text}"
            history.append({"role": role, "content": text})
    return history


# ── Layer 4: Ollama AI ────────────────────────────────────────────────────────
def ai_chat(user_message, max_tokens=500, system_prompt=None):
    """使用本地 Ollama AI 对话，带历史上下文"""
    if system_prompt is None:
        system_prompt = (
            "你是用户的私人助手，说话简洁、口语化，像朋友聊天。\n"
            "用户使用 iPhone。\n"
            "如果用户询问历史对话中已有的数据（股市、天气、汇率等），直接从历史中提取回答，不要说查不到。\n"
            "知道就说知道，不知道就说不知道，不要编造。\n"
            "回答尽量简短，不超过200字。\n"
            "禁止啰嗦，禁止废话。"
        )
    try:
        history = _load_recent_history(limit=6)
        messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_message}]
        resp = requests.post(
            "http://localhost:11434/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": "gpt-oss:120b-cloud",
                "messages": messages,
                "max_tokens": max_tokens,
            },
            timeout=(10, 120),
        )
        if resp.status_code != 200:
            return f"AI 错误: {resp.status_code}"
        data = resp.json()
        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return reply.strip() if reply else "..."
    except requests.exceptions.Timeout:
        return "请求超时了"
    except requests.exceptions.ConnectionError:
        return "AI 服务连接失败"
    except Exception as e:
        return f"AI 异常: {e}"


# ── Claude Code CLI 辅助 ────────────────────────────────────────────────────────
import re
from datetime import datetime

OUTPUT_FILE_MARKER = "[OUTPUT_FILE]"

# ── CMD 输出美化 ───────────────────────────────────────────────────────────────
class CmdColors:
    RESET = "[0m"
    BOLD = "[1m"
    RED = "[31m"
    GREEN = "[32m"
    YELLOW = "[33m"
    BLUE = "[34m"
    MAGENTA = "[35m"
    CYAN = "[36m"
    WHITE = "[37m"
    BRIGHT_RED = "[91m"
    BRIGHT_GREEN = "[92m"
    BRIGHT_YELLOW = "[93m"
    BRIGHT_CYAN = "[96m"
    BG_BLUE = "[44m"
    BG_MAGENTA = "[45m"

    @staticmethod
    def colored(text, color):
        return f"{color}{text}{CmdColors.RESET}"

    @staticmethod
    def timestamp():
        return datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def log(text, color=None):
        ts = CmdColors.timestamp()
        print(f"[90m[{ts}][0m {CmdColors.colored(text, color or CmdColors.WHITE)}")

    @staticmethod
    def log_icon(icon, text, color=None):
        print(f"  {icon} {CmdColors.colored(text, color or CmdColors.WHITE)}")

    @staticmethod
    def section(title):
        print(CmdColors.colored(f"\n{'═' * 54}", CmdColors.CYAN))
        print(CmdColors.colored(f"  {title}", CmdColors.BOLD + CmdColors.CYAN))
        print(CmdColors.colored(f"{'─' * 54}", CmdColors.CYAN))


def _strip_ansi(text):
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _extract_output_file(text):
    """从 Claude Code 输出中提取 [OUTPUT_FILE] 标记的文件路径。"""
    lines = text.split("\n")
    clean_lines = []
    file_path = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(OUTPUT_FILE_MARKER):
            file_path = stripped[len(OUTPUT_FILE_MARKER):].strip()
        else:
            clean_lines.append(line)
    return "\n".join(clean_lines).rstrip(), file_path
def _auto_send_output(account, from_user, context_token, file_path):
    """
    根据文件类型自动选择发送方式，返回描述文本。
    """
    if not os.path.exists(file_path):
        return f"文件不存在: {file_path}"

    ext = os.path.splitext(file_path)[1].lower()
    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
    video_exts = {".mp4", ".avi", ".mov", ".mkv", ".flv"}
    doc_exts = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"}

    if ext in image_exts:
        result = send_image_message(account, from_user, file_path, context_token)
    elif ext in video_exts:
        result = send_video_message(account, from_user, file_path, context_token)
    elif ext in doc_exts:
        result = send_file_message(account, from_user, file_path, context_token)
    else:
        result = send_file_message(account, from_user, file_path, context_token)

    ret = result.get("ret")
    if ret == 0 or ret is None:
        return f"✅ 已发送: {os.path.basename(file_path)}"
    else:
        return f"❌ 发送失败: {result.get('errmsg', '未知错误')}"


# ── Layer 3: Claude Code CLI ────────────────────────────────────────────────────
import re

PLAN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plan.md")


def _strip_ansi(text):
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _get_latest_file(directory):
    """获取目录下最新修改的文件路径"""
    if not os.path.exists(directory):
        return None
    files = [os.path.join(directory, f) for f in os.listdir(directory)]
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def _llm_generate_plan(user_prompt):
    """用本地 Ollama 生成 plan.md"""
    system = """\
你是一个计划生成器。根据用户需求生成 plan.md。

目录结构：
- 图片目录: {received_pics_dir}/
- 文件目录: {received_files_dir}/
- 视频目录: {received_videos_dir}/
- 输出目录: {processed_dir}/

plan.md 格式：
# 执行计划

## 目标
一句话描述要做什么

## 输入文件
需要处理的文件路径（从上述目录中找最新的，或用户指定的）

## TODO 列表
- [ ] 步骤1：具体操作
- [ ] 步骤2：具体操作
...

## 输出文件
最终输出文件路径（必须在 {processed_dir}/ 下）

## 命令
用于执行的命令行或 Python 脚本

最后一行为纯文本：[OUTPUT_FILE] /absolute/path/to/output.file
""".format(
        received_pics_dir=RECEIVED_PICS_DIR,
        received_files_dir=RECEIVED_FILES_DIR,
        received_videos_dir=RECEIVED_VIDEOS_DIR,
        processed_dir=PROCESSED_DIR,
    )

    try:
        resp = requests.post(
            "http://localhost:11434/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": "gpt-oss:120b-cloud",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 1000,
            },
            timeout=(10, 120),
        )
        if resp.status_code != 200:
            return None, f"Ollama 错误: {resp.status_code}"
        data = resp.json()
        plan = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return plan, None
    except requests.exceptions.Timeout:
        return None, "Ollama 请求超时"
    except requests.exceptions.ConnectionError:
        return None, "Ollama 连接失败"
    except Exception as e:
        return None, f"Ollama 异常: {e}"


def _template_generate_plan(user_prompt):
    """模板生成 plan.md（用户格式），检测操作类型"""
    prompt_lower = user_prompt.lower()

    # 检测资源类型
    if any(k in prompt_lower for k in ["图片", "图", "image", "photo"]):
        src_dir = RECEIVED_PICS_DIR
    elif any(k in prompt_lower for k in ["视频", "video"]):
        src_dir = RECEIVED_VIDEOS_DIR
    elif any(ext in prompt_lower for ext in [".txt", ".doc", ".pdf", ".xlsx", ".csv", "文档", "文件", "分析", "总结"]):
        src_dir = RECEIVED_FILES_DIR
    else:
        src_dir = RECEIVED_PICS_DIR

    latest = _get_latest_file(src_dir)
    if not latest:
        # 如果没找到，尝试另一个目录
        alt_dir = RECEIVED_FILES_DIR if src_dir == RECEIVED_PICS_DIR else RECEIVED_PICS_DIR
        latest = _get_latest_file(alt_dir)
        if latest:
            src_dir = alt_dir

    if not latest:
        return None, f"目录为空: {src_dir}"

    latest_path = latest.replace("\\", "/")

    # 检测是否需要发送
    need_send = "发" in prompt_lower or "发送" in prompt_lower

    # TODO 列表
    todo_items = [
        "[]分析用户需求，去 received_files/ 和 received_pics/ 目录下寻找相关文件",
        "[]按照用户需求执行操作，可以直接操作或者编写脚本执行",
    ]
    if need_send:
        todo_items.append("[]文件或者图片调用send_media.py发送消息，文字的直接发送消息")
    todo_text = "\n".join(todo_items)

    # 组装 plan.md（用户格式）
    plan = f"""## 当前工作目录: D:\\LLaMA\\weixinchat\\weixinctrl\\received
## 文件存储在: ./received_files/  ./received_pics/
## 发送图片/文件/文字脚本: send_media.py  用法: python send_media.py <文件路径>
## 用户需求：{user_prompt}
### todo
{todo_text}
"""
    return plan, latest_path


def run_claude_code(prompt):
    """
    1. 模板生成 plan.md（中文格式）
    2. 写入 received/plan.md 和 received/run_cli.bat
    3. 执行 run_cli.bat，claude -p 返回文字说明
    4. 返回 claude 的文字输出
    """
    plan_text, latest_path = _template_generate_plan(prompt)
    if not plan_text:
        return f"生成 plan 失败: {latest_path}", None

    received_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "received")
    plan_file = os.path.join(received_dir, "plan.md")
    run_bat = os.path.join(received_dir, "run_cli.bat")

    # 日志输出执行详情
    print()
    CmdColors.section("💻 Claude CLI 执行")
    CmdColors.log_icon("📝", f"需求: {prompt[:80]}{'...' if len(prompt) > 80 else ''}", CmdColors.CYAN)
    CmdColors.log_icon("📄", f"Plan: {plan_file}", CmdColors.WHITE)
    CmdColors.log_icon("🎯", f"输入文件: {latest_path or '无'}", CmdColors.WHITE)
    CmdColors.log_icon("⏱️", "超时: 7分钟 (420s)", CmdColors.YELLOW)
    print(CmdColors.colored(f"{'─' * 54}", CmdColors.CYAN))

    try:
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(plan_text)
        with open(run_bat, "w", encoding="utf-8") as f:
            # Claude 在 received/ 目录下执行 plan.md
            f.write(
                "@echo off\n"
                "chcp 65001 >nul 2>&1\n"
                "cd /d \"{}\"\n"
                "claude -p --dangerously-skip-permissions \"you are in {}\\ directory. read plan.md, execute the TODO list step by step. 直接操作文件/图片，用 python send_media.py <文件路径> 发送图片或文件，直接打印文字消息。不需要确认，直接执行并输出结果。\"\n".format(received_dir, received_dir)
            )
        logger.info("plan.md 已生成:\n%s", plan_text)
    except Exception as e:
        return f"写入文件失败: {e}", None

    # 执行 run_cli.bat（实时输出日志，超时7分钟）
    try:
        proc = subprocess.Popen(
            [run_bat],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8",
        )
        output_lines = []
        for line in iter(proc.stdout.readline, ""):
            if line:
                line = _strip_ansi(line)
                output_lines.append(line)
                CmdColors.log(f"claude: {line[:200]}", CmdColors.MAGENTA)
        proc.wait(timeout=420)
        output = "\n".join(output_lines)
        return output if output else "(无输出)", latest_path
    except subprocess.TimeoutExpired:
        proc.kill()
        return "执行超时 (420s / 7分钟)", latest_path
    except Exception as e:
        return f"执行失败: {e}", latest_path


def run_claude_code_knowledge(prompt):
    """
    Claude Code 操作 Obsidian 知识库
    在 C:\\Users\\Administrator\\Desktop\\个人 目录下执行
    """
    OBSIDIAN_DIR = r"C:\Users\Administrator\Desktop\个人"
    received_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "received")
    run_bat = os.path.join(received_dir, "run_cc_knowledge.bat")

    print()
    CmdColors.section("📚 Claude 知识库操作")
    CmdColors.log_icon("📝", f"需求: {prompt[:80]}{'...' if len(prompt) > 80 else ''}", CmdColors.CYAN)
    CmdColors.log_icon("📁", f"目录: {OBSIDIAN_DIR}", CmdColors.WHITE)
    CmdColors.log_icon("⏱️", "超时: 10分钟 (600s)", CmdColors.YELLOW)
    print(CmdColors.colored(f"{'─' * 54}", CmdColors.CYAN))

    try:
        # 生成知识库任务 plan
        plan_text = (
            "## 知识库目录: " + OBSIDIAN_DIR + "\n"
            "## 用户问题: " + prompt + "\n"
            "### 任务\n"
            "[]先读取目录下的 知识库结构.md 文件，了解知识库整体结构\n"
            "[]根据用户问题，执行相应的文件操作（搜索、阅读、创建、修改 md 文件等）\n"
            "[]如需发送图片/文件给用户，用 python send_media.py <文件路径>\n"
            "[]完成后直接输出结果文字，不需要确认\n"
        )

        plan_file = os.path.join(OBSIDIAN_DIR, "plan_knowledge.md")
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(plan_text)

        with open(run_bat, "w", encoding="utf-8") as f:
            f.write(
                "@echo off\n"
                "chcp 65001 >nul 2>&1\n"
                "cd /d \"" + OBSIDIAN_DIR + "\"\n"
                "claude -p --dangerously-skip-permissions \"read plan_knowledge.md in the current directory, then execute the TODO list step by step. 直接打印执行结果文字，不需要确认。\"\n"
            )
    except Exception as e:
        return f"写入文件失败: {e}", None

    try:
        proc = subprocess.Popen(
            [run_bat],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8",
        )
        output_lines = []
        for line in iter(proc.stdout.readline, ""):
            if line:
                line = _strip_ansi(line)
                output_lines.append(line)
                CmdColors.log(f"claude: {line[:200]}", CmdColors.MAGENTA)
        proc.wait(timeout=600)
        output = "\n".join(output_lines)
        return output if output else "(无输出)", None
    except subprocess.TimeoutExpired:
        proc.kill()
        return "执行超时 (600s / 10分钟)", None
    except Exception as e:
        return f"执行失败: {e}", None


# ── Layer 1: 内置命令 ─────────────────────────────────────────────────────────
def run_command(text):
    from commands import COMMANDS, parse_command
    cmd_name, args = parse_command(text)
    if not cmd_name:
        return None
    handler = COMMANDS.get(cmd_name)
    if handler:
        try:
            return handler(args)
        except Exception as e:
            return f"命令执行错误: {e}"
    return None


# ── 消息分发 ──────────────────────────────────────────────────────────────────
def handle_message(text, account, from_user, context_token):
    text = text.strip()
    if not text:
        return None

    # /<cmd> → 直接执行内置命令
    if text.startswith("/"):
        result = run_command(text[1:])
        if result is not None:
            return result
        return ai_chat(text)

    # 其他 → AI 对话
    return ai_chat(text)


