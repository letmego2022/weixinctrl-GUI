"""
main_window.py - 主窗口
整合所有面板 + 系统托盘
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QPushButton, QLineEdit, QLabel,
    QSystemTrayIcon, QMenu, QMessageBox,
    QDockWidget, QTextEdit, QApplication, QAction,
    QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon

from v2.gui.message_panel import MessagePanel
from v2.gui.plugin_panel import PluginPanel
from v2.gui.log_panel import LogPanel
from v2.gui.stylesheet import dark_theme


class MainWindow(QMainWindow):
    """
    主窗口。
    包含：消息日志面板 + 插件面板（可折叠） + 控制台日志（可折叠） + 消息输入框
    系统托盘支持。
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🐺 微信控制台 v2")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        # 窗口图标
        icon_path = os.path.join(os.path.dirname(__file__), "..", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 加载样式
        self.setStyleSheet(dark_theme())

        self._poller = None
        self._msg_count = 0
        self._last_msg_time = ""
        self._setup_ui()
        self._setup_statusbar()
        self._setup_tray()
        self._setup_shortcuts()

    def _setup_ui(self):
        # 中心区域：消息日志
        self._message_panel = MessagePanel()

        # 插件面板（右侧 Dock）
        self._plugin_dock = QDockWidget("插件", self)
        self._plugin_dock.setWidget(PluginPanel())
        self._plugin_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self._plugin_dock.setFixedWidth(280)
        self._plugin_dock.setTitleBarWidget(QLabel("插件管理"))
        self.addDockWidget(Qt.RightDockWidgetArea, self._plugin_dock)

        # 控制台日志面板（底部 Dock）
        self._log_dock = QDockWidget("控制台日志", self)
        self._log_panel = LogPanel()
        self._log_dock.setWidget(self._log_panel)
        self._log_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        self._log_dock.setFixedHeight(180)
        self.addDockWidget(Qt.BottomDockWidgetArea, self._log_dock)

        # 设置中心部件
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(4, 4, 4, 4)
        central_layout.setSpacing(4)

        # 顶部工具栏（QToolBar 风格）
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 6, 8, 6)
        toolbar.setSpacing(8)

        # 状态标签
        self._status_label = QLabel("⚫ 未启动")
        self._status_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        toolbar.addWidget(self._status_label)

        toolbar.addSpacing(12)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #30363d;")
        toolbar.addWidget(sep)

        toolbar.addSpacing(6)

        toolbar.addStretch()

        toolbar.addSpacing(6)

        # 登录按钮
        self._login_btn = QPushButton("🔐 登录微信")
        self._login_btn.setFixedHeight(28)
        self._login_btn.setToolTip("打开微信登录页面")
        self._login_btn.clicked.connect(self._open_login)
        toolbar.addWidget(self._login_btn)

        toolbar.addSpacing(6)

        # 面板切换按钮（右侧）
        self._plugin_toggle = QPushButton("📦 插件")
        self._plugin_toggle.setFixedHeight(28)
        self._plugin_toggle.setCheckable(True)
        self._plugin_toggle.setChecked(False)
        self._plugin_toggle.setToolTip("插件面板")
        self._plugin_toggle.clicked.connect(self._toggle_plugin_panel)
        toolbar.addWidget(self._plugin_toggle)

        self._log_toggle = QPushButton("📋 日志")
        self._log_toggle.setFixedHeight(28)
        self._log_toggle.setCheckable(True)
        self._log_toggle.setChecked(False)
        self._log_toggle.setToolTip("控制台日志")
        self._log_toggle.clicked.connect(self._toggle_log_panel)
        toolbar.addWidget(self._log_toggle)

        # 启动/停止按钮（最右侧）
        self._toggle_btn = QPushButton("▶")
        self._toggle_btn.setFixedSize(36, 28)
        self._toggle_btn.setToolTip("启动/停止轮询")
        self._toggle_btn.clicked.connect(self._toggle_polling)
        toolbar.addWidget(self._toggle_btn)

        central_layout.addLayout(toolbar)

        # 默认收起两个面板
        self._plugin_dock.hide()
        self._log_dock.hide()

        # 消息面板（占据主要空间）
        central_layout.addWidget(self._message_panel, stretch=1)

        # 消息输入区
        input_layout = QHBoxLayout()
        self._input_edit = QLineEdit()
        self._input_edit.setPlaceholderText("输入消息后按 Enter 发送，或点击发送按钮...")
        self._input_edit.returnPressed.connect(self._send_message)

        self._send_btn = QPushButton("发送")
        self._send_btn.setFixedSize(70, 32)
        self._send_btn.clicked.connect(self._send_message)

        input_layout.addWidget(self._input_edit, stretch=1)
        input_layout.addWidget(self._send_btn, stretch=0)

        central_layout.addLayout(input_layout)

        self.setCentralWidget(central)

    def _setup_statusbar(self):
        """底部状态栏"""
        self.statusBar().showMessage("就绪")

        # 连接消息信号用于状态栏更新
        from v2.bridge import bridge
        bridge.signal_message_received.connect(self._on_status_message)
        bridge.signal_polling_status.connect(self._on_status_polling)

    def _on_status_message(self, data: dict):
        self._msg_count += 1
        self._last_msg_time = data.get("timestamp", "")
        self.statusBar().showMessage(
            f"收到 {self._msg_count} 条消息  |  最后: {self._last_msg_time}  |  ⚡ 运行中"
        )

    def _on_status_polling(self, running: bool):
        if running:
            self._msg_count = 0
            self._last_msg_time = ""
            self.statusBar().showMessage("⚡ 轮询运行中...")
        else:
            self.statusBar().showMessage("⚫ 已停止")

    def _toggle_plugin_panel(self, checked: bool):
        self._plugin_dock.setVisible(checked)
        self._plugin_toggle.setText("📦 插件" if checked else "📦")

    def _toggle_log_panel(self, checked: bool):
        self._log_dock.setVisible(checked)
        self._log_toggle.setText("📋 日志" if checked else "📋")

    def _open_login(self):
        """打开微信登录页面"""
        import subprocess
        import sys
        # 使用 login.bat 登录，或者直接运行 node standalone-login.mjs
        login_path = os.path.join(os.path.dirname(__file__), "..", "..", "login.bat")
        if os.path.exists(login_path):
            subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", login_path], shell=True)
        else:
            QMessageBox.warning(self, "提示", "未找到 login.bat，请手动运行登录脚本")

    def _setup_tray(self):
        """系统托盘"""
        # 创建托盘图标（16x16 简单图形）
        from PyQt5.QtGui import QPixmap, QPainter, QColor, QIcon
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(0, 0, 0, 0))  # 透明背景
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#1f6feb"))
        painter.drawEllipse(1, 1, 14, 14)  # 蓝色圆
        painter.end()

        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(QIcon(pixmap))
        self._tray.setToolTip("🐺 微信控制台 v2")

        # 创建托盘菜单
        tray_menu = QMenu(self)

        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show)
        hide_action = QAction("隐藏", self)
        hide_action.triggered.connect(self.hide)
        separator1 = QAction("─────────────", self)
        separator1.setEnabled(False)
        start_action = QAction("▶ 启动轮询", self)
        start_action.triggered.connect(self._start_polling)
        stop_action = QAction("■ 停止轮询", self)
        stop_action.triggered.connect(self._stop_polling)
        separator2 = QAction("─────────────", self)
        separator2.setEnabled(False)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_app)

        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(separator1)
        tray_menu.addAction(start_action)
        tray_menu.addAction(stop_action)
        tray_menu.addAction(separator2)
        tray_menu.addAction(quit_action)

        self._tray.setContextMenu(tray_menu)

        # 点击托盘图标显示窗口
        self._tray.activated.connect(self._on_tray_activated)

        # 连接消息信号用于托盘提示
        from v2.bridge import bridge
        bridge.signal_message_received.connect(self._on_tray_message)

        self._tray.show()

    def _setup_shortcuts(self):
        """快捷键"""
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        # Ctrl+Q 退出
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self._quit_app)
        # Ctrl+Enter 发送
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._send_message)

    def _toggle_polling(self):
        if self._poller and self._poller._running:
            self._stop_polling()
        else:
            self._start_polling()

    def _start_polling(self):
        if self._poller and self._poller.isRunning():
            return

        from v2.worker.poller import PollerThread
        from v2.bridge import bridge
        self._poller = PollerThread(self)
        self._poller.finished.connect(self._on_poller_finished)
        self._poller.start()
        bridge.set_poller(self._poller)

        self._status_label.setText("⚡ 运行中")
        self._toggle_btn.setText("■")

    def _stop_polling(self):
        if self._poller:
            self._poller.stop()
        self._status_label.setText("⚫ 已停止")
        self._toggle_btn.setText("▶")

    def _on_poller_finished(self):
        self._status_label.setText("⚫ 已停止")
        self._toggle_btn.setText("▶")

    def _send_message(self):
        text = self._input_edit.text().strip()
        if not text:
            return

        if not self._poller or not self._poller._running:
            QMessageBox.warning(self, "提示", "请先启动轮询")
            return

        from v2.bridge import bridge
        from client import send_message

        account = self._poller._account
        user_id = self._poller._user_id
        context_token = ""

        result = send_message(account, user_id, text, context_token)
        ret = result.get("ret")

        if ret == 0 or ret is None:
            bridge.signal_message_sent.emit(text)
            self._input_edit.clear()
        else:
            QMessageBox.warning(self, "发送失败", f"错误: {result.get('errmsg', '未知错误')}")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    def _on_tray_message(self, data: dict):
        """收到消息时托盘提示"""
        from_user = data.get("from_user", "")
        content = data.get("content", "")[:30]
        self._tray.showMessage(
            f"来自 {from_user}",
            content,
            QSystemTrayIcon.Information,
            3000
        )

    def _quit_app(self):
        """退出程序"""
        self._stop_polling()
        QApplication.instance().quit()

    def closeEvent(self, event):
        """关闭事件 → 最小化到托盘"""
        event.ignore()
        self.hide()
        self._tray.showMessage(
            "微信控制台 v2",
            "程序已最小化到托盘，右键退出",
            QSystemTrayIcon.Information,
            2000
        )
