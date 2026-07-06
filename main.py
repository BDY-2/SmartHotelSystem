# -*- coding: utf-8 -*-
"""
智能民宿管理系统 v3.0
智能化 / 可视化 / 角色化工作台
技术栈: Python + PyQt5 + MySQL + SQLAlchemy
"""
import sys
import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from src.utils.db import init_database
from src.views.login_window import LoginWindow
from src.views.main_window import MainWindow
from src.resources.theme import GLOBAL_QSS, install_styled_message_boxes


def main():
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    init_database()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    base_font = QFont("Microsoft YaHei", 11)
    base_font.setHintingPreference(QFont.PreferFullHinting)
    base_font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(base_font)
    app.setStyleSheet(GLOBAL_QSS)
    install_styled_message_boxes()

    login = LoginWindow()

    def on_login(user_info):
        login.hide()
        w = MainWindow(user_info)
        w.show()
        app._mw = w
        w.logout_signal.connect(lambda: on_logout())

    def on_logout():
        app._mw = None
        login.show()

    login.login_success.connect(on_login)
    login.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
