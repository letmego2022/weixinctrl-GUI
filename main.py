"""
v2/main.py - customtkinter GUI 入口
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk

from v2.gui.main_window import MainWindow

ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")


def check_login() -> bool:
    try:
        from v2.client import load_account
        account = load_account()
        return account is not None
    except (SystemExit, FileNotFoundError, KeyError):
        return False


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    if not check_login():
        ctk.CTkMessageBox(title="未登录", message="请先运行 login.bat 完成微信登录，再启动 v2。")
        sys.exit(1)

    app = ctk.CTk()
    app.title("weixinctrl v2")
    app.geometry("1100x700")
    app.minsize(900, 600)
    if os.path.exists(ICON_PATH):
        app.iconbitmap(ICON_PATH)

    window = MainWindow(app)
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
