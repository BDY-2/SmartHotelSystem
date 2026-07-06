# -*- coding: utf-8 -*-
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PyQt5.QtWidgets import QApplication, QPushButton

from src.views.dashboard_view import DashboardView
from src.views.settings_view import SettingsView


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication([])
    return _APP


def test_admin_dashboard_replaces_recent_orders_with_wide_visuals():
    _app()
    view = DashboardView({"id": 1, "role": "管理员", "real_name": "管理员"})
    view.show()

    assert not view.order_panel.isVisible()
    assert view.quick_panel.isVisible()
    assert view.trend_panel.isVisible()
    assert view.secondary_chart_panel.isVisible()
    assert view.quick_panel.property("wideManagementPanel") is True
    assert view.trend_panel.property("wideManagementPanel") is True
    assert view.secondary_chart_panel.property("wideManagementPanel") is True


def test_settings_night_audit_has_primary_button_and_result_cards():
    _app()
    view = SettingsView()
    button = view.findChild(QPushButton, "settingsNightAuditButton")

    assert button is not None
    assert "background" in button.styleSheet()
    assert hasattr(view, "audit_revenue_value")
    assert hasattr(view, "audit_occupancy_value")
