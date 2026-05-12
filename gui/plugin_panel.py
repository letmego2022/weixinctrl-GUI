"""
plugin_panel.py - 插件管理面板
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QHeaderView, QMenu, QMessageBox, QApplication, QAction
)
from PyQt5.QtCore import Qt, QTimer
from datetime import datetime


class PluginPanel(QWidget):
    """
    插件状态管理面板。
    显示插件列表，支持启用/禁用/立即运行。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

        # 连接信号
        from v2.bridge import bridge
        bridge.signal_plugin_update.connect(self._on_plugin_update)

        # 刷新定时器
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_plugins)
        self._refresh_timer.start(30000)  # 每30秒刷新

        # 初始加载
        QTimer.singleShot(500, self._refresh_plugins)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 标题栏
        title_layout = QHBoxLayout()
        lbl = QLabel("插件管理")
        lbl.setStyleSheet("font-weight: bold; color: #d4d4d4;")
        title_layout.addWidget(lbl)
        title_layout.addStretch()

        refresh_btn = QPushButton("↻ 刷新")
        refresh_btn.clicked.connect(self._refresh_plugins)
        refresh_btn.setFixedSize(60, 24)
        title_layout.addWidget(refresh_btn)

        layout.addLayout(title_layout)

        # 表格
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["名称", "间隔", "状态", "上次运行"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.verticalHeader().setVisible(False)

        # 列宽
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self._table.setColumnWidth(0, 100)
        self._table.setColumnWidth(1, 60)
        self._table.setColumnWidth(2, 60)

        layout.addWidget(self._table)

    def _format_interval(self, seconds: int) -> str:
        if seconds == 0:
            return "启动一次"
        elif seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds // 60}分钟"
        else:
            return f"{seconds // 3600}小时"

    def _format_last_run(self, timestamp: float) -> str:
        if timestamp == 0:
            return "未运行"
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%H:%M:%S")

    def _on_plugin_update(self, plugins: list):
        """插件状态更新"""
        self._table.setRowCount(len(plugins))
        for row, p in enumerate(plugins):
            if isinstance(p, dict):
                name = p.get("name", "")
                interval = p.get("interval", 0)
                enabled = p.get("enabled", True)
                last_run = p.get("last_run", 0)
            else:
                name, interval, enabled, last_run = p
            self._table.setItem(row, 0, QTableWidgetItem(name))
            self._table.setItem(row, 1, QTableWidgetItem(self._format_interval(interval)))
            status_item = QTableWidgetItem("启用" if enabled else "禁用")
            status_item.setForeground(
                Qt.green if enabled else Qt.red
            )
            self._table.setItem(row, 2, status_item)
            self._table.setItem(row, 3, QTableWidgetItem(self._format_last_run(last_run)))

    def _refresh_plugins(self):
        """刷新插件列表"""
        from v2.bridge import bridge
        poller = bridge.get_poller()
        if poller:
            plugin_list = poller.plugin_manager.list_plugins()
            bridge.signal_plugin_update.emit(plugin_list)

    def _show_context_menu(self, pos):
        row = self._table.currentRow()
        if row < 0:
            return

        plugin_name = self._table.item(row, 0).text()
        menu = QMenu(self)

        enable_action = QAction("启用", self)
        enable_action.triggered.connect(lambda: self._set_enabled(plugin_name, True))
        disable_action = QAction("禁用", self)
        disable_action.triggered.connect(lambda: self._set_enabled(plugin_name, False))
        run_action = QAction("立即运行", self)
        run_action.triggered.connect(lambda: self._run_now(plugin_name))

        menu.addAction(enable_action)
        menu.addAction(disable_action)
        menu.addSeparator()
        menu.addAction(run_action)

        menu.exec(self._table.mapToGlobal(pos))

    def _set_enabled(self, name: str, enabled: bool):
        """启用/禁用插件"""
        from v2.bridge import bridge
        poller = bridge.get_poller()
        if poller:
            plugin = poller.plugin_manager.get_plugin(name)
            if plugin:
                plugin.enabled = enabled
                self._refresh_plugins()

    def _run_now(self, name: str):
        """立即运行插件"""
        from v2.bridge import bridge
        poller = bridge.get_poller()
        if poller:
            plugin = poller.plugin_manager.get_plugin(name)
            if plugin:
                account = poller._account
                user_id = poller._user_id
                try:
                    msg = plugin.on_start(account, user_id)
                    if msg:
                        from client import send_message
                        send_message(account, user_id, msg)
                        self._refresh_plugins()
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"运行失败: {e}")
