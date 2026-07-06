# -*- coding: utf-8 -*-
"""v3.0 智能工作台服务。

本层只产出数据，不写 UI，避免 v3.0 中 UI 与业务口径混在一起。
"""
from collections import defaultdict
from datetime import date, timedelta

from src.models.bill_item import BillItem
from src.models.customer import Customer
from src.models.order import Order
from src.models.room import Room
from src.models.room_type import RoomType
from src.services.smart_service import build_room_action_plan


REVENUE_TYPES = ("房费", "杂费", "退款")


def build_role_workbench(session, user_info):
    role = (user_info or {}).get("role", "前台")
    today = date.today()
    rooms = session.query(Room).all()
    orders = session.query(Order).order_by(Order.created_at.desc()).all()

    room_counts = _count_by(rooms, "status")
    todos = _build_todos(orders, room_counts, today)
    metrics = _build_metrics(session, orders, rooms, today)
    charts = _build_charts(session, orders, today)
    insights = _build_insights(metrics, todos, room_counts)

    return {
        "role": role,
        "user_name": (user_info or {}).get("real_name", ""),
        "primary_panel": _primary_panel(role),
        "workspace": _workspace_config(role),
        "metrics": metrics,
        "metric_cards": _metric_cards(role, metrics, todos, room_counts),
        "todos": todos,
        "charts": charts,
        "insights": insights,
        "action_plan": build_room_action_plan(session, today),
        "quick_actions": _quick_actions(role),
        "recent_orders": _recent_orders(session, orders[:8]),
    }


def _count_by(items, attr):
    counts = defaultdict(int)
    for item in items:
        counts[getattr(item, attr, None) or "-"] += 1
    return dict(counts)


def _build_todos(orders, room_counts, today):
    return {
        "arrivals": sum(1 for o in orders if o.check_in_date == today and o.status == "已确认"),
        "departures": sum(1 for o in orders if o.check_out_date == today and o.status == "已入住"),
        "in_house": sum(1 for o in orders if o.status == "已入住"),
        "dirty_rooms": room_counts.get("脏房", 0),
        "maintenance_rooms": room_counts.get("维修", 0),
        "unsettled": sum(1 for o in orders if (o.total_amount or 0) > (o.paid_amount or 0)
                         and o.status in ("已入住", "已退房")),
    }


def _build_metrics(session, orders, rooms, today):
    total_rooms = len(rooms) or 1
    today_revenue = _revenue_between(session, today, today)
    first_day = today.replace(day=1)
    month_revenue = _revenue_between(session, first_day, today)
    occupied = sum(1 for r in rooms if r.status == "已入住")
    room_revenue = sum((i.amount or 0) for i in session.query(BillItem).filter(
        BillItem.item_type == "房费"
    ).all())
    return {
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "occupancy_rate": round(occupied / total_rooms * 100, 1),
        "adr": round(room_revenue / occupied, 1) if occupied else 0,
        "revpar": round(room_revenue / total_rooms, 1) if total_rooms else 0,
        "active_members": session.query(Customer).filter(Customer.vip_level != "普通").count(),
    }


def _build_charts(session, orders, today):
    revenue_7d = []
    occ_7d = []
    total_rooms = session.query(Room).count() or 1
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        revenue_7d.append({"date": day.strftime("%m-%d"), "value": _revenue_between(session, day, day)})
        active = sum(
            1 for o in orders
            if o.status in ("已入住", "已退房")
            and o.check_in_date and o.check_out_date
            and o.check_in_date <= day < o.check_out_date
        )
        occ_7d.append({"date": day.strftime("%m-%d"), "value": round(active / total_rooms * 100, 1)})

    order_status = _count_by([o for o in orders if o.status != "已取消"], "status")
    room_status = _count_by(session.query(Room).all(), "status")
    member_levels = _count_by(session.query(Customer).all(), "vip_level")
    room_type_revenue = _room_type_revenue(session)

    return {
        "revenue_7d": revenue_7d,
        "occupancy_7d": occ_7d,
        "order_status": order_status,
        "room_status": room_status,
        "member_levels": member_levels,
        "room_type_revenue": room_type_revenue,
    }


def _room_type_revenue(session):
    names = {rt.id: rt.name for rt in session.query(RoomType).all()}
    result = defaultdict(float)
    orders = {o.id: o for o in session.query(Order).all()}
    for item in session.query(BillItem).filter(BillItem.item_type.in_(REVENUE_TYPES)).all():
        order = orders.get(item.order_id)
        if not order:
            continue
        result[names.get(order.room_type_id, "未知房型")] += item.amount or 0
    return dict(result)


def _revenue_between(session, start_date, end_date):
    from datetime import datetime
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    return sum((i.amount or 0) for i in session.query(BillItem).filter(
        BillItem.item_type.in_(REVENUE_TYPES),
        BillItem.created_at >= start_dt,
        BillItem.created_at < end_dt,
    ).all())


def _quick_actions(role):
    if role == "财务":
        return [
            {"label": "查看流水", "target": "cashier"},
            {"label": "处理退款", "target": "cashier"},
            {"label": "导出报表", "target": "reports"},
        ]
    if role == "管理员":
        return [
            {"label": "查看报表", "target": "reports"},
            {"label": "房态总览", "target": "rooms"},
            {"label": "操作日志", "target": "settings"},
        ]
    return [
        {"label": "办理入住", "target": "checkin"},
        {"label": "散客入住", "target": "checkin"},
        {"label": "退房结算", "target": "checkout"},
    ]


def _primary_panel(role):
    if role == "财务":
        return "finance"
    if role == "管理员":
        return "manager"
    return "frontdesk"


def _workspace_config(role):
    if role in ("管理员", "财务"):
        return {
            "kind": "management",
            "summary_title": "运营摘要",
            "action_title": "经营行动队列",
            "recent_title": "最近订单",
            "quick_title": "管理入口",
            "primary_chart_title": "订单结构",
            "primary_chart_key": "order_status",
            "secondary_chart_title": "房型收入",
            "secondary_chart_key": "room_type_revenue",
            "secondary_panel_title": "房型收入",
            "focus_items": [],
        }
    if role == "客房":
        return {
            "kind": "housekeeping",
            "summary_title": "房态摘要",
            "action_title": "客房行动队列",
            "recent_title": "最近房态",
            "quick_title": "客房入口",
            "primary_chart_title": "房态结构",
            "primary_chart_key": "room_status",
            "secondary_chart_title": None,
            "secondary_chart_key": None,
            "secondary_panel_title": "客房重点",
            "focus_items": [
                "先处理脏房和维修房，避免影响后续分房。",
                "房态更新后及时刷新，确保前台看到最新可售房。",
                "维修房恢复后先改为空闲，再安排入住。",
            ],
        }
    return {
        "kind": "frontdesk",
        "summary_title": "接待摘要",
        "action_title": "接待行动队列",
        "recent_title": "最近接待订单",
        "quick_title": "快捷接待",
        "primary_chart_title": "房态结构",
        "primary_chart_key": "room_status",
        "secondary_chart_title": None,
        "secondary_chart_key": None,
        "secondary_panel_title": "下一步处理",
        "focus_items": [
            "预抵订单优先确认房型、房价和入住日期。",
            "脏房先通知客房清洁，再进行房间分配。",
            "未结账订单交接给收银台，避免离店后漏收。",
        ],
    }


def _metric_cards(role, metrics, todos, room_counts):
    if role == "前台":
        return [
            {"key": "arrivals", "label": "今日预抵", "value": todos["arrivals"], "format": "count", "color": "accent"},
            {"key": "departures", "label": "今日待退", "value": todos["departures"], "format": "count", "color": "warning"},
            {"key": "in_house", "label": "当前在住", "value": todos["in_house"], "format": "count", "color": "info"},
            {"key": "vacant", "label": "空闲房", "value": room_counts.get("空闲", 0), "format": "count", "color": "success"},
            {"key": "dirty_rooms", "label": "脏房", "value": todos["dirty_rooms"], "format": "count", "color": "room_dirty"},
            {"key": "unsettled", "label": "未结账", "value": todos["unsettled"], "format": "count", "color": "danger"},
        ]
    if role == "客房":
        return [
            {"key": "dirty_rooms", "label": "脏房", "value": todos["dirty_rooms"], "format": "count", "color": "room_dirty"},
            {"key": "maintenance_rooms", "label": "维修房", "value": todos["maintenance_rooms"], "format": "count", "color": "room_maintenance"},
            {"key": "vacant", "label": "空闲房", "value": room_counts.get("空闲", 0), "format": "count", "color": "success"},
            {"key": "occupied", "label": "在住房", "value": room_counts.get("已入住", 0), "format": "count", "color": "danger"},
        ]
    return [
        {"key": "today_revenue", "label": "今日收入", "value": metrics["today_revenue"], "format": "money", "color": "success"},
        {"key": "month_revenue", "label": "本月收入", "value": metrics["month_revenue"], "format": "money", "color": "primary"},
        {"key": "occupancy_rate", "label": "出租率", "value": metrics["occupancy_rate"], "format": "percent", "color": "info"},
        {"key": "adr", "label": "ADR", "value": metrics["adr"], "format": "money", "color": "accent"},
        {"key": "revpar", "label": "RevPAR", "value": metrics["revpar"], "format": "money", "color": "purple"},
        {"key": "active_members", "label": "会员数", "value": metrics["active_members"], "format": "count", "color": "room_dirty"},
    ]


def _recent_orders(session, orders):
    customers = {c.id: c.name for c in session.query(Customer).all()}
    room_types = {rt.id: rt.name for rt in session.query(RoomType).all()}
    return [
        {
            "order_no": o.order_no or "-",
            "customer": customers.get(o.customer_id, "-"),
            "room_type": room_types.get(o.room_type_id, "-"),
            "status": o.status or "-",
        }
        for o in orders
    ]


def _build_insights(metrics, todos, room_counts):
    insights = []
    if todos["arrivals"]:
        insights.append({"level": "info", "text": f"今日有 {todos['arrivals']} 单预抵，建议优先完成房间分配。"})
    if todos["dirty_rooms"]:
        insights.append({"level": "warning", "text": f"当前有 {todos['dirty_rooms']} 间脏房，可能影响后续入住。"})
    if todos["unsettled"]:
        insights.append({"level": "danger", "text": f"存在 {todos['unsettled']} 单未结清账务，请收银台跟进。"})
    if metrics["occupancy_rate"] >= 80:
        insights.append({"level": "success", "text": "当前出租率较高，需关注退房和清洁衔接。"})
    if not insights:
        insights.append({"level": "success", "text": "今日经营状态平稳，暂无高优先级异常。"})
    return insights[:4]
