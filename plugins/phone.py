#!/usr/bin/env python3
"""
手机号查询插件
命令: /phone xxxxx
通过 MongoDB 索引查询手机号相关信息
"""
import os
import time
import base64
import binascii
from typing import Optional

from pymongo import MongoClient
from . import PluginBase

# MongoDB 配置
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/?replicaSet=rs0")
DB_NAME = "sensitive_info_db"
INDEX_COLLECTION = "phonenum_index_v2"


def _decode_base64_safe(encoded_str: str) -> str:
    """安全地尝试解码 Base64 字符串"""
    if not encoded_str:
        return "未知来源"
    encoded_str = str(encoded_str).strip()
    try:
        padded = encoded_str + "=" * ((4 - len(encoded_str) % 4) % 4)
        decoded = base64.b64decode(padded).decode("utf-8")
        return decoded
    except (binascii.Error, UnicodeDecodeError, ValueError, TypeError):
        return encoded_str


# 模块级连接复用
_mongo_client = None


def _get_mongo_client():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, maxPoolSize=5)
    return _mongo_client


def _search_phone(phone_number: str) -> Optional[str]:
    """查询手机号，返回格式化结果"""
    try:
        client = _get_mongo_client()
        db = client[DB_NAME]
        collection = db[INDEX_COLLECTION]

        index_records = list(collection.find({"phonenum": phone_number}))
        if not index_records:
            return None

        results = []
        orphan = 0

        for record in index_records:
            target_col = record["ref_collection"]
            target_id = record["ref_id"]
            full_doc = db[target_col].find_one({"_id": target_id})
            if full_doc:
                full_doc["_source"] = target_col
                results.append(full_doc)
            else:
                orphan += 1

        lines = [f"## 📱 手机号查询结果: `{phone_number}`", ""]
        lines.append(f"共找到 **{len(results)}** 条关联记录\n")

        for i, doc in enumerate(results, 1):
            folder_raw = doc.get("folder_name", "")
            folder = _decode_base64_safe(folder_raw)
            content = doc.get("line_content", "无内容")
            source = doc.get("_source", "")

            if len(content) > 200:
                content = content[:200] + " ... [已截断]"

            lines.append(f"**[{i}] 📂 {folder}**")
            lines.append(f"📋 分表: `{source}`")
            lines.append(f"📄 内容: {content}")
            lines.append("---")

        if orphan > 0:
            lines.append(f"⚠️ 另有 **{orphan}** 条底层数据已失效")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 查询失败: {e}"


class PhonePlugin(PluginBase):
    """手机号查询插件"""

    name = "phone"
    interval = 0  # 仅在收到消息时触发
    enabled = True

    def on_start(self, account, user_id: str) -> Optional[str]:
        return None

    def on_interval(self, account, user_id: str) -> Optional[str]:
        return None

    def on_message(self, msg, account, from_user: str) -> Optional[str]:
        """收到 /phone 命令时查询手机号"""
        from client import extract_text
        text = extract_text(msg)
        if not text:
            return None

        # 匹配 /phone 格式
        if not text.startswith("/phone ") and not text.startswith("/phone"):
            return None

        phone = text.split(maxsplit=1)[-1].strip()
        if not phone or len(phone) < 7:
            return "用法: `/phone 手机号`\n示例: `/phone 13800138000`"

        result = _search_phone(phone)
        if result:
            return result
        self.log_info(f"未找到号码 {phone} 的记录")
        return f"❌ 未找到与 `{phone}` 相关的任何记录"


if __name__ == "__main__":
    # 简单测试
    test_num = input("输入手机号: ").strip()
    if test_num:
        result = _search_phone(test_num)
        print(result if result else "未找到记录")
