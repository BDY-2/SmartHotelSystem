# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.resources.theme import COLORS, GLOBAL_QSS


def test_v3_primary_color_uses_premium_purple():
    assert COLORS["primary"] == "#3C2B56"
    assert "#6d28d9" not in GLOBAL_QSS
    assert "#8b5cf6" not in GLOBAL_QSS


def test_disabled_button_variants_keep_visible_background():
    assert 'QPushButton[variant="text"]:disabled' in GLOBAL_QSS
    assert 'QPushButton[variant="secondary"]:disabled' in GLOBAL_QSS
    assert 'QPushButton[variant="danger"]:disabled' in GLOBAL_QSS
