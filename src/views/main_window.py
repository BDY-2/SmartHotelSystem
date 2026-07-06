# -*- coding: utf-8 -*-
"""v3.0 主窗口 —— 智能工作台 + 业务导航"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QStackedWidget, QListWidget,
                              QListWidgetItem, QFrame, QStatusBar, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QPoint
from PyQt5.QtGui import QFont, QIcon
from datetime import datetime
from src.config import APP_NAME, APP_WIDTH, APP_HEIGHT
from src.views.dashboard_view import DashboardView
from src.views.room_status_view import RoomStatusView
from src.views.reservation_view import ReservationView
from src.views.checkin_view import CheckinView
from src.views.checkout_view import CheckoutView
from src.views.cashier_view import CashierView
from src.views.customer_view import CustomerView
from src.views.report_view import ReportView
from src.views.settings_view import SettingsView
from src.resources.theme import COLORS, SPACING, FONTS, apply_font
from src.utils.event_bus import event_bus


# 导航项配置：(图标, 名称, stack索引)
NAV_ITEMS = [
    ("📊", "仪表盘", 0),
    ("🏨", "房态管理", 1),
    ("📋", "预订管理", 2),
    ("✅", "入住办理", 3),
    ("🏁", "退房结算", 4),
    ("💰", "收银台", 5),
    ("👥", "客户管理", 6),
    ("📈", "报表中心", 7),
    ("⚙️", "系统设置", 8),
]

NAV_TARGETS = {
    "dashboard": 0,
    "rooms": 1,
    "reservations": 2,
    "checkin": 3,
    "checkout": 4,
    "cashier": 5,
    "customers": 6,
    "reports": 7,
    "settings": 8,
}

ROLE_NAV_KEYS = {
    "管理员": ["dashboard", "rooms", "reservations", "checkin", "checkout", "cashier", "customers", "reports", "settings"],
    "前台": ["dashboard", "rooms", "reservations", "checkin", "checkout", "cashier", "customers"],
    "财务": ["dashboard", "cashier", "reports", "customers"],
    "客房": ["dashboard", "rooms"],
}


def role_nav_items(role):
    allowed = ROLE_NAV_KEYS.get(role, ROLE_NAV_KEYS["前台"])
    by_target = {target: NAV_ITEMS[index] for target, index in NAV_TARGETS.items()}
    return [by_target[target] for target in allowed if target in by_target]


def role_nav_targets(role):
    return {target: NAV_TARGETS[target] for target in ROLE_NAV_KEYS.get(role, ROLE_NAV_KEYS["前台"]) if target in NAV_TARGETS}


class MainWindow(QMainWindow):
    logout_signal = pyqtSignal()

    def __init__(self, user_info):
        super().__init__()
        self.user_info = user_info
        self.nav_items = role_nav_items(self.user_info.get("role"))
        self.nav_targets = role_nav_targets(self.user_info.get("role"))
        self._drag_pos = None
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(APP_WIDTH, APP_HEIGHT)
        self.resize(1360, 820)
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        central.setObjectName("windowChromeRoot")
        central.setStyleSheet(f"""
            QWidget#windowChromeRoot {{
                background: {COLORS['bg']};
                border: 1px solid {COLORS['primary']};
            }}
        """)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)
        root.addWidget(self._build_window_title_bar())

        ml = QHBoxLayout()
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)
        root.addLayout(ml, 1)

        # ========= 侧边栏 =========
        sb = QFrame()
        sb.setFixedWidth(180)
        sb.setStyleSheet(f"background: {COLORS['primary']}; border: none;")
        sl = QVBoxLayout(sb)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)

        # Logo区
        logo_frame = QFrame()
        logo_frame.setFixedHeight(58)
        logo_layout = QHBoxLayout(logo_frame)
        logo_layout.setContentsMargins(16, 0, 14, 0)
        logo_layout.setSpacing(8)
        
        logo_icon = QLabel("🏨")
        logo_icon.setFont(QFont("Segoe UI Emoji", 17))
        logo_icon.setStyleSheet("color: white;")
        logo_layout.addWidget(logo_icon)
        
        logo_text = QLabel("iHome PMS")
        logo_text.setFont(QFont("Segoe UI", 14, QFont.Bold))
        logo_text.setStyleSheet("color: white; letter-spacing: 1px;")
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        
        sl.addWidget(logo_frame)

        # 分隔线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.1);")
        sep.setContentsMargins(16, 0, 16, 0)
        sl.addWidget(sep)

        # 导航列表
        self.nav = QListWidget()
        self.nav.setFont(QFont(*FONTS["body"]))
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
                padding: 8px 0;
            }}
            QListWidget::item {{
                padding: 9px 14px;
                margin: 2px 10px;
                border-radius: 6px;
                color: rgba(255,255,255,0.7);
                font-size: 13px;
            }}
            QListWidget::item:selected {{
                background: rgba(255,255,255,0.15);
                color: white;
                font-weight: bold;
            }}
            QListWidget::item:hover {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)
        self.nav.setIconSize(QSize(16, 16))
        
        for icon_text, name, _ in self.nav_items:
            item = QListWidgetItem(f"  {icon_text}   {name}")
            item.setSizeHint(QSize(0, 42))
            self.nav.addItem(item)
        
        self.nav.currentRowChanged.connect(self._nav)
        self.nav.blockSignals(True)
        self.nav.setCurrentRow(0)
        self.nav.blockSignals(False)
        sl.addWidget(self.nav, 1)

        # 底部用户信息
        uf = QFrame()
        uf.setObjectName("sidebarUserPanel")
        uf.setStyleSheet("""
            QFrame#sidebarUserPanel {
                background: rgba(0,0,0,0.2);
                border: none;
            }
            QFrame#sidebarUserPanel QLabel {
                background: transparent;
                border: none;
            }
        """)
        ul = QHBoxLayout(uf)
        ul.setContentsMargins(12, 10, 12, 10)
        ul.setSpacing(8)
        
        # 头像（用首字母代替）
        avatar = QLabel(self.user_info['real_name'][0] if self.user_info.get('real_name') else "U")
        avatar.setFixedSize(30, 30)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFont(QFont(*FONTS["body_b"]))
        avatar.setStyleSheet(f"""
            background: {COLORS['accent']};
            color: white;
            border-radius: 15px;
            font-weight: bold;
        """)
        ul.addWidget(avatar)
        
        # 用户信息
        user_info_layout = QVBoxLayout()
        user_info_layout.setSpacing(2)
        nm = QLabel(self.user_info['real_name'])
        nm.setFont(QFont(*FONTS["body_b"]))
        nm.setStyleSheet("color: white;")
        user_info_layout.addWidget(nm)
        rl = QLabel(self.user_info['role'])
        rl.setFont(QFont(*FONTS["caption"]))
        rl.setStyleSheet("color: rgba(255,255,255,0.6);")
        user_info_layout.addWidget(rl)
        ul.addLayout(user_info_layout, 1)

        switch_btn = QPushButton("切换")
        switch_btn.setObjectName("sidebarSwitchAccountButton")
        switch_btn.setFixedSize(46, 26)
        switch_btn.setCursor(Qt.PointingHandCursor)
        switch_btn.setFocusPolicy(Qt.NoFocus)
        switch_btn.setStyleSheet("""
            QPushButton#sidebarSwitchAccountButton {
                background: rgba(255,255,255,0.14);
                color: white;
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton#sidebarSwitchAccountButton:hover {
                background: rgba(255,255,255,0.24);
            }
        """)
        switch_btn.clicked.connect(self._do_logout)
        ul.addWidget(switch_btn)
        
        sl.addWidget(uf)

        ml.addWidget(sb)

        # ========= 右侧主内容区 =========
        r = QFrame()
        r.setStyleSheet(f"background: {COLORS['bg']};")
        rl = QVBoxLayout(r)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # 顶部工具栏
        tb = QFrame()
        tb.setFixedHeight(54)
        tb.setStyleSheet(f"""
            background: {COLORS['surface']};
            border-bottom: 1px solid {COLORS['border']};
        """)
        tl = QHBoxLayout(tb)
        tl.setContentsMargins(20, 0, 20, 0)
        tl.setSpacing(12)

        self.crumb = QLabel("仪表盘")
        self.crumb.setFont(QFont(*FONTS["h3"]))
        self.crumb.setStyleSheet(f"color: {COLORS['text_primary']};")
        tl.addWidget(self.crumb)
        tl.addStretch()

        self.clock = QLabel()
        self.clock.setFont(QFont(*FONTS["body_sm"]))
        self.clock.setStyleSheet(f"color: {COLORS['text_muted']};")
        tl.addWidget(self.clock)
        rl.addWidget(tb)

        # 时钟
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(1000)
        self._tick()

        # 内容栈
        self.stack = QStackedWidget()
        self.dash = DashboardView(self.user_info, navigate_callback=self.navigate_to)  # 0
        self.rooms = RoomStatusView()          # 1
        self.reservations = ReservationView()  # 2
        self.checkin = CheckinView()           # 3
        self.checkout = CheckoutView()         # 4
        self.cashier = CashierView()           # 5
        self.customers = CustomerView()        # 6
        self.reports = ReportView()            # 7
        self.settings = SettingsView()         # 8
        for w in [self.dash, self.rooms, self.reservations,
                   self.checkin, self.checkout, self.cashier,
                   self.customers, self.reports, self.settings]:
            w.current_user = self.user_info
            self.stack.addWidget(w)
        
        # 导航映射
        # 退出登录
        self.settings.logout_requested.connect(self._do_logout)
        event_bus.data_changed.connect(self._sync_pages)
        rl.addWidget(self.stack, 1)

        self.status_label = QLabel(
            f"  用户: {self.user_info['real_name']}  |  "
            f"角色: {self.user_info['role']}  |  "
            f"数据库: MySQL  |  房量: 10 间"
        )
        self.status_label.setFixedHeight(24)
        self.status_label.setFont(QFont(*FONTS["caption"]))
        self.status_label.setStyleSheet(f"""
            background: {COLORS['surface']};
            color: {COLORS['text_secondary']};
            border-top: 1px solid {COLORS['border']};
        """)
        root.addWidget(self.status_label)

        ml.addWidget(r, 1)

    def _build_window_title_bar(self):
        bar = QFrame()
        bar.setObjectName("customTitleBar")
        bar.setFixedHeight(42)
        bar.setStyleSheet(f"""
            QFrame#customTitleBar {{
                background: {COLORS['surface']};
                border: none;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QFrame#customTitleBar QLabel {{
                background: transparent;
                border: none;
            }}
            QPushButton#windowButton {{
                background: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: 6px;
                min-width: 40px;
                max-width: 40px;
                min-height: 30px;
                max-height: 30px;
                font-size: 18px;
                font-weight: normal;
                padding: 0;
            }}
            QPushButton#windowButton:hover {{
                background: {COLORS['primary_light']};
                color: {COLORS['primary']};
            }}
            QPushButton#windowCloseButton {{
                background: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: 6px;
                min-width: 40px;
                max-width: 40px;
                min-height: 30px;
                max-height: 30px;
                font-size: 20px;
                font-weight: normal;
                padding: 0;
            }}
            QPushButton#windowCloseButton:hover {{
                background: {COLORS['danger']};
                color: white;
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(8)

        icon = QLabel("🏨")
        icon.setFont(QFont("Segoe UI Emoji", 12))
        layout.addWidget(icon)
        title = QLabel(APP_NAME)
        title.setFont(QFont(*FONTS["caption_b"]))
        title.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(title)
        layout.addStretch()

        min_btn = QPushButton("−")
        min_btn.setObjectName("windowButton")
        min_btn.setFont(QFont("Segoe UI", 16))
        min_btn.setFocusPolicy(Qt.NoFocus)
        min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(min_btn)

        max_btn = QPushButton("□")
        max_btn.setObjectName("windowButton")
        max_btn.setFont(QFont("Segoe UI", 13))
        max_btn.setFocusPolicy(Qt.NoFocus)
        max_btn.clicked.connect(self._toggle_maximize)
        layout.addWidget(max_btn)

        close_btn = QPushButton("×")
        close_btn.setObjectName("windowCloseButton")
        close_btn.setFont(QFont("Segoe UI", 18))
        close_btn.setFocusPolicy(Qt.NoFocus)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        bar.mousePressEvent = self._title_mouse_press
        bar.mouseMoveEvent = self._title_mouse_move
        bar.mouseReleaseEvent = self._title_mouse_release
        bar.mouseDoubleClickEvent = lambda _: self._toggle_maximize()
        return bar

    def _title_mouse_press(self, event):
        if event.button() == Qt.LeftButton and not self.isMaximized():
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def _title_mouse_move(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def _title_mouse_release(self, event):
        self._drag_pos = None
        event.accept()

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _nav(self, idx):
        if 0 <= idx < len(self.nav_items):
            _, name, stack_idx = self.nav_items[idx]
            self.crumb.setText(name)
            self.stack.setCurrentIndex(stack_idx)

    def navigate_to(self, target):
        if target not in self.nav_targets:
            target = "dashboard"
        stack_index = self.nav_targets.get(target)
        for row, (_, _, item_stack_index) in enumerate(self.nav_items):
            if item_stack_index == stack_index:
                self.nav.setCurrentRow(row)
                return

    def _do_logout(self):
        self.close()
        self.logout_signal.emit()

    def _sync_pages(self, topic="all"):
        refreshers = [
            (self.dash, "_load_data"),
            (self.rooms, "_load"),
            (self.reservations, "_load"),
            (self.checkin, "_load_data"),
            (self.checkout, "_load"),
            (self.cashier, "_load"),
            (self.customers, "_load"),
            (self.reports, "_load"),
        ]
        for widget, method_name in refreshers:
            method = getattr(widget, method_name, None)
            if callable(method):
                method()

    def _tick(self):
        self.clock.setText(datetime.now().strftime("%Y年%m月%d日  %H:%M:%S"))
