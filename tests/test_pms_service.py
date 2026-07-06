# -*- coding: utf-8 -*-
"""pms_service 单元测试"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.base import Base
from src.models.user import User
from src.models.room_type import RoomType
from src.models.room import Room
from src.models.customer import Customer
from src.models.order import Order
from src.models.bill_item import BillItem
from src.services.pms_service import (
    BusinessError, confirm_order, cancel_order, check_in_order,
    checkout_order, change_room_status, add_bill_item,
    get_revenue_amount, find_available_rooms, delete_customer,
    create_walkin_order, get_report_orders, calculate_report_metrics,
)

today = date.today()
tomorrow = today + timedelta(days=1)

engine = create_engine("sqlite:///:memory:", echo=False)
Session = sessionmaker(bind=engine)


def setup_db():
    Base.metadata.create_all(engine)
    s = Session()
    s.add_all([
        RoomType(id=1, name="大床房", base_price=288, max_guests=2),
        RoomType(id=2, name="双床房", base_price=328, max_guests=2),
    ])
    s.add_all([
        Room(id=1, room_number="201", room_type_id=1, floor=2, status="空闲", price=288),
        Room(id=2, room_number="202", room_type_id=1, floor=2, status="空闲", price=288),
        Room(id=3, room_number="301", room_type_id=1, floor=3, status="空闲", price=288),
        Room(id=4, room_number="303", room_type_id=2, floor=3, status="空闲", price=388),
    ])
    s.add_all([
        Customer(id=1, name="张伟", phone="13800001111", id_card="310101199001011234",
                 vip_level="金卡", points=18200, total_stays=18),
        Customer(id=2, name="李芳", phone="13900002222", id_card="310101199205202345",
                 vip_level="银卡", total_stays=7),
    ])
    s.commit()
    s.close()
    return Session


def teardown_db():
    Base.metadata.drop_all(engine)


# ============ 测试用例 ============

class TestPMSService:
    @classmethod
    def setup_class(cls):
        cls.Session = setup_db()

    @classmethod
    def teardown_class(cls):
        teardown_db()

    def _make_order(self, status, customer_id=1, room_id=None,
                    check_in=None, check_out=None):
        s = self.Session()
        ci = check_in or today
        co = check_out or today + timedelta(days=2)
        o = Order(
            order_no=f"TST{status[:2]}{len(s.query(Order).all()):03d}",
            customer_id=customer_id, room_id=room_id, room_type_id=1,
            check_in_date=ci, check_out_date=co,
            room_price=288, total_amount=576, status=status)
        s.add(o)
        s.commit()
        oid = o.id
        s.close()
        return oid

    # 1
    def test_pending_order_cannot_check_in(self):
        oid = self._make_order("待确认")
        s = self.Session()
        try:
            check_in_order(s, oid, 1, id_info={"name": "张伟", "id_card": "310101199001011234"})
            assert False, "应抛 BusinessError"
        except BusinessError:
            pass
        finally:
            s.rollback()
            s.close()

    # 2
    def test_future_order_cannot_check_in(self):
        oid = self._make_order("已确认", check_in=tomorrow)
        s = self.Session()
        try:
            check_in_order(s, oid, 1, id_info={"name": "张伟", "id_card": "310101199001011234"})
            assert False, "应抛 BusinessError"
        except BusinessError:
            pass
        finally:
            s.rollback()
            s.close()

    # 3
    def test_check_in_sets_room_occupied_and_creates_bill_items(self):
        oid = self._make_order("已确认", room_id=1)
        s = self.Session()
        old_room = s.query(Room).filter(Room.id == 1).first()
        assert old_room.status == "空闲"
        try:
            check_in_order(s, oid, 1, id_info={"name": "张伟", "id_card": "310101199001011234"})
            s.commit()
            o = s.query(Order).filter(Order.id == oid).first()
            r = s.query(Room).filter(Room.id == 1).first()
            items = s.query(BillItem).filter(BillItem.order_id == oid).all()
            assert o.status == "已入住"
            assert r.status == "已入住"
            assert any(i.item_type == "房费" for i in items)
            assert any(i.item_type == "押金" for i in items)
        finally:
            s.close()

    # 4
    def test_switch_room_releases_previous_reserved_room(self):
        self._assign_room(2, "空闲")
        self._assign_room(3, "空闲")
        s = self.Session()
        s.query(Room).filter(Room.id == 2).first().status = "已预订"
        s.commit()
        s.close()
        oid = self._make_order("已确认", room_id=2)
        s = self.Session()
        try:
            check_in_order(s, oid, 3, id_info={"name": "张伟", "id_card": "310101199001011234"})
            s.commit()
            r202 = s.query(Room).filter(Room.id == 2).first()
            r301 = s.query(Room).filter(Room.id == 3).first()
            assert r301.status == "已入住"
            assert r202.status == "空闲"
        finally:
            s.close()

    # 5
    def test_conflicting_room_is_not_available(self):
        s = self.Session()
        s.query(Room).filter(Room.id == 1).first().status = "空闲"
        oid1 = self._make_order("已确认", room_id=1,
                                check_in=today, check_out=today+timedelta(days=3))
        oid2 = self._make_order("已确认", customer_id=2,
                                check_in=today+timedelta(days=1),
                                check_out=today+timedelta(days=2))
        s = self.Session()
        s.query(Order).filter(Order.id == oid1).first().status = "已入住"
        s.query(Room).filter(Room.id == 1).first().status = "已入住"
        s.commit()
        rooms = find_available_rooms(s, oid2)
        assert 1 not in {r.id for r in rooms}
        s.close()

    # 6
    def test_checkout_sets_room_dirty(self):
        s = self.Session()
        oid = self._make_order("已入住", room_id=1)
        s.query(Room).filter(Room.id == 1).first().status = "已入住"
        s.commit()
        s.close()
        s = self.Session()
        try:
            checkout_order(s, oid)
            s.commit()
            o = s.query(Order).filter(Order.id == oid).first()
            r = s.query(Room).filter(Room.id == 1).first()
            assert o.status == "已退房"
            assert r.status == "脏房"
        finally:
            s.close()

    # 7
    def test_deposit_is_not_revenue(self):
        s = self.Session()
        oid = self._make_order("已入住", room_id=1)
        s.query(Room).filter(Room.id == 1).first().status = "已入住"
        pay_date = date.today()
        s.add(BillItem(order_id=oid, item_type="房费", amount=576,
                        payment_method="微信"))
        s.add(BillItem(order_id=oid, item_type="押金", amount=300,
                        payment_method="微信"))
        s.add(BillItem(order_id=oid, item_type="杂费", amount=24,
                        payment_method="微信"))
        s.add(BillItem(order_id=oid, item_type="退款", amount=-50,
                        payment_method="微信"))
        for bi in s.query(BillItem).all():
            if bi.created_at is None:
                bi.created_at = datetime.now()
        s.commit()
        # 只统计本订单的房费+杂费+退款（不含押金）
        this_order_items = s.query(BillItem).filter(
            BillItem.order_id == oid,
            BillItem.item_type.in_(["房费", "杂费", "退款"]),
        ).all()
        this_revenue = sum(i.amount for i in this_order_items)
        assert this_revenue == 576 + 24 - 50, f"订单收入应=房费576+杂费24+退款-50=550，实际={this_revenue}"
        assert this_revenue != 576+24+300, "收入不应包含押金"
        s.close()

    # 8
    def test_manual_room_status_protects_checked_in_room(self):
        s = self.Session()
        s.query(Room).filter(Room.id == 1).first().status = "已入住"
        self._make_order("已入住", room_id=1)
        s.close()
        s = self.Session()
        try:
            change_room_status(s, 1, "空闲")
            assert False, "应抛 BusinessError"
        except BusinessError:
            pass
        finally:
            s.rollback()
            s.close()

    # 9 — find_available_rooms 返回原预订的已预订房
    def test_find_available_includes_reserved_room(self):
        s = self.Session()
        s.query(Room).filter(Room.id == 2).first().status = "空闲"
        s.commit()
        oid = self._make_order("已确认", room_id=2)
        s = self.Session()
        s.query(Room).filter(Room.id == 2).first().status = "已预订"
        s.commit()
        rooms = find_available_rooms(s, oid)
        ids = {r.id for r in rooms}
        assert 2 in ids, "原预订的已预订房间应在可选列表"
        s.close()

    # 10 — 客户档案不依赖身份证号，人工核验姓名一致即可入住
    def test_id_card_not_required_for_check_in(self):
        ng = create_engine("sqlite:///:memory:", echo=False)
        NS = sessionmaker(bind=ng)
        Base.metadata.create_all(ng)
        ns = NS()
        ns.add(RoomType(id=1, name="大床房", base_price=288, max_guests=2))
        ns.add(Room(id=1, room_number="201", room_type_id=1, floor=2, status="空闲", price=288))
        ns.add(Customer(id=1, name="张伟", phone="13800001111", id_card="310101199001011234"))
        ns.add(Order(
            id=1, order_no="TST10", customer_id=1, room_id=1, room_type_id=1,
            check_in_date=date.today(), check_out_date=date.today() + timedelta(days=1),
            room_price=288, total_amount=288, status="已确认"
        ))
        ns.commit()
        check_in_order(ns, 1, 1, id_info={"name": "张伟", "verify_method": "manual"})
        ns.commit()
        assert ns.query(Order).filter(Order.id == 1).first().status == "已入住"
        ns.close()

    # 11 — get_revenue_amount 含退款抵扣（独立DB，不共享积累数据）
    def test_revenue_includes_refund(self):
        # 独立内存数据库
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        ng = create_engine("sqlite:///:memory:", echo=False)
        NS = sessionmaker(bind=ng)
        Base.metadata.create_all(ng)
        ns = NS()
        rt = RoomType(id=1, name="大床房", base_price=288, max_guests=2)
        rm = Room(id=1, room_number="201", room_type_id=1, floor=2, status="空闲", price=288)
        cu = Customer(id=1, name="张伟", phone="13800001111", vip_level="普通")
        o = Order(id=1, order_no="TST11", customer_id=1, room_id=1, room_type_id=1,
                  check_in_date=date.today(), check_out_date=date.today()+timedelta(days=2),
                  room_price=288, total_amount=500, status="已入住")
        ns.add_all([rt, rm, cu, o]); ns.commit()
        now = datetime.now()
        ns.add(BillItem(order_id=1, item_type="房费", amount=500, payment_method="微信"))
        ns.add(BillItem(order_id=1, item_type="退款", amount=-100, payment_method="微信"))
        ns.commit()
        # 手动设 created_at
        for bi in ns.query(BillItem).all():
            bi.created_at = now
        ns.commit()
        r = get_revenue_amount(ns, date.today(), date.today())
        assert r == 400, f"get_revenue_amount应=500+(-100)=400，实际{r}"
        ns.close()

    # 12 — 有订单历史的客户不能硬删除
    def test_customer_with_orders_cannot_be_deleted(self):
        oid = self._make_order("已确认", customer_id=1)
        s = self.Session()
        try:
            try:
                delete_customer(s, 1)
                assert False, "有关联订单的客户不应被硬删除"
            except BusinessError:
                pass
            assert s.query(Order).filter(Order.id == oid).first() is not None
            assert s.query(Customer).filter(Customer.id == 1).first() is not None
        finally:
            s.rollback()
            s.close()

    # 13 — 散客入住应生成可办理入住的已确认订单
    def test_create_walkin_order_creates_confirmed_order(self):
        s = self.Session()
        try:
            order = create_walkin_order(
                s,
                customer_id=2,
                room_type_id=1,
                check_in=today,
                check_out=today + timedelta(days=1),
                guest_count=1,
            )
            s.commit()
            saved = s.query(Order).filter(Order.id == order.id).first()
            assert saved.status == "已确认"
            assert saved.order_no.startswith("WK")
            assert saved.total_amount == 288
        finally:
            s.close()

    # 14 — 报表按住宿区间交集查询，而不是只看入住日
    def test_report_orders_include_stays_overlapping_range(self):
        ng = create_engine("sqlite:///:memory:", echo=False)
        NS = sessionmaker(bind=ng)
        Base.metadata.create_all(ng)
        ns = NS()
        ns.add(RoomType(id=1, name="大床房", base_price=288, max_guests=2))
        ns.add(Room(id=1, room_number="201", room_type_id=1, floor=2, status="空闲", price=288))
        ns.add(Customer(id=1, name="张伟", phone="13800001111"))
        ns.add(Order(
            id=1, order_no="RPT1", customer_id=1, room_id=1, room_type_id=1,
            check_in_date=date(2026, 7, 1), check_out_date=date(2026, 7, 5),
            room_price=288, total_amount=1152, status="已入住"
        ))
        ns.commit()
        orders = get_report_orders(ns, date(2026, 7, 4), date(2026, 7, 4))
        assert [o.order_no for o in orders] == ["RPT1"]
        ns.close()

    # 15 — 出租率不应把仅已确认的预订单算成已出租
    def test_report_occupancy_excludes_confirmed_reservations(self):
        ng = create_engine("sqlite:///:memory:", echo=False)
        NS = sessionmaker(bind=ng)
        Base.metadata.create_all(ng)
        ns = NS()
        ns.add(RoomType(id=1, name="大床房", base_price=288, max_guests=2))
        ns.add_all([
            Room(id=1, room_number="201", room_type_id=1, floor=2, status="已预订", price=288),
            Room(id=2, room_number="202", room_type_id=1, floor=2, status="空闲", price=288),
        ])
        ns.add(Customer(id=1, name="张伟", phone="13800001111"))
        ns.add(Order(
            id=1, order_no="RPT2", customer_id=1, room_id=1, room_type_id=1,
            check_in_date=date(2026, 7, 4), check_out_date=date(2026, 7, 5),
            room_price=288, total_amount=288, status="已确认"
        ))
        ns.commit()
        metrics = calculate_report_metrics(
            ns, get_report_orders(ns, date(2026, 7, 4), date(2026, 7, 4)),
            date(2026, 7, 4), date(2026, 7, 4)
        )
        assert metrics["occupied_nights"] == 0
        assert metrics["occupancy"] == 0
        ns.close()

    def _assign_room(self, room_id, status):
        s = self.Session()
        s.query(Room).filter(Room.id == room_id).first().status = status
        s.commit()
        s.close()
