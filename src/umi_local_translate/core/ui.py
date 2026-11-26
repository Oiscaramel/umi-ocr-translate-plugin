# -*- coding: utf-8 -*-
"""QML 窗口管理（独立翻译窗口）。"""

import os

from . import compat, log, paths


class Ui:
    def __init__(self, backend, cfg):
        self.backend = backend
        self.cfg = cfg
        self._win = None
        self._import_path = compat.qml_import_path()

    # ------------------------------------------------------------------

    def _create(self, qml_name, flags, size):
        from PySide2.QtCore import Qt, QUrl
        from PySide2.QtQuick import QQuickView

        view = QQuickView()
        view.setColor(Qt.transparent)
        view.setFlags(flags)
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        if self._import_path:
            view.engine().addImportPath(self._import_path)
        view.rootContext().setContextProperty("backend", self.backend)
        view.setSource(QUrl.fromLocalFile(os.path.join(paths.QML_DIR, qml_name)))
        if view.status() == QQuickView.Error:
            for err in view.errors():
                log.get().error("QML 错误 [%s] %s", qml_name, err.toString())
        view.resize(size[0], size[1])
        return view

    # ------------------------------------------------------------------

    def show_window(self):
        from PySide2.QtCore import Qt

        win_cfg = self.cfg.get("window", {})
        if self._win is None:
            flags = Qt.Window | Qt.FramelessWindowHint
            if win_cfg.get("always_on_top", False):
                flags |= Qt.WindowStaysOnTopHint
            w = int(win_cfg.get("width", 760))
            h = int(win_cfg.get("height", 420))
            self._win = self._create("TranslateWindow.qml", flags, (w, h))
            self._apply_geometry(win_cfg)
        self._win.show()
        try:
            self._win.raise_()
            self._win.requestActivate()
        except Exception:  # noqa: BLE001
            pass

    def hide_window(self):
        if self._win is None:
            return
        self._remember_geometry()
        self._win.hide()

    def _apply_geometry(self, win_cfg):
        """恢复上次位置；没有记录则居中。"""
        try:
            from PySide2.QtGui import QGuiApplication

            scr = QGuiApplication.primaryScreen()
            if scr is None:
                return
            geo = scr.availableGeometry()
            x = win_cfg.get("x")
            y = win_cfg.get("y")
            if x is None or y is None:
                self._center(self._win)
                return
            x = int(x)
            y = int(y)
            # 防止显示器变化后窗口跑到屏幕外
            x = max(geo.x(), min(x, geo.x() + geo.width() - 240))
            y = max(geo.y(), min(y, geo.y() + geo.height() - 160))
            self._win.setPosition(x, y)
        except Exception:  # noqa: BLE001
            pass

    def _remember_geometry(self):
        try:
            pos = self._win.position()
            win_cfg = self.cfg.setdefault("window", {})
            win_cfg["x"] = pos.x()
            win_cfg["y"] = pos.y()
            win_cfg["width"] = self._win.width()
            win_cfg["height"] = self._win.height()
            self.backend.app.save_config()
        except Exception:  # noqa: BLE001
            pass

    def start_resize(self, edge):
        if self._win is None:
            return
        from PySide2.QtCore import Qt

        table = {
            "left": Qt.LeftEdge,
            "right": Qt.RightEdge,
            "top": Qt.TopEdge,
            "bottom": Qt.BottomEdge,
            "topleft": Qt.LeftEdge | Qt.TopEdge,
            "topright": Qt.RightEdge | Qt.TopEdge,
            "bottomleft": Qt.LeftEdge | Qt.BottomEdge,
            "bottomright": Qt.RightEdge | Qt.BottomEdge,
        }
        e = table.get(edge)
        if e is None:
            return
        try:
            self._win.startSystemResize(e)
        except Exception:  # noqa: BLE001
            pass

    def set_always_on_top(self, on):
        if self._win is None:
            return
        from PySide2.QtCore import Qt

        geo = self._win.geometry()
        visible = self._win.isVisible()
        flags = self._win.flags()
        if on:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        self._win.setFlags(flags)
        self._win.setGeometry(geo)
        if visible:
            self._win.show()
            try:
                self._win.raise_()
            except Exception:  # noqa: BLE001
                pass

    def _center(self, view):
        try:
            from PySide2.QtGui import QGuiApplication

            scr = QGuiApplication.primaryScreen()
            if scr is None:
                return
            geo = scr.availableGeometry()
            view.setPosition(
                geo.x() + (geo.width() - view.width()) // 2,
                geo.y() + (geo.height() - view.height()) // 2,
            )
        except Exception:  # noqa: BLE001
            pass

    def move_by(self, dx, dy):
        if self._win is None:
            return
        pos = self._win.position()
        self._win.setPosition(pos.x() + int(dx), pos.y() + int(dy))
