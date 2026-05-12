#!/usr/bin/env python3
"""
命令注册表 - 包含内置命令和自然语言路由
"""
import json
import os
import platform
import shutil
import socket
import subprocess
from typing import Optional

import psutil
import requests


# ── 内置命令 ──────────────────────────────────────────────────────────────────
def cmd_echo(args):
    return " ".join(args) if args else "Hello from WeChat!"


def cmd_system(args):
    info = {
        "系统": platform.system(),
        "版本": platform.version(),
        "主机名": socket.gethostname(),
        "Python": platform.python_version(),
    }
    return "系统信息:\n" + "\n".join(f"  {k}: {v}" for k, v in info.items())


def cmd_cpu(args):
    return f"CPU 使用率: {psutil.cpu_percent(interval=1)}%"


def cmd_memory(args):
    mem = psutil.virtual_memory()
    return f"内存: {mem.percent}% (已用 {mem.used // (1024**3)}GB / 总计 {mem.total // (1024**3)}GB)"


def cmd_disk(args):
    partitions = psutil.disk_partitions()
    lines = []
    for p in partitions:
        try:
            usage = psutil.disk_usage(p.mountpoint)
            lines.append(f"  {p.mountpoint}: {usage.percent}% (已用 {usage.used // (1024**3)}GB)")
        except:
            pass
    return "磁盘使用:\n" + "\n".join(lines) if lines else "无法获取磁盘信息"


def cmd_net(args):
    connections = psutil.net_connections()
    established = [c for c in connections if c.status == "ESTABLISHED"]
    return f"网络连接: {len(established)} 个已建立连接"


def cmd_processes(args):
    if not args:
        return "用法: /cmd 帮我搜索 nginx 进程"
    keyword = args[0].lower()
    processes = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            if keyword in p.info["name"].lower():
                processes.append(f"  {p.info['pid']} {p.info['name']}")
        except:
            pass
    return f"进程 ({keyword}):\n" + ("\n".join(processes[:20]) if processes else "未找到")


def cmd_kill(args):
    if not args:
        return "用法: /cmd 帮我结束 PID 1234"
    target = args[0]
    killed = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            if target.isdigit():
                if p.info["pid"] == int(target):
                    p.kill()
                    killed.append(f"已结束 PID {target}")
            elif target.lower() in p.info["name"].lower():
                p.kill()
                killed.append(f"已结束 {p.info['name']} (PID {p.info['pid']})")
        except:
            pass
    return "\n".join(killed) if killed else f"未找到进程: {target}"


def cmd_services(args):
    if platform.system() != "Windows":
        return "仅支持 Windows"
    keyword = args[0].lower() if args else ""
    try:
        result = subprocess.run(
            ["sc", "query", "state=", "all"],
            capture_output=True, text=True, timeout=10,
        )
        lines = result.stdout.split("\n")
        services = []
        current = {}
        for line in lines:
            if "SERVICE_NAME" in line:
                if current:
                    services.append(current)
                current = {"name": line.split(":", 1)[1].strip()}
            elif "DISPLAY_NAME" in line and current:
                current["display"] = line.split(":", 1)[1].strip()
        if current:
            services.append(current)
        if keyword:
            services = [s for s in services if keyword in s.get("name", "").lower() or keyword in s.get("display", "").lower()]
        return "服务列表:\n" + "\n".join(f"  {s.get('name')} - {s.get('display', '')}" for s in services[:20])
    except Exception as e:
        return f"获取服务失败: {e}"


def cmd_start_service(args):
    if platform.system() != "Windows":
        return "仅支持 Windows"
    if len(args) < 1:
        return "用法: /cmd 帮我启动 MySQL 服务"
    service_name = " ".join(args)
    try:
        subprocess.run(["net", "start", service_name], capture_output=True, text=True, timeout=10)
        return f"已启动服务: {service_name}"
    except Exception as e:
        return f"启动失败: {e}"


def cmd_stop_service(args):
    if platform.system() != "Windows":
        return "仅支持 Windows"
    if len(args) < 1:
        return "用法: /cmd 帮我停止 MySQL 服务"
    service_name = " ".join(args)
    try:
        subprocess.run(["net", "stop", service_name], capture_output=True, text=True, timeout=10)
        return f"已停止服务: {service_name}"
    except Exception as e:
        return f"停止失败: {e}"


def cmd_searchfile(args):
    """使用 Everything (es.exe) 搜索文件，检测到'发送'意图时自动发送第一个结果"""
    if not args:
        return "用法: /cmd 帮我搜索 D盘 下的 xxx 文件\n示例: /cmd 帮我搜索 D盘 下的 python.pdf"
    # 解析 "D盘 下的 xxx" 或 "D:\xxx" 格式
    query = " ".join(args)

    # 检测是否需要自动发送：查询中包含"发送"、"发给我"、"发给我"等
    auto_send = any(kw in query for kw in ["发送", "发给我", "发给我", "发过来"])

    # 提取搜索关键词和路径
    path = ""
    keyword = query
    if "D盘" in query or "D:" in query:
        parts = query.replace("D盘", "D:").replace("下的", "|").split("|")
        if len(parts) >= 2:
            path = parts[0].strip()
            keyword = parts[1].strip()
        else:
            keyword = query.replace("D盘", "").replace("下的", "").strip()

    # 清理发送相关的词，得到干净的关键字
    for kw in ["发送", "发给我", "发给我", "发过来"]:
        keyword = keyword.replace(kw, "").strip()

    # 优先检查项目目录，再检查 D:\tools
    project_es = os.path.join(os.path.dirname(os.path.abspath(__file__)), "es.exe")
    if os.path.exists(project_es):
        es_path = project_es
    elif os.path.exists("D:\\tools\\es.exe"):
        es_path = "D:\\tools\\es.exe"
    else:
        return "未找到 es.exe，请确认 Everything 已安装并放置到项目目录或 D:\\tools\\"

    try:
        # es.exe 命令格式: es.exe <搜索词> -s
        cmd = [es_path, keyword, "-s"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        output = result.stdout.strip()
        if not output:
            return f"未找到文件: {keyword}"

        lines = [l.strip() for l in output.split("\n") if l.strip()]
        if len(lines) > 30:
            output = "\n".join(lines[:30]) + f"\n... 共 {len(lines)} 条结果"

        if auto_send:
            # 自动发送第一个结果
            first_file = lines[0]
            from client import load_account, send_file_message
            account = load_account()
            to_user_id = account.get("user_id", "")
            try:
                send_result = send_file_message(account, to_user_id, first_file)
                ret = send_result.get("ret") if send_result else None
                if ret == 0 or ret is None or ret == -2:
                    return f"已找到并发送: {first_file}"
                return f"找到文件: {first_file}\n发送失败: ret={ret} errmsg={send_result.get('errmsg', '')}"
            except Exception as e:
                return f"找到文件: {first_file}\n发送异常: {e}"

        return f"搜索结果 ({keyword}):\n{output}"
    except subprocess.TimeoutExpired:
        return "搜索超时"
    except Exception as e:
        return f"搜索失败: {e}"


def cmd_execute(args):
    if not args:
        return "用法: /cmd 帮我执行 ipconfig /all"
    cmd = " ".join(args)
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout or "(无输出)"
        error = result.stderr or ""
        return f"命令: {cmd}\n\n输出:\n{output}" + (f"\n错误:\n{error}" if error else "")
    except subprocess.TimeoutExpired:
        return f"命令执行超时 (30s): {cmd}"
    except Exception as e:
        return f"执行失败: {e}"


def cmd_screenshot(args):
    """截取屏幕截图"""
    try:
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct.shot(output="screenshot.png", mon=1)
        return "截图已保存: screenshot.png"
    except Exception as e:
        return f"截图失败: {e}"


def cmd_clipboard(args):
    """读写剪贴板内容，无参数时读取，有参数时写入"""
    try:
        if not args:
            # 读取剪贴板
            r = subprocess.run(
                ["powershell", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5,
            )
            text = r.stdout.strip()
            return f"剪贴板内容:\n{text}" if text else "剪贴板为空"
        else:
            # 写入剪贴板
            content = " ".join(args)
            r = subprocess.run(
                ["powershell", "-Command", f"Set-Clipboard -Value '{content}'"],
                capture_output=True, text=True, timeout=5,
            )
            return f"已写入剪贴板: {content[:50]}"
    except Exception as e:
        return f"剪贴板操作失败: {e}"


def cmd_window(args):
    """窗口管理：列出窗口、关闭、最小化、最大化"""
    keyword = args[0].lower() if args else ""

    try:
        r = subprocess.run(
            ["powershell", "-Command",
             "Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object Name,MainWindowTitle | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10,
        )
        if not r.stdout.strip():
            return "没有找到窗口"

        import json as json_module
        try:
            windows = json_module.loads(r.stdout)
        except:
            return f"获取窗口失败: {r.stdout[:200]}"

        if isinstance(windows, dict):
            windows = [windows]

        if not keyword:
            lines = [f"• {w['Name']}: {w['MainWindowTitle']}" for w in windows[:20]]
            return "当前窗口:\n" + "\n".join(lines) if lines else "没有找到窗口"

        # 关闭包含关键词的窗口
        for w in windows:
            if keyword in w['Name'].lower() or keyword in w['MainWindowTitle'].lower():
                name = w['Name']
                subprocess.run(["taskkill", "/IM", f"{name}.exe", "/F"],
                             capture_output=True, text=True, timeout=5)
                return f"已关闭窗口: {name}"

        return f"未找到匹配的窗口: {keyword}"

    except Exception as e:
        return f"窗口操作失败: {e}"


def cmd_ipconfig(args):
    """查看 IP 配置信息"""
    try:
        r = subprocess.run(["ipconfig", "/all"],
                         capture_output=True, text=True, timeout=10)
        output = r.stdout
        # 提取关键信息
        lines = output.split("\n")
        result = []
        capture = False
        for line in lines:
            if "Windows IP" in line or "以太网适配器" in line or "Wireless" in line or "无线" in line:
                if result:
                    result.append("")
                result.append(line.strip())
                capture = True
            elif capture and line.strip().startswith(("IPv4", "DHCP", "DNS", "物理地址")):
                result.append(line.strip())
        return "IP 配置:\n" + "\n".join(result[:30]) if result else output[:500]
    except Exception as e:
        return f"IP 配置查询失败: {e}"


def cmd_ping(args):
    """Ping 测试网络延迟"""
    if not args:
        return "用法: /cmd ping www.baidu.com"
    target = args[0]
    try:
        r = subprocess.run(["ping", "-n", "4", target],
                         capture_output=True, text=True, timeout=15)
        lines = r.stdout.split("\n")
        result = []
        for line in lines:
            if "TTL" in line or "时间" in line or "来自" in line or "Reply" in line or "往返" in line:
                result.append(line.strip())
        return "\n".join(result[-6:]) if result else r.stdout[:400]
    except Exception as e:
        return f"Ping 失败: {e}"


def cmd_nslookup(args):
    """DNS 查询"""
    if not args:
        return "用法: /cmd dns www.baidu.com"
    domain = args[0]
    try:
        r = subprocess.run(["nslookup", domain],
                         capture_output=True, text=True, timeout=10)
        return r.stdout[:600] if r.stdout else f"DNS 查询失败: {domain}"
    except Exception as e:
        return f"DNS 查询失败: {e}"


def cmd_netstat(args):
    """网络连接详情"""
    try:
        r = subprocess.run(["netstat", "-ano"],
                         capture_output=True, text=True, timeout=10)
        lines = r.stdout.split("\n")
        established = [l for l in lines if "ESTABLISHED" in l]
        listening = [l for l in lines if "LISTENING" in l]
        result = [f"活动连接 ({len(established)} 个):"]
        for l in established[:15]:
            parts = l.split()
            if len(parts) >= 5:
                result.append(f"  {parts[4]}  {parts[3]} -> {parts[5] if len(parts) > 5 else ''}")
        result.append(f"\n监听端口 ({len(listening)} 个):")
        ports = {}
        for l in listening:
            parts = l.split()
            if len(parts) >= 5:
                port = parts[4].split(":")[-1]
                pid = parts[-1]
                if port not in ports:
                    ports[port] = pid
        for port, pid in list(ports.items())[:15]:
            result.append(f"  :{port}  PID:{pid}")
        return "\n".join(result)
    except Exception as e:
        return f"网络详情查询失败: {e}"


def cmd_shutdown(args):
    """关机、重启、注销"""
    if not args:
        return "用法: /cmd 关机 或 /cmd 重启 或 /cmd 注销"

    action = args[0]
    if action in ["关机", "shut"]:
        subprocess.run(["shutdown", "/s", "/t", "30"])
        return "系统将在 30 秒后关机..."
    elif action in ["重启", "reboot"]:
        subprocess.run(["shutdown", "/r", "/t", "30"])
        return "系统将在 30 秒后重启..."
    elif action in ["注销", "logoff"]:
        subprocess.run(["shutdown", "/l"])
        return "正在注销..."
    elif action in ["取消", "abort"]:
        subprocess.run(["shutdown", "/a"])
        return "已取消关机/重启计划"
    else:
        return "用法: /cmd 关机 / 重启 / 注销 / 取消"


def cmd_sendfile(args):
    """发送文件给用户"""
    if not args:
        return "用法: /cmd 帮我发送文件 D:\\path\\to\\file.xlsx"
    file_path = " ".join(args).strip()
    if not os.path.exists(file_path):
        return f"文件不存在: {file_path}"
    # 延迟导入避免循环
    from client import send_file_message
    try:
        result = send_file_message(file_path)
        if result and result.get("ret") == 0:
            return f"已发送文件: {os.path.basename(file_path)}"
        return f"发送失败: {result.get('errmsg', result)}"
    except Exception as e:
        return f"发送失败: {e}"


# ── 自然语言命令路由 ───────────────────────────────────────────────────────────
# 可用命令的描述，用于 AI 判断
# ── 敏感信息处理工具脚本目录 ──────────────────────────────────────────────────
HEXIN_DIR = r"D:\game\sentse\new\hexin"

# 关键词 → 脚本映射（按文件名顺序）
# 格式: "关键词": "脚本文件名"
HEXIN_SCRIPTS = {
    "doc":      "00_docchuli.py",
    "txt":      "00_otherchuli.py",
    "java":     "00_otherchuli.py",
    "py":       "00_pychecker.py",
    "js":       "00_jschuli.py",
    "json":     "00_jsonchuli.py",
    "xml":      "00_xmlchuli.py",
    "log":      "00_logchuli.py",
    "zip":      "00_zipchuli.py",
    "rar":      "00_zipchuli.py",
    "7z":       "00_zipchuli.py",
    "pdf":      "00_pdfchuli.py",
    "phone":    "05_phonechuli.py",
    "phones":   "03_search_phone.py",
    "delete":   "07_phonedelete.py",
    "archive":  "01_streaming_archive_script_v2.py",
    "index":    "02_update_phonenum_index_from_archives_v2.py",
    "profile":  "06_build_profile_test.py",
    "shit":     "11-shitprompt.py",
    "burp":     "12-burpzip.py",
    "chuli":    "04_chuli.py",
    "runall":   "00_run_all.py",
}

# 所有可用关键词
HEXIN_KEYWORDS = sorted(HEXIN_SCRIPTS.keys())


def cmd_natural(args):
    """
    根据关键词直接映射到 hexin 目录下的脚本执行。
    用法: /cmd <关键词> [脚本参数]  或  /cmd -h 查看帮助
    例如: /cmd zip  或  /cmd phone  或  /cmd chuli
    """
    # -h / --help / help → 显示帮助
    if not args or args[0] in ("-h", "--help", "help", "-?"):
        return (
            "🐺 微信控制台命令帮助\n\n"
            "  /cmd <关键词>      — 运行 hexin 敏感信息处理脚本\n"
            "  /搜索文件 <关键词> — 用 Everything 搜索本地文件\n"
            "  /发送文件 <路径>  — 发送文件到微信\n"
            "  /帮助              — 显示此帮助\n\n"
            "处理脚本（hexin）：\n"
            "  /cmd doc      — 文档处理 (.doc/.docx/.txt)\n"
            "  /cmd zip      — 压缩包处理 (.zip/.rar/.7z)\n"
            "  /cmd pdf      — PDF处理\n"
            "  /cmd js       — JavaScript处理\n"
            "  /cmd json     — JSON处理\n"
            "  /cmd xml      — XML处理\n"
            "  /cmd log      — 日志处理\n"
            "  /cmd java     — Java代码处理\n"
            "  /cmd py       — Python代码检查\n"
            "  /cmd phone    — 手机号AI清洗\n"
            "  /cmd phones   — 手机号查询\n"
            "  /cmd archive  — 流式归档\n"
            "  /cmd index    — 构建索引\n"
            "  /cmd chuli    — AI清洗（索引版）\n"
            "  /cmd delete   — 目录清理\n"
            "  /cmd runall   — 运行全部脚本\n"
        )

    keyword = args[0].lower()
    script_file = HEXIN_SCRIPTS.get(keyword)

    if not script_file:
        return (f"未知处理类型: {keyword}\n"
                f"可用: {', '.join(HEXIN_KEYWORDS)}")

    script_path = os.path.join(HEXIN_DIR, script_file)
    if not os.path.exists(script_path):
        return f"脚本不存在: {script_path}"

    # 执行脚本，参数透传
    script_args = args[1:] if len(args) > 1 else []
    cmd = ["python", script_path] + script_args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=120, shell=True,
            cwd=HEXIN_DIR,
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if out:
            return out if len(out) <= 3000 else out[:3000] + "\n...(输出过长)"
        if err:
            return f"[stderr]\n{err[:1000]}"
        return "(脚本无输出)"
    except subprocess.TimeoutExpired:
        return f"脚本执行超时 (120秒)"
    except FileNotFoundError:
        return "未找到 python 解释器"
    except Exception as e:
        return f"执行失败: {e}"


# ── 帮助命令 ──────────────────────────────────────────────────────────────────
def cmd_help(args):
    return (
        "## 🐺 微信控制台\n\n"
        "### 插件（自动触发）\n\n"
        "| 插件 | 触发关键词 |\n"
        "|------|-----------|\n"
        "| 股市 | 股市、指数、行情、纳指、日经、恒生、上证、大盘 |\n"
        "| 汇率 | 汇率、换汇、美元、外汇、换成美元、换成人民币 |\n"
        "| 天气 | 天气、温度、气温 |\n\n"
        "### 自动任务\n\n"
        "| 任务 | 执行时间 |\n"
        "|------|----------|\n"
        "| 每日总结 | 每天 20:00 |\n\n"
        "### 命令\n\n"
        "| 命令 | 说明 |\n"
        "|------|------|\n"
        "| /cmd <需求> | Claude Code CLI 执行（如 /cmd 查看系统占用） |\n"
        "| /cc <需求> | Claude Code 操作 Obsidian 知识库 |\n"
        "| /phone <手机号> | 查询手机号归属地 |\n"
        "| /帮助 | 显示帮助 |\n"
    )


# ── 命令注册表 ────────────────────────────────────────────────────────────────
COMMANDS = {
    "help": cmd_help,
    "帮助": cmd_help,
}


def parse_command(text: str) -> tuple[str, list[str]]:
    """解析命令，返回 (命令名, 参数列表)"""
    parts = text.strip().split()
    if not parts:
        return "", []
    return parts[0], parts[1:]


def run_command(text: str) -> Optional[str]:
    """执行命令并返回结果，未找到返回 None"""
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
