# -*- coding: utf-8 -*-
"""客户模型"""
from sqlalchemy import Column, Integer, String, Text, Date
from .base import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, comment="姓名")
    phone = Column(String(20), comment="手机号")
    id_card = Column(String(18), comment="身份证号")
    vip_level = Column(String(20), default="普通", comment="普通/银卡/金卡")
    points = Column(Integer, default=0, comment="积分")
    total_stays = Column(Integer, default=0, comment="累计入住")
    last_stay = Column(Date, comment="最近入住日期")
    preference = Column(Text, comment="偏好")
