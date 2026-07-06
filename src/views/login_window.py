# -*- coding: utf-8 -*-
"""v3.0 登录窗口 —— 专业B端登录风格"""
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLineEdit, QFrame, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import hashlib
from src.utils.db import Session
from src.models.user import User
from src.resources.theme import COLORS, FONTS
from src.config import APP_NAME


class LoginWindow(QWidget):
    login_success = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._drag_pos = None
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setWindowTitle("iHome PMS 登录")
        self.setMinimumSize(720, 460)
        self.resize(760, 480)
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("loginWindowRoot")
        root = QVBoxLayout()
        root.setContentsMargins(1, 0, 1, 1)
        root.setSpacing(0)
        root_widget_style = f"""
            QWidget#loginWindowRoot {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['primary']};
            }}
        """

        root.addWidget(self._build_window_title_bar())
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ═══ 左侧品牌区 ═══
        left_panel = QFrame()
        left_panel.setObjectName("loginLeftPanel")
        left_panel.setFixedWidth(280)
        left_panel.setAutoFillBackground(True)
        left_panel.setStyleSheet(f"""
            QFrame#loginLeftPanel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {COLORS['primary']}, stop:1 {COLORS['primary_pressed']});
                border: none;
            }}
            QFrame#loginLeftPanel QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(34, 36, 34, 28)
        left_layout.setSpacing(0)

        # Logo
        logo_layout = QHBoxLayout()
        logo_layout.setSpacing(12)
        
        logo_icon = QLabel("🏨")
        logo_icon.setFont(QFont("Segoe UI Emoji", 22))
        logo_layout.addWidget(logo_icon)
        
        logo_text = QLabel("iHome PMS")
        logo_text.setFont(QFont("Microsoft YaHei UI", 18, QFont.Bold))
        logo_text.setStyleSheet("color: white; letter-spacing: 2px;")
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        
        left_layout.addLayout(logo_layout)
        left_layout.addSpacing(12)

        # 副标题
        subtitle = QLabel("智能民宿管理系统")
        subtitle.setFont(QFont(*FONTS["h3"]))
        subtitle.setStyleSheet("color: rgba(255,255,255,0.85);")
        left_layout.addWidget(subtitle)

        left_layout.addStretch()

        # 特性列表
        features = [
            "✓  千人千面工作台",
            "✓  流程化入住办理",
            "✓  经营数据可视化",
            "✓  操作日志与夜审",
        ]
        for f in features:
            fl = QLabel(f)
            fl.setFont(QFont(*FONTS["body"]))
            fl.setStyleSheet("color: rgba(255,255,255,0.75); padding: 4px 0;")
            left_layout.addWidget(fl)

        left_layout.addStretch()

        # 底部版权
        copyright_label = QLabel("© 2026 iHome PMS v3.0")
        copyright_label.setFont(QFont(*FONTS["caption"]))
        copyright_label.setStyleSheet("color: rgba(255,255,255,0.5);")
        left_layout.addWidget(copyright_label)

        main_layout.addWidget(left_panel)

        # ═══ 右侧登录表单区 ═══
        right_panel = QFrame()
        right_panel.setObjectName("loginRightPanel")
        right_panel.setStyleSheet("""
            QFrame#loginRightPanel {
                background: white;
                border: none;
            }
            QFrame#loginRightPanel QLabel {
                background: transparent;
                border: none;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(44, 36, 44, 36)
        right_layout.setSpacing(0)

        # 欢迎标题
        welcome = QLabel("欢迎登录")
        welcome.setFont(QFont(*FONTS["h1"]))
        welcome.setStyleSheet("color: #0f172a;")
        right_layout.addWidget(welcome)
        right_layout.addSpacing(8)

        tip = QLabel("请输入您的账号信息以继续")
        tip.setFont(QFont(*FONTS["body"]))
        tip.setStyleSheet("color: #94a3b8;")
        right_layout.addWidget(tip)
        right_layout.addSpacing(20)

        # 用户名
        user_label = QLabel("用户名")
        user_label.setFont(QFont(*FONTS["body_sm"]))
        user_label.setStyleSheet(f"color: {COLORS['text_secondary']}; margin-bottom: 6px;")
        right_layout.addWidget(user_label)
        
        self.username = QLineEdit()
        self.username.setPlaceholderText("请输入用户名")
        self.username.setMinimumHeight(36)
        self.username.setFont(QFont(*FONTS["body"]))
        self.username.returnPressed.connect(self._do_login)
        right_layout.addWidget(self.username)
        right_layout.addSpacing(14)

        # 密码
        pwd_label = QLabel("密码")
        pwd_label.setFont(QFont(*FONTS["body_sm"]))
        pwd_label.setStyleSheet(f"color: {COLORS['text_secondary']}; margin-bottom: 6px;")
        right_layout.addWidget(pwd_label)
        
        self.password = QLineEdit()
        self.password.setPlaceholderText("请输入密码")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setMinimumHeight(36)
        self.password.setFont(QFont(*FONTS["body"]))
        self.password.returnPressed.connect(self._do_login)
        right_layout.addWidget(self.password)
        right_layout.addSpacing(10)

        # 默认账号提示
        tip2 = QLabel("默认账号: admin / admin123")
        tip2.setFont(QFont(*FONTS["caption"]))
        tip2.setStyleSheet("color: #94a3b8;")
        right_layout.addWidget(tip2)
        right_layout.addSpacing(20)

        # 登录按钮
        login_btn = QPushButton("登  录")
        login_btn.setMinimumHeight(38)
        login_btn.setProperty("variant", "primary")
        login_btn.setProperty("size", "large")
        login_btn.setFont(QFont(*FONTS["body_b"]))
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.clicked.connect(self._do_login)
        right_layout.addWidget(login_btn)

        right_layout.addStretch()

        main_layout.addWidget(right_panel, 1)

        root.addLayout(main_layout, 1)
        self.setStyleSheet(root_widget_style)
        self.setLayout(root)

        # 设置默认值（方便演示）
        self.username.setText("admin")
        self.password.setText("admin123")

    def _build_window_title_bar(self):
        bar = QFrame()
        bar.setObjectName("loginTitleBar")
        bar.setFixedHeight(42)
        bar.setStyleSheet(f"""
            QFrame#loginTitleBar {{
                background: {COLORS['surface']};
                border: none;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QFrame#loginTitleBar QLabel {{
                background: transparent;
                border: none;
            }}
            QPushButton#loginWindowButton {{
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
            QPushButton#loginWindowButton:hover {{
                background: {COLORS['primary_light']};
                color: {COLORS['primary']};
            }}
            QPushButton#loginCloseButton {{
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
            QPushButton#loginCloseButton:hover {{
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
        title = QLabel(f"{APP_NAME} 登录")
        title.setFont(QFont(*FONTS["caption_b"]))
        title.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(title)
        layout.addStretch()

        min_btn = QPushButton("−")
        min_btn.setObjectName("loginWindowButton")
        min_btn.setFont(QFont("Segoe UI", 16))
        min_btn.setFocusPolicy(Qt.NoFocus)
        min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(min_btn)

        close_btn = QPushButton("×")
        close_btn.setObjectName("loginCloseButton")
        close_btn.setFont(QFont("Segoe UI", 18))
        close_btn.setFocusPolicy(Qt.NoFocus)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        bar.mousePressEvent = self._title_mouse_press
        bar.mouseMoveEvent = self._title_mouse_move
        bar.mouseReleaseEvent = self._title_mouse_release
        return bar

    def _title_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def _title_mouse_move(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def _title_mouse_release(self, event):
        self._drag_pos = None
        event.accept()

    def _do_login(self):
        u = self.username.text().strip()
        p = self.password.text()
        if not u or not p:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return

        s = Session()
        try:
            user = s.query(User).filter(User.username == u, User.is_active == True).first()
            if not user:
                QMessageBox.warning(self, "登录失败", "用户不存在或已禁用")
                return

            pwd_hash = hashlib.sha256(p.encode()).hexdigest()
            if user.password_hash != pwd_hash:
                QMessageBox.warning(self, "登录失败", "密码错误")
                return

            user_info = {
                "id": user.id,
                "username": user.username,
                "real_name": user.real_name or user.username,
                "role": user.role,
            }
            self.login_success.emit(user_info)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"登录异常: {str(e)}")
        finally:
            s.close()
