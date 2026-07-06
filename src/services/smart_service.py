# -*- coding: utf-8 -*-
"""v3.0 轻量智能建议服务。

这里做可解释的规则建议，不接大模型，也不依赖身份证号。
"""
from datetime import date

from src.models.customer import Customer
from src.models.order import Order
from src.models.room import Room
from src.models.room_type import RoomType


def build_guest_profile(session, customer_id):
    customer = session.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return {
            "name": "-",
            "identity_key": "-",
            "vip_level": "普通",
            "tags": ["新客"],
            "service_tips": ["先确认手机号和入住偏好。"],
        }

    tags = []
    if customer.vip_level in ("金卡", "铂金"):
        tags.append("高价值会员")
    if (customer.total_stays or 0) >= 5:
        tags.append("常住客")
    if customer.preference:
        tags.append("有偏好")
    if not tags:
        tags.append("普通客")

    tips = []
    if customer.preference:
        tips.append(f"优先满足偏好：{customer.preference}")
    if customer.vip_level in ("金卡", "铂金"):
        tips.append("可主动说明会员折扣、免押或升级权益。")
    if (customer.total_stays or 0) <= 1:
        tips.append("新客建议简短说明早餐、退房时间和联系方式。")
    if not tips:
        tips.append("按标准入住流程办理即可。")

    phone = customer.phone or "未留手机号"
    return {
        "name": customer.name,
        "identity_key": f"{customer.name} / {phone}",
        "vip_level": customer.vip_level or "普通",
        "points": customer.points or 0,
        "total_stays": customer.total_stays or 0,
        "last_stay": customer.last_stay.isoformat() if customer.last_stay else "-",
        "tags": tags,
        "service_tips": tips,
    }


def build_room_action_plan(session, target_date=None):
    today = target_date or date.today()
    orders = session.query(Order).all()
    rooms = session.query(Room).all()
    room_types = {rt.id: rt.name for rt in session.query(RoomType).all()}

    arrivals = [o for o in orders if o.status == "已确认" and o.check_in_date == today]
    departures = [o for o in orders if o.status == "已入住" and o.check_out_date == today]
    dirty_rooms = [r for r in rooms if r.status == "脏房"]
    maintenance_rooms = [r for r in rooms if r.status == "维修"]

    plan = []
    if arrivals:
        names = _room_type_summary(arrivals, room_types)
        plan.append({
            "level": "high",
            "title": f"{len(arrivals)} 单预抵待办理",
            "detail": f"优先检查可售房和会员偏好：{names}",
            "target": "checkin",
        })
    if dirty_rooms:
        plan.append({
            "level": "medium",
            "title": f"{len(dirty_rooms)} 间脏房需清洁",
            "detail": "先处理今日预抵同房型，避免入住时临时换房。",
            "target": "rooms",
        })
    if departures:
        plan.append({
            "level": "medium",
            "title": f"{len(departures)} 单今日离店",
            "detail": "提前核对押金和消费明细，退房后房态应自动转脏房。",
            "target": "checkout",
        })
    if maintenance_rooms:
        plan.append({
            "level": "low",
            "title": f"{len(maintenance_rooms)} 间维修房",
            "detail": "确认维修预计完成时间，避免被误分配。",
            "target": "rooms",
        })
    if not plan:
        plan.append({
            "level": "normal",
            "title": "暂无高优先级任务",
            "detail": "保持房态、账务、订单三处数据一致即可。",
            "target": "dashboard",
        })
    return plan


def _room_type_summary(orders, room_types):
    counts = {}
    for order in orders:
        name = room_types.get(order.room_type_id, "未知房型")
        counts[name] = counts.get(name, 0) + 1
    return "、".join(f"{name} {count} 间" for name, count in counts.items())
