# -*- coding: utf-8 -*-
"""订单模型"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from .base import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(20), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    room_type_id = Column(Integer, ForeignKey("room_types.id"))
    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    actual_check_in = Column(DateTime)
    actual_check_out = Column(DateTime)
    room_price = Column(Float, default=0)
    deposit = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    paid_amount = Column(Float, default=0)
    status = Column(String(20), default="待确认", comment="待确认/已确认/已入住/已退房/已取消")
    guest_count = Column(Integer, default=1)
    remark = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
