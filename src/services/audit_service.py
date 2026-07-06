# -*- coding: utf-8 -*-
"""v3.0 操作日志与轻量夜审服务。"""
from datetime import datetime, date

from src.models.bill_item import BillItem
from src.models.night_audit import NightAudit
from src.models.operation_log import OperationLog
from src.models.order import Order
from src.models.room import Room


def log_operation(session, user_id, action, detail, ip_address="local"):
    log = OperationLog(
        user_id=user_id,
        action=action,
        detail=detail,
        ip_address=ip_address,
    )
    session.add(log)
    session.flush()
    return log


def run_light_night_audit(session, audit_date=None, operator_id=None):
    audit_day = audit_date or date.today()
    revenue = _daily_revenue(session, audit_day)
    total_orders = session.query(Order).filter(
        Order.check_in_date <= audit_day,
        Order.check_out_date > audit_day,
        Order.status.in_(("已确认", "已入住", "已退房")),
    ).count()
    total_rooms = session.query(Room).count() or 1
    occupied = session.query(Room).filter(Room.status == "已入住").count()
    occupancy = round(occupied / total_rooms * 100, 1)
    adr = round(revenue / occupied, 1) if occupied else 0
    revpar = round(revenue / total_rooms, 1)

    audit = NightAudit(
        audit_date=audit_day,
        total_revenue=revenue,
        total_orders=total_orders,
        occupancy_rate=occupancy,
        adr=adr,
        revpar=revpar,
        executed_at=datetime.now(),
        operator_id=operator_id,
    )
    session.add(audit)
    session.flush()
    return audit


def _daily_revenue(session, audit_day):
    start_dt = datetime.combine(audit_day, datetime.min.time())
    end_dt = datetime.combine(audit_day, datetime.max.time())
    return sum((item.amount or 0) for item in session.query(BillItem).filter(
        BillItem.item_type.in_(("房费", "杂费", "退款")),
        BillItem.created_at >= start_dt,
        BillItem.created_at <= end_dt,
    ).all())
