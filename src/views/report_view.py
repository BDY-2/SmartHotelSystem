# -*- coding: utf-8 -*-
"""v3.0 报表中心"""
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QMessageBox, QDateEdit, QFrame,
                              QAbstractItemView)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor
from datetime import date, datetime, time, timedelta
from src.utils.db import DEMO_REPORT_END_DATE, Session
from src.models.order import Order
from src.models.room import Room
from src.models.customer import Customer
from src.models.bill_item import BillItem
from src.resources.theme import COLORS, SPACING, FONTS
from src.services.pms_service import get_report_orders, calculate_report_metrics
from src.services.report_insight_service import build_report_insights
from src.views.dashboard_view import MiniBarChart, MiniDonutChart


class ReportView(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._load()

    def _init_ui(self):
        l = QVBoxLayout()
        l.setContentsMargins(18, 16, 18, 18)
        l.setSpacing(12)

        # 顶部工具栏
        top = QHBoxLayout()
        
        title = QLabel("报表中心")
        title.setFont(QFont(*FONTS["h1"]))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        top.addWidget(title)
        top.addStretch()

        # 日期选择
        top.addWidget(QLabel("从:"))
        demo_to = QDate(DEMO_REPORT_END_DATE.year, DEMO_REPORT_END_DATE.month, DEMO_REPORT_END_DATE.day)
        self.from_d = QDateEdit(demo_to.addDays(-13))
        self.from_d.setCalendarPopup(True)
        self.from_d.setDisplayFormat("yyyy-MM-dd")
        self.from_d.setMinimumHeight(32)
        self.from_d.setFixedWidth(176)
        self._style_date_edit(self.from_d)
        top.addWidget(self.from_d)
        
        top.addWidget(QLabel("到:"))
        self.to_d = QDateEdit(demo_to)
        self.to_d.setCalendarPopup(True)
        self.to_d.setDisplayFormat("yyyy-MM-dd")
        self.to_d.setMinimumHeight(32)
        self.to_d.setFixedWidth(176)
        self._style_date_edit(self.to_d)
        top.addWidget(self.to_d)

        # 查询按钮
        query_btn = QPushButton("🔍 查询")
        query_btn.setObjectName("reportQueryButton")
        query_btn.setMinimumHeight(32)
        query_btn.setMinimumWidth(92)
        query_btn.setCursor(Qt.PointingHandCursor)
        query_btn.setStyleSheet(f"""
            QPushButton#reportQueryButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#reportQueryButton:hover {{
                background: {COLORS['primary_hover']};
            }}
        """)
        query_btn.clicked.connect(self._load)
        top.addWidget(query_btn)

        l.addLayout(top)

        # 核心指标卡片
        cards = QHBoxLayout()
        cards.setSpacing(SPACING["md"])
        
        self.card_rev = self._build_stat_card("总收入", "¥ 0", COLORS["success"])
        cards.addWidget(self.card_rev, 1)
        
        self.card_cnt = self._build_stat_card("订单数", "0", COLORS["info"])
        cards.addWidget(self.card_cnt, 1)
        
        self.card_occ = self._build_stat_card("平均出租率", "0%", COLORS["primary"])
        cards.addWidget(self.card_occ, 1)
        
        self.card_adr = self._build_stat_card("平均房价 (ADR)", "¥ 0", COLORS["accent"])
        cards.addWidget(self.card_adr, 1)
        
        l.addLayout(cards)

        charts = QHBoxLayout()
        charts.setSpacing(SPACING["md"])

        trend_panel, trend_body = self._build_chart_panel("收入趋势")
        self.revenue_chart = MiniBarChart(COLORS["primary"])
        trend_body.addWidget(self.revenue_chart)
        charts.addWidget(trend_panel, 2)

        room_panel, room_body = self._build_chart_panel("房型收入占比")
        self.room_revenue_chart = MiniDonutChart()
        room_body.addWidget(self.room_revenue_chart)
        charts.addWidget(room_panel, 1)

        l.addLayout(charts)

        assistant = QFrame()
        assistant.setObjectName("reportAssistantPanel")
        assistant.setStyleSheet(f"""
            QFrame#reportAssistantPanel {{
                background: {COLORS['primary_light']};
                border: 1px solid {COLORS['primary']};
                border-radius: 8px;
            }}
            QFrame#reportAssistantPanel QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        assistant_layout = QVBoxLayout(assistant)
        assistant_layout.setContentsMargins(14, 10, 14, 10)
        assistant_layout.setSpacing(6)
        assistant_title = QLabel("智能经营助手")
        assistant_title.setFont(QFont(*FONTS["h4"]))
        assistant_title.setStyleSheet(f"color: {COLORS['primary']};")
        assistant_layout.addWidget(assistant_title)
        self.assistant_rows = QVBoxLayout()
        self.assistant_rows.setSpacing(4)
        assistant_layout.addLayout(self.assistant_rows)
        l.addWidget(assistant)

        # 订单明细表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "订单号", "客户", "房型", "入住", "离店", "金额", "状态"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
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
        
        export_btn = QPushButton("📥 导出 CSV")
        export_btn.setObjectName("reportExportButton")
        export_btn.setMinimumHeight(36)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.setStyleSheet(f"""
            QPushButton#reportExportButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }}
            QPushButton#reportExportButton:hover {{
                border-color: {COLORS['primary']};
                color: {COLORS['primary']};
            }}
        """)
        export_btn.clicked.connect(self._export)
        bottom.addWidget(export_btn)
        
        l.addLayout(bottom)

        self.setLayout(l)

    def _style_date_edit(self, editor):
        editor.setStyleSheet(f"""
            QDateEdit {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 5px 22px 5px 10px;
                color: {COLORS['text_primary']};
            }}
            QDateEdit:focus {{
                border-color: {COLORS['primary']};
            }}
            QDateEdit::drop-down {{
                width: 24px;
                border: none;
            }}
            QDateEdit::down-arrow {{
                width: 0;
                height: 0;
            }}
        """)
        if editor.calendarWidget():
            editor.calendarWidget().setStyleSheet(f"""
                QCalendarWidget QWidget {{
                    background: {COLORS['surface']};
                    color: {COLORS['text_primary']};
                }}
                QCalendarWidget QToolButton {{
                    background: {COLORS['surface']};
                    color: {COLORS['text_primary']};
                    border: none;
                    border-radius: 5px;
                    padding: 4px 8px;
                }}
                QCalendarWidget QMenu {{
                    background: {COLORS['surface']};
                }}
                QCalendarWidget QAbstractItemView {{
                    selection-background-color: {COLORS['primary']};
                    selection-color: white;
                    outline: none;
                }}
            """)

    def _build_stat_card(self, label, value, color):
        card = QFrame()
        card.setObjectName("reportStatCard")
        card.setStyleSheet(f"""
            QFrame#reportStatCard {{
                background: {COLORS['surface']};
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
                border-top: 3px solid {color};
            }}
            QFrame#reportStatCard QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        card.setMinimumHeight(68)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 10, 14, 10)
        cl.setSpacing(4)
        
        v = QLabel(value)
        v.setFont(QFont(*FONTS["h2"]))
        v.setStyleSheet(f"color: {color};")
        cl.addWidget(v)
        
        l = QLabel(label)
        l.setFont(QFont(*FONTS["body_sm"]))
        l.setStyleSheet(f"color: {COLORS['text_muted']};")
        cl.addWidget(l)
        
        card.value_label = v
        return card

    def _build_chart_panel(self, title):
        panel = QFrame()
        panel.setObjectName("reportChartPanel")
        panel.setStyleSheet(f"""
            QFrame#reportChartPanel {{
                background: {COLORS['surface']};
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame#reportChartPanel QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        panel.setMinimumHeight(210)
        body = QVBoxLayout(panel)
        body.setContentsMargins(14, 12, 14, 12)
        body.setSpacing(8)
        label = QLabel(title)
        label.setFont(QFont(*FONTS["h4"]))
        label.setStyleSheet(f"color: {COLORS['text_primary']};")
        body.addWidget(label)
        return panel, body

    def _load(self):
        s = Session()
        try:
            fr = self.from_d.date().toPyDate()
            to = self.to_d.date().toPyDate()
            
            # 查询与日期范围有住宿交集的订单
            orders = get_report_orders(s, fr, to)
            
            # 预加载客户
            self._customers = {}
            self._room_types = {}
            
            for o in orders:
                if o.customer_id and o.customer_id not in self._customers:
                    c = s.query(Customer).filter(Customer.id == o.customer_id).first()
                    if c:
                        self._customers[o.customer_id] = c
                if o.room_type_id and o.room_type_id not in self._room_types:
                    from src.models.room_type import RoomType
                    rt = s.query(RoomType).filter(RoomType.id == o.room_type_id).first()
                    if rt:
                        self._room_types[o.room_type_id] = rt
            
            self.orders = orders
            
            metrics = calculate_report_metrics(s, orders, fr, to)
            
            # 更新卡片
            self.card_rev.value_label.setText(f"¥ {metrics['revenue']:.0f}")
            self.card_cnt.value_label.setText(str(metrics["order_count"]))
            self.card_occ.value_label.setText(f"{metrics['occupancy']:.1f}%")
            self.card_adr.value_label.setText(f"¥ {metrics['adr']:.0f}")
            revenue_trend = self._build_revenue_trend(s, fr, to)
            room_revenue = self._build_room_type_revenue(s, orders)
            self.revenue_chart.set_data(revenue_trend)
            self.room_revenue_chart.set_data(room_revenue)
            self._render_assistant(build_report_insights(metrics, revenue_trend, room_revenue))
            
            # 渲染表格
            self._render_table()
            
        except Exception as e:
            print(f"报表加载失败: {e}")
        finally:
            s.close()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _render_assistant(self, insights):
        self._clear_layout(self.assistant_rows)
        for tag, text in insights:
            row = QHBoxLayout()
            badge = QLabel(tag)
            badge.setFixedWidth(58)
            badge.setAlignment(Qt.AlignCenter)
            badge.setFont(QFont(*FONTS["caption_b"]))
            badge.setStyleSheet(f"""
                color: white;
                background: {COLORS['primary']};
                border-radius: 6px;
                padding: 2px 6px;
            """)
            row.addWidget(badge)
            label = QLabel(text)
            label.setWordWrap(True)
            label.setFont(QFont(*FONTS["body_sm"]))
            label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            row.addWidget(label, 1)
            self.assistant_rows.addLayout(row)

    def _build_revenue_trend(self, session, fr, to):
        if fr > to:
            fr, to = to, fr
        days = (to - fr).days + 1
        start = to - timedelta(days=min(days, 14) - 1)
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(to, time.max)
        rows = session.query(BillItem).filter(
            BillItem.created_at >= start_dt,
            BillItem.created_at <= end_dt,
            BillItem.item_type.in_(["房费", "杂费", "退款"]),
        ).all()
        totals = {}
        for item in rows:
            if not item.created_at:
                continue
            key = item.created_at.date()
            totals[key] = totals.get(key, 0) + float(item.amount or 0)
        return [
            {
                "date": (start + timedelta(days=i)).strftime("%m-%d"),
                "value": max(totals.get(start + timedelta(days=i), 0), 0),
            }
            for i in range((to - start).days + 1)
        ]

    def _build_room_type_revenue(self, session, orders):
        if not orders:
            return {}
        order_map = {o.id: o for o in orders}
        totals = {}
        rows = session.query(BillItem).filter(
            BillItem.order_id.in_(order_map.keys()),
            BillItem.item_type.in_(["房费", "杂费", "退款"]),
        ).all()
        for item in rows:
            order = order_map.get(item.order_id)
            if not order:
                continue
            room_type = self._room_types.get(order.room_type_id)
            name = room_type.name if room_type else "未知房型"
            totals[name] = totals.get(name, 0) + max(float(item.amount or 0), 0)
        return {k: v for k, v in totals.items() if v > 0}

    def _render_table(self):
        self.table.setRowCount(len(self.orders))
        for i, o in enumerate(self.orders):
            c = self._customers.get(o.customer_id)
            cname = c.name if c else "-"
            rt = self._room_types.get(o.room_type_id)
            rt_name = rt.name if rt else "-"
            
            values = [
                o.order_no or "-",
                cname,
                rt_name,
                str(o.check_in_date or "-"),
                str(o.check_out_date or "-"),
                f"¥{o.total_amount:.0f}" if o.total_amount else "-",
                o.status or "-",
            ]
            
            for j, v in enumerate(values):
                item = QTableWidgetItem(v)
                item.setFont(QFont(*FONTS["body_sm"]))
                
                # 金额
                if j == 5:
                    item.setForeground(QColor(COLORS["accent"]))
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                # 状态
                if j == 6:
                    status_colors = {
                        "已确认": COLORS["success"],
                        "待确认": COLORS["warning"],
                        "已入住": COLORS["info"],
                        "已退房": COLORS["text_muted"],
                    }
                    sc = status_colors.get(o.status, COLORS["text_muted"])
                    item.setForeground(QColor(sc))
                    item.setTextAlignment(Qt.AlignCenter)
                
                self.table.setItem(i, j, item)

    def _export(self):
        import csv
        path = f"report_{date.today()}.csv"
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(["订单号", "客户", "房型", "入住日期", "离店日期", "金额", "状态"])
            for r in range(self.table.rowCount()):
                w.writerow([self.table.item(r, c).text() for c in range(7)])
        QMessageBox.information(self, "导出完成", f"报表已保存到：\n{path}")
