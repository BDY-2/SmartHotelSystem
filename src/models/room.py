# -*- coding: utf-8 -*-
"""房源模型"""
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from .base import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_number = Column(String(20), unique=True, nullable=False, comment="房间号")
    room_type_id = Column(Integer, ForeignKey("room_types.id"), nullable=False)
    floor = Column(Integer, comment="楼层")
    status = Column(String(20), default="空闲", comment="空闲/已入住/已预订/脏房/维修")
    price = Column(Float, comment="实际房价")
    description = Column(Text, comment="房间描述")
