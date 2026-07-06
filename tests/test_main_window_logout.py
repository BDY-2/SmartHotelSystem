# -*- coding: utf-8 -*-
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PyQt5.QtWidgets import QApplication, QPushButton

from src.views.main_window import MainWindow, role_nav_targets


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication([])
    return _APP


def test_frontdesk_can_switch_account_without_settings_page():
    _app()
    assert "settings" not in role_nav_targets("\u524d\u53f0")

    window = MainWindow({"id": 2, "role": "\u524d\u53f0", "real_name": "\u524d\u53f0\u5458\u5de5"})
    buttons = window.findChildren(QPushButton, "sidebarSwitchAccountButton")

    assert len(buttons) == 1
    assert buttons[0].text() == "\u5207\u6362"
