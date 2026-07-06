# -*- coding: utf-8 -*-
"""v3.0 智能可视化工作台。"""
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QPushButton, QSizePolicy
)

from src.resources.theme import COLORS, FONTS
from src.services.dashboard_service import build_role_workbench
from src.utils.db import Session


class MiniBarChart(QWidget):
    def __init__(self, color=COLORS["primary"], parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.data = []
        self.setMinimumHeight(150)

    def set_data(self, data):
        self.data = data or []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(14, 8, -14, -30)
        values = [max(float(x.get("value", 0)), 0) for x in self.data]
        max_v = max(values) if values else 1
        max_v = max(max_v, 1)
        bar_w = rect.width() / max(len(values), 1) * 0.56
        gap = rect.width() / max(len(values), 1)
        painter.setPen(Qt.NoPen)
        for i, item in enumerate(self.data):
            v = max(float(item.get("value", 0)), 0)
            h = rect.height() * (v / max_v)
            x = rect.left() + i * gap + (gap - bar_w) / 2
            y = rect.bottom() - h
            painter.setBrush(self.color)
            painter.drawRoundedRect(QRectF(x, y, bar_w, h), 4, 4)

        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        painter.drawLine(int(rect.left()), int(rect.bottom()), int(rect.right()), int(rect.bottom()))
        for i, item in enumerate(self.data):
            x = rect.left() + i * gap + (gap - bar_w) / 2
            painter.setPen(QColor(COLORS["text_muted"]))
            painter.setFont(QFont(*FONTS["caption"]))
            painter.drawText(QRectF(x - 12, rect.bottom() + 8, bar_w + 24, 20),
                             Qt.AlignCenter, item.get("date", ""))


class MiniDonutChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {}
        self.palette = [COLORS["primary"], COLORS["success"], COLORS["accent"],
                        COLORS["info"], COLORS["room_dirty"], "#5A496F"]
        self.setMinimumHeight(150)

    def set_data(self, data):
        self.data = data or {}
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        size = min(104, max(76, h - 38))
        chart_x = max(18, int(w * 0.12))
        chart_y = int((h - size) / 2)
        rect = QRectF(chart_x, chart_y, size, size)
        values = [(label, max(float(value), 0)) for label, value in self.data.items() if float(value or 0) > 0]
        total = sum(value for _, value in values) or 1
        start = 90 * 16
        for idx, (_, value) in enumerate(values):
            span = -int((value / total) * 360 * 16)
            painter.setPen(QPen(QColor(self.palette[idx % len(self.palette)]), 16))
            painter.drawArc(rect, start, span)
            start += span

        inner = rect.adjusted(20, 20, -20, -20)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(COLORS["surface"]))
        painter.drawEllipse(inner)

        painter.setPen(QColor(COLORS["text_muted"]))
        painter.setFont(QFont(*FONTS["caption_b"]))
        painter.drawText(rect, Qt.AlignCenter, "占比")

        painter.setPen(QColor(COLORS["text_secondary"]))
        painter.setFont(QFont(*FONTS["body_sm"]))
        x = chart_x + size + 26
        y = max(20, chart_y + 6)
        legend_w = max(90, w - x - 10)
        for idx, (label, value) in enumerate(values[:5]):
            painter.setBrush(QColor(self.palette[idx % len(self.palette)]))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(x, y + 6, 8, 8)
            painter.setPen(QColor(COLORS["text_secondary"]))
            painter.drawText(QRectF(x + 16, y, legend_w, 22), Qt.AlignLeft | Qt.AlignVCenter,
                             f"{label} {value:g}")
            y += 24


class DashboardView(QWidget):
    def __init__(self, user_info=None, navigate_callback=None):
        super().__init__()
        self.user_info = user_info or {"role": "前台", "real_name": ""}
        self.navigate_callback = navigate_callback
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        self.setObjectName("dashboardV3")
        self.setStyleSheet(f"""
            QWidget#dashboardV3 {{ background: {COLORS['bg']}; }}
            QLabel {{ background: transparent; border: none; }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 18)
        root.setSpacing(12)

        top = QHBoxLayout()
        self.title = QLabel("智能经营工作台")
        self.title.setFont(QFont(*FONTS["h1"]))
        top.addWidget(self.title)
        self.role_badge = QLabel("")
        self.role_badge.setFont(QFont(*FONTS["caption_b"]))
        self.role_badge.setStyleSheet(f"""
            color: {COLORS['primary']};
            background: {COLORS['primary_light']};
            border-radius: 10px;
            padding: 4px 10px;
        """)
        top.addWidget(self.role_badge)
        top.addStretch()
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.setObjectName("dashboardRefreshButton")
        self.refresh_btn.setFixedHeight(34)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setStyleSheet(self._primary_button_qss())
        self.refresh_btn.clicked.connect(self._load_data)
        top.addWidget(self.refresh_btn)
        root.addLayout(top)

        self.insight_row = QHBoxLayout()
        self.insight_row.setSpacing(10)
        root.addLayout(self.insight_row)

        metric_grid = QGridLayout()
        metric_grid.setHorizontalSpacing(10)
        metric_grid.setVerticalSpacing(10)
        self.metric_cards = []
        for idx in range(6):
            card = self._metric_card("-", COLORS["primary"])
            self.metric_cards.append(card)
            metric_grid.addWidget(card, idx // 3, idx % 3)
        root.addLayout(metric_grid)

        self.lower_grid = QGridLayout()
        self.lower_grid.setHorizontalSpacing(12)
        self.lower_grid.setVerticalSpacing(12)
        self.lower_grid.setColumnStretch(0, 3)
        self.lower_grid.setColumnStretch(1, 2)
        self.lower_grid.setColumnStretch(2, 2)

        action_panel, action_layout = self._panel("智能行动队列")
        self.action_panel = action_panel
        self.action_panel_title = action_panel.title_label
        self.action_plan_box = QVBoxLayout()
        self.action_plan_box.setSpacing(8)
        action_layout.addLayout(self.action_plan_box)
        action_layout.addStretch()
        self.lower_grid.addWidget(action_panel, 0, 0)

        summary_panel, summary_layout = self._panel("运营摘要")
        self.summary_panel = summary_panel
        self.summary_panel_title = summary_panel.title_label
        self.todo_box = QVBoxLayout()
        self.todo_box.setSpacing(8)
        summary_layout.addLayout(self.todo_box)
        summary_layout.addStretch()
        self.lower_grid.addWidget(summary_panel, 0, 1)

        donut_panel, donut_layout = self._panel("结构分布")
        self.primary_chart_panel = donut_panel
        self.primary_chart_title = donut_panel.title_label
        self.status_chart = MiniDonutChart()
        donut_layout.addWidget(self.status_chart)
        self.lower_grid.addWidget(donut_panel, 0, 2)

        order_panel, order_layout = self._panel("最近订单")
        self.order_panel = order_panel
        self.recent_panel_title = order_panel.title_label
        self.order_list = QVBoxLayout()
        self.order_list.setSpacing(6)
        order_layout.addLayout(self.order_list)
        order_layout.addStretch()

        quick_panel, quick_layout = self._panel("快捷处理")
        self.quick_panel = quick_panel
        self.quick_panel.setProperty("wideManagementPanel", True)
        self.quick_panel_title = quick_panel.title_label
        quick_panel.setMinimumHeight(220)
        quick_panel.setMaximumHeight(240)
        self.action_box = QHBoxLayout()
        self.action_box.setSpacing(8)
        quick_layout.addLayout(self.action_box)
        quick_layout.addStretch()

        trend_panel, trend_layout = self._panel("经营趋势")
        self.trend_panel = trend_panel
        self.trend_panel.setProperty("wideManagementPanel", True)
        self.trend_panel.setMinimumHeight(220)
        self.trend_panel.setMaximumHeight(240)
        self.trend_panel_title = trend_panel.title_label
        self.trend_chart = MiniBarChart(COLORS["primary"])
        trend_layout.addWidget(self.trend_chart)

        room_type_panel, room_type_layout = self._panel("房型收入")
        self.secondary_chart_panel = room_type_panel
        self.secondary_chart_panel.setProperty("wideManagementPanel", True)
        self.secondary_chart_panel.setMinimumHeight(220)
        self.secondary_chart_panel.setMaximumHeight(240)
        self.secondary_chart_title = room_type_panel.title_label
        self.room_type_chart = MiniDonutChart()
        room_type_layout.addWidget(self.room_type_chart)
        self.secondary_focus_box = QVBoxLayout()
        self.secondary_focus_box.setSpacing(8)
        room_type_layout.addLayout(self.secondary_focus_box)
        room_type_layout.addStretch()
        self.lower_grid.addWidget(order_panel, 1, 0)
        self.lower_grid.addWidget(quick_panel, 1, 1)
        self.lower_grid.addWidget(room_type_panel, 1, 2)
        self.trend_panel.hide()
        root.addLayout(self.lower_grid, 1)

    def _metric_card(self, label, color):
        card = QFrame()
        card.setObjectName("metricCard")
        card.setMinimumHeight(78)
        card.setStyleSheet(f"""
            QFrame#metricCard {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-left: 4px solid {color};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 8, 14, 8)
        value = QLabel("0")
        value.setFont(QFont(*FONTS["h2"]))
        value.setStyleSheet(f"color: {color};")
        layout.addWidget(value)
        name = QLabel(label)
        name.setFont(QFont(*FONTS["caption"]))
        name.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(name)
        card.value_label = value
        card.name_label = name
        return card

    def _panel(self, title):
        panel = QFrame()
        panel.setObjectName("workbenchPanel")
        panel.setStyleSheet(f"""
            QFrame#workbenchPanel {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        t = QLabel(title)
        t.setFont(QFont(*FONTS["h3"]))
        layout.addWidget(t)
        panel.title_label = t
        return panel, layout

    def _primary_button_qss(self):
        return f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 7px 12px;
                font-weight: bold;
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
        """

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _load_data(self):
        s = Session()
        try:
            self.data = build_role_workbench(s, self.user_info)
        finally:
            s.close()
        self._render()

    def _render(self):
        role = self.data["role"]
        workspace = self.data.get("workspace", {})
        self._workspace_kind = workspace.get("kind")
        self.title.setText({
            "管理员": "智能经营工作台",
            "前台": "前台接待工作台",
            "财务": "财务经营工作台",
            "客房": "客房房态工作台",
        }.get(role, "智能工作台"))
        self.role_badge.setText(f"{role}视角")
        for idx, card in enumerate(self.metric_cards):
            if idx >= len(self.data.get("metric_cards", [])):
                card.hide()
                continue
            item = self.data["metric_cards"][idx]
            color = _metric_color(item.get("color"))
            card.show()
            card.name_label.setText(item["label"])
            card.value_label.setText(_format_metric_value(item["value"], item.get("format")))
            card.value_label.setStyleSheet(f"color: {color};")
            card.setStyleSheet(f"""
                QFrame#metricCard {{
                    background: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-left: 4px solid {color};
                    border-radius: 8px;
                }}
            """)

        self._render_insights(self.data["insights"])
        self.action_panel_title.setText(workspace.get("action_title", "智能行动队列"))
        self.summary_panel_title.setText(workspace.get("summary_title", "运营摘要"))
        self.recent_panel_title.setText(workspace.get("recent_title", "最近订单"))
        self.quick_panel_title.setText(workspace.get("quick_title", "快捷处理"))
        self.primary_chart_title.setText(workspace.get("primary_chart_title") or "结构分布")
        self._arrange_lower_panels(workspace.get("kind"))
        self._render_action_plan(self.data.get("action_plan", []))
        self._render_todos(self.data["todos"])
        self._render_actions(self.data["quick_actions"])
        primary_key = workspace.get("primary_chart_key", "order_status")
        self.status_chart.set_data(self.data["charts"].get(primary_key, {}))
        if workspace.get("kind") == "management":
            self.trend_panel.show()
            self.trend_panel_title.setText("近7日收入趋势")
            self.trend_chart.set_data(self.data["charts"].get("revenue_7d", []))
        else:
            self.trend_panel.hide()
        secondary_key = workspace.get("secondary_chart_key")
        if secondary_key:
            self.secondary_chart_panel.show()
            self.secondary_chart_title.setText(workspace.get("secondary_chart_title") or "")
            self.room_type_chart.show()
            self._render_focus_items([])
            self.room_type_chart.set_data(self.data["charts"].get(secondary_key, {}))
        else:
            self.secondary_chart_panel.show()
            self.secondary_chart_title.setText(workspace.get("secondary_panel_title") or "下一步处理")
            self.room_type_chart.hide()
            self._render_focus_items(workspace.get("focus_items", []))
        self._render_orders(self.data["recent_orders"])

    def _arrange_lower_panels(self, kind):
        for panel in (self.order_panel, self.quick_panel, self.trend_panel, self.secondary_chart_panel):
            self.lower_grid.removeWidget(panel)
            panel.hide()

        if kind == "management":
            for panel in (self.quick_panel, self.trend_panel, self.secondary_chart_panel):
                panel.setMinimumHeight(220)
                panel.setMaximumHeight(240)
            self.lower_grid.addWidget(self.quick_panel, 1, 0)
            self.lower_grid.addWidget(self.trend_panel, 1, 1)
            self.lower_grid.addWidget(self.secondary_chart_panel, 1, 2)
            self.quick_panel.show()
            self.trend_panel.show()
            self.secondary_chart_panel.show()
            return

        for panel in (self.quick_panel, self.secondary_chart_panel):
            panel.setMinimumHeight(0)
            panel.setMaximumHeight(16777215)
        self.lower_grid.addWidget(self.order_panel, 1, 0)
        self.lower_grid.addWidget(self.quick_panel, 1, 1)
        self.lower_grid.addWidget(self.secondary_chart_panel, 1, 2)
        self.order_panel.show()
        self.quick_panel.show()
        self.secondary_chart_panel.show()

    def _render_insights(self, insights):
        self._clear_layout(self.insight_row)
        colors = {
            "success": COLORS["success_light"],
            "info": COLORS["info_light"],
            "warning": COLORS["warning_light"],
            "danger": COLORS["danger_light"],
        }
        text_colors = {
            "success": COLORS["success"],
            "info": COLORS["info"],
            "warning": COLORS["warning"],
            "danger": COLORS["danger"],
        }
        for item in insights[:4]:
            label = QLabel(item["text"])
            label.setWordWrap(True)
            level = item.get("level", "info")
            label.setFont(QFont(*FONTS["body_sm"]))
            label.setStyleSheet(f"""
                background: {colors.get(level, COLORS['info_light'])};
                color: {text_colors.get(level, COLORS['info'])};
                border-radius: 8px;
                padding: 8px 10px;
            """)
            self.insight_row.addWidget(label, 1)

    def _render_action_plan(self, plan):
        self._clear_layout(self.action_plan_box)
        level_style = {
            "high": (COLORS["danger"], COLORS["danger_light"], "优先"),
            "medium": (COLORS["warning"], COLORS["warning_light"], "跟进"),
            "low": (COLORS["info"], COLORS["info_light"], "关注"),
            "normal": (COLORS["success"], COLORS["success_light"], "正常"),
        }
        for item in plan[:4]:
            color, bg, tag = level_style.get(item.get("level"), level_style["normal"])
            card = QFrame()
            card.setObjectName("actionPlanCard")
            card.setMinimumHeight(70)
            card.setCursor(Qt.PointingHandCursor)
            card.setStyleSheet(f"""
                QFrame#actionPlanCard {{
                    background: {bg};
                    border: 1px solid {color};
                    border-radius: 8px;
                }}
                QFrame#actionPlanCard QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
            layout = QVBoxLayout(card)
            layout.setContentsMargins(12, 9, 12, 9)
            layout.setSpacing(5)
            head = QHBoxLayout()
            badge = QLabel(tag)
            badge.setFont(QFont(*FONTS["caption_b"]))
            badge.setStyleSheet(f"color: white; background: {color}; border-radius: 6px; padding: 2px 6px;")
            head.addWidget(badge)
            title = QLabel(item["title"])
            title.setFont(QFont(*FONTS["body_b"]))
            title.setStyleSheet(f"color: {COLORS['text_primary']};")
            head.addWidget(title, 1)
            layout.addLayout(head)
            detail = QLabel(item["detail"])
            detail.setWordWrap(True)
            detail.setFont(QFont(*FONTS["caption"]))
            detail.setStyleSheet(f"color: {COLORS['text_secondary']};")
            layout.addWidget(detail)
            card.mousePressEvent = lambda _, target=item.get("target", "dashboard"): self._navigate(target)
            self.action_plan_box.addWidget(card)

    def _render_todos(self, todos):
        self._clear_layout(self.todo_box)
        rows = [
            ("今日预抵", todos["arrivals"], COLORS["accent"]),
            ("今日待退", todos["departures"], COLORS["warning"]),
            ("当前在住", todos["in_house"], COLORS["info"]),
            ("脏房待清洁", todos["dirty_rooms"], COLORS["room_dirty"]),
            ("未结清账务", todos["unsettled"], COLORS["danger"]),
        ]
        for name, value, color in rows:
            box = QFrame()
            box.setObjectName("summaryRow")
            box.setStyleSheet(f"""
                QFrame#summaryRow {{
                    background: {COLORS['surface']};
                    border: none;
                    border-bottom: 1px solid {COLORS['border_light']};
                    border-radius: 0;
                }}
                QFrame#summaryRow QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
            row = QHBoxLayout(box)
            row.setContentsMargins(2, 6, 2, 6)
            l = QLabel(name)
            l.setFont(QFont(*FONTS["body_sm"]))
            l.setStyleSheet(f"color: {COLORS['text_secondary']};")
            row.addWidget(l)
            row.addStretch()
            v = QLabel(str(value))
            v.setFont(QFont(*FONTS["body_b"]))
            v.setStyleSheet(f"color: {color};")
            row.addWidget(v)
            self.todo_box.addWidget(box)

    def _render_actions(self, actions):
        self._clear_layout(self.action_box)
        if getattr(self, "_workspace_kind", "") == "management":
            container = QFrame()
            container.setStyleSheet("background: transparent; border: none;")
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
            for action in actions:
                btn = QPushButton(action["label"])
                btn.setMinimumHeight(38)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet(self._primary_button_qss())
                btn.clicked.connect(lambda _, target=action["target"]: self._navigate(target))
                layout.addWidget(btn)
            layout.addStretch()
            self.action_box.addWidget(container)
            return
        for action in actions:
            btn = QPushButton(action["label"])
            btn.setMinimumHeight(34)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._primary_button_qss())
            btn.clicked.connect(lambda _, target=action["target"]: self._navigate(target))
            self.action_box.addWidget(btn)

    def _render_focus_items(self, items):
        self._clear_layout(self.secondary_focus_box)
        for index, text in enumerate(items[:4], 1):
            row = QFrame()
            row.setObjectName("focusRow")
            row.setStyleSheet(f"""
                QFrame#focusRow {{
                    background: {COLORS['surface']};
                    border: 1px solid {COLORS['border_light']};
                    border-radius: 7px;
                }}
                QFrame#focusRow QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
            layout = QHBoxLayout(row)
            layout.setContentsMargins(10, 8, 10, 8)
            badge = QLabel(str(index))
            badge.setFixedSize(22, 22)
            badge.setAlignment(Qt.AlignCenter)
            badge.setFont(QFont(*FONTS["caption_b"]))
            badge.setStyleSheet(f"""
                color: white;
                background: {COLORS['primary']};
                border-radius: 11px;
            """)
            layout.addWidget(badge)
            label = QLabel(text)
            label.setWordWrap(True)
            label.setFont(QFont(*FONTS["body_sm"]))
            label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            layout.addWidget(label, 1)
            self.secondary_focus_box.addWidget(row)

    def _navigate(self, target):
        if self.navigate_callback:
            self.navigate_callback(target)

    def _render_orders(self, orders):
        self._clear_layout(self.order_list)
        for order in orders[:5]:
            row = QFrame()
            row.setObjectName("orderListRow")
            row.setStyleSheet(f"""
                QFrame#orderListRow {{
                    background: {COLORS['surface']};
                    border: 1px solid {COLORS['border_light']};
                    border-radius: 7px;
                }}
                QFrame#orderListRow:hover {{
                    background: {COLORS['surface_hover']};
                    border-color: {COLORS['border']};
                }}
                QFrame#orderListRow QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 7, 12, 7)
            layout.setSpacing(12)

            order_no = QLabel(_short_text(order["order_no"], 16))
            order_no.setFont(QFont(*FONTS["caption_b"]))
            order_no.setStyleSheet(f"color: {COLORS['text_primary']};")
            layout.addWidget(order_no, 2)

            guest = QLabel(order["customer"])
            guest.setFont(QFont(*FONTS["body_sm"]))
            guest.setStyleSheet(f"color: {COLORS['text_secondary']};")
            layout.addWidget(guest, 1)

            room = QLabel(order["room_type"])
            room.setFont(QFont(*FONTS["body_sm"]))
            room.setStyleSheet(f"color: {COLORS['text_muted']};")
            layout.addWidget(room, 1)

            status = QLabel(order["status"])
            status.setAlignment(Qt.AlignCenter)
            status.setFixedWidth(64)
            status.setFont(QFont(*FONTS["caption_b"]))
            color = _status_color(order["status"])
            status.setStyleSheet(f"""
                color: {color};
                background: {_status_bg(order["status"])};
                border-radius: 6px;
                padding: 3px 6px;
            """)
            layout.addWidget(status)
            self.order_list.addWidget(row)


def _status_color(status):
    return {
        "已入住": COLORS["info"],
        "已确认": COLORS["success"],
        "待确认": COLORS["warning"],
        "已退房": COLORS["text_muted"],
        "已取消": COLORS["danger"],
    }.get(status, COLORS["text_secondary"])


def _status_bg(status):
    return {
        "已入住": COLORS["info_light"],
        "已确认": COLORS["success_light"],
        "待确认": COLORS["warning_light"],
        "已退房": COLORS["bg"],
        "已取消": COLORS["danger_light"],
    }.get(status, COLORS["bg"])


def _metric_color(name):
    return {
        "primary": COLORS["primary"],
        "success": COLORS["success"],
        "accent": COLORS["accent"],
        "warning": COLORS["warning"],
        "danger": COLORS["danger"],
        "info": COLORS["info"],
        "room_dirty": COLORS["room_dirty"],
        "room_maintenance": COLORS["room_maintenance"],
        "purple": "#5A496F",
    }.get(name, COLORS["primary"])


def _format_metric_value(value, fmt):
    value = value or 0
    if fmt == "money":
        return f"¥ {float(value):.0f}"
    if fmt == "percent":
        return f"{float(value):.1f}%"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _short_text(text, max_len):
    text = str(text or "-")
    return text if len(text) <= max_len else text[:max_len - 1] + "…"
