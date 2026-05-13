"""
v2/main.py - customtkinter GUI 入口
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from v2.gui.main_window import MainWindow


def check_login() -> bool:
    try:
        from client import load_account
        account = load_account()
        return account is not None
    except (SystemExit, FileNotFoundError, KeyError):
        return False


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    if not check_login():
        win = ctk.CTk()
        win.withdraw()
        ctk.CTkMessageBox(title="未登录", message="请先运行 login.bat 完成微信登录，再启动 v2。")
        sys.exit(1)

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()