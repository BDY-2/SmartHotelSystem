# -*- coding: utf-8 -*-
"""统一业务服务层 —— 订单/房态/入住/退房/账务状态流转"""
from datetime import datetime, date, timedelta
import random
from src.models.order import Order
from src.models.room import Room
from src.models.customer import Customer
from src.models.bill_item import BillItem


class BusinessError(Exception):
    pass


# ============ 辅助函数（供内部使用） ============

def _date_ranges_overlap(a_start, a_end, b_start, b_end):
    """判断两个日期区间是否重叠"""
    return a_start < b_end and a_end > b_start


def _room_has_conflicting_order(session, room_id, check_in, check_out,
                                 exclude_order_id=None):
    """检查某房间在指定日期区间内是否有其他有效订单冲突"""
    active_statuses = ("已确认", "已入住")
    q = session.query(Order).filter(
        Order.room_id == room_id,
        Order.status.in_(active_statuses),
        Order.check_in_date < check_out,
        Order.check_out_date > check_in,
    )
    if exclude_order_id is not None:
        q = q.filter(Order.id != exclude_order_id)
    return q.first() is not None


def _order_no(prefix):
    return f"{prefix}{datetime.now().strftime('%y%m%d%H%M%S')}{random.randint(100, 999)}"


def _room_price(session, room):
    """Return the sellable price for a room, falling back to room type base price."""
    if not room:
        return 0
    if room.price is not None:
        return room.price
    from src.models.room_type import RoomType
    rt = session.query(RoomType).filter(RoomType.id == room.room_type_id).first()
    return rt.base_price if rt and rt.base_price is not None else 0


def _order_booked_price(session, order):
    """Return the minimum acceptable room price for the booking standard."""
    if not order:
        return 0
    if order.room_price is not None:
        return order.room_price
    from src.models.room_type import RoomType
    rt = session.query(RoomType).filter(RoomType.id == order.room_type_id).first()
    return rt.base_price if rt and rt.base_price is not None else 0


def _validate_roommate_identities(roommates):
    """Every co-guest must be explicitly identity-verified for this stay."""
    for guest in roommates or []:
        name = (guest or {}).get("name")
        verify_method = (guest or {}).get("verify_method")
        if not name or not verify_method:
            raise BusinessError("同住人必须完成身份核验后才能办理入住")


def _release_room_if_unused(session, room_id, exclude_order_id=None):
    """释放房间：检查是否有与当前订单日期重叠的其他活跃订单。
    无重叠 → 释放为"空闲"。有不重叠的未来订单 → 不影响释放。"""
    excluded = session.query(Order).filter(Order.id == exclude_order_id).first() \
        if exclude_order_id else None
    active = session.query(Order).filter(
        Order.room_id == room_id,
        Order.status.in_(("已确认", "已入住")),
    )
    if exclude_order_id is not None:
        active = active.filter(Order.id != exclude_order_id)

    ref_start = excluded.check_in_date if excluded and excluded.check_in_date else date.today()
    ref_end = excluded.check_out_date if excluded and excluded.check_out_date else date.today()

    has_conflict = False
    for ao in active:
        if ao.status == "已入住":
            has_conflict = True; break
        if ao.check_in_date and ao.check_out_date:
            if _date_ranges_overlap(ref_start, ref_end,
                                     ao.check_in_date, ao.check_out_date):
                has_conflict = True; break

    if not has_conflict:
        room = session.query(Room).filter(Room.id == room_id).first()
        if room:
            room.status = "空闲"


# ============ 业务服务函数 ============

def confirm_order(session, order_id):
    o = session.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise BusinessError(f"订单 {order_id} 不存在")
    if o.status != "待确认":
        raise BusinessError(f"只有待确认的订单可以确认，当前状态：{o.status}")

    o.status = "已确认"

    # 如果已绑定房间且无冲突，设为已预订
    if o.room_id:
        has_conflict = _room_has_conflicting_order(
            session, o.room_id, o.check_in_date, o.check_out_date,
            exclude_order_id=order_id)
        if not has_conflict:
            room = session.query(Room).filter(Room.id == o.room_id).first()
            if room and room.status == "空闲":
                room.status = "已预订"


def cancel_order(session, order_id):
    o = session.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise BusinessError(f"订单 {order_id} 不存在")
    if o.status not in ("待确认", "已确认"):
        raise BusinessError(f"只有待确认/已确认的订单可以取消，当前状态：{o.status}")

    o.status = "已取消"

    # 释放已绑定的房间
    if o.room_id:
        _release_room_if_unused(session, o.room_id, exclude_order_id=order_id)


def delete_customer(session, customer_id):
    """删除客户档案。

    已产生订单的客户不能硬删除，避免破坏历史订单、账单、会员统计。
    """
    c = session.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise BusinessError(f"客户 {customer_id} 不存在")

    has_orders = session.query(Order).filter(Order.customer_id == customer_id).first()
    if has_orders:
        raise BusinessError("该客户已有订单记录，不能删除；请保留历史档案")

    session.delete(c)


def create_walkin_order(session, customer_id, room_type_id, check_in=None,
                        check_out=None, guest_count=1, room_price=None,
                        remark="散客入住"):
    """创建散客入住订单，默认生成已确认订单，供入住流程继续办理。"""
    c = session.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise BusinessError(f"客户 {customer_id} 不存在")

    from src.models.room_type import RoomType
    rt = session.query(RoomType).filter(RoomType.id == room_type_id).first()
    if not rt:
        raise BusinessError(f"房型 {room_type_id} 不存在")

    ci = check_in or date.today()
    co = check_out or (ci + timedelta(days=1))
    if co <= ci:
        raise BusinessError("离店日期必须晚于入住日期")
    if guest_count <= 0:
        raise BusinessError("入住人数必须大于 0")

    price = room_price if room_price is not None else rt.base_price
    nights = max(1, (co - ci).days)
    order = Order(
        order_no=_order_no("WK"),
        customer_id=customer_id,
        room_type_id=room_type_id,
        check_in_date=ci,
        check_out_date=co,
        room_price=price,
        total_amount=price * nights,
        guest_count=guest_count,
        status="已确认",
        deposit=0,
        paid_amount=0,
        remark=remark,
    )
    session.add(order)
    session.flush()
    return order


def find_available_rooms(session, order_id, room_type_id=None):
    o = session.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise BusinessError(f"订单 {order_id} 不存在")

    from sqlalchemy import or_, and_
    base_q = session.query(Room).filter(
        or_(
            Room.status == "空闲",
            and_(Room.id == o.room_id, Room.status == "已预订")
        )
    )

    if room_type_id is not None:
        base_q = base_q.filter(Room.room_type_id == room_type_id)

    candidates = base_q.all()
    booked_price = _order_booked_price(session, o)
    candidates = [rm for rm in candidates if _room_price(session, rm) >= booked_price]

    occupied_rooms = set()
    for rm in candidates:
        if _room_has_conflicting_order(
            session, rm.id, o.check_in_date, o.check_out_date,
            exclude_order_id=order_id
        ):
            occupied_rooms.add(rm.id)

    return [rm for rm in candidates if rm.id not in occupied_rooms]


def check_in_order(session, order_id, room_id, id_info=None,
                   pay_method="现金", upgrade_mode=None, roommates=None):
    o = session.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise BusinessError(f"订单 {order_id} 不存在")
    if o.status != "已确认":
        raise BusinessError(f"只有已确认的订单可以入住，当前状态：{o.status}")

    today = date.today()
    if o.check_in_date > today:
        raise BusinessError(
            f"入住日期 {o.check_in_date} 晚于今天 {today}，无法提前入住")

    if not id_info or not id_info.get("name"):
        raise BusinessError("必须提供入住人身份信息（至少包含姓名）")
    _validate_roommate_identities(roommates)

    c = session.query(Customer).filter(Customer.id == o.customer_id).first()
    if not c:
        raise BusinessError("订单未关联客户")

    if id_info.get("name") != c.name:
        raise BusinessError(
            f"入住人姓名 {id_info.get('name')} 与预订人 {c.name} 不匹配")

    new_room = session.query(Room).filter(Room.id == room_id).first()
    if not new_room:
        raise BusinessError(f"房间 {room_id} 不存在")

    # 先明确拦截降档，避免只给出笼统的“不可用”提示。
    booked_price = _order_booked_price(session, o)
    selected_price = _room_price(session, new_room)
    if selected_price < booked_price:
        raise BusinessError(
            f"所选房间低于预订标准，不能降档入住（目标 ¥{selected_price:.0f} < 预订 ¥{booked_price:.0f}）")

    available = find_available_rooms(session, order_id)
    avail_ids = {rm.id for rm in available}
    if room_id not in avail_ids:
        raise BusinessError(f"房间 {room_id} 不可用")

    # 检查房型是否与原订单一致
    billing_price = booked_price
    if new_room.room_type_id != o.room_type_id:
        if selected_price > booked_price:
            if upgrade_mode == "paid":
                billing_price = selected_price
            elif upgrade_mode == "free":
                billing_price = booked_price
            else:
                raise BusinessError(
                    f"升级房型需选择付费升级或免费升级，目标房价 ¥{selected_price:.0f} > 原房价 ¥{booked_price:.0f}")

    # 释放原来绑定的已预订房间
    if o.room_id and o.room_id != room_id:
        _release_room_if_unused(session, o.room_id, exclude_order_id=order_id)

    # 确定押金
    deposit = 300 if billing_price < 400 else 500
    nights = max(1, (o.check_out_date - o.check_in_date).days)
    room_total = billing_price * nights

    o.room_id = room_id
    o.status = "已入住"
    o.actual_check_in = datetime.now()
    o.room_price = billing_price
    o.deposit = deposit
    o.total_amount = room_total + deposit
    o.paid_amount = room_total + deposit
    o.payment_method = pay_method

    new_room.status = "已入住"

    # 账单：房费
    session.add(BillItem(
        order_id=o.id, item_type="房费",
        description=f"{new_room.room_number} 房费 {nights}晚",
        amount=room_total, payment_method=pay_method))
    # 账单：押金
    session.add(BillItem(
        order_id=o.id, item_type="押金",
        description="入住押金", amount=deposit,
        payment_method=pay_method))


def checkout_order(session, order_id):
    o = session.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise BusinessError(f"订单 {order_id} 不存在")
    if o.status != "已入住":
        raise BusinessError(f"只有已入住的订单可以退房，当前状态：{o.status}")

    balance = round((o.total_amount or 0) - (o.paid_amount or 0), 2)
    if balance > 0 and (o.paid_amount or 0) > 0:
        raise BusinessError(
            f"该订单还有 ¥{balance:.2f} 未结清，请先前往收银台结清账务"
        )

    o.status = "已退房"
    o.actual_check_out = datetime.now()

    room = session.query(Room).filter(Room.id == o.room_id).first()
    if room:
        room.status = "脏房"

    if o.customer_id:
        c = session.query(Customer).filter(Customer.id == o.customer_id).first()
        if c:
            c.total_stays = (c.total_stays or 0) + 1
            c.last_stay = date.today()


def change_room_status(session, room_id, new_status):
    if new_status not in ("空闲", "已入住", "已预订", "脏房", "维修"):
        raise BusinessError(f"无效的房态：{new_status}")

    room = session.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise BusinessError(f"房间 {room_id} 不存在")

    # 如果有已入住订单，禁止手动改为空闲/维修/脏房
    if room.status == "已入住" and new_status in ("空闲", "维修", "脏房"):
        active = session.query(Order).filter(
            Order.room_id == room_id, Order.status == "已入住"
        ).first()
        if active:
            raise BusinessError(
                f"房间 {room.room_number} 有关联的已入住订单 {active.order_no}，"
                f"请先办理退房再修改房态")

    room.status = new_status


def add_bill_item(session, order_id, item_type, amount,
                  description="", pay_method="现金"):
    if item_type not in ("房费", "押金", "杂费", "退款"):
        raise BusinessError(f"无效的费用类型：{item_type}")

    if item_type == "退款":
        if amount > 0:
            raise BusinessError("退款金额必须为负数")
    else:
        if amount <= 0:
            raise BusinessError(f"{item_type} 金额必须为正数")

    o = session.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise BusinessError(f"订单 {order_id} 不存在")

    session.add(BillItem(
        order_id=order_id,
        item_type=item_type,
        description=description or item_type,
        amount=amount,
        payment_method=pay_method,
    ))

    # 更新已付金额
    o.paid_amount = (o.paid_amount or 0) + amount


def settle_order_balance(session, order_id, pay_method="现金"):
    """结清订单尾款。

    结清流水表示收款动作，不重复计入房费/杂费收入，避免报表重复统计。
    """
    o = session.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise BusinessError(f"订单 {order_id} 不存在")
    if o.status not in ("已入住", "已退房"):
        raise BusinessError(f"只有已入住/已退房订单可以结清，当前状态：{o.status}")

    balance = round((o.total_amount or 0) - (o.paid_amount or 0), 2)
    if balance <= 0:
        raise BusinessError("该订单已无未结清金额")

    item = BillItem(
        order_id=order_id,
        item_type="结算",
        description="结清账务尾款",
        amount=balance,
        payment_method=pay_method,
    )
    session.add(item)
    o.paid_amount = (o.paid_amount or 0) + balance
    return item


def get_revenue_amount(session, start_date, end_date):
    """统计收入：只计算房费+杂费，不统计押金，退款自然抵扣（负值）"""
    from datetime import timedelta
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    items = session.query(BillItem).filter(
        BillItem.item_type.in_(["房费", "杂费", "退款"]),
        BillItem.created_at >= start_dt,
        BillItem.created_at < end_dt,
    ).all()
    return sum(item.amount for item in items)


def get_report_orders(session, start_date, end_date):
    """按住宿日期区间交集查询订单。

    end_date 按自然日包含，因此转换成次日作为开区间右边界。
    """
    query_end = end_date + timedelta(days=1)
    return session.query(Order).filter(
        Order.status != "已取消",
        Order.check_in_date < query_end,
        Order.check_out_date > start_date,
    ).order_by(Order.check_in_date.desc()).all()


def calculate_report_metrics(session, orders, start_date, end_date):
    """计算报表核心指标。

    出租率只统计已实际占用过房间的订单：已入住、已退房。
    已确认预订单不计入出租间夜。
    """
    query_end = end_date + timedelta(days=1)
    total_rooms = session.query(Room).count()
    days = max(1, (query_end - start_date).days)
    total_room_nights = total_rooms * days if total_rooms else 1

    order_ids = [o.id for o in orders]
    bill_revenue = 0
    if order_ids:
        items = session.query(BillItem).filter(
            BillItem.order_id.in_(order_ids),
            BillItem.item_type.in_(["房费", "杂费", "退款"]),
        ).all()
        bill_revenue = sum(i.amount for i in items) or 0

    occupied_nights = 0
    for o in orders:
        if o.status not in ("已入住", "已退房"):
            continue
        if not o.check_in_date or not o.check_out_date:
            continue
        overlap_start = max(o.check_in_date, start_date)
        overlap_end = min(o.check_out_date, query_end)
        nights = max(0, (overlap_end - overlap_start).days)
        occupied_nights += nights

    occupancy = (occupied_nights / total_room_nights * 100) if total_room_nights else 0
    adr = (bill_revenue / occupied_nights) if occupied_nights else 0
    return {
        "revenue": bill_revenue,
        "order_count": len(orders),
        "occupied_nights": occupied_nights,
        "occupancy": occupancy,
        "adr": adr,
    }
