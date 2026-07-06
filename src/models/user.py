# -*- coding: utf-8 -*-
"""用户模型"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="登录账号")
    password_hash = Column(String(200), nullable=False, comment="密码哈希")
    role = Column(String(20), nullable=False, default="前台", comment="管理员/前台/客房/财务")
    real_name = Column(String(50), comment="真实姓名")
    last_login = Column(DateTime, comment="最后登录时间")
    is_active = Column(Boolean, default=True, comment="账号状态")
