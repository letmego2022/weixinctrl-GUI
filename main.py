"""
v2/main.py - customtkinter GUI 入口
"""
import sys
import os
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk

from v2.gui.main_window import MainWindow

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")


def setup_logging():
    """配置日志系统：控制台 + 文件"""
    os.makedirs(LOG_DIR, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%m-%d %H:%M:%S",
    )

    # 文件 handler — 按天轮转
    today = datetime.now().strftime("%Y-%m-%d")
    fh = logging.FileHandler(
        os.path.join(LOG_DIR, f"{today}.log"), encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # 控制台 handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(fh)
    root.addHandler(ch)

ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")


def check_login() -> bool:
    try:
        from v2.client import load_account
        account = load_account()
        return account is not None
    except (SystemExit, FileNotFoundError, KeyError):
        return False


def main():
    setup_logging()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    logged_in = check_login()

    app = ctk.CTk()
    app.title("weixinctrl v2")
    app.geometry("1100x700")
    app.minsize(900, 600)
    if os.path.exists(ICON_PATH):
        app.iconbitmap(ICON_PATH)

    window = MainWindow(app, auto_login=not logged_in)
    window.pack(fill="both", expand=True)

    def on_close():
        window._stop_polling()
        window.destroy()
        app.quit()
        try:
            app.destroy()
        except Exception:
            pass
        os._exit(0)

    app.protocol("WM_DELETE_WINDOW", on_close)

    app.mainloop()


if __name__ == "__main__":
    main()
