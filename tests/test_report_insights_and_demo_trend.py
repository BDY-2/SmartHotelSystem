# -*- coding: utf-8 -*-
import os
import sys
from datetime import date, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from PyQt5.QtWidgets import QApplication

from src.models.base import Base
from src.models.bill_item import BillItem
from src.models.room import Room
from src.models.room_type import RoomType
from src.services.report_insight_service import build_report_insights
from src.utils.db import reset_demo_data
from src.views.report_view import ReportView


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication([])
    return _APP


def make_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    s.add_all([
        RoomType(id=1, name="大床房", base_price=288, max_guests=2),
        RoomType(id=2, name="双床房", base_price=328, max_guests=2),
        RoomType(id=3, name="豪华套房", base_price=588, max_guests=4),
    ])
    for floor in (2, 3):
        for num in range(1, 6):
            price = [288, 288, 288, 328, 588][num - 1]
            s.add(Room(room_number=f"{floor}0{num}", room_type_id=1 if num <= 3 else 2 if num == 4 else 3,
                       floor=floor, status="空闲", price=price))
    s.commit()
    return s


def test_reset_demo_data_writes_two_weeks_of_revenue_items():
    s = make_session()
    reset_demo_data(s)
    s.commit()

    today = date(2026, 7, 10)
    days = {
        item.created_at.date()
        for item in s.query(BillItem).filter(BillItem.item_type == "房费").all()
        if today - timedelta(days=13) <= item.created_at.date() <= today
    }

    assert len(days) == 14
    s.close()


def test_report_insight_service_outputs_analysis_and_suggestions():
    insights = build_report_insights(
        {"revenue": 8800, "order_count": 18, "occupancy": 78.5, "adr": 410},
        [{"date": f"07-{i:02d}", "value": 300 + i * 80} for i in range(1, 15)],
        {"豪华套房": 5200, "大床房": 2600},
    )

    titles = [item[0] for item in insights]
    text = "\n".join(item[1] for item in insights)
    assert "趋势" in titles
    assert "出租率" in titles
    assert "建议" in titles
    assert "豪华套房" in text


def test_report_view_defaults_to_july_10_demo_window_and_has_ai_panel():
    _app()
    view = ReportView()

    assert view.to_d.date().toString("yyyy-MM-dd") == "2026-07-10"
    assert view.from_d.date().toString("yyyy-MM-dd") == "2026-06-27"
    assert view.assistant_rows.count() >= 1
