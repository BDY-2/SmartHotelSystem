# -*- coding: utf-8 -*-
"""
v3.0 前台入住办理工作台
流程驱动设计，对标华掌柜
步骤：订单确认 → 证件登记 → 选房分配 → 账务确认
"""
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QSpinBox, QFrame, QAbstractItemView, QScrollArea, QGridLayout,
    QMessageBox, QButtonGroup, QRadioButton, QTextEdit, QSizePolicy, QDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor
from datetime import datetime, date, timedelta
from src.utils.db import Session
from src.models.order import Order
from src.models.customer import Customer
from src.models.room import Room
from src.models.room_type import RoomType
from src.models.bill_item import BillItem
from src.resources.theme import COLORS, SPACING, FONTS, apply_font, status_tag_style
from src.services.pms_service import BusinessError, create_walkin_order
from src.services.smart_service import build_guest_profile
from src.utils.event_bus import notify_data_changed

# 会员等级配置：(折扣率, 免押金额度, 升级权益)
TIERS = {
    "普通":  {"discount": 1.0,  "free_deposit": False, "upgrade": 0, "color": "#94a3b8"},
    "银卡":  {"discount": 0.95, "free_deposit": False, "upgrade": 0, "color": "#06b6d4"},
    "金卡":  {"discount": 0.90, "free_deposit": True,  "upgrade": 1, "color": "#f59e0b"},
    "铂金":  {"discount": 0.85, "free_deposit": True,  "upgrade": 1, "color": "#5A496F"},
}

# 房态颜色
ROOM_STATUS_COLORS = {
    "空闲": COLORS["room_vacant"],
    "脏房": COLORS["room_dirty"],
    "维修": COLORS["room_maintenance"],
    "已入住": COLORS["room_occupied"],
    "已预订": COLORS["room_reserved"],
}

# 订单状态颜色
ORDER_STATUS_COLORS = {
    "已确认": COLORS["success"],
    "待确认": COLORS["warning"],
    "已入住": COLORS["info"],
}

# 步骤配置
STEPS = ["订单确认", "证件登记", "选房分配", "账务确认"]


class TextInputDialog(QDialog):
    def __init__(self, title, label, placeholder="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedWidth(380)
        self.setStyleSheet(f"""
            QDialog {{
                background: {COLORS['surface']};
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {COLORS['text_primary']};
            }}
            QLineEdit {{
                background: {COLORS['bg']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 8px 10px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['primary']};
                background: {COLORS['surface']};
            }}
            QPushButton {{
                min-width: 90px;
                min-height: 34px;
                border-radius: 7px;
                font-weight: bold;
                padding: 6px 14px;
            }}
            QPushButton#primaryDialogButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
            }}
            QPushButton#primaryDialogButton:hover {{
                background: {COLORS['primary_hover']};
            }}
            QPushButton#secondaryDialogButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
            }}
            QPushButton#secondaryDialogButton:hover {{
                background: {COLORS['surface_hover']};
                border-color: {COLORS['text_muted']};
            }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)
        title_label = QLabel(title)
        title_label.setFont(QFont(*FONTS["h2"]))
        root.addWidget(title_label)
        prompt = QLabel(label)
        prompt.setFont(QFont(*FONTS["body_sm"]))
        prompt.setStyleSheet(f"color: {COLORS['text_secondary']};")
        root.addWidget(prompt)
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setFont(QFont(*FONTS["body_sm"]))
        root.addWidget(self.input)
        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("取消")
        cancel.setObjectName("secondaryDialogButton")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        ok = QPushButton("确认")
        ok.setObjectName("primaryDialogButton")
        ok.clicked.connect(self.accept)
        actions.addWidget(ok)
        root.addLayout(actions)

    def value(self):
        return self.input.text().strip()


class RoommateVerifyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加同住人")
        self.setModal(True)
        self.setFixedWidth(420)
        self.setStyleSheet(f"""
            QDialog {{
                background: {COLORS['surface']};
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {COLORS['text_primary']};
            }}
            QLineEdit, QComboBox {{
                background: {COLORS['bg']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 8px 10px;
                font-size: 14px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {COLORS['primary']};
                background: {COLORS['surface']};
            }}
            QPushButton {{
                min-width: 92px;
                min-height: 34px;
                border-radius: 7px;
                font-weight: bold;
                padding: 6px 14px;
            }}
            QPushButton#primaryDialogButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
            }}
            QPushButton#primaryDialogButton:hover {{
                background: {COLORS['primary_hover']};
            }}
            QPushButton#secondaryDialogButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
            }}
            QPushButton#secondaryDialogButton:hover {{
                background: {COLORS['surface_hover']};
                border-color: {COLORS['text_muted']};
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        title = QLabel("同住人身份核验")
        title.setFont(QFont(*FONTS["h2"]))
        root.addWidget(title)

        tip = QLabel("同住人也必须完成本次入住身份核验，系统只记录核验方式，不写入客户档案。")
        tip.setWordWrap(True)
        tip.setFont(QFont(*FONTS["body_sm"]))
        tip.setStyleSheet(f"color: {COLORS['text_secondary']};")
        root.addWidget(tip)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("同住人姓名")
        self.name_input.setFont(QFont(*FONTS["body_sm"]))
        root.addWidget(self.name_input)

        self.verify_combo = QComboBox()
        self.verify_combo.addItems(["人工核验", "读卡器模拟"])
        self.verify_combo.setFont(QFont(*FONTS["body_sm"]))
        root.addWidget(self.verify_combo)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("取消")
        cancel.setObjectName("secondaryDialogButton")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        ok = QPushButton("确认添加")
        ok.setObjectName("primaryDialogButton")
        ok.clicked.connect(self._accept_if_valid)
        actions.addWidget(ok)
        root.addLayout(actions)

    def _accept_if_valid(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入同住人姓名")
            return
        self.accept()

    def value(self):
        return {
            "name": self.name_input.text().strip(),
            "verify_method": self.verify_combo.currentText(),
        }


class CheckinView(QWidget):
    def __init__(self):
        super().__init__()
        self._order = None
        self._customer = None
        self._selected_room = None
        self._upgrade_mode = None
        self._extras = []
        self._roommates = []
        self._current_step = 0
        self._room_types = {}
        self._init_ui()
        self._load_data()

    # ==================== UI 构建 ====================
    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ═══ 顶部通栏 ═══
        top_bar = self._build_top_bar()
        main_layout.addWidget(top_bar)

        # ═══ 主体三栏 ═══
        body = QHBoxLayout()
        body.setContentsMargins(12, 12, 12, 12)
        body.setSpacing(12)

        # 左栏：订单列表
        left_panel = self._build_order_list()
        body.addWidget(left_panel)

        # 中栏：步骤操作区
        center_panel = self._build_step_area()
        body.addWidget(center_panel, 4)

        # 右栏：账单常驻
        right_panel = self._build_bill_panel()
        body.addWidget(right_panel)

        main_layout.addLayout(body, 1)
        self.setLayout(main_layout)

    # ---------- 顶部通栏 ----------
    def _build_top_bar(self):
        top = QFrame()
        top.setObjectName("checkinTopBar")
        top.setFixedHeight(54)
        top.setStyleSheet(f"""
            QFrame#checkinTopBar {{
                background: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
            QFrame#checkinTopBar QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(20, 0, 20, 0)
        tl.setSpacing(12)

        # 页面标题
        title = QLabel("前台接待 · 入住办理")
        title.setFont(QFont(*FONTS["h3"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        tl.addWidget(title)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  搜索订单号 / 姓名 / 手机号")
        self.search_input.setMinimumHeight(34)
        self.search_input.setFont(QFont(*FONTS["body"]))
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 6px 12px;
                background: {COLORS['bg']};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
                background: {COLORS['surface']};
            }}
        """)
        self.search_input.textChanged.connect(self._filter_orders)
        tl.addWidget(self.search_input, 1)

        # 散客入住按钮
        walkin_btn = QPushButton("➕  散客入住")
        walkin_btn.setObjectName("walkinButton")
        walkin_btn.setMinimumHeight(34)
        walkin_btn.setMinimumWidth(128)
        walkin_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        walkin_btn.setProperty("variant", "accent")
        walkin_btn.setFont(QFont(*FONTS["body_b"]))
        walkin_btn.setCursor(Qt.PointingHandCursor)
        walkin_btn.setStyleSheet(f"""
            QPushButton#walkinButton {{
                background: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#walkinButton:hover {{
                background: #d97706;
            }}
        """)
        walkin_btn.clicked.connect(self._start_walkin)
        tl.addWidget(walkin_btn)

        tl.addStretch()

        # 时间
        clock = QLabel(datetime.now().strftime("%H:%M"))
        clock.setFont(QFont(*FONTS["body_sm"]))
        clock.setStyleSheet(f"color: {COLORS['text_muted']};")
        tl.addWidget(clock)

        return top

    # ---------- 左侧订单列表 ----------
    def _build_order_list(self):
        panel = QFrame()
        panel.setObjectName("checkinOrderPanel")
        panel.setFixedWidth(280)
        panel.setStyleSheet(f"""
            QFrame#checkinOrderPanel {{
                background: {COLORS['surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#checkinOrderPanel QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        header = QHBoxLayout()
        header.setContentsMargins(14, 12, 14, 8)
        title = QLabel("预订列表")
        title.setFont(QFont(*FONTS["h4"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Tab切换
        tab_layout = QHBoxLayout()
        tab_layout.setContentsMargins(10, 0, 10, 0)
        tab_layout.setSpacing(4)
        
        self.tab_buttons = []
        for i, tab_name in enumerate(["今日预抵", "待确认"]):
            btn = QPushButton(tab_name)
            btn.setProperty("variant", "text")
            btn.setCheckable(True)
            btn.setMinimumHeight(28)
            btn.setFont(QFont(*FONTS["body_sm"]))
            btn.setCursor(Qt.PointingHandCursor)
            if i == 0:
                btn.setChecked(True)
                btn.setStyleSheet(f"""
                    background: {COLORS['primary_light']};
                    color: {COLORS['primary']};
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-weight: bold;
                """)
            else:
                btn.setStyleSheet(f"""
                    background: transparent;
                    color: {COLORS['text_secondary']};
                    border-radius: 6px;
                    padding: 5px 12px;
                """)
            btn.clicked.connect(lambda _, idx=i: self._switch_tab(idx))
            tab_layout.addWidget(btn)
            self.tab_buttons.append(btn)
        
        tab_layout.addStretch()
        layout.addLayout(tab_layout)
        layout.addSpacing(8)

        # 订单表格
        self.order_table = QTableWidget()
        self.order_table.setColumnCount(2)
        self.order_table.setHorizontalHeaderLabels(["客人", "房型"])
        self.order_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.order_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.order_table.setColumnWidth(0, 126)
        self.order_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.order_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.order_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.order_table.verticalHeader().setVisible(False)
        self.order_table.setShowGrid(False)
        self.order_table.setStyleSheet(f"""
            QTableWidget {{
                border: none;
                border-radius: 0;
                background: transparent;
            }}
            QTableWidget::item {{
                padding: 8px 10px;
                border-bottom: 1px solid {COLORS['border_light']};
            }}
            QTableWidget::item:selected {{
                background: {COLORS['primary_light']};
                color: {COLORS['primary']};
            }}
            QHeaderView::section {{
                background: transparent;
                border: none;
                border-bottom: 1px solid {COLORS['border']};
                padding: 7px 10px;
                font-size: 12px;
                color: {COLORS['text_muted']};
            }}
        """)
        self.order_table.clicked.connect(self._on_order_select)
        self.order_table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.order_table, 1)

        return panel

    # ---------- 中间步骤区 ----------
    def _build_step_area(self):
        panel = QFrame()
        panel.setObjectName("checkinStepPanel")
        panel.setStyleSheet(f"""
            QFrame#checkinStepPanel {{
                background: {COLORS['surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#checkinStepPanel QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 步骤条
        self.step_bar = self._build_step_bar()
        layout.addWidget(self.step_bar)

        # 分隔线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {COLORS['border']};")
        layout.addWidget(sep)

        # 步骤内容区（滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.step_content = QWidget()
        self.step_content_layout = QVBoxLayout(self.step_content)
        self.step_content_layout.setContentsMargins(18, 16, 18, 18)
        self.step_content_layout.setSpacing(12)
        scroll.setWidget(self.step_content)
        layout.addWidget(scroll, 1)

        # 初始显示空状态
        self._show_empty_state()

        return panel

    def _build_step_bar(self):
        bar = QFrame()
        bar.setFixedHeight(56)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(18, 0, 18, 0)
        bar_layout.setSpacing(6)

        self.step_labels = []
        self.step_seps = []

        for i, step_name in enumerate(STEPS):
            # 步骤节点
            step_widget = QWidget()
            step_widget.setMinimumWidth(78)
            step_layout = QHBoxLayout(step_widget)
            step_layout.setContentsMargins(0, 0, 0, 0)
            step_layout.setSpacing(6)

            # 数字圆圈
            num_label = QLabel(str(i + 1))
            num_label.setFixedSize(22, 22)
            num_label.setAlignment(Qt.AlignCenter)
            num_label.setFont(QFont(*FONTS["body_b"]))
            num_label.setStyleSheet(f"""
                background: {COLORS['border']};
                color: {COLORS['text_muted']};
                border-radius: 11px;
                font-weight: bold;
            """)
            step_layout.addWidget(num_label)

            # 步骤名
            name_label = QLabel(step_name)
            name_label.setMinimumWidth(48)
            name_label.setFont(QFont(*FONTS["caption_b"]))
            name_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            step_layout.addWidget(name_label)

            bar_layout.addWidget(step_widget)
            self.step_labels.append((num_label, name_label))

            # 分隔线
            if i < len(STEPS) - 1:
                sep = QFrame()
                sep.setFixedHeight(2)
                sep.setStyleSheet(f"background: {COLORS['border']};")
                sep.setFixedWidth(14)
                bar_layout.addWidget(sep)
                self.step_seps.append(sep)

        # 更新第一步为当前状态
        self._update_step_bar(0)

        return bar

    def _show_empty_state(self):
        # 清空内容
        while self.step_content_layout.count():
            item = self.step_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(16)

        icon = QLabel("📋")
        icon.setFont(QFont("Segoe UI Emoji", 48))
        icon.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(icon)

        text = QLabel("请在左侧选择预订订单\n或点击「散客入住」开始办理")
        text.setFont(QFont(*FONTS["body"]))
        text.setAlignment(Qt.AlignCenter)
        text.setStyleSheet(f"color: {COLORS['text_muted']};")
        empty_layout.addWidget(text)

        self.step_content_layout.addWidget(empty, 1)

    # ---------- 右侧账单栏 ----------
    def _build_bill_panel(self):
        panel = QFrame()
        panel.setObjectName("checkinBillPanel")
        panel.setFixedWidth(300)
        panel.setStyleSheet(f"""
            QFrame#checkinBillPanel {{
                background: {COLORS['surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#checkinBillPanel QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        header = QHBoxLayout()
        header.setContentsMargins(14, 12, 14, 8)
        title = QLabel("账单明细")
        title.setFont(QFont(*FONTS["h4"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # 分隔线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {COLORS['border']};")
        layout.addWidget(sep)

        # 滚动内容区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        content = QWidget()
        self.bill_layout = QVBoxLayout(content)
        self.bill_layout.setContentsMargins(14, 14, 14, 14)
        self.bill_layout.setSpacing(12)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # 底部操作按钮区
        action_frame = QFrame()
        action_frame.setObjectName("checkinBillAction")
        action_frame.setStyleSheet(f"""
            QFrame#checkinBillAction {{
                background: {COLORS['surface']};
                border-top: 1px solid {COLORS['border']};
            }}
            QFrame#checkinBillAction QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        action_layout = QVBoxLayout(action_frame)
        action_layout.setContentsMargins(14, 12, 14, 14)
        action_layout.setSpacing(8)

        # 应付总额
        total_layout = QHBoxLayout()
        total_label = QLabel("应付总额")
        total_label.setFont(QFont(*FONTS["body"]))
        total_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        total_layout.addWidget(total_label)
        total_layout.addStretch()
        
        self.total_amount_label = QLabel("¥ 0")
        self.total_amount_label.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.total_amount_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.total_amount_label.setStyleSheet(f"color: {COLORS['accent']};")
        total_layout.addWidget(self.total_amount_label)
        action_layout.addLayout(total_layout)

        # 流程导航按钮
        nav_row = QHBoxLayout()
        nav_row.setSpacing(10)

        self.prev_action_btn = QPushButton("上一步")
        self.prev_action_btn.setObjectName("checkinPrevAction")
        self.prev_action_btn.setMinimumHeight(38)
        self.prev_action_btn.setFont(QFont(*FONTS["body_b"]))
        self.prev_action_btn.setCursor(Qt.PointingHandCursor)
        self.prev_action_btn.setVisible(False)
        self.prev_action_btn.setStyleSheet(f"""
            QPushButton#checkinPrevAction {{
                background: {COLORS['surface']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: bold;
            }}
            QPushButton#checkinPrevAction:hover {{
                background: {COLORS['bg']};
                color: {COLORS['text_primary']};
            }}
        """)
        self.prev_action_btn.clicked.connect(self._go_previous_step)
        nav_row.addWidget(self.prev_action_btn, 1)

        self.main_action_btn = QPushButton("请选择订单")
        self.main_action_btn.setObjectName("checkinMainAction")
        self.main_action_btn.setMinimumHeight(38)
        self.main_action_btn.setMinimumWidth(190)
        self.main_action_btn.setProperty("variant", "accent")
        self.main_action_btn.setProperty("size", "large")
        self.main_action_btn.setFont(QFont(*FONTS["body_b"]))
        self.main_action_btn.setCursor(Qt.PointingHandCursor)
        self.main_action_btn.setStyleSheet(f"""
            QPushButton#checkinMainAction {{
                background: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: bold;
            }}
            QPushButton#checkinMainAction:hover {{
                background: #d97706;
            }}
            QPushButton#checkinMainAction:disabled {{
                background: {COLORS['bg']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
            }}
        """)
        self.main_action_btn.setEnabled(False)
        self.main_action_btn.clicked.connect(self._on_main_action)
        nav_row.addWidget(self.main_action_btn, 2)
        action_layout.addLayout(nav_row)

        layout.addWidget(action_frame)

        # 初始化账单空状态
        self._init_bill_empty()

        return panel

    def _init_bill_empty(self):
        # 清空账单内容
        while self.bill_layout.count():
            item = self.bill_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        empty = QLabel("暂无订单信息")
        empty.setFont(QFont(*FONTS["body_sm"]))
        empty.setAlignment(Qt.AlignCenter)
        empty.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 40px 0;")
        self.bill_layout.addWidget(empty)

    # ==================== 数据加载 ====================
    def _load_data(self):
        s = Session()
        try:
            # 加载房型
            room_types = s.query(RoomType).all()
            self._room_types = {rt.id: rt for rt in room_types}
            
            # 加载订单
            self._all_orders = s.query(Order).filter(
                Order.status.in_(["已确认", "待确认"])
            ).order_by(Order.check_in_date).all()
            
            # 预加载客户信息
            self._customers = {}
            for o in self._all_orders:
                if o.customer_id and o.customer_id not in self._customers:
                    c = s.query(Customer).filter(Customer.id == o.customer_id).first()
                    if c:
                        self._customers[o.customer_id] = c
            
            # 加载房间
            self._all_rooms = s.query(Room).order_by(Room.floor, Room.room_number).all()
            
        finally:
            s.close()
        
        self._current_tab = 0
        self._filter_orders()

    def _switch_tab(self, idx):
        self._current_tab = idx
        # 更新Tab样式
        for i, btn in enumerate(self.tab_buttons):
            if i == idx:
                btn.setChecked(True)
                btn.setStyleSheet(f"""
                    background: {COLORS['primary_light']};
                    color: {COLORS['primary']};
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-weight: bold;
                """)
            else:
                btn.setChecked(False)
                btn.setStyleSheet(f"""
                    background: transparent;
                    color: {COLORS['text_secondary']};
                    border-radius: 6px;
                    padding: 6px 14px;
                """)
        self._filter_orders()

    def _filter_orders(self, *_):
        kw = self.search_input.text().strip().lower()
        
        # Tab过滤
        if self._current_tab == 0:
            status_filter = ["已确认", "待确认"]
        else:
            status_filter = ["待确认"]
        
        filtered = []
        for o in self._all_orders:
            if o.status not in status_filter:
                continue
            # 关键词过滤
            if kw:
                c = self._customers.get(o.customer_id)
                cname = c.name if c else ""
                cphone = c.phone if c else ""
                if (kw not in (o.order_no or "").lower() and 
                    kw not in cname.lower() and 
                    kw not in (cphone or "").lower()):
                    continue
            filtered.append(o)
        
        # 渲染表格
        self.order_table.setRowCount(len(filtered))
        for i, order in enumerate(filtered):
            c = self._customers.get(order.customer_id)
            cname = c.name if c else "散客"
            
            # 客人信息列
            item0 = QTableWidgetItem(cname)
            item0.setFont(QFont(*FONTS["body_sm"]))
            item0.setToolTip(f"{cname}\n订单号：{order.order_no or '-'}")
            
            # 房型列
            rt = self._room_types.get(order.room_type_id)
            rt_name = rt.name if rt else "-"
            item1 = QTableWidgetItem(rt_name)
            item1.setFont(QFont(*FONTS["body_sm"]))
            item1.setTextAlignment(Qt.AlignCenter)
            item1.setToolTip(rt_name)
            sc = ORDER_STATUS_COLORS.get(order.status, COLORS["text_muted"])
            item1.setForeground(QColor(sc))
            
            self.order_table.setItem(i, 0, item0)
            self.order_table.setItem(i, 1, item1)
        
        self._filtered_orders = filtered

    # ==================== 订单选择 ====================
    def _on_order_select(self, *_):
        row = self.order_table.currentRow()
        if row < 0 or row >= len(self._filtered_orders):
            return
        
        self._order = self._filtered_orders[row]
        self._customer = self._customers.get(self._order.customer_id)
        self._selected_room = None
        self._upgrade_mode = None
        self._id_info = None
        self._extras = []
        self._roommates = []
        self._current_step = 0
        
        # 更新步骤条
        self._update_step_bar(0)
        
        # 渲染步骤1内容
        self._render_step_1()
        
        # 更新账单
        self._update_bill()
        
        # 更新主按钮
        self.main_action_btn.setEnabled(True)
        self.main_action_btn.setText("下一步：证件登记")
        self._sync_nav_buttons()

    def _update_step_bar(self, current_idx):
        for i, (num_label, name_label) in enumerate(self.step_labels):
            if i < current_idx:
                # 已完成
                num_label.setText("✓")
                num_label.setStyleSheet(f"""
                    background: {COLORS['success']};
                    color: white;
                    border-radius: 11px;
                    font-weight: bold;
                """)
                name_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            elif i == current_idx:
                # 当前
                num_label.setText(str(i + 1))
                num_label.setStyleSheet(f"""
                    background: {COLORS['primary']};
                    color: white;
                    border-radius: 11px;
                    font-weight: bold;
                """)
                name_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold;")
            else:
                # 未完成
                num_label.setText(str(i + 1))
                num_label.setStyleSheet(f"""
                    background: {COLORS['border']};
                    color: {COLORS['text_muted']};
                    border-radius: 11px;
                    font-weight: bold;
                """)
                name_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        
        # 更新分隔线
        for i, sep in enumerate(self.step_seps):
            if i < current_idx:
                sep.setStyleSheet(f"background: {COLORS['success']};")
            else:
                sep.setStyleSheet(f"background: {COLORS['border']};")

    # ==================== 步骤渲染 ====================
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            if child_layout:
                self._clear_layout(child_layout)
                child_layout.deleteLater()

            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _clear_step_content(self):
        self._clear_layout(self.step_content_layout)

    def _sync_nav_buttons(self):
        has_order = self._order is not None
        self.prev_action_btn.setVisible(has_order and self._current_step > 0)
        self.prev_action_btn.setEnabled(has_order and self._current_step > 0)

    def _render_step_1(self):
        """步骤1：订单确认"""
        self._clear_step_content()
        self._current_step = 0

        # 客人信息 + 订单信息 并排
        info_row = QHBoxLayout()
        info_row.setSpacing(16)

        # 客人信息卡片
        customer_card = self._build_info_card("客人信息", self._build_customer_info())
        info_row.addWidget(customer_card, 1)

        # 订单信息卡片
        order_card = self._build_info_card("订单信息", self._build_order_info())
        info_row.addWidget(order_card, 1)

        self.step_content_layout.addLayout(info_row)

        # 会员权益卡片（如果是会员）
        if self._customer and self._customer.vip_level and self._customer.vip_level != "普通":
            vip_card = self._build_vip_card()
            self.step_content_layout.addWidget(vip_card)

        if self._customer:
            self.step_content_layout.addWidget(self._build_guest_profile_card())

        self.step_content_layout.addStretch()
        self._sync_nav_buttons()

    def _build_info_card(self, title, content_layout):
        card = QFrame()
        card.setObjectName("checkinInfoCard")
        card.setStyleSheet(f"""
            QFrame#checkinInfoCard {{
                background: {COLORS['bg']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#checkinInfoCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setFont(QFont(*FONTS["h4"]))
        title_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title_label)

        layout.addLayout(content_layout)

        return card

    def _build_customer_info(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)

        c = self._customer
        if not c:
            tip = QLabel("未关联客户信息")
            tip.setFont(QFont(*FONTS["body_sm"]))
            tip.setStyleSheet(f"color: {COLORS['text_muted']};")
            layout.addWidget(tip)
            return layout

        fields = [
            ("姓名", c.name or "-"),
            ("手机号", c.phone or "-"),
            ("会员等级", c.vip_level or "普通"),
            ("入住偏好", c.preference or "无"),
        ]

        for label, value in fields:
            row = QHBoxLayout()
            row.setSpacing(8)
            
            l = QLabel(label)
            l.setFixedWidth(60)
            l.setFont(QFont(*FONTS["body_sm"]))
            l.setStyleSheet(f"color: {COLORS['text_muted']};")
            row.addWidget(l)
            
            v = QLabel(str(value))
            v.setFont(QFont(*FONTS["body"]))
            v.setStyleSheet(f"color: {COLORS['text_primary']};")
            v.setWordWrap(True)
            row.addWidget(v, 1)
            
            layout.addLayout(row)

        return layout

    def _build_guest_profile_card(self):
        s = Session()
        try:
            profile = build_guest_profile(s, self._customer.id)
        finally:
            s.close()

        card = QFrame()
        card.setObjectName("guestProfileCard")
        card.setStyleSheet(f"""
            QFrame#guestProfileCard {{
                background: {COLORS['primary_light']};
                border: 1px solid {COLORS['primary']};
                border-radius: 10px;
            }}
            QFrame#guestProfileCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("智能客情提示")
        title.setFont(QFont(*FONTS["h4"]))
        title.setStyleSheet(f"color: {COLORS['primary_pressed']};")
        head.addWidget(title)
        head.addStretch()
        identity = QLabel(profile["identity_key"])
        identity.setFont(QFont(*FONTS["caption_b"]))
        identity.setStyleSheet(f"color: {COLORS['primary']};")
        head.addWidget(identity)
        layout.addLayout(head)

        tag_row = QHBoxLayout()
        tag_row.setSpacing(6)
        for tag in profile["tags"]:
            tag_label = QLabel(tag)
            tag_label.setFont(QFont(*FONTS["caption_b"]))
            tag_label.setStyleSheet(f"""
                color: white;
                background: {COLORS['primary']};
                border-radius: 6px;
                padding: 3px 8px;
            """)
            tag_row.addWidget(tag_label)
        tag_row.addStretch()
        layout.addLayout(tag_row)

        for tip in profile["service_tips"][:3]:
            tip_label = QLabel(f"• {tip}")
            tip_label.setWordWrap(True)
            tip_label.setFont(QFont(*FONTS["body_sm"]))
            tip_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            layout.addWidget(tip_label)

        return card

    def _build_order_info(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)

        o = self._order
        if not o:
            return layout

        rt = self._room_types.get(o.room_type_id)
        rt_name = rt.name if rt else "-"
        days = max(1, (o.check_out_date - o.check_in_date).days) if o.check_in_date and o.check_out_date else 1

        fields = [
            ("订单号", o.order_no or "-"),
            ("房型", rt_name),
            ("入住日期", str(o.check_in_date or "-")),
            ("离店日期", str(o.check_out_date or "-")),
            ("间夜数", f"{days} 晚"),
            ("订单状态", o.status or "-"),
        ]

        for label, value in fields:
            row = QHBoxLayout()
            row.setSpacing(8)
            
            l = QLabel(label)
            l.setFixedWidth(60)
            l.setFont(QFont(*FONTS["body_sm"]))
            l.setStyleSheet(f"color: {COLORS['text_muted']};")
            row.addWidget(l)
            
            v = QLabel(str(value))
            v.setFont(QFont(*FONTS["body"]))
            v.setStyleSheet(f"color: {COLORS['text_primary']};")
            
            # 状态特殊处理
            if label == "订单状态":
                sc = ORDER_STATUS_COLORS.get(value, COLORS["text_muted"])
                v.setStyleSheet(f"color: {sc}; font-weight: bold;")
            
            row.addWidget(v, 1)
            layout.addLayout(row)

        return layout

    def _build_vip_card(self):
        """会员权益卡片"""
        c = self._customer
        tier_info = TIERS.get(c.vip_level, TIERS["普通"])
        tier_color = tier_info["color"]

        card = QFrame()
        card.setObjectName("checkinVipCard")
        card.setStyleSheet(f"""
            QFrame#checkinVipCard {{
                background: {COLORS['surface']};
                border-radius: 10px;
                border: 1px solid {tier_color};
            }}
            QFrame#checkinVipCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # 标题行
        title_row = QHBoxLayout()
        icon = QLabel("⭐")
        icon.setFont(QFont("Segoe UI Emoji", 16))
        title_row.addWidget(icon)
        
        title = QLabel(f"{c.vip_level}会员权益")
        title.setFont(QFont(*FONTS["h4"]))
        title.setStyleSheet(f"color: {tier_color};")
        title_row.addWidget(title)
        title_row.addStretch()
        
        points = QLabel(f"积分: {c.points or 0}")
        points.setFont(QFont(*FONTS["body_sm"]))
        points.setStyleSheet(f"color: {COLORS['text_secondary']};")
        title_row.addWidget(points)
        
        layout.addLayout(title_row)

        # 权益列表
        benefits = []
        if tier_info["discount"] < 1.0:
            benefits.append(f"🏷️  房费 {int(tier_info['discount']*100)} 折优惠")
        if tier_info["free_deposit"]:
            benefits.append("💰  免押金入住")
        if tier_info["upgrade"] > 0:
            benefits.append("⬆️  免费房型升级权益")
        benefits.append(f"📊  累计入住 {c.total_stays or 0} 次")

        for b in benefits:
            bl = QLabel(b)
            bl.setFont(QFont(*FONTS["body_sm"]))
            bl.setStyleSheet(f"color: {COLORS['text_secondary']};")
            layout.addWidget(bl)

        return card

    def _render_step_2(self):
        """步骤2：证件登记"""
        self._clear_step_content()
        self._current_step = 1

        # 主操作区
        action_card = QFrame()
        action_card.setObjectName("checkinIdActionCard")
        action_card.setStyleSheet(f"""
            QFrame#checkinIdActionCard {{
                background: {COLORS['bg']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#checkinIdActionCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(24, 20, 24, 20)
        action_layout.setSpacing(16)
        action_layout.setAlignment(Qt.AlignCenter)

        # 图标
        icon = QLabel("🪪")
        icon.setFont(QFont("Segoe UI Emoji", 48))
        icon.setAlignment(Qt.AlignCenter)
        action_layout.addWidget(icon)

        # 提示文字
        tip = QLabel("请将身份证放置在读卡器上\n或手动录入证件信息")
        tip.setFont(QFont(*FONTS["body"]))
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet(f"color: {COLORS['text_secondary']};")
        action_layout.addWidget(tip)

        # 刷证/人工核验按钮
        id_button_row = QHBoxLayout()
        id_button_row.setSpacing(10)

        scan_btn = QPushButton("📟  刷身份证")
        scan_btn.setObjectName("checkinScanIdButton")
        scan_btn.setMinimumHeight(44)
        scan_btn.setFont(QFont(*FONTS["body_b"]))
        scan_btn.setCursor(Qt.PointingHandCursor)
        scan_btn.setStyleSheet(f"""
            QPushButton#checkinScanIdButton {{
                background: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 9px 20px;
                font-weight: bold;
            }}
            QPushButton#checkinScanIdButton:hover {{
                background: {COLORS['accent_hover']};
            }}
            QPushButton#checkinScanIdButton:pressed {{
                background: {COLORS['accent_pressed']};
            }}
        """)
        scan_btn.clicked.connect(self._simulate_id_scan)
        id_button_row.addWidget(scan_btn)

        manual_btn = QPushButton("人工核验")
        manual_btn.setObjectName("checkinManualVerifyButton")
        manual_btn.setMinimumHeight(44)
        manual_btn.setFont(QFont(*FONTS["body_b"]))
        manual_btn.setCursor(Qt.PointingHandCursor)
        manual_btn.setStyleSheet(f"""
            QPushButton#checkinManualVerifyButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 9px 20px;
                font-weight: bold;
            }}
            QPushButton#checkinManualVerifyButton:hover {{
                background: {COLORS['surface_hover']};
                border-color: {COLORS['primary']};
                color: {COLORS['primary']};
            }}
        """)
        manual_btn.clicked.connect(self._manual_id_verify)
        id_button_row.addWidget(manual_btn)
        action_layout.addLayout(id_button_row)

        self.step_content_layout.addWidget(action_card)

        # 证件信息展示区
        self.id_info_card = self._build_info_card("证件信息", self._build_id_info())
        self.step_content_layout.addWidget(self.id_info_card)

        # 同住人区域
        roommate_card = QFrame()
        roommate_card.setObjectName("checkinRoommateCard")
        roommate_card.setStyleSheet(f"""
            QFrame#checkinRoommateCard {{
                background: {COLORS['surface']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#checkinRoommateCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        rm_layout = QVBoxLayout(roommate_card)
        rm_layout.setContentsMargins(16, 14, 16, 14)
        rm_layout.setSpacing(10)

        rm_title = QHBoxLayout()
        t = QLabel("同住人")
        t.setFont(QFont(*FONTS["h4"]))
        t.setStyleSheet(f"color: {COLORS['text_primary']};")
        rm_title.addWidget(t)
        rm_title.addStretch()
        
        add_btn = QPushButton("+ 添加同住人")
        add_btn.setProperty("variant", "text")
        add_btn.setProperty("size", "small")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_roommate)
        rm_title.addWidget(add_btn)
        
        rm_layout.addLayout(rm_title)

        self.roommate_list = QLabel("暂无同住人")
        self.roommate_list.setFont(QFont(*FONTS["body_sm"]))
        self.roommate_list.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 8px 0;")
        rm_layout.addWidget(self.roommate_list)

        self.step_content_layout.addWidget(roommate_card)

        self.step_content_layout.addStretch()
        
        # 更新主按钮
        self.main_action_btn.setText("下一步：选房分配")
        self._sync_nav_buttons()

    def _build_id_info(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)

        if not hasattr(self, '_id_info') or not self._id_info:
            tip = QLabel("尚未读取证件信息")
            tip.setFont(QFont(*FONTS["body_sm"]))
            tip.setStyleSheet(f"color: {COLORS['text_muted']};")
            layout.addWidget(tip)
            return layout

        fields = [
            ("姓名", self._id_info.get('name', '-')),
            ("核验方式", self._id_info.get('verify_method', '-')),
            ("证件号", self._id_info.get('id_card', '未保存')),
            ("性别", self._id_info.get('gender', '-')),
            ("住址", self._id_info.get('address', '-')),
        ]

        for label, value in fields:
            row = QHBoxLayout()
            row.setSpacing(8)
            l = QLabel(label)
            l.setFixedWidth(60)
            l.setFont(QFont(*FONTS["body_sm"]))
            l.setStyleSheet(f"color: {COLORS['text_muted']};")
            row.addWidget(l)
            v = QLabel(str(value))
            v.setFont(QFont(*FONTS["body"]))
            v.setStyleSheet(f"color: {COLORS['text_primary']};")
            row.addWidget(v, 1)
            layout.addLayout(row)

        return layout

    def _simulate_id_scan(self):
        """模拟刷身份证（演示用）"""
        c = self._customer
        self._id_info = {
            'name': c.name if c else '张三',
            'id_card': c.id_card if c and c.id_card else '610101199501011234',
            'gender': '男',
            'address': '陕西省西安市雁塔区',
            'verify_method': '读卡器模拟',
        }
        self._refresh_id_info_card()
        QMessageBox.information(self, "成功", "证件读取成功！")

    def _manual_id_verify(self):
        """人工核验：只确认本次入住人姓名，不把证件号写入客户档案。"""
        if not self._customer:
            QMessageBox.warning(self, "提示", "请先选择订单")
            return
        self._id_info = {
            'name': self._customer.name,
            'verify_method': '人工核验',
            'gender': '-',
            'address': '前台已人工核验证件',
        }
        self._refresh_id_info_card()
        QMessageBox.information(self, "成功", "人工核验已通过")

    def _refresh_id_info_card(self):
        """刷新证件信息卡片。"""
        self.id_info_card.deleteLater()
        self.id_info_card = self._build_info_card("证件信息", self._build_id_info())
        idx = self.step_content_layout.indexOf(self.roommate_list.parent())
        self.step_content_layout.insertWidget(idx, self.id_info_card)

    def _add_roommate(self):
        dlg = RoommateVerifyDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return
        guest = dlg.value()
        name = guest.get("name")
        if not name:
            return
        existing_names = {item.get("name") for item in self._roommates}
        if name not in existing_names:
            self._roommates.append(guest)
        display = "、".join(
            f"{item.get('name')}（{item.get('verify_method')}）"
            for item in self._roommates
        )
        self.roommate_list.setText(display or "暂无同住人")
        self.roommate_list.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 8px 0;")

    def _render_step_3(self):
        """步骤3：选房分配"""
        self._clear_step_content()
        self._current_step = 2

        # 筛选栏
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        # 房型筛选
        filter_label = QLabel("房型筛选:")
        filter_label.setFont(QFont(*FONTS["body_sm"]))
        filter_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        filter_row.addWidget(filter_label)

        self.room_type_filter = QComboBox()
        self.room_type_filter.addItem("全部房型")
        for rt in self._room_types.values():
            self.room_type_filter.addItem(rt.name, rt.id)
        self.room_type_filter.setMinimumWidth(140)
        self.room_type_filter.currentTextChanged.connect(self._render_room_grid)
        filter_row.addWidget(self.room_type_filter)

        filter_row.addStretch()

        # 房型升级按钮
        if self._customer and self._customer.vip_level in ["金卡", "铂金"]:
            upgrade_btn = QPushButton("⬆️  免费升级房型")
            upgrade_btn.setProperty("variant", "secondary")
            upgrade_btn.setCursor(Qt.PointingHandCursor)
            upgrade_btn.clicked.connect(self._show_upgrade_options)
            filter_row.addWidget(upgrade_btn)

        self.step_content_layout.addLayout(filter_row)

        # 房间网格
        self.room_grid_frame = QFrame()
        self.room_grid_frame.setObjectName("checkinRoomGrid")
        self.room_grid_frame.setStyleSheet("""
            QFrame#checkinRoomGrid {
                background: transparent;
                border: none;
            }
        """)
        self.room_grid_layout = QGridLayout(self.room_grid_frame)
        self.room_grid_layout.setSpacing(12)
        self.room_grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._render_room_grid()
        self.step_content_layout.addWidget(self.room_grid_frame)

        # 已选房间提示
        self.selected_room_tip = QLabel("")
        self.selected_room_tip.setFont(QFont(*FONTS["body_sm"]))
        self.selected_room_tip.setAlignment(Qt.AlignCenter)
        self.selected_room_tip.setStyleSheet(f"""
            padding: 10px;
            background: {COLORS['primary_light']};
            color: {COLORS['primary']};
            border-radius: 8px;
            font-weight: bold;
        """)
        self.selected_room_tip.setVisible(False)
        self.step_content_layout.addWidget(self.selected_room_tip)

        self.step_content_layout.addStretch()
        
        # 更新主按钮
        self.main_action_btn.setText("下一步：账务确认")
        self.main_action_btn.setEnabled(False)
        self._sync_nav_buttons()

    def _render_room_grid(self, *_):
        # 清空
        while self.room_grid_layout.count():
            item = self.room_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 筛选
        filter_text = self.room_type_filter.currentText()
        rooms = self._all_rooms
        
        if filter_text != "全部房型":
            rt_id = self.room_type_filter.currentData()
            rooms = [r for r in rooms if r.room_type_id == rt_id]

        # 使用服务层 find_available_rooms 判断可选房。低于预订标准的房间保留展示但置灰。
        available_ids = set()
        if self._order:
            s = Session()
            try:
                from src.services.pms_service import find_available_rooms
                available_rooms = find_available_rooms(
                    s, self._order.id,
                    room_type_id=self.room_type_filter.currentData() if filter_text != "全部房型" else None
                )
                available_ids = {r.id for r in available_rooms}
            finally:
                s.close()

        for i, room in enumerate(rooms):
            card = self._build_room_card(room, room.id in available_ids)
            self.room_grid_layout.addWidget(card, i // 3, i % 3)

    def _build_room_card(self, room, service_available=True):
        status_color = ROOM_STATUS_COLORS.get(room.status, "#999")
        rt = self._room_types.get(room.room_type_id)
        rt_name = rt.name if rt else ""

        is_selected = self._selected_room and self._selected_room.id == room.id
        reserved_room_id = self._order.room_id if self._order else None
        is_physically_available = room.status == "空闲" or (reserved_room_id and room.id == reserved_room_id and room.status == "已预订")
        is_available = bool(is_physically_available and service_available)
        is_downgrade = self._is_downgrade_room(room)

        card = QFrame()
        card.setObjectName("checkinRoomCard")
        card.setCursor(Qt.PointingHandCursor if is_available else Qt.ForbiddenCursor)
        
        border_color = COLORS["primary"] if is_selected else COLORS["border"]
        border_width = 2 if is_selected else 1
        bg_color = COLORS["primary_light"] if is_selected else (COLORS["bg"] if not is_available else COLORS["surface"])
        text_color = COLORS["text_muted"] if not is_available else COLORS["text_primary"]
        secondary_color = COLORS["text_muted"] if not is_available else COLORS["text_secondary"]

        card.setStyleSheet(f"""
            QFrame#checkinRoomCard {{
                background: {bg_color};
                border: {border_width}px solid {border_color};
                border-radius: 10px;
            }}
            QFrame#checkinRoomCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        card.setMinimumWidth(130)
        card.setMaximumWidth(180)
        card.setMinimumHeight(82)
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(4)

        # 房号
        room_no = QLabel(room.room_number)
        room_no.setFont(QFont("Segoe UI", 16, QFont.Bold))
        room_no.setStyleSheet(f"color: {text_color};")
        layout.addWidget(room_no)

        # 房型
        rt_label = QLabel(rt_name)
        rt_label.setFont(QFont(*FONTS["body_sm"]))
        rt_label.setStyleSheet(f"color: {secondary_color};")
        layout.addWidget(rt_label)

        # 状态和价格
        bottom_row = QHBoxLayout()
        status_text = "低于预订" if is_downgrade else room.status
        tag_color = COLORS["text_muted"] if not is_available else status_color
        tag_bg = COLORS["border_light"] if not is_available else f"{status_color}20"
        status_tag = QLabel(status_text)
        status_tag.setFont(QFont(*FONTS["caption_b"]))
        status_tag.setAlignment(Qt.AlignCenter)
        status_tag.setStyleSheet(f"""
            background: {tag_bg};
            color: {tag_color};
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: bold;
        """)
        bottom_row.addWidget(status_tag)
        bottom_row.addStretch()

        price = QLabel(f"¥{int(room.price)}")
        price.setFont(QFont("Segoe UI", 12, QFont.Bold))
        price.setStyleSheet(f"color: {COLORS['text_muted'] if not is_available else COLORS['accent']};")
        bottom_row.addWidget(price)

        layout.addLayout(bottom_row)

        # 选中标记
        if is_selected:
            check = QLabel("✓ 已选")
            check.setFont(QFont(*FONTS["caption_b"]))
            check.setAlignment(Qt.AlignCenter)
            check.setStyleSheet(f"color: {COLORS['primary']};")
            layout.addWidget(check)

        card.mousePressEvent = lambda e, r=room: self._select_room(r) if is_available else None

        return card

    def _select_room(self, room):
        if self._is_downgrade_room(room):
            QMessageBox.warning(self, "不可选择", "所选房间低于预订房型标准，不能降档入住")
            return
        previous_room = self._selected_room
        previous_mode = self._upgrade_mode
        self._upgrade_mode = None
        if self._is_upgrade_room(room):
            mode = self._ask_upgrade_mode(room)
            if not mode:
                self._selected_room = previous_room
                self._upgrade_mode = previous_mode
                return
            self._upgrade_mode = mode

        self._selected_room = room
        self._render_room_grid()
        self._update_bill()
        
        # 显示提示
        rt = self._room_types.get(room.room_type_id)
        rt_name = rt.name if rt else ""
        billed_price = self._get_billed_room_price(room)
        upgrade_text = ""
        if self._upgrade_mode == "paid":
            upgrade_text = "，付费升级"
        elif self._upgrade_mode == "free":
            upgrade_text = "，免费升级"
        self.selected_room_tip.setText(
            f"已选择 {room.room_number} 号房（{rt_name}），结算价 ¥{int(billed_price)}/晚{upgrade_text}"
        )
        self.selected_room_tip.setVisible(True)
        
        # 启用下一步
        self.main_action_btn.setEnabled(True)

    def _get_booked_room_price(self):
        if not self._order:
            return 0
        if self._order.room_price:
            return self._order.room_price
        rt = self._room_types.get(self._order.room_type_id)
        return rt.base_price if rt else 0

    def _is_upgrade_room(self, room):
        return bool(room and room.price and room.price > self._get_booked_room_price())

    def _is_downgrade_room(self, room):
        return bool(room and room.price is not None and room.price < self._get_booked_room_price())

    def _get_billed_room_price(self, room=None):
        room = room or self._selected_room
        if not room:
            return self._get_booked_room_price()
        if self._upgrade_mode == "free":
            return self._get_booked_room_price()
        return room.price or self._get_booked_room_price()

    def _ask_upgrade_mode(self, room):
        booked_price = self._get_booked_room_price()
        diff = max(0, (room.price or 0) - booked_price)
        rt = self._room_types.get(room.room_type_id)
        rt_name = rt.name if rt else "所选房型"

        dlg = QDialog(self)
        dlg.setWindowTitle("升房确认")
        dlg.setModal(True)
        dlg.setFixedWidth(360)
        dlg.setStyleSheet(f"""
            QDialog {{
                background: {COLORS['surface']};
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {COLORS['text_primary']};
            }}
            QPushButton {{
                min-height: 34px;
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#paidUpgrade {{
                background: {COLORS['accent']};
                color: white;
                border: none;
            }}
            QPushButton#freeUpgrade {{
                background: {COLORS['primary']};
                color: white;
                border: none;
            }}
            QPushButton#cancelUpgrade {{
                background: {COLORS['surface']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
            }}
        """)

        result = {"mode": None}
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(14)

        title = QLabel("升房确认")
        title.setFont(QFont(*FONTS["h3"]))
        layout.addWidget(title)

        detail = QLabel(
            f"所选房间 {room.room_number}（{rt_name}）高于预订价格。\n\n"
            f"预订价：¥{int(booked_price)}/晚\n"
            f"房间价：¥{int(room.price or 0)}/晚\n"
            f"差价：¥{int(diff)}/晚\n\n"
            "请选择本次升房方式。"
        )
        detail.setFont(QFont(*FONTS["body"]))
        detail.setWordWrap(True)
        detail.setStyleSheet(f"color: {COLORS['text_secondary']}; line-height: 150%;")
        layout.addWidget(detail)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        paid_btn = QPushButton("付费升级")
        paid_btn.setObjectName("paidUpgrade")
        free_btn = QPushButton("免费升级")
        free_btn.setObjectName("freeUpgrade")
        cancel_btn = QPushButton("取消选择")
        cancel_btn.setObjectName("cancelUpgrade")
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(free_btn)
        btn_row.addWidget(paid_btn)
        layout.addLayout(btn_row)

        paid_btn.clicked.connect(lambda: (result.update(mode="paid"), dlg.accept()))
        free_btn.clicked.connect(lambda: (result.update(mode="free"), dlg.accept()))
        cancel_btn.clicked.connect(dlg.reject)

        return result["mode"] if dlg.exec_() == QDialog.Accepted else None

    def _show_upgrade_options(self):
        QMessageBox.information(self, "免费升级", "检测到您有免费升级权益！\n\n可升级房型：豪华套房\n\n请在上方房型筛选中选择升级后的房型")

    def _render_step_4(self):
        """步骤4：账务确认"""
        self._clear_step_content()
        self._current_step = 3

        # 支付方式
        pay_card = QFrame()
        pay_card.setObjectName("checkinPayCard")
        pay_card.setStyleSheet(f"""
            QFrame#checkinPayCard {{
                background: {COLORS['bg']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#checkinPayCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        pay_layout = QVBoxLayout(pay_card)
        pay_layout.setContentsMargins(16, 14, 16, 14)
        pay_layout.setSpacing(12)

        title = QLabel("支付方式")
        title.setFont(QFont(*FONTS["h4"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        pay_layout.addWidget(title)

        # 支付方式按钮组
        self.pay_method = "微信"
        pay_methods = [
            ("微信", "💚"),
            ("支付宝", "💙"),
            ("现金", "💵"),
            ("银行卡", "💳"),
            ("挂账", "📝"),
        ]

        pay_row = QHBoxLayout()
        pay_row.setSpacing(8)
        self.pay_buttons = []

        for i, (name, icon) in enumerate(pay_methods):
            btn = QPushButton(f"{icon}\n{name}")
            btn.setMinimumHeight(60)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            if i == 0:
                btn.setChecked(True)
                btn.setStyleSheet(f"""
                    background: {COLORS['primary_light']};
                    color: {COLORS['primary']};
                    border: 2px solid {COLORS['primary']};
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: bold;
                """)
            else:
                btn.setStyleSheet(f"""
                    background: {COLORS['surface']};
                    color: {COLORS['text_secondary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    font-size: 12px;
                """)
            btn.clicked.connect(lambda _, n=name, b=btn: self._select_pay_method(n, b))
            pay_row.addWidget(btn, 1)
            self.pay_buttons.append(btn)

        pay_layout.addLayout(pay_row)
        self.step_content_layout.addWidget(pay_card)

        # 杂费
        extra_card = QFrame()
        extra_card.setObjectName("checkinExtraCard")
        extra_card.setStyleSheet(f"""
            QFrame#checkinExtraCard {{
                background: {COLORS['surface']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#checkinExtraCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        extra_layout = QVBoxLayout(extra_card)
        extra_layout.setContentsMargins(16, 14, 16, 14)
        extra_layout.setSpacing(10)

        extra_title = QHBoxLayout()
        t = QLabel("杂费")
        t.setFont(QFont(*FONTS["h4"]))
        t.setStyleSheet(f"color: {COLORS['text_primary']};")
        extra_title.addWidget(t)
        extra_title.addStretch()
        extra_layout.addLayout(extra_title)

        # 添加杂费行
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self.extra_name = QLineEdit()
        self.extra_name.setPlaceholderText("杂费项目名称")
        add_row.addWidget(self.extra_name, 2)
        
        self.extra_amount = QSpinBox()
        self.extra_amount.setRange(1, 99999)
        self.extra_amount.setValue(50)
        self.extra_amount.setPrefix("¥ ")
        add_row.addWidget(self.extra_amount, 1)
        
        add_btn = QPushButton("添加")
        add_btn.setProperty("variant", "secondary")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_extra_fee)
        add_row.addWidget(add_btn)
        
        extra_layout.addLayout(add_row)

        # 杂费列表
        self.extra_list_label = QLabel("暂无杂费")
        self.extra_list_label.setFont(QFont(*FONTS["body_sm"]))
        self.extra_list_label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 4px 0;")
        extra_layout.addWidget(self.extra_list_label)

        self.step_content_layout.addWidget(extra_card)

        # 备注
        remark_card = QFrame()
        remark_card.setObjectName("checkinRemarkCard")
        remark_card.setStyleSheet(f"""
            QFrame#checkinRemarkCard {{
                background: {COLORS['surface']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#checkinRemarkCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        remark_layout = QVBoxLayout(remark_card)
        remark_layout.setContentsMargins(16, 14, 16, 14)
        remark_layout.setSpacing(10)

        rt = QLabel("备注")
        rt.setFont(QFont(*FONTS["h4"]))
        rt.setStyleSheet(f"color: {COLORS['text_primary']};")
        remark_layout.addWidget(rt)

        self.remark_input = QTextEdit()
        self.remark_input.setPlaceholderText("填写入住备注信息...")
        self.remark_input.setMaximumHeight(80)
        remark_layout.addWidget(self.remark_input)

        self.step_content_layout.addWidget(remark_card)

        self.step_content_layout.addStretch()
        
        # 更新主按钮
        self.main_action_btn.setText("✅  确认入住")
        self.main_action_btn.setEnabled(True)
        self._sync_nav_buttons()

    def _select_pay_method(self, method, btn):
        self.pay_method = method
        for b in self.pay_buttons:
            if b == btn:
                b.setChecked(True)
                b.setStyleSheet(f"""
                    background: {COLORS['primary_light']};
                    color: {COLORS['primary']};
                    border: 2px solid {COLORS['primary']};
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: bold;
                """)
            else:
                b.setChecked(False)
                b.setStyleSheet(f"""
                    background: {COLORS['surface']};
                    color: {COLORS['text_secondary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    font-size: 12px;
                """)

    def _add_extra_fee(self):
        name = self.extra_name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入杂费项目名称")
            return
        amount = self.extra_amount.value()
        self._extras.append((name, amount))
        self.extra_name.clear()
        self._update_extra_list()
        self._update_bill()

    def _update_extra_list(self):
        if not self._extras:
            self.extra_list_label.setText("暂无杂费")
            self.extra_list_label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 4px 0;")
        else:
            text = "\n".join([f"• {name}: ¥{amount}" for name, amount in self._extras])
            self.extra_list_label.setText(text)
            self.extra_list_label.setStyleSheet(f"color: {COLORS['text_primary']}; padding: 4px 0;")

    # ==================== 账单更新 ====================
    def _update_bill(self):
        # 清空
        while self.bill_layout.count():
            item = self.bill_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._order:
            self._init_bill_empty()
            self.total_amount_label.setText("¥ 0")
            return

        o = self._order
        c = self._customer
        rt = self._room_types.get(o.room_type_id)
        days = max(1, (o.check_out_date - o.check_in_date).days) if o.check_in_date and o.check_out_date else 1

        # 计算价格
        room = self._selected_room
        booked_price = self._get_booked_room_price()
        selected_price = room.price if room else booked_price
        room_price = self._get_billed_room_price(room)
        base_total = booked_price * days
        upgrade_total = max(0, selected_price - booked_price) * days if self._upgrade_mode == "paid" else 0
        room_total = room_price * days

        # 会员折扣
        tier_name = c.vip_level if c and c.vip_level else "普通"
        tier_info = TIERS.get(tier_name, TIERS["普通"])
        discount = tier_info["discount"]
        discount_amount = room_total * (1 - discount) if discount < 1 else 0

        # 押金
        free_deposit = tier_info["free_deposit"]
        deposit = 0 if free_deposit else (300 if room_price < 400 else 500)

        # 杂费
        extras_total = sum(a for _, a in self._extras)

        # 总计
        total = room_total + deposit + extras_total - discount_amount

        # 订单快照
        snapshot = self._build_bill_section("订单信息", [
            ("房型", rt.name if rt else "-"),
            ("入住", str(o.check_in_date or "-")),
            ("离店", str(o.check_out_date or "-")),
            ("间夜", f"{days} 晚"),
        ])
        self.bill_layout.addWidget(snapshot)

        # 房费明细
        room_items = [("房费", f"¥{base_total:.0f}")]
        if room and selected_price > booked_price:
            if self._upgrade_mode == "paid":
                room_items.append(("升房差价", f"¥{upgrade_total:.0f}"))
            elif self._upgrade_mode == "free":
                room_items.append(("升房差价", "免费"))
        room_items.append(("会员折扣", f"-¥{discount_amount:.0f}" if discount_amount > 0 else "无"))
        room_section = self._build_bill_section("房费明细", room_items)
        self.bill_layout.addWidget(room_section)

        # 押金
        deposit_section = self._build_bill_section("押金", [
            ("入住押金", f"¥{deposit:.0f}" + ("（免押）" if free_deposit else "")),
        ])
        self.bill_layout.addWidget(deposit_section)

        # 杂费
        if self._extras:
            extras_items = [(n, f"¥{a:.0f}") for n, a in self._extras]
            extras_section = self._build_bill_section("杂费", extras_items)
            self.bill_layout.addWidget(extras_section)

        self.bill_layout.addStretch()

        # 更新总额
        self.total_amount_label.setText(f"¥ {total:.0f}")

    def _build_bill_section(self, title, items):
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setFont(QFont(*FONTS["caption_b"]))
        title_label.setStyleSheet(f"color: {COLORS['text_muted']}; text-transform: uppercase;")
        layout.addWidget(title_label)

        for label, value in items:
            row = QHBoxLayout()
            row.setSpacing(8)
            
            l = QLabel(label)
            l.setFont(QFont(*FONTS["body_sm"]))
            l.setStyleSheet(f"color: {COLORS['text_secondary']};")
            row.addWidget(l)
            row.addStretch()
            
            v = QLabel(str(value))
            v.setFont(QFont(*FONTS["body_sm"]))
            v.setStyleSheet(f"color: {COLORS['text_primary']};")
            v.setAlignment(Qt.AlignRight)
            row.addWidget(v)
            
            layout.addLayout(row)

        # 分隔线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {COLORS['border_light']}; margin-top: 4px;")
        layout.addWidget(sep)

        return section

    # ==================== 主操作按钮逻辑 ====================
    def _go_previous_step(self):
        if not self._order or self._current_step <= 0:
            return

        target_step = self._current_step - 1
        self._update_step_bar(target_step)

        if target_step == 0:
            self._render_step_1()
            self.main_action_btn.setText("下一步：证件登记")
            self.main_action_btn.setEnabled(True)
        elif target_step == 1:
            self._render_step_2()
            self.main_action_btn.setText("下一步：选房分配")
            self.main_action_btn.setEnabled(True)
        elif target_step == 2:
            self._render_step_3()
            self.main_action_btn.setText("下一步：账务确认")
            self.main_action_btn.setEnabled(self._selected_room is not None)

        self._sync_nav_buttons()

    def _on_main_action(self):
        if self._current_step == 0:
            # 订单确认 → 证件登记
            self._update_step_bar(1)
            self._render_step_2()
        elif self._current_step == 1:
            # 证件登记 → 选房分配
            self._update_step_bar(2)
            self._render_step_3()
        elif self._current_step == 2:
            # 选房分配 → 账务确认
            if not self._selected_room:
                QMessageBox.warning(self, "提示", "请先选择房间")
                return
            self._update_step_bar(3)
            self._render_step_4()
        elif self._current_step == 3:
            # 账务确认 → 完成入住
            self._do_checkin()

    # ==================== 完成入住 ====================
    def _do_checkin(self):
        if not self._order or not self._selected_room:
            return

        s = Session()
        try:
            o = s.query(Order).filter(Order.id == self._order.id).first()
            if not o:
                return

            from src.services.pms_service import check_in_order, BusinessError
            id_info = getattr(self, "_id_info", None)
            if not id_info:
                QMessageBox.warning(self, "提示", "请先在证件登记步骤刷身份证并核验证件信息")
                return
            check_in_order(s, o.id, self._selected_room.id,
                          id_info=id_info,
                          pay_method=self.pay_method,
                          upgrade_mode=self._upgrade_mode,
                          roommates=self._roommates)

            # 备注
            remark_text = self.remark_input.toPlainText().strip() if hasattr(self, "remark_input") else ""
            if remark_text:
                o.remark = remark_text

            # 杂费（服务层已处理房费+押金，此处只加杂费）
            for name, amount in self._extras:
                from src.services.pms_service import add_bill_item
                add_bill_item(s, o.id, "杂费", amount, description=name,
                             pay_method=self.pay_method)

            s.commit()
            notify_data_changed("checkin")

            rm = s.query(Room).filter(Room.id == self._selected_room.id).first()
            try:
                from src.services.audit_service import log_operation
                user = getattr(self, "current_user", {}) or {}
                log_operation(s, user.get("id"), "办理入住",
                              f"订单 {o.order_no} 入住房间 {rm.room_number if rm else '?'}")
                s.commit()
            except Exception:
                s.rollback()
            QMessageBox.information(self, "入住成功",
                f"✅  入住办理成功！\n\n"
                f"房间号：{rm.room_number if rm else '?'}\n"
                f"客人：{self._customer.name if self._customer else '散客'}\n"
                f"支付方式：{self.pay_method}")

            self._order = None
            self._customer = None
            self._selected_room = None
            self._upgrade_mode = None
            self._extras = []
            self._roommates = []
            self._current_step = 0
            self._load_data()
            self._show_empty_state()
            self._init_bill_empty()
            self.main_action_btn.setEnabled(False)
            self.main_action_btn.setText("请选择订单")
            self._sync_nav_buttons()
            self.total_amount_label.setText("¥ 0")
        except BusinessError as e:
            s.rollback()
            QMessageBox.warning(self, "操作失败", str(e))

        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()

    # ==================== 散客入住 ====================
    def _start_walkin(self):
        """开始散客入住"""
        from src.views.customer_view import CustomerDialog
        dlg = CustomerDialog(self)
        if dlg.exec_() != dlg.Accepted:
            return

        customer_id = getattr(dlg, "created_customer_id", None)
        if not customer_id:
            QMessageBox.warning(self, "错误", "客户创建失败，无法生成散客订单")
            return

        s = Session()
        try:
            rt = s.query(RoomType).order_by(RoomType.base_price, RoomType.id).first()
            if not rt:
                QMessageBox.warning(self, "错误", "暂无可用房型，无法生成散客订单")
                return
            order = create_walkin_order(
                s,
                customer_id=customer_id,
                room_type_id=rt.id,
                check_in=date.today(),
                check_out=date.today() + timedelta(days=1),
                guest_count=1,
                remark="前台散客入住",
            )
            order_id = order.id
            s.commit()
            notify_data_changed("reservation")
        except BusinessError as e:
            s.rollback()
            QMessageBox.warning(self, "无法创建散客订单", str(e))
            return
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
            return
        finally:
            s.close()

        self._load_data()
        for idx, order in enumerate(getattr(self, "_filtered_orders", [])):
            if order.id == order_id:
                self.order_table.selectRow(idx)
                self._on_order_select()
                break
