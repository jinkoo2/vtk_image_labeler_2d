"""Splash screen used at Image Labeler 2D startup."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from splash_screen import close_splash, create_splash, show_message


def test_splash_shows_title_and_closes():
    app = QApplication.instance() or QApplication([])
    icon = QIcon()
    splash = create_splash(version="0.1.4", icon=icon)
    assert splash.pixmap().width() == 460
    assert splash.pixmap().height() == 280

    splash.show()
    show_message(splash, "Building main window...")
    assert "Building main window..." in splash.message()
    close_splash(splash)
    app.processEvents()
    assert not splash.isVisible()
