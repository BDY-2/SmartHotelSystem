# -*- coding: utf-8 -*-
"""房型模型"""
from sqlalchemy import Column, Integer, String, Float
from .base import Base

class RoomType(Base):
    __tablename__ = "room_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, comment="大床房/双床房/套房")
    base_price = Column(Float, nullable=False, comment="基准价")
    max_guests = Column(Integer, default=2, comment="最大入住人数")
