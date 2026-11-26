# -*- coding: utf-8 -*-
"""QML 后端：属性 + 槽 + 线程编组。"""

import json
import os
import subprocess
import threading

from PySide2.QtCore import Property, QObject, Signal, Slot

from . import config, log, paths

LANG_LABEL = {"zh": "中文", "en": "英文"}


class Backend(QObject):
    # ---- 通知信号 ----
    statusChanged = Signal()
    sourceChanged = Signal()
    targetChanged = Signal()
    busyChanged = Signal()
    directionChanged = Signal()
    autoTranslateChanged = Signal()
    lineModeChanged = Signal()
    pinnedChanged = Signal()
    serviceTextChanged = Signal()
    hotkeyChanged = Signal()
    toastMessage = Signal(str)

    # ---- 线程编组 ----
    ocrTextArrived = Signal(str)
    translateEvent = Signal(int, str)
    serviceTextUpdate = Signal(str)
    busyUpdate = Signal(bool)
    hotkeyPressed = Signal()

    def __init__(self, app):
        super().__init__()
        self.app = app
        self._status = "就绪"
        self._source = ""
        self._target = ""
        self._busy = False
        self._direction = app.cfg.get("direction", "auto")
        self._auto = bool(app.cfg.get("auto_translate", False))
        self._line_mode = app.cfg.get("line_mode", "block")
        self._service_text = "未启动"
        self._req = 0
        self.ocrTextArrived.connect(self._on_ocr_text)
        self.translateEvent.connect(self._on_translate_event)
        self.serviceTextUpdate.connect(self._on_service_text_update)
        self.busyUpdate.connect(self._on_busy_update)
        self.hotkeyPressed.connect(self._on_hotkey_pressed)

    # ================= 属性 =================

    def _get_status(self):
        return self._status

    def _set_status(self, v):
        v = v or ""
        if v != self._status:
            self._status = v
            self.statusChanged.emit()

    statusText = Property(str, _get_status, notify=statusChanged)

    def _get_source(self):
        return self._source

    def _set_source(self, v):
        v = v or ""
        if v != self._source:
            self._source = v
            self.sourceChanged.emit()

    sourceText = Property(str, _get_source, _set_source, notify=sourceChanged)

    def _get_target(self):
        return self._target

    def _set_target(self, v):
        v = v or ""
        if v != self._target:
            self._target = v
            self.targetChanged.emit()

    targetText = Property(str, _get_target, notify=targetChanged)

    def _get_busy(self):
        return self._busy

    def _set_busy(self, v):
        v = bool(v)
        if v != self._busy:
            self._busy = v
            self.busyChanged.emit()

    busy = Property(bool, _get_busy, notify=busyChanged)

    def _get_direction(self):
        return self._direction

    def _set_direction(self, v):
        v = v or "auto"
        if v != self._direction:
            self._direction = v
            self.directionChanged.emit()
            self.app.cfg["direction"] = v
            self.app.save_config()

    direction = Property(str, _get_direction, notify=directionChanged)

    def _get_auto(self):
        return self._auto

    autoTranslate = Property(bool, _get_auto, notify=autoTranslateChanged)

    def _get_line_mode(self):
        return self._line_mode

    lineMode = Property(str, _get_line_mode, notify=lineModeChanged)

    def _get_pinned(self):
        return bool(self.app.cfg.get("window", {}).get("always_on_top", False))

    pinned = Property(bool, _get_pinned, notify=pinnedChanged)

    def _get_service_text(self):
        return self._service_text

    def _set_service_text(self, v):
        if v != self._service_text:
            self._service_text = v
            self.serviceTextChanged.emit()

    serviceText = Property(str, _get_service_text, notify=serviceTextChanged)

    def _get_hotkey_enabled(self):
        return bool(self.app.cfg.get("hotkey_enabled", True))

    hotkeyEnabled = Property(bool, _get_hotkey_enabled, notify=hotkeyChanged)

    def _get_hotkey_text(self):
        return self.app.cfg.get("hotkey") or ""

    hotkeyText = Property(str, _get_hotkey_text, notify=hotkeyChanged)

    # ================= 槽：线程回主线程 =================

    @Slot(str)
    def _on_service_text_update(self, text):
        self._set_service_text(text)

    @Slot(bool)
    def _on_busy_update(self, busy):
        self._set_busy(busy)

    @Slot()
    def _on_hotkey_pressed(self):
        from . import embed

        text = embed.active_text() or self.app.last_text or self._source
        text = (text or "").strip()
        self._set_source(text)
        self.app.ui.show_window()
        if text:
            self._start(text)

    # ================= 槽：翻译 =================

    @Slot()
    def translateLastOcr(self):
        self.app.open_translate()

    @Slot()
    def requestTranslate(self):
        self._start(self._source)

    @Slot(str)
    def translate_text(self, text):
        self._set_source(text)
        self._start(text)

    @Slot(str)
    def set_source_text(self, text):
        self._set_source(text)

    @Slot(str)
    def status_message(self, msg):
        self._set_status(msg)

    @Slot(str)
    def setDirection(self, d):
        if d in ("auto", "zh-en", "en-zh"):
            self._set_direction(d)

    @Slot()
    def cycleDirection(self):
        order = ["auto", "zh-en", "en-zh"]
        try:
            i = order.index(self._direction)
        except ValueError:
            i = 0
        self._set_direction(order[(i + 1) % len(order)])

    def _start(self, text):
        text = (text or "").strip()
        if not text:
            self._set_status("没有可翻译的文本。")
            return
        if self._busy:
            return
        self._set_busy(True)
        self._req += 1
        rid = self._req
        src, tgt = config.direction_to_langs(self._direction)
        mode = self._line_mode
        self._set_status("正在启动翻译服务…")
        t = threading.Thread(
            target=self._worker, args=(rid, text, src, tgt, mode), name="umi-translate", daemon=True
        )
        t.start()

    def _worker(self, rid, text, src, tgt, mode):
        def progress(msg):
            self.translateEvent.emit(
                rid, json.dumps({"phase": "progress", "message": msg}, ensure_ascii=False)
            )

        try:
            res = self.app.service.translate(
                text, source=src, target=tgt, mode=mode, on_progress=progress
            )
            self.translateEvent.emit(
                rid, json.dumps({"phase": "done", "result": res}, ensure_ascii=False)
            )
        except Exception as e:  # noqa: BLE001
            log.get().exception("翻译请求失败")
            self.translateEvent.emit(
                rid, json.dumps({"phase": "error", "message": str(e)}, ensure_ascii=False)
            )

    @Slot(int, str)
    def _on_translate_event(self, rid, payload):
        if rid != self._req:
            return
        try:
            ev = json.loads(payload)
        except Exception:  # noqa: BLE001
            return
        phase = ev.get("phase")
        if phase == "progress":
            self._set_status(ev.get("message") or "处理中…")
            return
        if phase == "done":
            res = ev.get("result") or {}
            self._set_target(res.get("text") or "")
            src = res.get("src", "?")
            tgt = res.get("tgt", "?")
            self._set_status(
                "%s → %s · %d ms · %s 段%s"
                % (
                    LANG_LABEL.get(src, src),
                    LANG_LABEL.get(tgt, tgt),
                    res.get("ms", 0),
                    res.get("segments", 0),
                    " · 缓存" if res.get("cached") else "",
                )
            )
            self._set_busy(False)
            self._update_service_text()
            return
        # error
        self._set_busy(False)
        self._set_status("翻译失败：" + (ev.get("message") or "未知错误"))
        self._update_service_text()

    # ================= 槽：OCR 文本 =================

    @Slot(str)
    def _on_ocr_text(self, text):
        if not text:
            return
        self._set_source(text)
        if self._auto:
            self.app.open_translate(text)

    # ================= 槽：界面 =================

    @Slot()
    def closeWindow(self):
        self.app.ui.hide_window()

    @Slot()
    def showWindow(self):
        self.app.ui.show_window()

    @Slot(int, int)
    def moveBy(self, dx, dy):
        self.app.ui.move_by(dx, dy)

    @Slot(str)
    def startResize(self, edge):
        self.app.ui.start_resize(edge)

    @Slot()
    def togglePin(self):
        new = not self._get_pinned()
        self.app.cfg.setdefault("window", {})["always_on_top"] = new
        self.app.ui.set_always_on_top(new)
        self.app.save_config()
        self.pinnedChanged.emit()

    @Slot()
    def copySource(self):
        self._copy(self._source)

    @Slot()
    def copyTarget(self):
        self._copy(self._target)

    def _copy(self, text):
        if not text:
            self._set_status("没有可复制的内容。")
            return
        try:
            from PySide2.QtGui import QGuiApplication

            cb = QGuiApplication.clipboard()
            if cb is not None:
                cb.setText(text)
                self._set_status("已复制到剪贴板。")
        except Exception:  # noqa: BLE001
            log.get().exception("复制失败")

    @Slot()
    def toggleAutoTranslate(self):
        self._auto = not self._auto
        self.app.cfg["auto_translate"] = self._auto
        self.autoTranslateChanged.emit()
        self.app.save_config()

    @Slot()
    def toggleLineMode(self):
        self._line_mode = "line" if self._line_mode == "block" else "block"
        self.app.cfg["line_mode"] = self._line_mode
        self.lineModeChanged.emit()
        self.app.save_config()

    # ================= 槽：独立窗口热键 =================

    @Slot(bool)
    def setHotkeyEnabled(self, on):
        ok, msg = self.app.apply_hotkey(self._get_hotkey_text(), bool(on))
        self._set_status(msg)
        self.hotkeyChanged.emit()

    @Slot(str)
    def applyHotkey(self, combo):
        ok, msg = self.app.apply_hotkey(combo, True)
        self._set_status(msg)
        self.hotkeyChanged.emit()

    # ================= 槽：服务 =================

    @Slot()
    def restartService(self):
        self._set_busy(True)
        self._set_status("正在重启翻译服务…")

        def job():
            try:
                self.app.service.stop()
                self.app.service.ensure_started(
                    on_progress=lambda m: self.translateEvent.emit(
                        self._req,
                        json.dumps({"phase": "progress", "message": m}, ensure_ascii=False),
                    )
                )
                msg = "服务已就绪。"
            except Exception as e:  # noqa: BLE001
                msg = "服务启动失败：%s" % e
            self.translateEvent.emit(
                self._req,
                json.dumps({"phase": "progress", "message": msg}, ensure_ascii=False),
            )
            self.busyUpdate.emit(False)
            self._update_service_text()

        threading.Thread(target=job, name="umi-translate-restart", daemon=True).start()

    @Slot()
    def stopService(self):
        def job():
            try:
                self.app.service.stop()
            except Exception:  # noqa: BLE001
                pass
            self._update_service_text()

        threading.Thread(target=job, name="umi-translate-stop", daemon=True).start()
        self._set_status("已停止翻译服务。")

    def _update_service_text(self):
        def job():
            self.serviceTextUpdate.emit(self.app.service.status_text())

        threading.Thread(target=job, name="umi-translate-status", daemon=True).start()

    @Slot()
    def refreshService(self):
        self._update_service_text()

    @Slot()
    def openLogs(self):
        try:
            os.startfile(paths.LOGS_DIR)
        except Exception:  # noqa: BLE001
            log.get().exception("打开日志目录失败")

    @Slot(result=str)
    def runtimeInfo(self):
        rt = "系统 Python 3.8（插件内）"
        bits = [
            "服务：%s" % self._service_text,
            "模型：%s" % ("已就绪" if paths.model_ready() else "缺失"),
            "运行时：%s" % ("已就绪" if paths.runtime_ready() else "缺失"),
        ]
        return " · ".join(bits)
