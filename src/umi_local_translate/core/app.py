# -*- coding: utf-8 -*-
"""插件应用装配：事件订阅 + 热键 + 服务 + 界面。"""

import threading

from . import compat, config, embed, log
from .backend import Backend
from .hotkey import HotkeyListener
from .service_manager import ServiceManager
from .ui import Ui


class App:
    def __init__(self, cfg):
        self.cfg = cfg
        self.last_text = ""
        self._hotkey = None
        self._started = False
        self._scanner = None
        self.service = ServiceManager(cfg)
        self.backend = Backend(self)
        self.ui = Ui(self.backend, cfg)

    # ------------------------------------------------------------------

    def start(self):
        if self._started:
            return
        self._started = True

        compat.subscribe("<<ScreenshotOcrEnd>>", self._on_ocr_end)
        self._restart_hotkey()

        try:
            from PySide2.QtGui import QGuiApplication

            app = QGuiApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(self.shutdown)
        except Exception:  # noqa: BLE001
            log.get().exception("连接 aboutToQuit 失败")

        # 定时把「翻译」标签注入到截图OCR页面（页面可能稍后才创建）
        if self.cfg.get("embed_button", True):
            try:
                self._scanner = embed.Scanner(self)
                self._scanner.start()
            except Exception:  # noqa: BLE001
                log.get().exception("启动内嵌「翻译」按钮失败")

        if self.cfg.get("preload"):
            threading.Thread(target=self._preload, name="umi-translate-preload", daemon=True).start()

        log.get().info(
            "本地翻译插件已启动（hotkey=%s, enabled=%s）",
            self.cfg.get("hotkey"),
            self.cfg.get("hotkey_enabled", True),
        )

    def _preload(self):
        try:
            self.service.ensure_started()
            log.get().info("翻译服务预热完成")
        except Exception as e:  # noqa: BLE001
            log.get().warning("翻译服务预热失败: %s", e)

    # ------------------------------------------------------------------
    # 热键
    # ------------------------------------------------------------------

    def apply_hotkey(self, combo, enabled=True):
        """运行时修改热键并落盘。返回 (ok, message)。"""
        combo = (combo or "").strip().lower()
        self.cfg["hotkey"] = combo
        self.cfg["hotkey_enabled"] = bool(enabled)
        self.save_config()
        self._restart_hotkey()

        if not enabled:
            return True, "独立窗口热键已关闭。"
        if not combo:
            return True, "热键为空，已关闭。"
        hk = self._hotkey
        if hk is None:
            return False, "热键注册失败。"
        if hk.failed:
            return False, "热键不可用：%s" % (hk.error or combo)
        return True, "热键已生效：%s" % combo

    def _restart_hotkey(self):
        if self._hotkey is not None:
            try:
                self._hotkey.stop()
            except Exception:  # noqa: BLE001
                pass
            self._hotkey = None

        if not self.cfg.get("hotkey_enabled", True):
            log.get().info("独立窗口热键已关闭")
            return

        combo = (self.cfg.get("hotkey") or "").strip()
        if not combo:
            return
        try:
            hk = HotkeyListener(combo, self._on_hotkey)
            hk.start()
            try:
                hk._ready.wait(1.2)
            except Exception:  # noqa: BLE001
                pass
            self._hotkey = hk
            if hk.failed:
                log.get().warning("热键 %s 注册失败: %s", combo, hk.error)
        except Exception:  # noqa: BLE001
            log.get().exception("注册热键失败")

    def _on_hotkey(self):
        # 热键线程 -> 主线程（Backend.hotkeyPressed 是排队连接）
        self.backend.hotkeyPressed.emit()

    # ------------------------------------------------------------------
    # 打开翻译（内嵌面板优先，否则独立窗口）
    # ------------------------------------------------------------------

    def open_translate(self, text=None):
        host = embed.active_host()
        if host is not None and host.is_alive():
            host.open_external(text)
            return True

        self.ui.show_window()
        text = (text or embed.active_text() or self.last_text or "").strip()
        if text:
            self.backend.translate_text(text)
        return False

    # ------------------------------------------------------------------

    def _on_ocr_end(self, payload):
        try:
            text = compat.collect_ocr_text(payload)
        except Exception:  # noqa: BLE001
            log.get().exception("解析 OCR 结果失败")
            return
        if not text:
            log.get().debug("收到识图结束事件（无文字）")
            return
        log.get().info("收到识图结果，共 %d 字", len(text))
        self.last_text = text
        # 通过信号切回主线程
        self.backend.ocrTextArrived.emit(text)

    # ------------------------------------------------------------------

    def save_config(self):
        try:
            config.save(self.cfg)
        except Exception:  # noqa: BLE001
            log.get().exception("保存配置失败")

    def shutdown(self):
        try:
            if self._hotkey is not None:
                self._hotkey.stop()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.service.stop()
        except Exception:  # noqa: BLE001
            pass
        log.get().info("本地翻译插件已退出")
