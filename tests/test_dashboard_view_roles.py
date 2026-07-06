# -*- coding: utf-8 -*-
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PyQt5.QtWidgets import QApplication

from src.views.dashboard_view import DashboardView


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication([])
    return _APP


def test_frontdesk_dashboard_hides_business_revenue_chart():
    app = _app()
    view = DashboardView({"id": 2, "role": "\u524d\u53f0", "real_name": "\u524d\u53f0\u5458\u5de5"})
    view.resize(1360, 820)
    view.show()
    app.processEvents()
    assert view.title.text() == "前台接待工作台"
    assert view.summary_panel_title.text() == "接待摘要"
    assert view.primary_chart_title.text() == "房态结构"
    assert view.secondary_chart_title.text() == "下一步处理"
    assert not view.room_type_chart.isVisible()
    assert view.secondary_focus_box.count() >= 3
    aligned_pairs = [
        (view.action_panel, view.order_panel),
        (view.summary_panel, view.quick_panel),
        (view.primary_chart_panel, view.secondary_chart_panel),
    ]
    for top, bottom in aligned_pairs:
        assert abs(top.geometry().x() - bottom.geometry().x()) <= 1
        assert abs(top.geometry().width() - bottom.geometry().width()) <= 1
    assert abs(view.order_panel.geometry().height() - view.quick_panel.geometry().height()) <= 1
    assert abs(view.order_panel.geometry().height() - view.secondary_chart_panel.geometry().height()) <= 1


def test_manager_dashboard_shows_business_revenue_chart():
    _app()
    view = DashboardView({"id": 1, "role": "管理员", "real_name": "管理员"})
    view.show()
    assert view.title.text() == "智能经营工作台"
    assert view.summary_panel_title.text() == "运营摘要"
    assert view.primary_chart_title.text() == "订单结构"
    assert view.secondary_chart_title.text() == "房型收入"
    assert view.secondary_chart_panel.isVisible()
