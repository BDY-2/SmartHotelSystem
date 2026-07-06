# -*- coding: utf-8 -*-
"""账单明细模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from .base import Base

class BillItem(Base):
    __tablename__ = "bill_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    item_type = Column(String(20), nullable=False, comment="房费/押金/杂费/退款")
    description = Column(String(200))
    amount = Column(Float, nullable=False, comment="正=收入,负=退款")
    payment_method = Column(String(20), comment="现金/微信/支付宝/银行卡")
    created_at = Column(DateTime, server_default=func.now())
