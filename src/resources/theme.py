# -*- coding: utf-8 -*-
"""
v3.0 全局主题系统
参考华住华掌柜 / 现代B端设计风格
设计原则：清晰、高效、克制、不刺眼
"""
from PyQt5.QtGui import QFont, QColor

# ===== 调色板 =====
COLORS = {
    # 主色调 —— 酒店会员感紫色系
    "primary":        "#3C2B56",   # 主色（按钮、选中态）
    "primary_hover":  "#4A356A",   # 悬停
    "primary_pressed":"#2F2243",   # 按下
    "primary_light":  "#EEEAF4",   # 浅色背景（选中行背景）
    
    # 强调色 —— 琥珀金（核心操作、提醒）
    "accent":         "#f59e0b",
    "accent_hover":   "#fbbf24",
    "accent_pressed": "#d97706",
    "accent_light":   "#fef3c7",
    
    # 中性色
    "bg":             "#f1f5f9",   # 页面背景
    "surface":        "#ffffff",   # 卡片/面板背景
    "surface_hover":  "#f8fafc",   # 悬停行背景
    "border":         "#e2e8f0",   # 边框
    "border_light":   "#f1f5f9",   # 细分隔线
    
    # 文字层级
    "text_primary":   "#0f172a",   # 正文/标题
    "text_secondary": "#334155",   # 次要文字
    "text_muted":     "#64748b",   # 辅助/占位文字
    "text_inverse":   "#ffffff",   # 反白文字
    
    # 房态色
    "room_vacant":    "#10b981",   # 空闲 —— 翠绿
    "room_occupied":  "#ef4444",   # 已入住 —— 红
    "room_reserved":  "#f59e0b",   # 已预订 —— 琥珀
    "room_dirty":     "#f97316",   # 脏房 —— 橙（原来的深棕太暗，白字看不清）
    "room_maintenance":"#64748b",  # 维修 —— 灰蓝
    
    # 功能色
    "success":        "#10b981",
    "success_light":  "#d1fae5",
    "warning":        "#f59e0b",
    "warning_light":  "#fef3c7",
    "danger":         "#ef4444",
    "danger_light":   "#fee2e2",
    "info":           "#2563eb",
    "info_light":     "#dbeafe",
}

# ===== 尺寸系统 (4px 基础网格) =====
SPACING = {
    "xs":   4,
    "sm":   8,
    "md":   12,
    "lg":   16,
    "xl":   20,
    "xxl":  24,
    "xxxl": 32,
}

# ===== 圆角系统 =====
RADIUS = {
    "sm": 4,
    "md": 6,
    "lg": 8,
    "xl": 12,
}

# ===== 字体层级 =====
B = 75   # QFont.Bold
M = 63   # QFont.DemiBold
N = 50   # QFont.Normal
L = 25   # QFont.Light

FONTS = {
    "h1":      ("Microsoft YaHei", 22, B),
    "h2":      ("Microsoft YaHei", 20, B),
    "h3":      ("Microsoft YaHei", 18, B),
    "h4":      ("Microsoft YaHei", 16, B),
    "body":    ("Microsoft YaHei", 15, N),
    "body_b":  ("Microsoft YaHei", 15, B),
    "body_sm": ("Microsoft YaHei", 14, N),
    "caption": ("Microsoft YaHei", 13, N),
    "caption_b":("Microsoft YaHei", 13, B),
    
    # 数字字体（等宽）
    "number":    ("Segoe UI", 24, B),
    "number_lg": ("Segoe UI", 30, B),
    "number_sm": ("Segoe UI", 15, B),
    "room_number": ("Segoe UI", 26, B),
}

# ===== 全局 QSS =====
GLOBAL_QSS = f"""
/* ========== 全局基础 ========== */
* {{
    font-family: "Microsoft YaHei", "Microsoft YaHei UI", "Segoe UI";
    font-size: 15px;
    color: {COLORS['text_primary']};
    outline: none;
}}

QWidget {{
    background: transparent;
}}

/* ========== 标签 ========== */
QLabel {{
    background: transparent;
    border: none;
    color: {COLORS['text_primary']};
}}

/* ========== 输入框 ========== */
QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit, QComboBox {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: {RADIUS['md']}px;
    padding: 6px 10px;
    font-size: 14px;
    color: {COLORS['text_primary']};
    min-height: 24px;
    selection-background-color: {COLORS['primary_light']};
    selection-color: {COLORS['primary']};
}}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover, QDateTimeEdit:hover, QComboBox:hover {{
    border-color: {COLORS['text_muted']};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus, QComboBox:focus {{
    border: 1px solid {COLORS['primary']};
    background: {COLORS['surface']};
}}

QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled, QDateTimeEdit:disabled, QComboBox:disabled {{
    background: {COLORS['bg']};
    color: {COLORS['text_muted']};
    border-color: {COLORS['border']};
}}

/* 占位符文字 */
QLineEdit[placeholderText=""] {{ /* noop */ }}
QLineEdit::placeholder {{
    color: {COLORS['text_muted']};
}}

/* 数字输入框按钮 */
QSpinBox::up-button, QDoubleSpinBox::up-button, QDateEdit::up-button, QDateTimeEdit::up-button {{
    width: 20px;
    border: none;
    background: transparent;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button, QDateEdit::down-button, QDateTimeEdit::down-button {{
    width: 20px;
    border: none;
    background: transparent;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QDateEdit::up-arrow, QDateTimeEdit::up-arrow {{
    width: 8px; height: 8px;
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 4px solid {COLORS['text_secondary']};
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QDateEdit::down-arrow, QDateTimeEdit::down-arrow {{
    width: 8px; height: 8px;
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid {COLORS['text_secondary']};
}}

/* ========== 下拉框 ========== */
QComboBox {{
    padding-right: 28px;
}}
QComboBox::drop-down {{
    width: 28px;
    border: none;
}}
QComboBox::down-arrow {{
    width: 8px; height: 8px;
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid {COLORS['text_secondary']};
}}
QComboBox QAbstractItemView {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: {RADIUS['md']}px;
    padding: 4px;
    selection-background-color: {COLORS['primary_light']};
    selection-color: {COLORS['primary']};
    outline: none;
}}

/* ========== 按钮 ========== */
QPushButton {{
    background: {COLORS['primary']};
    color: white;
    border: none;
    border-radius: {RADIUS['md']}px;
    padding: 7px 14px;
    font-size: 14px;
    font-weight: bold;
    min-height: 24px;
}}
QPushButton:hover {{
    background: {COLORS['primary_hover']};
}}
QPushButton:pressed {{
    background: {COLORS['primary_pressed']};
}}
QPushButton:disabled {{
    background: {COLORS['border']};
    color: {COLORS['text_muted']};
}}

/* 次要按钮（描边） */
QPushButton[variant="secondary"] {{
    background: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
}}
QPushButton[variant="secondary"]:hover {{
    background: {COLORS['surface_hover']};
    border-color: {COLORS['text_muted']};
}}
QPushButton[variant="secondary"]:pressed {{
    background: {COLORS['bg']};
}}

/* 强调按钮（琥珀色，主操作） */
QPushButton[variant="accent"] {{
    background: {COLORS['accent']};
    color: white;
}}
QPushButton[variant="accent"]:hover {{
    background: {COLORS['accent_hover']};
}}
QPushButton[variant="accent"]:pressed {{
    background: {COLORS['accent_pressed']};
}}
QPushButton[variant="accent"]:disabled {{
    background: {COLORS['border']};
    color: {COLORS['text_muted']};
}}

/* 危险按钮 */
QPushButton[variant="danger"] {{
    background: {COLORS['danger']};
    color: white;
}}
QPushButton[variant="danger"]:hover {{
    background: #f87171;
}}
QPushButton[variant="danger"]:pressed {{
    background: #dc2626;
}}

/* 文字按钮 */
QPushButton[variant="text"] {{
    background: transparent;
    color: {COLORS['primary']};
    padding: 6px 12px;
    font-weight: normal;
}}
QPushButton[variant="text"]:hover {{
    background: {COLORS['primary_light']};
}}
QPushButton[variant="text"]:disabled {{
    background: {COLORS['bg']};
    color: {COLORS['text_muted']};
    border: 1px solid {COLORS['border']};
}}
QPushButton[variant="secondary"]:disabled,
QPushButton[variant="danger"]:disabled {{
    background: {COLORS['border']};
    color: {COLORS['text_muted']};
    border: 1px solid {COLORS['border']};
}}

/* 小按钮 */
QPushButton[size="small"] {{
    padding: 6px 12px;
    font-size: 14px;
    min-height: 24px;
}}

/* 大按钮 */
QPushButton[size="large"] {{
    padding: 10px 20px;
    font-size: 14px;
    min-height: 30px;
    border-radius: {RADIUS['lg']}px;
}}

/* ========== 表格 ========== */
QTableWidget {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: {RADIUS['lg']}px;
    gridline-color: {COLORS['border_light']};
    font-size: 14px;
    selection-background-color: {COLORS['primary_light']};
    selection-color: {COLORS['primary']};
    outline: none;
}}

QTableWidget::item {{
    padding: 9px 12px;
    border-bottom: 1px solid {COLORS['border_light']};
}}

QTableWidget::item:selected {{
    background: {COLORS['primary_light']};
    color: {COLORS['primary']};
}}

QTableWidget::item:hover {{
    background: {COLORS['surface_hover']};
}}

/* 表头 */
QHeaderView::section {{
    background: {COLORS['bg']};
    border: none;
    border-bottom: 2px solid {COLORS['border']};
    padding: 10px 12px;
    font-weight: bold;
    font-size: 14px;
    color: {COLORS['text_secondary']};
    text-align: left;
}}

QHeaderView::section:first {{
    border-top-left-radius: {RADIUS['lg']}px;
}}
QHeaderView::section:last {{
    border-top-right-radius: {RADIUS['lg']}px;
}}

/* 表格角落 */
QTableCornerButton::section {{
    background: {COLORS['bg']};
    border: none;
    border-bottom: 2px solid {COLORS['border']};
    border-top-left-radius: {RADIUS['lg']}px;
}}

/* 滚动条 */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 4px;
    min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS['text_muted']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS['border']};
    border-radius: 4px;
    min-width: 40px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {COLORS['text_muted']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* ========== 状态栏 ========== */
QStatusBar {{
    color: {COLORS['text_secondary']};
    background: {COLORS['surface']};
    border-top: 1px solid {COLORS['border']};
    font-size: 13px;
    padding: 0 16px;
    height: 36px;
}}
QStatusBar::item {{
    border: none;
}}

/* ========== 列表控件 ========== */
QListWidget {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{
    padding: 10px 16px;
    border-radius: {RADIUS['md']}px;
    margin: 2px 8px;
    color: {COLORS['text_secondary']};
}}
QListWidget::item:hover {{
    background: rgba(255,255,255,0.05);
    color: white;
}}
QListWidget::item:selected {{
    background: rgba(255,255,255,0.12);
    color: white;
    font-weight: bold;
}}

/* ========== 菜单 ========== */
QMenu {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: {RADIUS['md']}px;
    padding: 4px;
}}
QMenu::item {{
    padding: 8px 24px 8px 16px;
    border-radius: {RADIUS['sm']}px;
    font-size: 13px;
}}
QMenu::item:selected {{
    background: {COLORS['primary_light']};
    color: {COLORS['primary']};
}}
QMenu::separator {{
    height: 1px;
    background: {COLORS['border']};
    margin: 4px 8px;
}}

/* ========== 弹窗 ========== */
QMessageBox {{
    background: {COLORS['surface']};
}}
QMessageBox QLabel {{
    background: transparent;
    border: none;
    color: {COLORS['text_primary']};
}}
QMessageBox QPushButton {{
    background: {COLORS['primary']};
    color: white;
    border: none;
    border-radius: {RADIUS['md']}px;
    padding: 7px 16px;
    min-width: 78px;
    min-height: 28px;
    font-weight: bold;
}}
QMessageBox QPushButton:hover {{
    background: {COLORS['primary_hover']};
}}
QDialog {{
    background: {COLORS['surface']};
}}
QDialog QLabel {{
    background: transparent;
    border: none;
}}

/* ========== 滚动区域 ========== */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* ========== 分组框 ========== */
QGroupBox {{
    border: 1px solid {COLORS['border']};
    border-radius: {RADIUS['md']}px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: {COLORS['text_secondary']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}}

/* ========== 进度条 ========== */
QProgressBar {{
    background: {COLORS['bg']};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {COLORS['primary']};
    border-radius: 4px;
}}

/* ========== 防止容器 QFrame 样式误伤文字 ==========
   QLabel 继承自 QFrame；页面局部样式中的 QFrame 选择器会把边框套到文字上。
   这里用更具体的选择器统一恢复标签为纯文字。 */
QWidget QLabel, QFrame QLabel {{
    background: transparent;
    border: none;
}}
"""


# ===== 工具函数 =====

def apply_font(widget, font_key):
    """给控件应用预设字体"""
    font_info = FONTS.get(font_key, FONTS["body"])
    font = QFont(font_info[0], font_info[1], font_info[2])
    widget.setFont(font)
    return font


def darken_color(hex_color, factor=0.85):
    """颜色加深"""
    c = hex_color.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"


def lighten_color(hex_color, factor=0.9):
    """颜色变浅"""
    c = hex_color.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    r = int(r + (255 - r) * (1 - factor))
    g = int(g + (255 - g) * (1 - factor))
    b = int(b + (255 - b) * (1 - factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def panel_style(border=True):
    """通用面板 QSS"""
    if border:
        return (
            "Panel {"
            f"  background: {COLORS['surface']};"
            f"  border-radius: {RADIUS['lg']}px;"
            f"  border: 1px solid {COLORS['border']};"
            "}"
            "Panel QLabel { background: transparent; border: none; }"
        )
    else:
        return (
            "Panel {"
            f"  background: {COLORS['surface']};"
            f"  border-radius: {RADIUS['lg']}px;"
            "}"
            "Panel QLabel { background: transparent; border: none; }"
        )


def dash_card_style(fg_color):
    """仪表盘卡片 QSS"""
    return (
        "DashCard {"
        f"  background: {COLORS['surface']};"
        f"  border-radius: {RADIUS['xl']}px;"
        f"  border-top: 3px solid {fg_color};"
        "}"
        "DashCard QLabel { background: transparent; border: none; }"
    )


def status_tag_style(color, bg_color=None):
    """状态标签 QSS"""
    if bg_color is None:
        # 自动生成浅色背景
        bg = lighten_color(color, 0.9)
    else:
        bg = bg_color
    return (
        f"background: {bg};"
        f"color: {color};"
        f"border-radius: {RADIUS['sm']}px;"
        f"padding: 2px 8px;"
        f"font-size: 11px;"
        f"font-weight: bold;"
    )


def sidebar_style():
    """侧边栏 QSS"""
    return (
        "QLabel { color: rgba(255,255,255,0.9); background: transparent; border: none; }"
    )


MESSAGE_BOX_QSS = f"""
QMessageBox {{
    background: {COLORS['surface']};
}}
QMessageBox QLabel {{
    background: transparent;
    border: none;
    color: {COLORS['text_primary']};
    font-family: "Microsoft YaHei";
    font-size: 15px;
}}
QMessageBox QPushButton {{
    background: {COLORS['primary']};
    color: white;
    border: none;
    border-radius: {RADIUS['md']}px;
    padding: 8px 18px;
    min-width: 88px;
    min-height: 32px;
    font-family: "Microsoft YaHei";
    font-size: 14px;
    font-weight: bold;
}}
QMessageBox QPushButton:hover {{
    background: {COLORS['primary_hover']};
}}
QMessageBox QPushButton:pressed {{
    background: {COLORS['primary_pressed']};
}}
"""


def install_styled_message_boxes():
    """Route all QMessageBox static calls through one compact styled dialog."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import (
        QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
        QPushButton, QVBoxLayout
    )

    icon_meta = {
        QMessageBox.Information: ("i", COLORS["primary"], COLORS["primary_light"]),
        QMessageBox.Warning: ("!", COLORS["accent"], COLORS["accent_light"]),
        QMessageBox.Critical: ("!", COLORS["danger"], "#fee2e2"),
        QMessageBox.Question: ("?", COLORS["primary"], COLORS["primary_light"]),
    }
    button_text = {
        QMessageBox.Ok: "确定",
        QMessageBox.Yes: "确定",
        QMessageBox.No: "取消",
        QMessageBox.Cancel: "取消",
        QMessageBox.Close: "关闭",
    }

    def _button_values(buttons):
        order = [
            QMessageBox.Yes,
            QMessageBox.Ok,
            QMessageBox.No,
            QMessageBox.Cancel,
            QMessageBox.Close,
        ]
        return [value for value in order if buttons & value] or [QMessageBox.Ok]

    def _show(icon, parent, title, text, buttons=QMessageBox.Ok, default_button=QMessageBox.NoButton):
        dialog = QDialog(parent)
        dialog.setObjectName("styledMessageDialog")
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.setMinimumWidth(340)
        dialog.setStyleSheet(f"""
            QDialog#styledMessageDialog {{
                background: {COLORS['surface']};
            }}
            QDialog#styledMessageDialog QLabel {{
                background: transparent;
                border: none;
                color: {COLORS['text_primary']};
                font-family: "Microsoft YaHei";
                font-size: 15px;
            }}
            QLabel#styledMessageIcon {{
                min-width: 34px;
                max-width: 34px;
                min-height: 34px;
                max-height: 34px;
                border-radius: 17px;
                font-size: 20px;
                font-weight: 800;
            }}
            QPushButton#styledMessagePrimary {{
                min-width: 92px;
                min-height: 34px;
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 7px 18px;
                font-family: "Microsoft YaHei";
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton#styledMessagePrimary:hover {{
                background: {COLORS['primary_hover']};
            }}
            QPushButton#styledMessageSecondary {{
                min-width: 92px;
                min-height: 34px;
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 7px 18px;
                font-family: "Microsoft YaHei";
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton#styledMessageSecondary:hover {{
                background: {COLORS['surface_hover']};
                border-color: {COLORS['text_muted']};
            }}
        """)

        root = QVBoxLayout(dialog)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(18)

        content = QHBoxLayout()
        content.setSpacing(16)

        symbol, fg, bg = icon_meta.get(icon, icon_meta[QMessageBox.Information])
        icon_label = QLabel(symbol)
        icon_label.setObjectName("styledMessageIcon")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(
            f"background: {bg}; color: {fg}; border: none; border-radius: 17px;"
        )
        content.addWidget(icon_label, 0, Qt.AlignTop)

        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setMinimumWidth(210)
        text_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        content.addWidget(text_label, 1)
        root.addLayout(content)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background: {COLORS['border_light']}; border: none; max-height: 1px;")
        root.addWidget(line)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch()

        result = {"value": QMessageBox.NoButton}
        values = _button_values(buttons)
        primary_value = default_button if default_button != QMessageBox.NoButton else values[0]
        if primary_value not in values:
            primary_value = values[0]

        def make_handler(value):
            def handler():
                result["value"] = value
                dialog.accept()
            return handler

        for value in values:
            btn = QPushButton(button_text.get(value, "确定"))
            btn.setObjectName(
                "styledMessagePrimary" if value == primary_value else "styledMessageSecondary"
            )
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(make_handler(value))
            if value == primary_value:
                btn.setDefault(True)
                btn.setAutoDefault(True)
            actions.addWidget(btn)

        root.addLayout(actions)
        if dialog.exec_() == QDialog.Accepted:
            return result["value"]
        return QMessageBox.No if (buttons & QMessageBox.No) else QMessageBox.Cancel

    QMessageBox.information = staticmethod(
        lambda parent, title, text, buttons=QMessageBox.Ok, defaultButton=QMessageBox.NoButton:
            _show(QMessageBox.Information, parent, title, text, buttons, defaultButton)
    )
    QMessageBox.warning = staticmethod(
        lambda parent, title, text, buttons=QMessageBox.Ok, defaultButton=QMessageBox.NoButton:
            _show(QMessageBox.Warning, parent, title, text, buttons, defaultButton)
    )
    QMessageBox.critical = staticmethod(
        lambda parent, title, text, buttons=QMessageBox.Ok, defaultButton=QMessageBox.NoButton:
            _show(QMessageBox.Critical, parent, title, text, buttons, defaultButton)
    )
    QMessageBox.question = staticmethod(
        lambda parent, title, text, buttons=QMessageBox.Yes | QMessageBox.No, defaultButton=QMessageBox.NoButton:
            _show(QMessageBox.Question, parent, title, text, buttons, defaultButton)
    )
