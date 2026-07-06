# -*- coding: utf-8 -*-
"""操作日志模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from .base import Base

class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(50), comment="操作类型")
    detail = Column(Text, comment="操作详情")
    ip_address = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
