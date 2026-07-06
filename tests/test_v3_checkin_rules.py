# -*- coding: utf-8 -*-
import os
import sys
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.base import Base
from src.models.customer import Customer
from src.models.order import Order
from src.models.room import Room
from src.models.room_type import RoomType
from src.services.pms_service import BusinessError, check_in_order, find_available_rooms


def make_rule_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    today = date.today()
    s.add_all([
        RoomType(id=1, name="大床房", base_price=288, max_guests=2),
        RoomType(id=2, name="双床房", base_price=328, max_guests=2),
        RoomType(id=3, name="豪华套房", base_price=588, max_guests=2),
        Room(id=1, room_number="101", room_type_id=1, floor=1, status="空闲", price=288),
        Room(id=2, room_number="201", room_type_id=2, floor=2, status="空闲", price=328),
        Room(id=3, room_number="301", room_type_id=3, floor=3, status="空闲", price=588),
        Customer(id=1, name="周雨", phone="13200006666", vip_level="普通"),
        Order(id=1, order_no="BK1", customer_id=1, room_type_id=3,
              check_in_date=today, check_out_date=today + timedelta(days=1),
              room_price=588, total_amount=588, status="已确认"),
    ])
    s.commit()
    return s


def test_checkin_requires_each_roommate_identity_verification():
    s = make_rule_session()
    with pytest.raises(BusinessError, match="同住人"):
        check_in_order(
            s,
            order_id=1,
            room_id=3,
            id_info={"name": "周雨", "verify_method": "人工核验"},
            roommates=[{"name": "李芳"}],
        )
    s.close()


def test_checkin_accepts_verified_roommates():
    s = make_rule_session()
    check_in_order(
        s,
        order_id=1,
        room_id=3,
        id_info={"name": "周雨", "verify_method": "人工核验"},
        roommates=[{"name": "李芳", "verify_method": "人工核验"}],
    )
    s.commit()
    assert s.query(Order).filter(Order.id == 1).first().status == "已入住"
    s.close()


def test_premium_booking_cannot_select_lower_grade_room():
    s = make_rule_session()
    available_numbers = {room.room_number for room in find_available_rooms(s, 1)}
    assert "301" in available_numbers
    assert "101" not in available_numbers
    assert "201" not in available_numbers

    with pytest.raises(BusinessError, match="低于预订"):
        check_in_order(
            s,
            order_id=1,
            room_id=1,
            id_info={"name": "周雨", "verify_method": "人工核验"},
        )
    s.close()
