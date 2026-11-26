# -*- coding: utf-8 -*-
"""全局热键（纯 ctypes，不依赖 pynput/keyboard）。"""

import ctypes
import threading
from ctypes import wintypes

from . import log

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

_MODS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "meta": MOD_WIN,
    "cmd": MOD_WIN,
}

_VK = {
    "space": 0x20,
    "enter": 0x0D,
    "return": 0x0D,
    "esc": 0x1B,
    "escape": 0x1B,
    "tab": 0x09,
    "insert": 0x2D,
    "delete": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
}
for _i in range(1, 13):
    _VK["f%d" % _i] = 0x6F + _i


def parse(combo):
    combo = (combo or "").strip().lower()
    if not combo:
        return 0, 0
    mods = 0
    key = ""
    for part in combo.split("+"):
        part = part.strip()
        if not part:
            continue
        if part in _MODS:
            mods |= _MODS[part]
        else:
            key = part
    if not key:
        raise ValueError("热键缺少主键: %s" % combo)
    if len(key) == 1:
        vk = ord(key.upper())
    else:
        vk = _VK.get(key)
        if vk is None:
            raise ValueError("不支持的热键: %s" % combo)
    return mods, vk


class HotkeyListener(threading.Thread):
    def __init__(self, combo, callback):
        super().__init__(name="umi-translate-hotkey", daemon=True)
        self.combo = combo
        self.callback = callback
        self.failed = False
        self.error = ""
        self._tid = 0
        self._ready = threading.Event()
        self._stop = False
        self._user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None

    def run(self):
        try:
            mods, vk = parse(self.combo)
        except Exception as e:  # noqa: BLE001
            self.failed = True
            self.error = str(e)
            self._ready.set()
            log.get().warning("热键解析失败: %s", self.error)
            return
        if not vk:
            self._ready.set()
            return

        u = self._user32
        self._tid = ctypes.windll.kernel32.GetCurrentThreadId()
        self._ready.set()
        if not u.RegisterHotKey(None, 1, mods | MOD_NOREPEAT, vk):
            self.failed = True
            self.error = "RegisterHotKey 失败（可能被其他程序占用）"
            log.get().warning("热键 %s 注册失败", self.combo)
            return

        log.get().info("热键已注册: %s", self.combo)
        try:
            msg = wintypes.MSG()
            while not self._stop:
                r = u.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if r == 0 or r == -1:
                    break
                if msg.message == WM_HOTKEY:
                    try:
                        self.callback()
                    except Exception:  # noqa: BLE001
                        log.get().exception("热键回调异常")
        finally:
            u.UnregisterHotKey(None, 1)
            log.get().info("热键已注销: %s", self.combo)

    def stop(self):
        self._stop = True
        if not self._ready.wait(1.0):
            return
        if self._tid:
            try:
                ctypes.windll.user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
            except Exception:  # noqa: BLE001
                pass
