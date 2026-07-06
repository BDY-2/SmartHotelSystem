# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_views_no_longer_use_native_input_dialogs():
    views_dir = os.path.join(os.path.dirname(__file__), "..", "src", "views")
    offenders = []
    for name in os.listdir(views_dir):
        if not name.endswith(".py"):
            continue
        path = os.path.join(views_dir, name)
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        if "QInputDialog" in source or "getText(" in source:
            offenders.append(name)
    assert offenders == []
