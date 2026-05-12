"""
深色主题 QSS 样式表 - VS Code / Discord 风格
"""


def dark_theme() -> str:
    return """
    /* ── 全局 ── */
    QMainWindow, QWidget {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
        font-size: 13px;
    }

    /* ── 中心区域 ── */
    QWidget#centralWidget {
        background-color: #0d1117;
    }

    /* ── 面板卡片 ── */
    QFrame#panel {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
    }

    /* ── Dock 面板 ── */
    QDockWidget {
        border: 1px solid #30363d;
        border-radius: 8px;
        background-color: #161b22;
    }
    QDockWidget::title {
        background-color: #161b22;
        border-bottom: 1px solid #30363d;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        padding: 8px 12px;
        color: #8b949e;
        font-size: 12px;
        font-weight: bold;
    }
    QDockWidget > QWidget {
        background-color: #161b22;
        border-radius: 0 0 8px 8px;
    }

    /* ── 按钮 ── */
    QPushButton {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 5px 14px;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #30363d;
        border-color: #8b949e;
    }
    QPushButton:pressed {
        background-color: #161b22;
        border-color: #58a6ff;
    }
    QPushButton:disabled {
        background-color: #161b22;
        color: #484f58;
        border-color: #21262d;
    }
    QPushButton:checkable {
        background-color: #161b22;
        border-color: #30363d;
    }
    QPushButton:checkable:checked {
        background-color: #1f6feb;
        border-color: #58a6ff;
        color: #ffffff;
    }

    /* ── 输入框 ── */
    QLineEdit {
        background-color: #0d1117;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 7px 10px;
        selection-background-color: #1f6feb;
    }
    QLineEdit:focus {
        border: 1px solid #58a6ff;
        background-color: #161b22;
    }
    QLineEdit:placeholder {
        color: #484f58;
    }

    /* ── 多行文本（消息日志/控制台） ── */
    QTextEdit {
        background-color: #0d1117;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 8px;
        font-family: "Cascadia Code", "Consolas", "Microsoft YaHei UI", monospace;
        font-size: 12px;
        padding: 8px;
    }

    /* ── 表格 ── */
    QTableWidget {
        background-color: #0d1117;
        alternate-background-color: #161b22;
        gridline-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 8px;
    }
    QTableWidget::item {
        color: #c9d1d9;
        padding: 6px 8px;
        border-bottom: 1px solid #21262d;
    }
    QTableWidget::item:selected {
        background-color: #1f6feb;
        color: #ffffff;
    }
    QTableWidget::item:hover {
        background-color: #1c2128;
    }
    QHeaderView::section {
        background-color: #161b22;
        color: #8b949e;
        border: none;
        border-bottom: 1px solid #30363d;
        padding: 6px 8px;
        font-weight: 600;
        font-size: 12px;
    }

    /* ── 滚动条 ── */
    QScrollBar:vertical {
        background-color: transparent;
        width: 8px;
        margin: 4px 0;
    }
    QScrollBar::handle:vertical {
        background-color: #30363d;
        border-radius: 4px;
        min-height: 40px;
        margin: 0 2px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #484f58;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        background-color: transparent;
        height: 8px;
        margin: 0 4px;
    }
    QScrollBar::handle:horizontal {
        background-color: #30363d;
        border-radius: 4px;
        min-width: 40px;
        margin: 2px 0;
    }
    QScrollBar::handle:horizontal:hover {
        background-color: #484f58;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    /* ── 下拉框 ── */
    QComboBox {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 5px 10px;
    }
    QComboBox:hover {
        border-color: #8b949e;
    }
    QComboBox:focus {
        border-color: #58a6ff;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid #8b949e;
        margin-right: 6px;
    }
    QComboBox QAbstractItemView {
        background-color: #161b22;
        color: #c9d1d9;
        selection-background-color: #1f6feb;
        outline: 0;
        border: 1px solid #30363d;
        border-radius: 6px;
    }

    /* ── 标签 ── */
    QLabel {
        color: #c9d1d9;
        background-color: transparent;
    }

    /* ── 分隔线 ── */
    QFrame[frameShape="4"] {
        color: #30363d;
    }

    /* ── 菜单 ── */
    QMenu {
        background-color: #161b22;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 28px 6px 12px;
        border-radius: 4px;
    }
    QMenu::item:selected {
        background-color: #1f6feb;
    }
    QMenu::separator {
        height: 1px;
        background-color: #30363d;
        margin: 4px 8px;
    }
    QMenuBar {
        background-color: #161b22;
        color: #c9d1d9;
    }
    QMenuBar::item:selected {
        background-color: #1f6feb;
        border-radius: 4px;
    }

    /* ── 状态栏 ── */
    QStatusBar {
        background-color: #161b22;
        color: #8b949e;
        border-top: 1px solid #30363d;
        font-size: 12px;
        padding: 2px 8px;
    }
    QStatusBar::item {
        border: none;
    }

    /* ── 工具栏 ── */
    QToolBar {
        background-color: #161b22;
        border: none;
        border-bottom: 1px solid #30363d;
        spacing: 6px;
        padding: 6px;
    }
    QToolBar::separator {
        background-color: #30363d;
        width: 1px;
        margin: 4px 6px;
    }

    /* ── Dock 标题栏文字 ── */
    QDockWidget::title {
        text-align: left;
    }
    """
