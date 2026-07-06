# -*- coding: utf-8 -*-
"""数据库初始化与连接管理"""
import hashlib
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config import DB_CONFIG
from src.models.base import Base
from src.models import User, RoomType, Room, Customer, Order, BillItem
from datetime import date, datetime, timedelta


DEMO_REPORT_END_DATE = date(2026, 7, 10)

# 构建 MySQL 连接 URL
DB_URL = (
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    f"?charset={DB_CONFIG['charset']}"
)

engine = create_engine(DB_URL, echo=False, pool_size=5, pool_recycle=3600)
Session = sessionmaker(bind=engine)


def init_database():
    """创建数据库和表，插入初始数据"""
    # 先创建数据库（如果不存在）
    try:
        tmp_url = (
            f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}"
        )
        tmp_engine = create_engine(tmp_url, echo=False)
        with tmp_engine.connect() as conn:
            conn.execute(text(
                f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
            conn.commit()
        tmp_engine.dispose()
    except Exception as e:
        print(f"数据库创建警告: {e}")

    # 创建所有表
    Base.metadata.create_all(engine)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE orders MODIFY room_id INT NULL"))
            conn.commit()
    except Exception as e:
        print(f"数据库结构兼容警告: {e}")

    # 插入初始数据
    session = Session()
    try:
        _seed_users(session)
        _seed_room_types(session)
        _seed_rooms(session)
        _seed_demo_data(session)
        session.commit()
        print("数据库初始化完成")
    except Exception as e:
        session.rollback()
        print(f"初始化警告（可能已存在数据）: {e}")
    finally:
        session.close()


def _seed_users(session):
    """插入默认用户"""
    if session.query(User).count() > 0:
        return
    users = [
        User(username="admin", password_hash=_hash("admin123"),
             role="管理员", real_name="系统管理员", is_active=True),
        User(username="front", password_hash=_hash("front123"),
             role="前台", real_name="前台员工", is_active=True),
        User(username="finance", password_hash=_hash("finance123"),
             role="财务", real_name="财务员工", is_active=True),
        User(username="room", password_hash=_hash("room123"),
             role="客房", real_name="客房员工", is_active=True),
    ]
    session.add_all(users)


def _seed_room_types(session):
    """插入默认房型"""
    if session.query(RoomType).count() > 0:
        return
    types = [
        RoomType(name="大床房", base_price=288, max_guests=2),
        RoomType(name="双床房", base_price=328, max_guests=2),
        RoomType(name="豪华套房", base_price=588, max_guests=4),
    ]
    session.add_all(types)


def _seed_rooms(session):
    """插入示例房间（2层 x 每层5间）"""
    if session.query(Room).count() > 0:
        return
    rooms = []
    for floor in [2, 3]:
        for num in range(1, 6):
            room_no = f"{floor}0{num}"
            if num <= 3:
                type_id = 1  # 大床房
            elif num == 4:
                type_id = 2  # 双床房
            else:
                type_id = 3  # 套房
            rooms.append(Room(
                room_number=room_no, room_type_id=type_id,
                floor=floor, status="空闲",
                price=[288, 288, 288, 328, 588][num-1],
                description=f"{['大床房','大床房','大床房','双床房','豪华套房'][num-1]}",
            ))
    session.add_all(rooms)


def _hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


def _seed_demo_data(session):
    """插入演示数据（客户 + 订单 + 账单）"""
    if session.query(Customer).count() > 0:
        return
    _insert_v3_demo_data(session)
    return

    today = date.today()

    # 客户
    customers = [
        Customer(name="张伟", phone="13800001111", id_card="310101199001011234",
                 vip_level="金卡", points=18200, total_stays=18, last_stay=today,
                 preference="高楼层, 无烟房"),
        Customer(name="李芳", phone="13900002222", id_card="310101199205202345",
                 vip_level="银卡", points=6200, total_stays=7, last_stay=today,
                 preference="安静, 大床"),
        Customer(name="王强", phone="13700003333", id_card="320501198803303456",
                 vip_level="普通", points=800, total_stays=2, last_stay=today,
                 preference=""),
        Customer(name="赵敏", phone="13600004444", id_card="440101199506154567",
                 vip_level="铂金", points=35600, total_stays=35, last_stay=today,
                 preference="套房, 行政酒廊, 延迟退房"),
        Customer(name="陈明", phone="13500005555", id_card="330101199208055678",
                 vip_level="银卡", points=4500, total_stays=5, last_stay=today,
                 preference="双床, 近电梯"),
    ]
    session.add_all(customers)
    session.flush()

    # 订单: 3间已入住 + 2间已预订（明天的日期）+ 1间空闲
    orders = [
        # 已入住的
        Order(order_no="ORD260701001", customer_id=1, room_id=1, room_type_id=1,
              check_in_date=today, check_out_date=today + timedelta(days=2),
              actual_check_in=datetime.now(), room_price=288, deposit=300,
              total_amount=576, paid_amount=300, status="已入住", guest_count=1),
        Order(order_no="ORD260701002", customer_id=2, room_id=4, room_type_id=2,
              check_in_date=today, check_out_date=today + timedelta(days=1),
              actual_check_in=datetime.now(), room_price=328, deposit=300,
              total_amount=328, paid_amount=300, status="已入住", guest_count=2),
        Order(order_no="ORD260701003", customer_id=4, room_id=5, room_type_id=3,
              check_in_date=today, check_out_date=today + timedelta(days=3),
              actual_check_in=datetime.now(), room_price=588, deposit=500,
              total_amount=1764, paid_amount=500, status="已入住", guest_count=2,
              remark="铂金会员，免费升级套房"),
        # 已预订 明日
        Order(order_no="ORD260701004", customer_id=3, room_id=2, room_type_id=1,
              check_in_date=today + timedelta(days=1),
              check_out_date=today + timedelta(days=3),
              room_price=288, deposit=200, total_amount=576, status="已确认", guest_count=1),
        Order(order_no="ORD260701005", customer_id=5, room_id=3, room_type_id=1,
              check_in_date=today + timedelta(days=1),
              check_out_date=today + timedelta(days=2),
              room_price=288, deposit=200, total_amount=288, status="已确认", guest_count=2),
    ]
    session.add_all(orders)
    session.flush()

    # 更新房间状态
    from sqlalchemy import update
    session.execute(update(Room).where(Room.id == 1).values(status="已入住"))
    session.execute(update(Room).where(Room.id == 4).values(status="已入住"))
    session.execute(update(Room).where(Room.id == 5).values(status="已入住"))
    session.execute(update(Room).where(Room.id == 2).values(status="已预订"))
    session.execute(update(Room).where(Room.id == 3).values(status="已预订"))

    # 账单: 给已入住的订单加一些消费
    bill_items = [
        BillItem(order_id=1, item_type="房费", description="大床房 2晚", amount=576, payment_method="微信"),
        BillItem(order_id=1, item_type="押金", description="入住押金", amount=300, payment_method="微信"),
        BillItem(order_id=1, item_type="杂费", description="Minibar 可乐×2", amount=24, payment_method="挂账"),
        BillItem(order_id=2, item_type="房费", description="双床房 1晚", amount=328, payment_method="支付宝"),
        BillItem(order_id=2, item_type="押金", description="入住押金", amount=300, payment_method="支付宝"),
        BillItem(order_id=3, item_type="房费", description="豪华套房 3晚", amount=1764, payment_method="银行卡"),
        BillItem(order_id=3, item_type="押金", description="入住押金", amount=500, payment_method="银行卡"),
        BillItem(order_id=3, item_type="杂费", description="Minibar 依云水×4", amount=60, payment_method="挂账"),
        BillItem(order_id=3, item_type="杂费", description="加床费", amount=150, payment_method="挂账"),
    ]
    session.add_all(bill_items)


def reset_demo_data(session):
    """重置 v3.0 演示数据。

    用于课堂演示和答辩前恢复一组一致的住客、订单、房态和账务状态。
    """
    _seed_room_types(session)
    _seed_rooms(session)
    session.flush()

    session.query(BillItem).delete(synchronize_session=False)
    session.query(Order).delete(synchronize_session=False)
    session.query(Customer).delete(synchronize_session=False)

    for room in session.query(Room).all():
        room.status = "空闲"

    _insert_v3_demo_data(session)


def _demo_datetime(day, hour=10, minute=5):
    return datetime(day.year, day.month, day.day, hour, minute)


def _insert_v3_demo_data(session):
    today = DEMO_REPORT_END_DATE
    customers = [
        Customer(name="张伟", phone="13800001111", id_card=None,
                 vip_level="金卡", points=18200, total_stays=18,
                 last_stay=today - timedelta(days=1),
                 preference="高楼层, 无烟房, 大床"),
        Customer(name="李芳", phone="13900002222", id_card=None,
                 vip_level="银卡", points=6200, total_stays=7,
                 last_stay=today, preference="安静, 靠窗"),
        Customer(name="王强", phone="13700003333", id_card=None,
                 vip_level="普通", points=800, total_stays=2,
                 last_stay=today - timedelta(days=20), preference=""),
        Customer(name="赵敏", phone="13600004444", id_card=None,
                 vip_level="铂金", points=35600, total_stays=35,
                 last_stay=today, preference="套房, 延迟退房"),
        Customer(name="陈明", phone="13500005555", id_card=None,
                 vip_level="银卡", points=4500, total_stays=5,
                 last_stay=today - timedelta(days=8), preference="双床, 近电梯"),
        Customer(name="周雨", phone="13200006666", id_card=None,
                 vip_level="普通", points=300, total_stays=1,
                 last_stay=today - timedelta(days=45), preference="低楼层"),
        Customer(name="林悦", phone="13100007777", id_card=None,
                 vip_level="金卡", points=12600, total_stays=12,
                 last_stay=today - timedelta(days=2), preference="无烟房"),
    ]
    session.add_all(customers)
    session.flush()

    customer_by_name = {c.name: c.id for c in customers}
    room_type_by_name = {rt.name: rt.id for rt in session.query(RoomType).all()}
    room_by_no = {r.room_number: r.id for r in session.query(Room).all()}

    orders = [
        Order(order_no="BK260705001", customer_id=customer_by_name["张伟"],
              room_id=room_by_no["201"], room_type_id=room_type_by_name["大床房"],
              check_in_date=today - timedelta(days=1), check_out_date=today,
              actual_check_in=datetime.now() - timedelta(days=1),
              room_price=288, deposit=300, total_amount=588, paid_amount=300,
              status="已入住", guest_count=1, remark="今日待退，需收清尾款"),
        Order(order_no="BK260705002", customer_id=customer_by_name["李芳"],
              room_id=room_by_no["202"], room_type_id=room_type_by_name["大床房"],
              check_in_date=today, check_out_date=today + timedelta(days=1),
              actual_check_in=datetime.now(),
              room_price=288, deposit=300, total_amount=588, paid_amount=588,
              status="已入住", guest_count=1, remark="已结清"),
        Order(order_no="BK260705003", customer_id=customer_by_name["赵敏"],
              room_id=room_by_no["302"], room_type_id=room_type_by_name["豪华套房"],
              check_in_date=today, check_out_date=today + timedelta(days=2),
              actual_check_in=datetime.now(),
              room_price=588, deposit=500, total_amount=1676, paid_amount=1676,
              status="已入住", guest_count=2, remark="铂金会员，套房偏好"),
        Order(order_no="BK260705004", customer_id=customer_by_name["王强"],
              room_id=None, room_type_id=room_type_by_name["大床房"],
              check_in_date=today, check_out_date=today + timedelta(days=1),
              room_price=288, deposit=300, total_amount=588, paid_amount=0,
              status="已确认", guest_count=1, remark="今日预抵，待分房"),
        Order(order_no="BK260705005", customer_id=customer_by_name["陈明"],
              room_id=room_by_no["304"], room_type_id=room_type_by_name["双床房"],
              check_in_date=today, check_out_date=today + timedelta(days=1),
              room_price=328, deposit=300, total_amount=628, paid_amount=0,
              status="已确认", guest_count=2, remark="今日预抵，已预留房间"),
        Order(order_no="BK260706001", customer_id=customer_by_name["周雨"],
              room_id=None, room_type_id=room_type_by_name["豪华套房"],
              check_in_date=today + timedelta(days=1),
              check_out_date=today + timedelta(days=3),
              room_price=588, deposit=500, total_amount=1676, paid_amount=0,
              status="已确认", guest_count=2, remark="明日预抵"),
        Order(order_no="BK260704001", customer_id=customer_by_name["林悦"],
              room_id=room_by_no["203"], room_type_id=room_type_by_name["大床房"],
              check_in_date=today - timedelta(days=2),
              check_out_date=today - timedelta(days=1),
              actual_check_in=datetime.now() - timedelta(days=2),
              actual_check_out=datetime.now() - timedelta(days=1),
              room_price=288, deposit=300, total_amount=876, paid_amount=876,
              status="已退房", guest_count=1, remark="已退房，房间待清洁"),
    ]
    trend_amounts = [520, 680, 610, 740, 820, 760, 980, 1120, 940, 1280, 1360, 1510, 1660, 1840]
    trend_room_types = ["大床房", "大床房", "双床房", "大床房", "豪华套房", "双床房", "大床房"]
    trend_customers = ["张伟", "李芳", "王强", "赵敏", "陈明", "周雨", "林悦"]
    for offset, amount in enumerate(trend_amounts):
        day = today - timedelta(days=13 - offset)
        room_type_name = trend_room_types[offset % len(trend_room_types)]
        customer_name = trend_customers[offset % len(trend_customers)]
        orders.append(Order(
            order_no=f"TR{day.strftime('%y%m%d')}{offset + 1:02d}",
            customer_id=customer_by_name[customer_name],
            room_id=None,
            room_type_id=room_type_by_name[room_type_name],
            check_in_date=day,
            check_out_date=day + timedelta(days=1),
            actual_check_in=_demo_datetime(day, 15, 0),
            actual_check_out=_demo_datetime(day + timedelta(days=1), 11, 0),
            room_price=amount,
            deposit=300,
            total_amount=amount,
            paid_amount=amount,
            status="已退房",
            guest_count=1,
            remark="两周收入趋势演示数据",
        ))
    session.add_all(orders)
    session.flush()

    room_status = {
        "201": "已入住",
        "202": "已入住",
        "203": "脏房",
        "204": "空闲",
        "205": "维修",
        "301": "空闲",
        "302": "已入住",
        "303": "空闲",
        "304": "已预订",
        "305": "空闲",
    }
    for room in session.query(Room).all():
        room.status = room_status.get(room.room_number, "空闲")

    order_by_no = {o.order_no: o.id for o in orders}
    session.add_all([
        BillItem(order_id=order_by_no["BK260705001"], item_type="押金",
                 description="入住押金", amount=300, payment_method="微信",
                 created_at=_demo_datetime(today - timedelta(days=1), 15, 8)),
        BillItem(order_id=order_by_no["BK260705001"], item_type="房费",
                 description="201 大床房 1晚", amount=288, payment_method="挂账",
                 created_at=_demo_datetime(today - timedelta(days=1), 15, 10)),
        BillItem(order_id=order_by_no["BK260705002"], item_type="房费",
                 description="202 大床房 1晚", amount=288, payment_method="支付宝",
                 created_at=_demo_datetime(today, 10, 15)),
        BillItem(order_id=order_by_no["BK260705002"], item_type="押金",
                 description="入住押金", amount=300, payment_method="支付宝",
                 created_at=_demo_datetime(today, 10, 16)),
        BillItem(order_id=order_by_no["BK260705003"], item_type="房费",
                 description="302 豪华套房 2晚", amount=1176, payment_method="银行卡",
                 created_at=_demo_datetime(today, 11, 5)),
        BillItem(order_id=order_by_no["BK260705003"], item_type="押金",
                 description="入住押金", amount=500, payment_method="银行卡",
                 created_at=_demo_datetime(today, 11, 6)),
        BillItem(order_id=order_by_no["BK260704001"], item_type="房费",
                 description="203 大床房 2晚", amount=576, payment_method="微信",
                 created_at=_demo_datetime(today - timedelta(days=2), 10, 30)),
        BillItem(order_id=order_by_no["BK260704001"], item_type="押金",
                 description="入住押金", amount=300, payment_method="微信",
                 created_at=_demo_datetime(today - timedelta(days=2), 10, 31)),
    ])
    for offset, amount in enumerate(trend_amounts):
        day = today - timedelta(days=13 - offset)
        session.add(BillItem(
            order_id=order_by_no[f"TR{day.strftime('%y%m%d')}{offset + 1:02d}"],
            item_type="房费",
            description=f"{day.strftime('%m-%d')} 演示房费收入",
            amount=amount,
            payment_method=["微信", "支付宝", "银行卡"][offset % 3],
            created_at=_demo_datetime(day, 12, 0),
        ))
