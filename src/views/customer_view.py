# -*- coding: utf-8 -*-
"""v3.0 客户管理"""
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QLineEdit, QMessageBox, QDialog,
                              QFormLayout, QComboBox, QFrame, QAbstractItemView)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
from src.utils.db import Session
from src.models.customer import Customer
from src.resources.theme import COLORS, SPACING, FONTS
from src.services.pms_service import BusinessError, delete_customer
from src.utils.event_bus import notify_data_changed


# 会员等级颜色
VIP_COLORS = {
    "普通": COLORS["text_muted"],
    "银卡": "#06b6d4",
    "金卡": COLORS["accent"],
    "铂金": "#5A496F",
}


class CustomerView(QWidget):
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
        
        title = QLabel("客户管理")
        title.setFont(QFont(*FONTS["h1"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        top.addWidget(title)
        top.addStretch()

        # 搜索
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  搜索姓名 / 手机号 / 证件号")
        self.search.setMinimumHeight(36)
        self.search.setFixedWidth(280)
        self.search.textChanged.connect(self._filter)
        top.addWidget(self.search)

        # 等级筛选
        self.vip_filter = QComboBox()
        self.vip_filter.addItem("全部等级")
        for v in VIP_COLORS.keys():
            self.vip_filter.addItem(v)
        self.vip_filter.setMinimumWidth(110)
        self.vip_filter.currentTextChanged.connect(self._filter)
        top.addWidget(self.vip_filter)

        # 新增客户
        add_btn = QPushButton("+ 新增客户")
        add_btn.setObjectName("customerAddButton")
        add_btn.setMinimumHeight(36)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton#customerAddButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#customerAddButton:hover {{
                background: {COLORS['primary_hover']};
            }}
        """)
        add_btn.clicked.connect(self._add_customer)
        top.addWidget(add_btn)

        l.addLayout(top)

        # 统计卡片
        stats = QHBoxLayout()
        stats.setSpacing(SPACING["md"])
        
        self.total_card = self._build_stat_card("客户总数", "0", COLORS["primary"])
        stats.addWidget(self.total_card, 1)
        
        self.vip_card = self._build_stat_card("会员客户", "0", COLORS["accent"])
        stats.addWidget(self.vip_card, 1)
        
        self.today_new_card = self._build_stat_card("今日新增", "0", COLORS["success"])
        stats.addWidget(self.today_new_card, 1)
        
        self.active_card = self._build_stat_card("活跃客户", "0", COLORS["info"])
        stats.addWidget(self.active_card, 1)
        
        l.addLayout(stats)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "姓名", "手机号", "会员等级", "积分", "累计入住", "上次入住", "操作"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        l.addWidget(self.table, 1)

        # 底部操作
        bottom = QHBoxLayout()
        bottom.addStretch()
        
        edit_btn = QPushButton("编辑")
        edit_btn.setObjectName("customerEditButton")
        edit_btn.setMinimumHeight(36)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet(f"""
            QPushButton#customerEditButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#customerEditButton:hover {{
                border-color: {COLORS['primary']};
                color: {COLORS['primary']};
            }}
        """)
        edit_btn.clicked.connect(self._edit_customer)
        bottom.addWidget(edit_btn)
        
        delete_btn = QPushButton("删除")
        delete_btn.setObjectName("customerDeleteButton")
        delete_btn.setMinimumHeight(36)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(f"""
            QPushButton#customerDeleteButton {{
                background: {COLORS['danger']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#customerDeleteButton:hover {{
                background: #dc2626;
            }}
        """)
        delete_btn.clicked.connect(self._delete_customer)
        bottom.addWidget(delete_btn)
        
        l.addLayout(bottom)

        self.setLayout(l)

    def _build_stat_card(self, label, value, color):
        card = QFrame()
        card.setObjectName("customerStatCard")
        card.setStyleSheet(f"""
            QFrame#customerStatCard {{
                background: {COLORS['surface']};
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
                border-left: 3px solid {color};
            }}
            QFrame#customerStatCard QLabel {{
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
            self.customers = s.query(Customer).order_by(Customer.id.desc()).all()
            
            # 统计
            total = len(self.customers)
            vip_count = sum(1 for c in self.customers if c.vip_level and c.vip_level != "普通")
            
            today = datetime.now().date()
            today_new = sum(1 for c in self.customers 
                          if hasattr(c, 'created_at') and c.created_at 
                          and c.created_at.date() == today)
            
            # 活跃客户（30天内有入住）
            active = sum(1 for c in self.customers 
                        if c.last_stay and (today - c.last_stay).days <= 30)
            
            self.total_card.value_label.setText(str(total))
            self.vip_card.value_label.setText(str(vip_count))
            self.today_new_card.value_label.setText(str(today_new))
            self.active_card.value_label.setText(str(active))
            
        finally:
            s.close()
        self._filter()

    def _filter(self, *_):
        kw = self.search.text().strip().lower()
        vip_filter = self.vip_filter.currentText()
        
        filtered = self.customers
        if vip_filter != "全部等级":
            filtered = [c for c in filtered if c.vip_level == vip_filter]
        if kw:
            filtered = [
                c for c in filtered
                if kw in (c.name or "").lower()
                or kw in (c.phone or "").lower()
            ]

        self.table.setRowCount(len(filtered))
        for i, c in enumerate(filtered):
            values = [
                c.name or "-",
                c.phone or "-",
                c.vip_level or "普通",
                str(c.points or 0),
                f"{c.total_stays or 0} 次",
                str(c.last_stay) if c.last_stay else "从未入住",
                "查看",
            ]
            
            for j, v in enumerate(values):
                item = QTableWidgetItem(v)
                item.setFont(QFont(*FONTS["body_sm"]))
                if j == 0:
                    item.setData(Qt.UserRole, c.id)
                
                # 会员等级
                if j == 2:
                    color = VIP_COLORS.get(c.vip_level or "普通", COLORS["text_muted"])
                    item.setForeground(QColor(color))
                    item.setTextAlignment(Qt.AlignCenter)
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                
                # 积分
                if j == 3:
                    item.setTextAlignment(Qt.AlignCenter)
                
                # 操作
                if j == 6:
                    item.setForeground(QColor(COLORS["primary"]))
                    item.setTextAlignment(Qt.AlignCenter)
                
                self.table.setItem(i, j, item)

    def _add_customer(self):
        dlg = CustomerDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            notify_data_changed("customers")
            self._load()
            QMessageBox.information(self, "成功", "客户已添加")

    def _edit_customer(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选中一个客户")
            return
        customer_id = self.table.item(row, 0).data(Qt.UserRole)
        dlg = CustomerDialog(self, customer_id=customer_id)
        if dlg.exec_() == QDialog.Accepted:
            notify_data_changed("customers")
            self._load()
            QMessageBox.information(self, "成功", "客户信息已更新")

    def _delete_customer(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选中一个客户")
            return
        
        r = QMessageBox.question(self, "确认", "确定要删除该客户吗？", QMessageBox.Yes | QMessageBox.No)
        if r != QMessageBox.Yes:
            return
        
        customer_id = self.table.item(row, 0).data(Qt.UserRole)
        s = Session()
        try:
            c = s.query(Customer).filter(Customer.id == customer_id).first()
            if c:
                delete_customer(s, c.id)
                s.commit()
                notify_data_changed("customers")
                self._load()
                QMessageBox.information(self, "成功", "客户已删除")
        except BusinessError as e:
            s.rollback()
            QMessageBox.warning(self, "无法删除", str(e))
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()


class CustomerDialog(QDialog):
    def __init__(self, parent=None, customer_id=None):
        super().__init__(parent)
        self.customer_id = customer_id
        self.setWindowTitle("编辑客户" if customer_id else "新增客户")
        self.setFixedSize(420, 400)
        self.created_customer_id = None
        self._init_ui()
        if self.customer_id:
            self._load_customer()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("编辑客户" if self.customer_id else "新增客户")
        title.setFont(QFont(*FONTS["h3"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.name = QLineEdit()
        self.name.setMinimumHeight(36)
        form.addRow("姓名:", self.name)

        self.phone = QLineEdit()
        self.phone.setMinimumHeight(36)
        form.addRow("手机号:", self.phone)

        self.vip_level = QComboBox()
        self.vip_level.addItems(["普通", "银卡", "金卡", "铂金"])
        self.vip_level.setMinimumHeight(36)
        form.addRow("会员等级:", self.vip_level)

        self.preference = QLineEdit()
        self.preference.setMinimumHeight(36)
        self.preference.setPlaceholderText("如：无烟房、高楼层等")
        form.addRow("入住偏好:", self.preference)

        layout.addLayout(form)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        cancel = QPushButton("取消")
        cancel.setProperty("variant", "secondary")
        cancel.setMinimumHeight(36)
        cancel.setMinimumWidth(100)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        
        ok = QPushButton("保存修改" if self.customer_id else "确认添加")
        ok.setMinimumHeight(36)
        ok.setMinimumWidth(100)
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(self._save)
        btn_row.addWidget(ok)
        
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def _save(self):
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "姓名为必填项")
            return

        s = Session()
        try:
            if self.customer_id:
                customer = s.query(Customer).filter(Customer.id == self.customer_id).first()
                if not customer:
                    QMessageBox.warning(self, "错误", "客户不存在")
                    return
                customer.name = name
                customer.phone = self.phone.text().strip() or None
                customer.vip_level = self.vip_level.currentText()
                customer.preference = self.preference.text().strip() or None
            else:
                customer = Customer(
                    name=name,
                    phone=self.phone.text().strip() or None,
                    vip_level=self.vip_level.currentText(),
                    preference=self.preference.text().strip() or None,
                    points=0,
                    total_stays=0,
                )
                s.add(customer)
            s.commit()
            self.created_customer_id = customer.id
            self.accept()
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()

    def _load_customer(self):
        s = Session()
        try:
            customer = s.query(Customer).filter(Customer.id == self.customer_id).first()
            if not customer:
                return
            self.name.setText(customer.name or "")
            self.phone.setText(customer.phone or "")
            idx = self.vip_level.findText(customer.vip_level or "普通")
            self.vip_level.setCurrentIndex(max(idx, 0))
            self.preference.setText(customer.preference or "")
        finally:
            s.close()
