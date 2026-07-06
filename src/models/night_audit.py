# -*- coding: utf-8 -*-
"""夜审记录模型"""
from sqlalchemy import Column, Integer, Float, Date, DateTime, ForeignKey
from .base import Base

class NightAudit(Base):
    __tablename__ = "night_audit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_date = Column(Date, nullable=False)
    total_revenue = Column(Float, default=0)
    total_orders = Column(Integer, default=0)
    occupancy_rate = Column(Float, default=0)
    adr = Column(Float, default=0)
    revpar = Column(Float, default=0)
    executed_at = Column(DateTime)
    operator_id = Column(Integer, ForeignKey("users.id"))
