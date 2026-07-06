# -*- coding: utf-8 -*-
"""v3.0 房态管理 —— 卡片式房态图"""
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QGridLayout, QFrame, QComboBox,
                              QMenu, QAction, QMessageBox, QSizePolicy,
                              QScrollArea, QDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from src.utils.db import Session
from src.models.room import Room
from src.models.room_type import RoomType
from src.resources.theme import COLORS, SPACING, FONTS
from src.utils.event_bus import notify_data_changed


# 房态颜色映射
ROOM_STATUS_COLORS = {
    "空闲": COLORS["room_vacant"],
    "已入住": COLORS["room_occupied"],
    "已预订": COLORS["room_reserved"],
    "脏房": COLORS["room_dirty"],
    "维修": COLORS["room_maintenance"],
}


class RoomStatusView(QWidget):
    def __init__(self):
        super().__init__()
        self._rooms = []
        self._room_types = {}
        self._init_ui()
        self._load()

    def _init_ui(self):
        l = QVBoxLayout()
        l.setContentsMargins(18, 16, 18, 18)
        l.setSpacing(12)

        # 顶部工具栏
        top = QHBoxLayout()
        
        title = QLabel("房态管理")
        title.setFont(QFont(*FONTS["h1"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        top.addWidget(title)
        top.addStretch()

        # 房态筛选
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态")
        for status in ROOM_STATUS_COLORS.keys():
            self.status_filter.addItem(status)
        self.status_filter.setMinimumWidth(104)
        self.status_filter.currentTextChanged.connect(self._render)
        top.addWidget(QLabel("状态:"))
        top.addWidget(self.status_filter)

        # 房型筛选
        self.type_filter = QComboBox()
        self.type_filter.addItem("全部房型")
        self.type_filter.setMinimumWidth(104)
        self.type_filter.currentTextChanged.connect(self._render)
        top.addWidget(QLabel("房型:"))
        top.addWidget(self.type_filter)

        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setObjectName("roomRefreshButton")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton#roomRefreshButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#roomRefreshButton:hover {{
                border-color: {COLORS['primary']};
                color: {COLORS['primary']};
            }}
        """)
        refresh_btn.clicked.connect(self._load)
        top.addWidget(refresh_btn)

        l.addLayout(top)

        # 统计栏
        self.stats_bar = self._build_stats_bar()
        l.addWidget(self.stats_bar)

        # 房态卡片区域（滚动）
        from PyQt5.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(14)
        scroll.setWidget(self.content)
        l.addWidget(scroll, 1)

        self.setLayout(l)

    def _build_stats_bar(self):
        """统计栏"""
        bar = QFrame()
        bar.setObjectName("roomStatsBar")
        bar.setStyleSheet(f"""
            QFrame#roomStatsBar {{
                background: {COLORS['surface']};
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#roomStatsBar QLabel {{
                background: transparent;
                border: none;
            }}
            QFrame#roomStatsBar QLabel#roomStatDot {{
                border: none;
            }}
            QWidget#roomStatItem {{
                background: transparent;
                border: none;
            }}
            QWidget#roomStatItem QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(14, 9, 14, 9)
        bar_layout.setSpacing(14)

        self.stats_labels = {}
        for status, color in ROOM_STATUS_COLORS.items():
            item = QWidget()
            item.setObjectName("roomStatItem")
            item.setAutoFillBackground(False)
            item.setAttribute(Qt.WA_StyledBackground, False)
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(6)
            
            dot = QLabel()
            dot.setObjectName("roomStatDot")
            dot.setAutoFillBackground(False)
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(f"background: {color}; border-radius: 5px;")
            item_layout.addWidget(dot)
            
            count = QLabel()
            count.setAutoFillBackground(False)
            count.setAttribute(Qt.WA_StyledBackground, False)
            count.setTextFormat(Qt.RichText)
            count.setFont(QFont(*FONTS["body_sm"]))
            count.setStyleSheet(f"""
                background: transparent;
                border: none;
                color: {COLORS['text_secondary']};
            """)
            item_layout.addWidget(count)
            
            bar_layout.addWidget(item)
            self.stats_labels[status] = count

        bar_layout.addStretch()
        return bar

    def _load(self):
        s = Session()
        try:
            self._rooms = s.query(Room).order_by(Room.floor, Room.room_number).all()
            room_types = s.query(RoomType).all()
            self._room_types = {rt.id: rt.name for rt in room_types}
            
            # 更新房型筛选
            current = self.type_filter.currentText()
            self.type_filter.blockSignals(True)
            self.type_filter.clear()
            self.type_filter.addItem("全部房型")
            for rt_name in self._room_types.values():
                self.type_filter.addItem(rt_name)
            # 恢复选中
            idx = self.type_filter.findText(current)
            if idx >= 0:
                self.type_filter.setCurrentIndex(idx)
            self.type_filter.blockSignals(False)
            
        finally:
            s.close()
        self._render()

    def _render(self, *_):
        # 清空
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 筛选
        status_filter = self.status_filter.currentText()
        type_filter = self.type_filter.currentText()
        
        filtered = self._rooms
        if status_filter != "全部状态":
            filtered = [r for r in filtered if r.status == status_filter]
        if type_filter != "全部房型":
            rt_id = None
            for rid, rname in self._room_types.items():
                if rname == type_filter:
                    rt_id = rid
                    break
            if rt_id:
                filtered = [r for r in filtered if r.room_type_id == rt_id]

        # 更新统计
        for status in ROOM_STATUS_COLORS.keys():
            count = sum(1 for r in self._rooms if r.status == status)
            color = ROOM_STATUS_COLORS[status]
            self.stats_labels[status].setText(
                f"<span style='color:{COLORS['text_secondary']}; background:transparent;'>{status}</span>"
                f" <span style='color:{color}; font-weight:700; background:transparent;'>{count}</span>"
            )

        # 按楼层分组
        floors = {}
        for r in filtered:
            floor = r.floor or 0
            if floor not in floors:
                floors[floor] = []
            floors[floor].append(r)

        # 渲染每个楼层
        for floor in sorted(floors.keys()):
            floor_widget = self._build_floor_section(floor, floors[floor])
            self.content_layout.addWidget(floor_widget)
        self.content_layout.addStretch()

        if not filtered:
            empty = QLabel("暂无符合条件的房间")
            empty.setFont(QFont(*FONTS["body"]))
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 60px 0;")
            self.content_layout.addWidget(empty)

    def _build_floor_section(self, floor, rooms):
        """楼层分组"""
        section = QWidget()
        section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 楼层标题
        title_row = QHBoxLayout()
        title = QLabel(f"{floor} 楼")
        title.setFont(QFont(*FONTS["h3"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_row.addWidget(title)
        
        count = QLabel(f"共 {len(rooms)} 间")
        count.setFont(QFont(*FONTS["body_sm"]))
        count.setStyleSheet(f"color: {COLORS['text_muted']};")
        title_row.addWidget(count)
        title_row.addStretch()
        
        layout.addLayout(title_row)

        # 房间卡片网格
        grid = QGridLayout()
        grid.setSpacing(10)
        
        for i, room in enumerate(rooms):
            card = self._build_room_card(room)
            grid.addWidget(card, i // 6, i % 6)
        
        layout.addLayout(grid)

        return section

    def _build_room_card(self, room):
        """房间卡片"""
        color = ROOM_STATUS_COLORS.get(room.status, "#999")
        rt_name = self._room_types.get(room.room_type_id, "")

        card = QFrame()
        card.setObjectName("roomCard")
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame#roomCard {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-left: 4px solid {color};
                border-radius: 8px;
            }}
            QFrame#roomCard:hover {{
                background: {COLORS['surface_hover']};
                border-color: {color};
            }}
            QFrame#roomCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        card.setMinimumHeight(74)
        card.setMinimumWidth(150)
        card.setMaximumWidth(220)
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(3)

        # 房号 + 状态
        top_row = QHBoxLayout()
        top_row.setSpacing(4)
        
        room_no = QLabel(room.room_number)
        room_no.setFont(QFont("Segoe UI", 16, QFont.Bold))
        room_no.setStyleSheet(f"color: {COLORS['text_primary']};")
        top_row.addWidget(room_no)
        top_row.addStretch()
        
        status_tag = QLabel(room.status)
        status_tag.setFont(QFont(*FONTS["caption_b"]))
        status_tag.setAlignment(Qt.AlignCenter)
        status_tag.setStyleSheet(f"""
            background: {color}15;
            color: {color};
            border-radius: 5px;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: bold;
        """)
        top_row.addWidget(status_tag)
        
        layout.addLayout(top_row)

        # 房型 + 价格
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(4)
        
        rt_label = QLabel(rt_name)
        rt_label.setFont(QFont(*FONTS["body_sm"]))
        rt_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        bottom_row.addWidget(rt_label)
        bottom_row.addStretch()
        
        price = QLabel(f"¥{int(room.price)}")
        price.setFont(QFont("Segoe UI", 12, QFont.Bold))
        price.setStyleSheet(f"color: {COLORS['accent']};")
        bottom_row.addWidget(price)
        
        layout.addLayout(bottom_row)

        # 右键菜单
        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(lambda pos, c=card, r=room: self._show_menu(c, pos, r))
        
        # 点击事件
        card.mousePressEvent = lambda e, r=room: self._on_room_click(e, r)

        return card

    def _on_room_click(self, event, room):
        if event.button() == Qt.LeftButton:
            self._show_room_detail(room)

    def _show_room_detail(self, room):
        dlg = QDialog(self)
        dlg.setWindowTitle("房间详情")
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
            QLabel#roomDetailIcon {{
                background: {COLORS['info']};
                color: white;
                border-radius: 28px;
                font-size: 28px;
                font-weight: bold;
            }}
            QPushButton#roomDetailOk {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 8px 22px;
                font-weight: bold;
                min-width: 88px;
            }}
            QPushButton#roomDetailOk:hover {{
                background: {COLORS['primary_hover']};
            }}
        """)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(16)

        body = QHBoxLayout()
        body.setSpacing(18)

        icon = QLabel("i")
        icon.setObjectName("roomDetailIcon")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(56, 56)
        body.addWidget(icon, 0, Qt.AlignTop)

        info = QVBoxLayout()
        info.setSpacing(8)
        rows = [
            ("房号", room.room_number),
            ("房型", self._room_types.get(room.room_type_id, "-")),
            ("楼层", f"{room.floor}楼"),
            ("状态", room.status),
            ("价格", f"¥{int(room.price)}/晚"),
            ("备注", room.description or "无"),
        ]
        for name, value in rows:
            row = QLabel(f"{name}: {value}")
            row.setFont(QFont(*FONTS["body"]))
            info.addWidget(row)
        body.addLayout(info, 1)
        root.addLayout(body)

        buttons = QHBoxLayout()
        buttons.addStretch()
        ok = QPushButton("确定")
        ok.setObjectName("roomDetailOk")
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(dlg.accept)
        buttons.addWidget(ok)
        root.addLayout(buttons)

        dlg.exec_()

    def _show_menu(self, card, pos, room):
        menu = QMenu(self)
        
        # 状态变更
        status_menu = menu.addMenu("变更状态")
        for status in ["空闲", "脏房", "维修"]:
            if room.status != status:
                action = QAction(status, self)
                action.triggered.connect(lambda _, s=status, r=room: self._change_status(r, s))
                status_menu.addAction(action)
        
        menu.addSeparator()
        
        # 刷新
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self._load)
        menu.addAction(refresh_action)

        # 显示菜单
        menu.exec_(card.mapToGlobal(pos))

    def _change_status(self, room, new_status):
        from src.services.pms_service import change_room_status, BusinessError
        s = Session()
        try:
            change_room_status(s, room.id, new_status)
            try:
                from src.services.audit_service import log_operation
                user = getattr(self, "current_user", {}) or {}
                log_operation(s, user.get("id"), "修改房态",
                              f"房间 {room.room_number} 修改为 {new_status}")
            except Exception:
                pass
            s.commit()
            notify_data_changed("rooms")
            self._load()
            QMessageBox.information(self, "成功", f"房态已更新为：{new_status}")
        except BusinessError as e:
            s.rollback()
            QMessageBox.warning(self, "操作失败", str(e))
        except Exception as e:
            s.rollback()
            QMessageBox.warning(self, "错误", str(e))
        finally:
            s.close()
