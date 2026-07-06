# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.views.main_window import role_nav_items, role_nav_targets


def test_front_role_gets_frontdesk_focused_navigation():
    labels = [item[1] for item in role_nav_items("前台")]
    assert labels == ["仪表盘", "房态管理", "预订管理", "入住办理", "退房结算", "收银台", "客户管理"]
    targets = role_nav_targets("前台")
    assert "settings" not in targets
    assert "reports" not in targets


def test_admin_role_keeps_full_navigation():
    labels = [item[1] for item in role_nav_items("管理员")]
    assert labels == ["仪表盘", "房态管理", "预订管理", "入住办理", "退房结算", "收银台", "客户管理", "报表中心", "系统设置"]
    assert role_nav_targets("管理员")["settings"] == 8


def test_housekeeping_role_only_gets_room_operations():
    labels = [item[1] for item in role_nav_items("客房")]
    assert labels == ["仪表盘", "房态管理"]
    assert role_nav_targets("客房") == {"dashboard": 0, "rooms": 1}
