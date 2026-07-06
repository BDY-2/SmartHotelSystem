# -*- coding: utf-8 -*-
"""v3.0 系统设置 + 用户管理"""
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QMessageBox, QDialog, QFormLayout,
                              QLineEdit, QComboBox, QFrame, QAbstractItemView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
import hashlib
from datetime import date
from src.utils.db import Session
from src.models.user import User
from src.models.operation_log import OperationLog
from src.models.night_audit import NightAudit
from src.resources.theme import COLORS, SPACING, FONTS
from src.utils.event_bus import notify_data_changed


class SettingsView(QWidget):
    logout_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._init_ui()
        self._load_users()

    def _init_ui(self):
        l = QVBoxLayout()
        l.setContentsMargins(SPACING["xxl"], SPACING["xxl"], SPACING["xxl"], SPACING["xxl"])
        l.setSpacing(SPACING["lg"])

        # 页面标题
        title = QLabel("系统设置")
        title.setFont(QFont(*FONTS["h1"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        l.addWidget(title)

        # 用户管理卡片
        user_card = QFrame()
        user_card.setObjectName("settingsUserCard")
        user_card.setStyleSheet(f"""
            QFrame#settingsUserCard {{
                background: {COLORS['surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#settingsUserCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        ul = QVBoxLayout(user_card)
        ul.setContentsMargins(SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["lg"])
        ul.setSpacing(SPACING["md"])

        # 卡片标题
        card_title = QHBoxLayout()
        t = QLabel("用户管理")
        t.setFont(QFont(*FONTS["h3"]))
        t.setStyleSheet(f"color: {COLORS['text_primary']};")
        card_title.addWidget(t)
        card_title.addStretch()
        
        add_btn = QPushButton("+ 添加用户")
        add_btn.setObjectName("settingsAddUserButton")
        add_btn.setMinimumHeight(32)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton#settingsAddUserButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton#settingsAddUserButton:hover {{
                background: {COLORS['primary_hover']};
            }}
        """)
        add_btn.clicked.connect(self._add_user)
        card_title.addWidget(add_btn)
        
        ul.addLayout(card_title)

        # 用户表格
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels(["用户名", "姓名", "角色", "状态", "操作"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.user_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.user_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.user_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.user_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.user_table.setShowGrid(False)
        self.user_table.verticalHeader().setVisible(False)
        self.user_table.verticalHeader().setDefaultSectionSize(44)
        ul.addWidget(self.user_table)

        # 操作按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        reset_btn = QPushButton("重置密码")
        reset_btn.setObjectName("settingsResetButton")
        reset_btn.setMinimumHeight(36)
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setStyleSheet(f"""
            QPushButton#settingsResetButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#settingsResetButton:hover {{
                border-color: {COLORS['primary']};
                color: {COLORS['primary']};
            }}
        """)
        reset_btn.clicked.connect(self._reset_pwd)
        btn_row.addWidget(reset_btn)
        
        toggle_btn = QPushButton("启用/禁用")
        toggle_btn.setObjectName("settingsToggleButton")
        toggle_btn.setMinimumHeight(36)
        toggle_btn.setCursor(Qt.PointingHandCursor)
        toggle_btn.setStyleSheet(f"""
            QPushButton#settingsToggleButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#settingsToggleButton:hover {{
                border-color: {COLORS['primary']};
                color: {COLORS['primary']};
            }}
        """)
        toggle_btn.clicked.connect(self._toggle_user)
        btn_row.addWidget(toggle_btn)
        
        ul.addLayout(btn_row)

        l.addWidget(user_card)

        # 操作日志与夜审卡片
        audit_card = QFrame()
        audit_card.setObjectName("settingsAuditCard")
        audit_card.setStyleSheet(f"""
            QFrame#settingsAuditCard {{
                background: {COLORS['surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#settingsAuditCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        al = QVBoxLayout(audit_card)
        al.setContentsMargins(SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["lg"])
        al.setSpacing(SPACING["md"])

        audit_title = QHBoxLayout()
        at = QLabel("操作日志与轻量夜审")
        at.setFont(QFont(*FONTS["h3"]))
        audit_title.addWidget(at)
        audit_title.addStretch()
        night_btn = QPushButton("执行今日夜审")
        night_btn.setObjectName("settingsNightAuditButton")
        night_btn.setMinimumHeight(32)
        night_btn.setCursor(Qt.PointingHandCursor)
        night_btn.setStyleSheet(f"""
            QPushButton#settingsNightAuditButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton#settingsNightAuditButton:hover {{
                background: {COLORS['primary_hover']};
            }}
        """)
        night_btn.clicked.connect(self._run_night_audit)
        audit_title.addWidget(night_btn)
        al.addLayout(audit_title)

        self.audit_summary = QLabel("最近夜审：尚未执行")
        self.audit_summary.setFont(QFont(*FONTS["body_sm"]))
        self.audit_summary.setStyleSheet(f"color: {COLORS['text_muted']};")
        al.addWidget(self.audit_summary)

        audit_result = QHBoxLayout()
        audit_result.setSpacing(SPACING["md"])
        self.audit_revenue_value = self._build_audit_metric("夜审收入", "¥ 0", COLORS["success"])
        self.audit_orders_value = self._build_audit_metric("覆盖订单", "0", COLORS["info"])
        self.audit_occupancy_value = self._build_audit_metric("出租率", "0.0%", COLORS["primary"])
        self.audit_revpar_value = self._build_audit_metric("RevPAR", "¥ 0", COLORS["accent"])
        for card in [
            self.audit_revenue_value,
            self.audit_orders_value,
            self.audit_occupancy_value,
            self.audit_revpar_value,
        ]:
            audit_result.addWidget(card, 1)
        al.addLayout(audit_result)

        self.log_table = QTableWidget()
        self.log_table.setColumnCount(4)
        self.log_table.setHorizontalHeaderLabels(["时间", "用户ID", "操作", "详情"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.log_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.log_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setShowGrid(False)
        self.log_table.verticalHeader().setDefaultSectionSize(32)
        al.addWidget(self.log_table)

        l.addWidget(audit_card, 1)

        # 退出登录卡片
        logout_card = QFrame()
        logout_card.setObjectName("settingsLogoutCard")
        logout_card.setStyleSheet(f"""
            QFrame#settingsLogoutCard {{
                background: {COLORS['surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#settingsLogoutCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        ll = QHBoxLayout(logout_card)
        ll.setContentsMargins(SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["lg"])

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        lt = QLabel("退出登录")
        lt.setFont(QFont(*FONTS["h4"]))
        lt.setStyleSheet(f"color: {COLORS['text_primary']};")
        info_layout.addWidget(lt)
        
        ld = QLabel("退出当前账号，返回登录页面")
        ld.setFont(QFont(*FONTS["body_sm"]))
        ld.setStyleSheet(f"color: {COLORS['text_muted']};")
        info_layout.addWidget(ld)
        
        ll.addLayout(info_layout)
        ll.addStretch()

        logout_btn = QPushButton("退出登录")
        logout_btn.setObjectName("settingsLogoutButton")
        logout_btn.setMinimumHeight(36)
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setStyleSheet(f"""
            QPushButton#settingsLogoutButton {{
                background: {COLORS['danger']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#settingsLogoutButton:hover {{
                background: #dc2626;
            }}
        """)
        logout_btn.clicked.connect(self._logout)
        ll.addWidget(logout_btn)

        l.addWidget(logout_card)

        l.addStretch()
        self.setLayout(l)

    def _load_users(self):
        s = Session()
        try:
            users = s.query(User).all()
        finally:
            s.close()
        
        self.user_table.setRowCount(len(users))
        for i, u in enumerate(users):
            values = [
                u.username or "-",
                u.real_name or "-",
                u.role or "-",
                "活跃" if u.is_active else "禁用",
                "编辑",
            ]
            
            for j, v in enumerate(values):
                item = QTableWidgetItem(v)
                item.setFont(QFont(*FONTS["body_sm"]))
                
                # 状态列
                if j == 3:
                    color = COLORS["success"] if u.is_active else COLORS["text_muted"]
                    item.setForeground(QColor(color))
                    item.setTextAlignment(Qt.AlignCenter)
                
                # 操作列
                if j == 4:
                    item.setForeground(QColor(COLORS["primary"]))
                    item.setTextAlignment(Qt.AlignCenter)
                
                self.user_table.setItem(i, j, item)
        self._load_logs()

    def _build_audit_metric(self, label, value, color):
        card = QFrame()
        card.setObjectName("auditMetricCard")
        card.setStyleSheet(f"""
            QFrame#auditMetricCard {{
                background: {COLORS['bg']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
            }}
            QFrame#auditMetricCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(3)
        value_label = QLabel(value)
        value_label.setFont(QFont(*FONTS["h4"]))
        value_label.setStyleSheet(f"color: {color};")
        name_label = QLabel(label)
        name_label.setFont(QFont(*FONTS["caption"]))
        name_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(value_label)
        layout.addWidget(name_label)
        card.value_label = value_label
        return card

    def _load_logs(self):
        s = Session()
        try:
            logs = s.query(OperationLog).order_by(OperationLog.created_at.desc()).limit(10).all()
            latest_audit = s.query(NightAudit).order_by(NightAudit.executed_at.desc()).first()
            if latest_audit:
                self.audit_summary.setText(
                    f"最近夜审：{latest_audit.audit_date}  收入 ¥{latest_audit.total_revenue:.0f}  "
                    f"订单 {latest_audit.total_orders}  出租率 {latest_audit.occupancy_rate:.1f}%"
                )
                self.audit_revenue_value.value_label.setText(f"¥ {latest_audit.total_revenue:.0f}")
                self.audit_orders_value.value_label.setText(str(latest_audit.total_orders or 0))
                self.audit_occupancy_value.value_label.setText(f"{latest_audit.occupancy_rate:.1f}%")
                self.audit_revpar_value.value_label.setText(f"¥ {latest_audit.revpar:.0f}")
        finally:
            s.close()

        self.log_table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            values = [
                str(log.created_at or "-"),
                str(log.user_id or "-"),
                log.action or "-",
                log.detail or "-",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFont(QFont(*FONTS["caption"]))
                if col in (1, 2):
                    item.setTextAlignment(Qt.AlignCenter)
                self.log_table.setItem(row, col, item)

    def _run_night_audit(self):
        s = Session()
        try:
            from src.services.audit_service import run_light_night_audit, log_operation
            user = getattr(self, "current_user", {}) or {}
            audit = run_light_night_audit(s, date.today(), user.get("id"))
            log_operation(s, user.get("id"), "执行夜审", f"生成 {audit.audit_date} 轻量夜审")
            s.commit()
            notify_data_changed("settings")
            self._load_logs()
            QMessageBox.information(self, "成功", "今日夜审已生成")
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()

    def _add_user(self):
        dlg = UserDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            notify_data_changed("settings")
            self._load_users()
            QMessageBox.information(self, "成功", "用户已添加")

    def _reset_pwd(self):
        row = self.user_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选中一个用户")
            return
        
        uname = self.user_table.item(row, 0).text()
        
        r = QMessageBox.question(
            self, "确认重置",
            f"确定要重置用户「{uname}」的密码吗？\n\n重置后密码为：123456",
            QMessageBox.Yes | QMessageBox.No
        )
        if r != QMessageBox.Yes:
            return

        s = Session()
        try:
            u = s.query(User).filter(User.username == uname).first()
            if u:
                u.password_hash = hashlib.sha256("123456".encode()).hexdigest()
                s.commit()
                notify_data_changed("settings")
                QMessageBox.information(self, "成功", f"密码已重置为：123456")
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()

    def _toggle_user(self):
        row = self.user_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选中一个用户")
            return
        
        uname = self.user_table.item(row, 0).text()
        status = self.user_table.item(row, 3).text()
        new_status = "禁用" if status == "活跃" else "活跃"

        s = Session()
        try:
            u = s.query(User).filter(User.username == uname).first()
            if u:
                u.is_active = not u.is_active
                s.commit()
                notify_data_changed("settings")
                self._load_users()
                QMessageBox.information(self, "成功", f"用户状态已改为：{new_status}")
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()

    def _logout(self):
        r = QMessageBox.question(
            self, "退出登录",
            "确定要退出登录吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if r == QMessageBox.Yes:
            self.logout_requested.emit()


class UserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加用户")
        self.setFixedSize(400, 360)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("添加用户")
        title.setFont(QFont(*FONTS["h3"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.uname = QLineEdit()
        self.uname.setMinimumHeight(36)
        form.addRow("用户名:", self.uname)

        self.name = QLineEdit()
        self.name.setMinimumHeight(36)
        form.addRow("姓名:", self.name)

        self.role_cb = QComboBox()
        self.role_cb.addItems(["管理员", "前台", "客房", "财务"])
        self.role_cb.setMinimumHeight(36)
        form.addRow("角色:", self.role_cb)

        tip = QLabel("初始密码：123456")
        tip.setFont(QFont(*FONTS["caption"]))
        tip.setStyleSheet(f"color: {COLORS['text_muted']};")
        form.addRow("", tip)

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
        
        ok = QPushButton("确认添加")
        ok.setMinimumHeight(36)
        ok.setMinimumWidth(100)
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(self._save)
        btn_row.addWidget(ok)
        
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def _save(self):
        u = self.uname.text().strip()
        if not u:
            QMessageBox.warning(self, "错误", "用户名为必填项")
            return

        s = Session()
        try:
            # 检查用户名是否已存在
            existing = s.query(User).filter(User.username == u).first()
            if existing:
                QMessageBox.warning(self, "错误", "用户名已存在")
                return

            user = User(
                username=u,
                real_name=self.name.text().strip() or None,
                role=self.role_cb.currentText(),
                password_hash=hashlib.sha256("123456".encode()).hexdigest(),
                is_active=True,
            )
            s.add(user)
            s.commit()
            self.accept()
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()
