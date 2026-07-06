# -*- coding: utf-8 -*-
"""v3.0 预订管理"""
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QLineEdit, QComboBox, QMessageBox,
                              QDialog, QFormLayout, QSpinBox, QDateEdit,
                              QFrame, QAbstractItemView)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
from src.utils.db import Session
from src.models.order import Order
from src.models.customer import Customer
from src.models.room import Room
from src.models.room_type import RoomType
from src.resources.theme import COLORS, SPACING, FONTS
from src.utils.event_bus import notify_data_changed


# 订单状态颜色
STATUS_COLORS = {
    "待确认": COLORS["warning"],
    "已确认": COLORS["success"],
    "已入住": COLORS["info"],
    "已退房": COLORS["text_muted"],
    "已取消": COLORS["text_muted"],
}


class ReservationView(QWidget):
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
        
        title = QLabel("预订管理")
        title.setFont(QFont(*FONTS["h1"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        top.addWidget(title)
        top.addStretch()

        # 搜索框
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  搜索订单号 / 客户名 / 手机号")
        self.search.setMinimumHeight(36)
        self.search.setFixedWidth(260)
        self.search.textChanged.connect(self._filter)
        top.addWidget(self.search)

        # 状态筛选
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态")
        for s in STATUS_COLORS.keys():
            self.status_filter.addItem(s)
        self.status_filter.setMinimumWidth(110)
        self.status_filter.currentTextChanged.connect(self._filter)
        top.addWidget(self.status_filter)

        # 新建预订
        add_btn = QPushButton("+ 新建预订")
        add_btn.setObjectName("reservationAddButton")
        add_btn.setMinimumHeight(36)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton#reservationAddButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#reservationAddButton:hover {{
                background: {COLORS['primary_hover']};
            }}
        """)
        add_btn.clicked.connect(self._new_order)
        top.addWidget(add_btn)

        l.addLayout(top)

        # 统计卡片
        stats = QHBoxLayout()
        stats.setSpacing(SPACING["md"])
        self.stats_labels = {}
        for status, color in STATUS_COLORS.items():
            card = QFrame()
            card.setObjectName("reservationStatCard")
            card.setStyleSheet(f"""
                QFrame#reservationStatCard {{
                    background: {COLORS['surface']};
                    border-radius: 8px;
                    border: 1px solid {COLORS['border']};
                    border-left: 3px solid {color};
                }}
                QFrame#reservationStatCard QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
            card.setMinimumHeight(56)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 8, 12, 8)
            cl.setSpacing(2)
            
            count = QLabel("0")
            count.setFont(QFont(*FONTS["h3"]))
            count.setStyleSheet(f"color: {color};")
            cl.addWidget(count)
            
            label = QLabel(status)
            label.setFont(QFont(*FONTS["caption"]))
            label.setStyleSheet(f"color: {COLORS['text_muted']};")
            cl.addWidget(label)
            
            stats.addWidget(card, 1)
            self.stats_labels[status] = count
        
        l.addLayout(stats)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "订单号", "客户", "房型", "入住日期", "离店日期", "间夜", "金额", "状态"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
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
        
        confirm_btn = QPushButton("确认预订")
        confirm_btn.setObjectName("reservationConfirmButton")
        confirm_btn.setMinimumHeight(36)
        confirm_btn.setMinimumWidth(104)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet(f"""
            QPushButton#reservationConfirmButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#reservationConfirmButton:hover {{
                border-color: {COLORS['primary']};
                color: {COLORS['primary']};
            }}
        """)
        confirm_btn.clicked.connect(self._confirm_order)
        bottom.addWidget(confirm_btn)
        
        cancel_btn = QPushButton("取消预订")
        cancel_btn.setObjectName("reservationCancelButton")
        cancel_btn.setMinimumHeight(36)
        cancel_btn.setMinimumWidth(104)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton#reservationCancelButton {{
                background: {COLORS['danger']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#reservationCancelButton:hover {{
                background: #dc2626;
            }}
        """)
        cancel_btn.clicked.connect(self._cancel_order)
        bottom.addWidget(cancel_btn)
        
        l.addLayout(bottom)

        self.setLayout(l)

    def _load(self):
        s = Session()
        try:
            self.orders = s.query(Order).order_by(Order.created_at.desc()).all()
            self._customers = {}
            self._room_types = {}
            
            for o in self.orders:
                if o.customer_id and o.customer_id not in self._customers:
                    c = s.query(Customer).filter(Customer.id == o.customer_id).first()
                    if c:
                        self._customers[o.customer_id] = c
                if o.room_type_id and o.room_type_id not in self._room_types:
                    rt = s.query(RoomType).filter(RoomType.id == o.room_type_id).first()
                    if rt:
                        self._room_types[o.room_type_id] = rt
        finally:
            s.close()
        self._filter()

    def _filter(self, *_):
        kw = self.search.text().strip().lower()
        status_filter = self.status_filter.currentText()
        
        # 统计
        stats = {s: 0 for s in STATUS_COLORS}
        for o in self.orders:
            if o.status in stats:
                stats[o.status] += 1
        for s, count in stats.items():
            self.stats_labels[s].setText(str(count))
        
        # 过滤
        filtered = self.orders
        if status_filter != "全部状态":
            filtered = [o for o in filtered if o.status == status_filter]
        if kw:
            filtered = [
                o for o in filtered
                if kw in (o.order_no or "").lower()
                or kw in (self._cname(o.customer_id) or "").lower()
                or kw in (self._cphone(o.customer_id) or "").lower()
            ]

        self.table.setRowCount(len(filtered))
        for i, o in enumerate(filtered):
            c = self._customers.get(o.customer_id)
            cname = c.name if c else "-"
            rt = self._room_types.get(o.room_type_id)
            rt_name = rt.name if rt else "-"
            days = max(1, (o.check_out_date - o.check_in_date).days) if o.check_in_date and o.check_out_date else 1
            
            values = [
                o.order_no or "-",
                cname,
                rt_name,
                str(o.check_in_date or "-"),
                str(o.check_out_date or "-"),
                f"{days} 晚",
                f"¥{o.total_amount:.0f}" if o.total_amount else "-",
                o.status or "-",
            ]
            
            for j, v in enumerate(values):
                item = QTableWidgetItem(v)
                item.setFont(QFont(*FONTS["body_sm"]))
                
                # 状态列特殊样式
                if j == 7:
                    sc = STATUS_COLORS.get(o.status, COLORS["text_muted"])
                    item.setForeground(QColor(sc))
                    item.setTextAlignment(Qt.AlignCenter)
                
                self.table.setItem(i, j, item)

    def _cname(self, cid):
        c = self._customers.get(cid)
        return c.name if c else "-"

    def _cphone(self, cid):
        c = self._customers.get(cid)
        return c.phone if c else ""

    def _new_order(self):
        dlg = OrderDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            notify_data_changed("reservation")
            self._load()
            QMessageBox.information(self, "成功", "预订已创建")

    def _confirm_order(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选中一条订单")
            return
        order_no = self.table.item(row, 0).text()
        s = Session()
        try:
            o = s.query(Order).filter(Order.order_no == order_no).first()
            if not o:
                return
            from src.services.pms_service import confirm_order, BusinessError
            confirm_order(s, o.id)
            try:
                from src.services.audit_service import log_operation
                user = getattr(self, "current_user", {}) or {}
                log_operation(s, user.get("id"), "确认预订", f"订单 {o.order_no} 已确认")
            except Exception:
                pass
            s.commit()
            notify_data_changed("reservation")
            self._load()
            QMessageBox.information(self, "成功", "预订已确认")
        except BusinessError as e:
            s.rollback()
            QMessageBox.warning(self, "操作失败", str(e))
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()

    def _cancel_order(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选中一条订单")
            return
        r = QMessageBox.question(self, "确认", "确定要取消该预订吗？", QMessageBox.Yes | QMessageBox.No)
        if r != QMessageBox.Yes:
            return
        order_no = self.table.item(row, 0).text()
        s = Session()
        try:
            o = s.query(Order).filter(Order.order_no == order_no).first()
            if not o:
                return
            from src.services.pms_service import cancel_order, BusinessError
            cancel_order(s, o.id)
            try:
                from src.services.audit_service import log_operation
                user = getattr(self, "current_user", {}) or {}
                log_operation(s, user.get("id"), "取消预订", f"订单 {o.order_no} 已取消")
            except Exception:
                pass
            s.commit()
            notify_data_changed("reservation")
            self._load()
            QMessageBox.information(self, "成功", "预订已取消")
        except BusinessError as e:
            s.rollback()
            QMessageBox.warning(self, "操作失败", str(e))
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()


class OrderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建预订")
        self.setObjectName("reservationOrderDialog")
        self.setFixedSize(560, 560)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        self.setStyleSheet(f"""
            QDialog#reservationOrderDialog {{
                background: {COLORS['bg']};
            }}
            QDialog#reservationOrderDialog QLabel {{
                background: transparent;
                border: none;
                color: {COLORS['text_primary']};
            }}
            QDialog#reservationOrderDialog QComboBox,
            QDialog#reservationOrderDialog QSpinBox,
            QDialog#reservationOrderDialog QDateEdit {{
                min-height: 38px;
                padding: 0 14px;
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                font-size: 15px;
            }}
            QDialog#reservationOrderDialog QComboBox:focus,
            QDialog#reservationOrderDialog QSpinBox:focus,
            QDialog#reservationOrderDialog QDateEdit:focus {{
                border: 1px solid {COLORS['primary']};
            }}
            QDialog#reservationOrderDialog QComboBox::drop-down {{
                width: 32px;
                border: none;
                background: transparent;
            }}
            QDialog#reservationOrderDialog QComboBox::down-arrow,
            QDialog#reservationOrderDialog QSpinBox::up-arrow,
            QDialog#reservationOrderDialog QSpinBox::down-arrow,
            QDialog#reservationOrderDialog QDateEdit::down-arrow {{
                image: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {COLORS['text_secondary']};
            }}
            QDialog#reservationOrderDialog QSpinBox::up-button,
            QDialog#reservationOrderDialog QSpinBox::down-button,
            QDialog#reservationOrderDialog QDateEdit::drop-down {{
                width: 28px;
                border: none;
                background: transparent;
            }}
            QPushButton#reservationDialogCancel {{
                min-height: 38px;
                min-width: 112px;
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton#reservationDialogCancel:hover {{
                background: {COLORS['surface_hover']};
                border-color: {COLORS['text_muted']};
            }}
            QPushButton#reservationDialogOk {{
                min-height: 38px;
                min-width: 128px;
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton#reservationDialogOk:hover {{
                background: {COLORS['primary_hover']};
            }}
            QPushButton#reservationDialogOk:pressed {{
                background: {COLORS['primary_pressed']};
            }}
        """)

        # 标题
        title = QLabel("新建预订")
        title.setFont(QFont(*FONTS["h3"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title)

        # 表单
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        # 客户选择
        self.customer_cb = QComboBox()
        self.customer_cb.setMinimumHeight(36)
        form.addRow("选择客户:", self.customer_cb)

        # 房型
        self.room_type_cb = QComboBox()
        self.room_type_cb.setMinimumHeight(36)
        self.room_type_cb.currentIndexChanged.connect(self._update_price)
        form.addRow("房型:", self.room_type_cb)

        # 入住日期
        self.check_in = QDateEdit(QDate.currentDate())
        self.check_in.setCalendarPopup(True)
        self.check_in.setMinimumHeight(36)
        self.check_in.dateChanged.connect(self._update_total)
        form.addRow("入住日期:", self.check_in)

        # 离店日期
        self.check_out = QDateEdit(QDate.currentDate().addDays(1))
        self.check_out.setCalendarPopup(True)
        self.check_out.setMinimumHeight(36)
        self.check_out.dateChanged.connect(self._update_total)
        form.addRow("离店日期:", self.check_out)

        # 人数
        self.guest_count = QSpinBox()
        self.guest_count.setRange(1, 10)
        self.guest_count.setValue(1)
        self.guest_count.setMinimumHeight(36)
        form.addRow("入住人数:", self.guest_count)

        # 房价
        self.price_spin = QSpinBox()
        self.price_spin.setRange(0, 99999)
        self.price_spin.setSuffix(" 元/晚")
        self.price_spin.setMinimumHeight(36)
        self.price_spin.valueChanged.connect(self._update_total)
        form.addRow("房价:", self.price_spin)

        # 预计金额
        self.total_label = QLabel("¥ 0")
        self.total_label.setFont(QFont(*FONTS["h3"]))
        self.total_label.setStyleSheet(f"color: {COLORS['accent']};")
        form.addRow("预计金额:", self.total_label)

        layout.addLayout(form)

        layout.addStretch()

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        cancel = QPushButton("取消")
        cancel.setObjectName("reservationDialogCancel")
        cancel.setProperty("variant", "secondary")
        cancel.setMinimumHeight(36)
        cancel.setMinimumWidth(100)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        
        ok = QPushButton("确认创建")
        ok.setObjectName("reservationDialogOk")
        ok.setMinimumHeight(36)
        ok.setMinimumWidth(100)
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(self._save)
        btn_row.addWidget(ok)
        
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def _load_data(self):
        s = Session()
        try:
            customers = s.query(Customer).all()
            for c in customers:
                self.customer_cb.addItem(f"{c.name} ({c.phone or '-'})", c.id)
            
            room_types = s.query(RoomType).all()
            self._room_types = room_types
            for rt in room_types:
                self.room_type_cb.addItem(rt.name, rt.id)
            
            if room_types:
                self.price_spin.setValue(int(room_types[0].base_price))
                self._update_total()
        finally:
            s.close()

    def _update_price(self):
        rt_id = self.room_type_cb.currentData()
        for rt in self._room_types:
            if rt.id == rt_id:
                self.price_spin.setValue(int(rt.base_price))
                break

    def _update_total(self):
        ci = self.check_in.date().toPyDate()
        co = self.check_out.date().toPyDate()
        days = max(1, (co - ci).days)
        price = self.price_spin.value()
        total = days * price
        self.total_label.setText(f"¥ {total}")

    def _save(self):
        cid = self.customer_cb.currentData()
        rt_id = self.room_type_cb.currentData()
        ci = self.check_in.date().toPyDate()
        co = self.check_out.date().toPyDate()
        price = self.price_spin.value()
        days = max(1, (co - ci).days)
        total = days * price

        if co <= ci:
            QMessageBox.warning(self, "错误", "离店日期必须晚于入住日期")
            return

        s = Session()
        try:
            from datetime import datetime
            import random
            order_no = f"BK{datetime.now().strftime('%Y%m%d%H%M')}{random.randint(100, 999)}"
            
            order = Order(
                order_no=order_no,
                customer_id=cid,
                room_type_id=rt_id,
                check_in_date=ci,
                check_out_date=co,
                room_price=price,
                total_amount=total,
                guest_count=self.guest_count.value(),
                status="待确认",
                deposit=0,
                paid_amount=0,
            )
            s.add(order)
            s.commit()
            self.accept()
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()
