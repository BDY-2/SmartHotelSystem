# -*- coding: utf-8 -*-
"""v3.0 退房结算"""
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QLineEdit, QMessageBox, QFrame,
                              QAbstractItemView)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
from src.utils.db import Session
from src.models.order import Order
from src.models.customer import Customer
from src.models.room import Room
from src.models.bill_item import BillItem
from src.services.pms_service import checkout_order, BusinessError as SvcError
from src.resources.theme import COLORS, SPACING, FONTS
from src.utils.event_bus import notify_data_changed


class CheckoutView(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._load()

    def _init_ui(self):
        l = QVBoxLayout()
        l.setContentsMargins(SPACING["xxl"], SPACING["xxl"], SPACING["xxl"], SPACING["xxl"])
        l.setSpacing(SPACING["lg"])

        # 顶部工具栏
        top = QHBoxLayout()
        
        title = QLabel("退房结算")
        title.setFont(QFont(*FONTS["h1"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        top.addWidget(title)
        top.addStretch()

        # 搜索框
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  搜索订单号 / 房号 / 客户名")
        self.search.setMinimumHeight(36)
        self.search.setFixedWidth(280)
        self.search.textChanged.connect(self._filter)
        top.addWidget(self.search)

        # 刷新
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setObjectName("checkoutRefreshButton")
        refresh_btn.setMinimumHeight(36)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton#checkoutRefreshButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#checkoutRefreshButton:hover {{
                border-color: {COLORS['primary']};
                color: {COLORS['primary']};
            }}
        """)
        refresh_btn.clicked.connect(self._load)
        top.addWidget(refresh_btn)

        l.addLayout(top)

        # 统计卡片
        stats = QHBoxLayout()
        stats.setSpacing(SPACING["md"])
        
        # 在住房间数
        self.in_house_card = self._build_stat_card("在住房间", "0", COLORS["info"])
        stats.addWidget(self.in_house_card, 1)
        
        # 今日预计离店
        self.today_depart_card = self._build_stat_card("今日预计离店", "0", COLORS["warning"])
        stats.addWidget(self.today_depart_card, 1)
        
        # 今日已退房
        self.today_checked_out_card = self._build_stat_card("今日已退房", "0", COLORS["success"])
        stats.addWidget(self.today_checked_out_card, 1)
        
        # 今日房费收入
        self.today_rev_card = self._build_stat_card("今日房费收入", "¥ 0", COLORS["accent"])
        stats.addWidget(self.today_rev_card, 1)
        
        l.addLayout(stats)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "订单号", "客户", "房号", "入住日期", "离店日期", "房费", "已付", "状态"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        l.addWidget(self.table, 1)

        # 底部操作栏
        bottom = QHBoxLayout()
        bottom.addStretch()
        
        checkout_btn = QPushButton("🏁  办理退房")
        checkout_btn.setMinimumHeight(40)
        checkout_btn.setObjectName("checkoutActionButton")
        checkout_btn.setFont(QFont(*FONTS["body_b"]))
        checkout_btn.setCursor(Qt.PointingHandCursor)
        checkout_btn.setStyleSheet(f"""
            QPushButton#checkoutActionButton {{
                background: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 8px 18px;
                font-weight: bold;
            }}
            QPushButton#checkoutActionButton:hover {{
                background: {COLORS['accent_hover']};
            }}
        """)
        checkout_btn.clicked.connect(self._do_checkout)
        bottom.addWidget(checkout_btn)
        
        l.addLayout(bottom)

        self.setLayout(l)

    def _build_stat_card(self, label, value, color):
        card = QFrame()
        card.setObjectName("checkoutStatCard")
        card.setStyleSheet(f"""
            QFrame#checkoutStatCard {{
                background: {COLORS['surface']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
                border-left: 3px solid {color};
            }}
            QFrame#checkoutStatCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        card.setMinimumHeight(64)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 10, 16, 10)
        cl.setSpacing(4)
        
        v = QLabel(value)
        v.setFont(QFont(*FONTS["h3"]))
        v.setStyleSheet(f"color: {color};")
        cl.addWidget(v)
        
        l = QLabel(label)
        l.setFont(QFont(*FONTS["body_sm"]))
        l.setStyleSheet(f"color: {COLORS['text_muted']};")
        cl.addWidget(l)
        
        card.value_label = v
        return card

    def _load(self):
        s = Session()
        try:
            # 加载在住订单
            self.orders = s.query(Order).filter(Order.status == "已入住").all()
            
            # 预加载客户和房间
            self._customers = {}
            self._rooms = {}
            
            for o in self.orders:
                if o.customer_id and o.customer_id not in self._customers:
                    c = s.query(Customer).filter(Customer.id == o.customer_id).first()
                    if c:
                        self._customers[o.customer_id] = c
                if o.room_id and o.room_id not in self._rooms:
                    r = s.query(Room).filter(Room.id == o.room_id).first()
                    if r:
                        self._rooms[o.room_id] = r
            
            # 统计数据
            today = datetime.now().date()
            in_house = len(self.orders)
            today_depart = sum(1 for o in self.orders if o.check_out_date == today)
            
            # 今日已退房
            today_checked_out = s.query(Order).filter(
                Order.status == "已退房",
                Order.actual_check_out >= datetime.combine(today, datetime.min.time())
            ).count()
            
            # 今日房费收入（今日退房的订单）
            today_checkout_orders = s.query(Order).filter(
                Order.status == "已退房",
                Order.actual_check_out >= datetime.combine(today, datetime.min.time())
            ).all()
            today_rev = 0
            if today_checkout_orders:
                oids = [o.id for o in today_checkout_orders]
                today_rev = sum(
                    bi.amount for bi in
                    s.query(BillItem).filter(
                        BillItem.order_id.in_(oids),
                        BillItem.item_type.in_(["房费", "杂费", "退款"])
                    ).all()
                ) or 0
            
            # 更新统计卡片
            self.in_house_card.value_label.setText(str(in_house))
            self.today_depart_card.value_label.setText(str(today_depart))
            self.today_checked_out_card.value_label.setText(str(today_checked_out))
            self.today_rev_card.value_label.setText(f"¥ {today_rev:.0f}")
            
        finally:
            s.close()
        self._filter()

    def _filter(self, *_):
        kw = self.search.text().strip().lower()
        
        filtered = self.orders
        if kw:
            filtered = [
                o for o in filtered
                if kw in (o.order_no or "").lower()
                or kw in (self._room_no(o.room_id) or "").lower()
                or kw in (self._cname(o.customer_id) or "").lower()
            ]

        self.table.setRowCount(len(filtered))
        for i, o in enumerate(filtered):
            values = [
                o.order_no or "-",
                self._cname(o.customer_id),
                self._room_no(o.room_id),
                str(o.check_in_date or "-"),
                str(o.check_out_date or "-"),
                f"¥{o.total_amount:.0f}" if o.total_amount else "-",
                f"¥{o.paid_amount or 0:.0f}",
                o.status or "-",
            ]
            
            for j, v in enumerate(values):
                item = QTableWidgetItem(v)
                item.setFont(QFont(*FONTS["body_sm"]))
                
                if j == 7:
                    item.setForeground(QColor(COLORS["info"]))
                    item.setTextAlignment(Qt.AlignCenter)
                
                self.table.setItem(i, j, item)

    def _cname(self, cid):
        c = self._customers.get(cid)
        return c.name if c else "-"

    def _room_no(self, rid):
        r = self._rooms.get(rid)
        return r.room_number if r else "-"

    def _do_checkout(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选中一条订单")
            return
        
        order_no = self.table.item(row, 0).text()
        
        # 确认对话框
        r = QMessageBox.question(
            self, "确认退房",
            f"确定要为订单 {order_no} 办理退房吗？\n\n"
            f"退房后房间将变为脏房状态，等待清洁。",
            QMessageBox.Yes | QMessageBox.No
        )
        if r != QMessageBox.Yes:
            return

        s = Session()
        try:
            o = s.query(Order).filter(Order.order_no == order_no).first()
            if not o:
                return
            
            from src.services.pms_service import checkout_order, BusinessError

            checkout_order(s, o.id)
            try:
                from src.services.audit_service import log_operation
                user = getattr(self, "current_user", {}) or {}
                log_operation(s, user.get("id"), "办理退房", f"订单 {o.order_no} 办理退房，房间转为脏房")
            except Exception:
                pass
            s.commit()
            notify_data_changed("checkout")
            self._load()

            QMessageBox.information(
                self, "退房成功",
                f"✅  退房办理成功！\n\n"
                f"订单号: {order_no}\n"
                f"房号: {self._room_no(o.room_id)}\n"
                f"房间已转为脏房状态"
            )
        except BusinessError as e:
            s.rollback()
            QMessageBox.warning(self, "操作失败", str(e))
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()
