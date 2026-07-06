# -*- coding: utf-8 -*-
"""Lightweight in-process event bus for cross-page data synchronization."""
from PyQt5.QtCore import QObject, pyqtSignal


class EventBus(QObject):
    data_changed = pyqtSignal(str)


event_bus = EventBus()


def notify_data_changed(topic="all"):
    event_bus.data_changed.emit(topic or "all")
