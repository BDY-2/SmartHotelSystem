# -*- coding: utf-8 -*-
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.user import User
from src.models.room_type import RoomType
from src.models.room import Room
from src.models.customer import Customer
from src.models.order import Order
from src.models.bill_item import BillItem
from src.models.operation_log import OperationLog
from src.models.night_audit import NightAudit
from src.services.dashboard_service import build_role_workbench
from src.services.audit_service import log_operation, run_light_night_audit
from src.services.smart_service import build_guest_profile, build_room_action_plan
from src.services.pms_service import (
    BusinessError,
    check_in_order,
    find_available_rooms,
    settle_order_balance,
)


def make_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    today = date.today()
    s.add_all([
        User(id=1, username="admin", password_hash="x", role="管理员", real_name="管理员"),
        User(id=2, username="front", password_hash="x", role="前台", real_name="前台员工"),
        RoomType(id=1, name="大床房", base_price=288, max_guests=2),
        RoomType(id=2, name="双床房", base_price=328, max_guests=2),
        Room(id=1, room_number="201", room_type_id=1, floor=2, status="已入住", price=288),
        Room(id=2, room_number="202", room_type_id=1, floor=2, status="脏房", price=288),
        Room(id=3, room_number="203", room_type_id=2, floor=2, status="已预订", price=328),
        Room(id=4, room_number="204", room_type_id=2, floor=2, status="空闲", price=328),
        Customer(id=1, name="张伟", phone="13800001111", vip_level="金卡", total_stays=18, preference="高楼层"),
        Customer(id=2, name="李芳", phone="13900002222", vip_level="普通", total_stays=2, preference="安静"),
        Order(id=1, order_no="ORD1", customer_id=1, room_id=1, room_type_id=1,
              check_in_date=today, check_out_date=today + timedelta(days=1),
              actual_check_in=datetime.now(), room_price=288, total_amount=288,
              status="已入住"),
        Order(id=2, order_no="ORD2", customer_id=2, room_id=3, room_type_id=2,
              check_in_date=today, check_out_date=today + timedelta(days=2),
              room_price=328, total_amount=656, status="已确认"),
    ])
    s.add_all([
        BillItem(order_id=1, item_type="房费", amount=288, payment_method="微信"),
        BillItem(order_id=1, item_type="杂费", amount=20, payment_method="微信"),
        BillItem(order_id=1, item_type="押金", amount=300, payment_method="微信"),
    ])
    s.commit()
    return s


def test_admin_workbench_contains_visual_metrics_and_todos():
    s = make_session()
    data = build_role_workbench(s, {"id": 1, "role": "管理员", "real_name": "管理员"})
    assert data["role"] == "管理员"
    assert data["metrics"]["today_revenue"] == 308
    assert data["metrics"]["occupancy_rate"] == 25.0
    assert data["metrics"]["adr"] == 288
    assert data["metrics"]["revpar"] == 72
    assert data["todos"]["arrivals"] == 1
    assert data["todos"]["dirty_rooms"] == 1
    assert len(data["charts"]["revenue_7d"]) == 7
    assert data["charts"]["order_status"]["已入住"] == 1
    assert data["charts"]["room_type_revenue"]["大床房"] == 308
    assert data["action_plan"][0]["target"] in ("checkin", "rooms", "checkout", "dashboard")
    assert data["insights"][0]["level"] in ("info", "warning", "danger", "success")
    s.close()


def test_frontdesk_workbench_emphasizes_flow_tasks():
    s = make_session()
    data = build_role_workbench(s, {"id": 2, "role": "前台", "real_name": "前台员工"})
    labels = [item["label"] for item in data["quick_actions"]]
    metric_labels = [item["label"] for item in data["metric_cards"]]
    workspace = data["workspace"]
    assert labels[:3] == ["办理入住", "散客入住", "退房结算"]
    assert metric_labels == ["今日预抵", "今日待退", "当前在住", "空闲房", "脏房", "未结账"]
    assert all(label not in metric_labels for label in ["今日收入", "本月收入", "ADR", "RevPAR"])
    assert workspace["kind"] == "frontdesk"
    assert workspace["summary_title"] == "接待摘要"
    assert workspace["primary_chart_key"] == "room_status"
    assert workspace["secondary_chart_key"] is None
    assert workspace["secondary_panel_title"] == "下一步处理"
    assert len(workspace["focus_items"]) >= 3
    assert data["primary_panel"] == "frontdesk"
    s.close()


def test_manager_workbench_keeps_business_metrics():
    s = make_session()
    data = build_role_workbench(s, {"id": 1, "role": "管理员", "real_name": "管理员"})
    metric_labels = [item["label"] for item in data["metric_cards"]]
    workspace = data["workspace"]
    assert metric_labels == ["今日收入", "本月收入", "出租率", "ADR", "RevPAR", "会员数"]
    assert workspace["kind"] == "management"
    assert workspace["summary_title"] == "运营摘要"
    assert workspace["primary_chart_key"] == "order_status"
    assert workspace["secondary_chart_key"] == "room_type_revenue"
    s.close()


def test_operation_log_and_light_night_audit():
    s = make_session()
    log = log_operation(s, user_id=1, action="办理入住", detail="订单 ORD1 完成入住")
    audit = run_light_night_audit(s, audit_date=date.today(), operator_id=1)
    s.commit()
    assert s.query(OperationLog).filter(OperationLog.id == log.id).first().action == "办理入住"
    saved = s.query(NightAudit).filter(NightAudit.id == audit.id).first()
    assert saved.total_revenue == 308
    assert saved.total_orders == 2
    assert saved.occupancy_rate == 25.0
    s.close()


def test_guest_profile_uses_customer_history_without_id_card_dependency():
    s = make_session()
    profile = build_guest_profile(s, customer_id=1)
    assert profile["name"] == "张伟"
    assert profile["identity_key"] == "张伟 / 13800001111"
    assert profile["vip_level"] == "金卡"
    assert profile["tags"][:2] == ["高价值会员", "常住客"]
    assert any("高楼层" in tip for tip in profile["service_tips"])
    assert "id_card" not in profile
    s.close()


def test_settle_order_balance_clears_unpaid_amount_without_double_counting_revenue():
    s = make_session()
    order = s.query(Order).filter(Order.id == 1).first()
    order.total_amount = 588
    order.paid_amount = 300
    settlement = settle_order_balance(s, order.id, pay_method="微信")
    s.commit()

    saved = s.query(Order).filter(Order.id == 1).first()
    assert saved.paid_amount == 588
    assert settlement.item_type == "结算"
    assert settlement.amount == 288
    assert settlement.payment_method == "微信"

    data = build_role_workbench(s, {"id": 2, "role": "前台", "real_name": "前台员工"})
    assert data["todos"]["unsettled"] == 0
    s.close()


def test_room_action_plan_prioritizes_arrivals_dirty_rooms_and_checkouts():
    s = make_session()
    today = date.today()
    s.add(Order(id=3, order_no="ORD3", customer_id=1, room_id=1, room_type_id=1,
                check_in_date=today - timedelta(days=1), check_out_date=today,
                actual_check_in=datetime.now(), room_price=288, total_amount=288,
                status="已入住"))
    s.commit()
    plan = build_room_action_plan(s)
    assert plan[0]["level"] == "high"
    assert "预抵" in plan[0]["title"]
    assert any(item["target"] == "rooms" and "脏房" in item["title"] for item in plan)
    assert any(item["target"] == "checkout" and "离店" in item["title"] for item in plan)
    s.close()
 
