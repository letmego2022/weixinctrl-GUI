"""
v2/main.py - PySide6 GUI 入口
"""
import sys
import os

# 将项目根目录加入 path（以便 import client.py 等）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

from v2.gui.main_window import MainWindow


def check_login() -> bool:
    """检测是否已登录"""
    try:
        from client import load_account
        account = load_account()
        return account is not None
    except (SystemExit, FileNotFoundError, KeyError):
        return False


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 检测登录状态
    if not check_login():
        QMessageBox.warning(
            None,
            "未登录",
            "请先运行 login.bat 完成微信登录，再启动 v2。\n\n"
            "登录入口：\n"
            "  双击运行 login.bat → 扫码登录\n"
            "  登录成功后再运行 v2start.bat"
        )
        sys.exit(1)

    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
