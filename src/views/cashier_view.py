# -*- coding: utf-8 -*-
"""v3.0 收银台"""
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QLineEdit, QMessageBox, QFrame,
                              QAbstractItemView, QComboBox, QDialog,
                              QDoubleSpinBox, QTextEdit, QFormLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
from src.utils.db import Session
from src.models.bill_item import BillItem
from src.models.order import Order
from src.resources.theme import COLORS, SPACING, FONTS
from src.utils.event_bus import notify_data_changed


class ChargeDialog(QDialog):
    def __init__(self, title, description_label, amount_label, default_description="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
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
            QTextEdit, QDoubleSpinBox {{
                background: {COLORS['bg']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 7px 9px;
                font-size: 14px;
            }}
            QTextEdit:focus, QDoubleSpinBox:focus {{
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
        root.setSpacing(16)

        title_label = QLabel(title)
        title_label.setFont(QFont(*FONTS["h2"]))
        root.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(14)

        self.description = QTextEdit()
        self.description.setFixedHeight(72)
        self.description.setPlaceholderText("请输入费用说明")
        self.description.setText(default_description)
        self.description.setFont(QFont(*FONTS["body_sm"]))
        form.addRow(description_label, self.description)

        self.amount = QDoubleSpinBox()
        self.amount.setRange(0.01, 999999)
        self.amount.setDecimals(2)
        self.amount.setSingleStep(10)
        self.amount.setPrefix("¥ ")
        self.amount.setFont(QFont(*FONTS["body_sm"]))
        form.addRow(amount_label, self.amount)
        root.addLayout(form)

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

    def values(self):
        return self.description.toPlainText().strip(), float(self.amount.value())


class SettleDialog(QDialog):
    def __init__(self, order_no, balance, parent=None):
        super().__init__(parent)
        self.setWindowTitle("结清账务")
        self.setModal(True)
        self.setFixedWidth(400)
        self.setStyleSheet(f"""
            QDialog {{
                background: {COLORS['surface']};
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {COLORS['text_primary']};
            }}
            QComboBox {{
                background: {COLORS['bg']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 7px 9px;
                font-size: 14px;
            }}
            QComboBox:focus {{
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

        title = QLabel("结清账务")
        title.setFont(QFont(*FONTS["h2"]))
        root.addWidget(title)

        info = QLabel(f"订单号：{order_no}\n应收尾款：¥ {balance:.2f}")
        info.setFont(QFont(*FONTS["body_sm"]))
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; line-height: 1.4;")
        root.addWidget(info)

        row = QHBoxLayout()
        label = QLabel("支付方式：")
        label.setFont(QFont(*FONTS["body_sm"]))
        row.addWidget(label)
        self.method = QComboBox()
        self.method.addItems(["现金", "微信", "支付宝", "银行卡"])
        row.addWidget(self.method, 1)
        root.addLayout(row)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("取消")
        cancel.setObjectName("secondaryDialogButton")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        ok = QPushButton("确认结清")
        ok.setObjectName("primaryDialogButton")
        ok.clicked.connect(self.accept)
        actions.addWidget(ok)
        root.addLayout(actions)

    def pay_method(self):
        return self.method.currentText()


class CashierView(QWidget):
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
        
        title = QLabel("收银台")
        title.setFont(QFont(*FONTS["h1"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        top.addWidget(title)
        top.addStretch()

        # 搜索
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  搜索订单号 / 项目")
        self.search.setMinimumHeight(36)
        self.search.setFixedWidth(260)
        self.search.textChanged.connect(self._filter)
        top.addWidget(self.search)

        # 类型筛选
        self.type_filter = QComboBox()
        self.type_filter.addItem("全部类型")
        self.type_filter.addItems(["房费", "押金", "杂费", "结算", "退款"])
        self.type_filter.setMinimumWidth(110)
        self.type_filter.currentTextChanged.connect(self._filter)
        top.addWidget(self.type_filter)

        # 刷新
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setObjectName("cashierRefreshButton")
        refresh_btn.setMinimumHeight(36)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton#cashierRefreshButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#cashierRefreshButton:hover {{
                border-color: {COLORS['primary']};
                color: {COLORS['primary']};
            }}
        """)
        refresh_btn.clicked.connect(self._load)
        top.addWidget(refresh_btn)

        l.addLayout(top)

        # 今日收银统计
        stats = QHBoxLayout()
        stats.setSpacing(SPACING["md"])
        
        self.today_income_card = self._build_stat_card("今日收入", "¥ 0", COLORS["success"])
        stats.addWidget(self.today_income_card, 1)
        
        self.today_count_card = self._build_stat_card("今日笔数", "0", COLORS["info"])
        stats.addWidget(self.today_count_card, 1)
        
        self.today_refund_card = self._build_stat_card("今日退款", "¥ 0", COLORS["danger"])
        stats.addWidget(self.today_refund_card, 1)
        
        self.total_income_card = self._build_stat_card("累计收入", "¥ 0", COLORS["accent"])
        stats.addWidget(self.total_income_card, 1)
        
        l.addLayout(stats)

        # 账单明细表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "时间", "订单号", "项目类型", "描述", "金额", "支付方式", "操作"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        l.addWidget(self.table, 1)

        # 底部操作
        bottom = QHBoxLayout()
        bottom.addStretch()
        
        settle_btn = QPushButton("结清账务")
        settle_btn.setObjectName("cashierSettleButton")
        settle_btn.setMinimumHeight(36)
        settle_btn.setCursor(Qt.PointingHandCursor)
        settle_btn.setStyleSheet(f"""
            QPushButton#cashierSettleButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#cashierSettleButton:hover {{
                background: {COLORS['primary_hover']};
            }}
        """)
        settle_btn.clicked.connect(self._settle_balance)
        bottom.addWidget(settle_btn)

        add_btn = QPushButton("+ 新增收费")
        add_btn.setObjectName("cashierAddButton")
        add_btn.setMinimumHeight(36)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton#cashierAddButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#cashierAddButton:hover {{
                background: {COLORS['primary_hover']};
            }}
        """)
        add_btn.clicked.connect(self._add_charge)
        bottom.addWidget(add_btn)
        
        refund_btn = QPushButton("退款")
        refund_btn.setObjectName("cashierRefundButton")
        refund_btn.setMinimumHeight(36)
        refund_btn.setCursor(Qt.PointingHandCursor)
        refund_btn.setStyleSheet(f"""
            QPushButton#cashierRefundButton {{
                background: {COLORS['danger']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#cashierRefundButton:hover {{
                background: #dc2626;
            }}
        """)
        refund_btn.clicked.connect(self._do_refund)
        bottom.addWidget(refund_btn)
        
        l.addLayout(bottom)

        self.setLayout(l)

    def _build_stat_card(self, label, value, color):
        card = QFrame()
        card.setObjectName("cashierStatCard")
        card.setStyleSheet(f"""
            QFrame#cashierStatCard {{
                background: {COLORS['surface']};
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
                border-left: 3px solid {color};
            }}
            QFrame#cashierStatCard QLabel {{
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
            self.items = s.query(BillItem).order_by(BillItem.created_at.desc()).all()
            self._order_nos = {}
            if self.items:
                oids = {i.order_id for i in self.items if i.order_id}
                if oids:
                    for o in s.query(Order).filter(Order.id.in_(oids)).all():
                        self._order_nos[o.id] = o.order_no
            
            # 今日统计
            today = datetime.now().date()
            today_items = [i for i in self.items if i.created_at and i.created_at.date() == today]
            
            revenue_types = ("房费", "杂费")
            today_income = sum(i.amount for i in today_items if i.item_type in revenue_types)
            today_count = len(today_items)
            today_refund = sum(i.amount for i in today_items if i.item_type == "退款")
            total_income = sum(i.amount for i in self.items if i.item_type in revenue_types)
            
            self.today_income_card.value_label.setText(f"¥ {today_income:.0f}")
            self.today_count_card.value_label.setText(str(today_count))
            self.today_refund_card.value_label.setText(f"¥ {today_refund:.0f}")
            self.total_income_card.value_label.setText(f"¥ {total_income:.0f}")
            
        finally:
            s.close()
        self._filter()

    def _filter(self, *_):
        kw = self.search.text().strip().lower()
        type_filter = self.type_filter.currentText()
        
        filtered = self.items
        if type_filter != "全部类型":
            filtered = [i for i in filtered if i.item_type == type_filter]
        if kw:
            filtered = [
                i for i in filtered
                if kw in self._order_nos.get(i.order_id, "").lower()
                or kw in (i.description or "").lower()
            ]

        self.table.setRowCount(len(filtered))
        for i, item in enumerate(filtered):
            time_str = item.created_at.strftime("%m-%d %H:%M") if item.created_at else "-"
            
            values = [
                time_str,
                self._order_nos.get(item.order_id, "-"),
                item.item_type or "-",
                item.description or "-",
                f"¥{item.amount:.0f}" if item.amount else "-",
                item.payment_method or "-",
                "详情",
            ]
            
            for j, v in enumerate(values):
                it = QTableWidgetItem(v)
                it.setFont(QFont(*FONTS["body_sm"]))
                
                # 金额列
                if j == 4:
                    color = COLORS["danger"] if item.item_type == "退款" else COLORS["success"]
                    it.setForeground(QColor(color))
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                # 类型列
                if j == 2:
                    type_colors = {
                        "房费": COLORS["info"],
                        "押金": COLORS["warning"],
                        "杂费": COLORS["text_secondary"],
                        "结算": COLORS["primary"],
                        "退款": COLORS["danger"],
                    }
                    c = type_colors.get(item.item_type, COLORS["text_muted"])
                    it.setForeground(QColor(c))
                    it.setTextAlignment(Qt.AlignCenter)
                
                # 操作列
                if j == 6:
                    it.setForeground(QColor(COLORS["primary"]))
                    it.setTextAlignment(Qt.AlignCenter)
                
                self.table.setItem(i, j, it)

    def _add_charge(self):
        from src.services.pms_service import add_bill_item, BusinessError
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选中一条订单记录")
            return
        order_no = self.table.item(row, 1).text()
        if order_no == "-":
            QMessageBox.warning(self, "提示", "无法识别订单号")
            return
        s = Session()
        try:
            o = s.query(Order).filter(Order.order_no == order_no).first()
            if not o:
                QMessageBox.warning(self, "提示", "订单不存在")
                return
            dlg = ChargeDialog("新增收费", "费用描述：", "收费金额：", parent=self)
            if dlg.exec_() != QDialog.Accepted:
                return
            desc, amount = dlg.values()
            if not desc:
                QMessageBox.warning(self, "错误", "请输入费用描述")
                return
            add_bill_item(s, o.id, "杂费", amount, description=desc.strip())
            s.commit()
            notify_data_changed("cashier")
            self._load()
            QMessageBox.information(self, "成功", f"已添加 {desc.strip()} ¥{amount:.0f}")
        except BusinessError as e:
            s.rollback()
            QMessageBox.warning(self, "操作失败", str(e))
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()

    def _settle_balance(self):
        from src.services.pms_service import settle_order_balance, BusinessError
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选中一条订单记录")
            return
        order_no = self.table.item(row, 1).text()
        if order_no == "-":
            QMessageBox.warning(self, "提示", "无法识别订单号")
            return
        s = Session()
        try:
            o = s.query(Order).filter(Order.order_no == order_no).first()
            if not o:
                QMessageBox.warning(self, "提示", "订单不存在")
                return
            balance = round((o.total_amount or 0) - (o.paid_amount or 0), 2)
            if balance <= 0:
                QMessageBox.information(self, "无需结清", "该订单已无未结清金额")
                return
            dlg = SettleDialog(order_no, balance, self)
            if dlg.exec_() != QDialog.Accepted:
                return
            settlement = settle_order_balance(s, o.id, pay_method=dlg.pay_method())
            s.commit()
            notify_data_changed("cashier")
            self._load()
            QMessageBox.information(self, "成功", f"已结清尾款 ¥{settlement.amount:.0f}")
        except BusinessError as e:
            s.rollback()
            QMessageBox.warning(self, "操作失败", str(e))
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()

    def _do_refund(self):
        from src.services.pms_service import add_bill_item, BusinessError
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选中一条记录")
            return
        order_no = self.table.item(row, 1).text()
        if order_no == "-":
            QMessageBox.warning(self, "提示", "无法识别订单号")
            return
        s = Session()
        try:
            o = s.query(Order).filter(Order.order_no == order_no).first()
            if not o:
                QMessageBox.warning(self, "提示", "订单不存在")
                return
            dlg = ChargeDialog("退款", "退款说明：", "退款金额：", default_description="退款", parent=self)
            if dlg.exec_() != QDialog.Accepted:
                return
            desc, raw_amount = dlg.values()
            if not desc:
                QMessageBox.warning(self, "错误", "请输入退款说明")
                return
            amount = -abs(raw_amount)
            add_bill_item(s, o.id, "退款", amount, description=desc)
            s.commit()
            notify_data_changed("cashier")
            self._load()
            QMessageBox.information(self, "成功", f"已退款 ¥{abs(amount):.0f}")
        except BusinessError as e:
            s.rollback()
            QMessageBox.warning(self, "操作失败", str(e))
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()
