"""
message_panel.py - 消息日志面板 (sci-fi 终端风格)
"""
import sys
import os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from customtkinter import CTkTextbox, CTkButton

CLR_RECV  = "#00e5ff"
CLR_SENT  = "#00e676"
CLR_ERR   = "#ff5252"
CLR_SYS   = "#626278"
CLR_TIME  = "#484860"
CLR_BAR   = "#1e1e30"
FONT      = ("Cascadia Code", 11)
FONT_SM   = ("Cascadia Code", 10)
SEP_W     = 56
GAP_MIN   = 5       # 分钟：超过此间隔→显示时间头
FOLD_H    = 2       # 小时：超过此时间→可折叠


class MessagePanel(ctk.CTkFrame):

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="#12121c", **kwargs)

        self._history_loaded = False
        self._at_bottom = True
        self._last_ts = None
        self._folded = True       # 默认折叠模式
        self._buffer = []         # [(role, name, content, timestamp)]  完整消息缓存
        self._fold_count = 0      # 折叠了多少条

        self._setup_ui()

        from v2.bridge import bridge
        bridge.on_message_received(self._on_message_received)
        bridge.on_message_sent(self._on_message_sent)
        bridge.on_polling_status(self._on_polling_started)

    def _setup_ui(self):
        # 展开按钮栏
        self._fold_bar = ctk.CTkFrame(self, height=28, fg_color="transparent")
        self._fold_bar.pack(fill="x", padx=4, pady=(2, 0))

        self._fold_btn = CTkButton(
            self._fold_bar, text="", width=160, height=22, corner_radius=3,
            font=FONT_SM, fg_color="#181825", hover_color="#1e1e30",
            text_color=CLR_SYS, command=self._toggle_fold
        )
        # 初始隐藏

        # 文本框
        self._textbox = CTkTextbox(self, font=FONT, wrap="word",
                                    fg_color="#12121c", text_color="#c8ccd4",
                                    corner_radius=0, border_width=0,
                                    spacing1=2, spacing2=2, spacing3=4)
        self._textbox.configure(state="disabled")
        self._textbox.pack(fill="both", expand=True)

        for tag, fg in [
            ("recv", CLR_RECV), ("sent", CLR_SENT),
            ("err", CLR_ERR), ("sys", CLR_SYS),
            ("time", CLR_TIME), ("bar", CLR_BAR),
        ]:
            self._textbox.tag_config(tag, foreground=fg)

        self._textbox.bind("<Configure>", self._on_configure)
        self._redraw()

    def _on_configure(self, event):
        self._at_bottom = self._textbox.yview()[1] >= 0.999

    # ── 重建显示 ──────────────────────────────────────────────────────────

    def _redraw(self):
        """根据 buffer + fold 状态重建整个文本"""
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")

        if not self._buffer:
            self._insl("· 等待连接…", "sys")
            self._insl()
            self._textbox.configure(state="disabled")
            return

        # 折叠阈值
        cutoff = datetime.now() - timedelta(hours=FOLD_H)

        # 统计折叠的条数
        if self._folded:
            self._fold_count = sum(1 for m in self._buffer
                                   if m[3] and m[3] < cutoff)
        else:
            self._fold_count = 0

        last_ts = None
        rendered = 0
        folded = 0

        for role, name, content, ts_dt in self._buffer:
            # 折叠模式：跳过旧消息
            if self._folded and ts_dt and ts_dt < cutoff:
                folded += 1
                continue

            ts_str = ts_dt.strftime("%H:%M:%S") if ts_dt else ""
            rendered += 1

            # 时间头判断
            show_head = True
            if last_ts and ts_dt:
                delta = (ts_dt - last_ts).total_seconds()
                if abs(delta) <= GAP_MIN * 60:
                    show_head = False

            if show_head:
                if role == "user":
                    self._ins("▌ ◀ " + name, "recv")
                else:
                    self._ins("▌ ▶ 发送", "sent")
                self._ins("  ·  " + ts_str, "time")
                self._insl()
                self._insl()

                for line in content.split("\n"):
                    self._insl("   " + line)
                self._insl()
                self._insl("▌" + "─" * SEP_W, "bar")
            else:
                for line in content.split("\n"):
                    self._insl("   " + line)

            self._insl()
            last_ts = ts_dt

        # 折叠提示行
        if folded > 0:
            self._insl()
            self._insl(f"▌ ━━ {folded} 条 {FOLD_H}小时前的消息已折叠 ━━", "sys")
            self._insl()

        # 按钮
        if self._fold_count > 0:
            self._fold_btn.configure(text=f"▸ 展开 {self._fold_count} 条更早消息")
            self._fold_btn.pack(side="left")
        else:
            self._fold_btn.pack_forget()

        self._textbox.configure(state="disabled")
        self._textbox.see("end")

    def _toggle_fold(self):
        self._folded = not self._folded
        self._redraw()

    # ── 写入原语 ─────────────────────────────────────────────────────────

    def _ins(self, s, tag=None):
        if tag:
            self._textbox.insert("end", s, tag)
        else:
            self._textbox.insert("end", s)

    def _insl(self, s="", tag=None):
        self._ins(s, tag)
        self._ins("\n")

    # ── 消息追加 ──────────────────────────────────────────────────────────

    def _check_bottom(self):
        self._at_bottom = self._textbox.yview()[1] >= 0.99

    def _append_to_buffer(self, role: str, name: str, content: str, ts_str: str):
        ts_dt = datetime.now()  # 使用当前时间，避免1900年导致的折叠误判
        self._buffer.append((role, name, content, ts_dt))
        self._last_ts = ts_dt
        self._folded = True  # 新消息来 → 重新折叠旧消息
        self._redraw()

    # ── 历史加载 ──────────────────────────────────────────────────────────

    def _on_polling_started(self, running: bool):
        if not running or self._history_loaded:
            return
        self._history_loaded = True

        from v2.client import load_chat_log
        log = load_chat_log()
        msgs = log.get("messages", [])

        for m in msgs:
            role = m.get("role", "")
            name = m.get("name", "")
            ts_full = m.get("timestamp", "")
            ts_str = ts_full[11:] if len(ts_full) > 11 else ""

            content = m.get("content", "")
            if isinstance(content, list):
                text = next((b.get("text", "") for b in content if b.get("type") == "text"), "")
            else:
                text = str(content)
            if not text:
                continue

            try:
                ts_dt = datetime.strptime(ts_full, "%Y-%m-%d %H:%M:%S")
            except Exception:
                ts_dt = datetime.now()

            if role == "user":
                self._buffer.append(("user", name, text, ts_dt))
            else:
                self._buffer.append(("assistant", "", text, ts_dt))

        if self._buffer:
            self._last_ts = self._buffer[-1][3]

        self._folded = True  # 启动时默认折叠
        self._redraw()

    # ── bridge 回调 ──────────────────────────────────────────────────────

    def _on_message_received(self, data: dict):
        self.after(0, lambda: self._append_to_buffer(
            "user",
            data.get("from_user", ""),
            data.get("content", ""),
            data.get("timestamp", self._now())
        ))

    def _on_message_sent(self, content: str):
        self.after(0, lambda: self._append_to_buffer(
            "assistant", "", content, self._now()
        ))

    @staticmethod
    def _now():
        return datetime.now().strftime("%H:%M:%S")
