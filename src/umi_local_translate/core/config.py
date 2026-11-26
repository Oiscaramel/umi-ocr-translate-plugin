# -*- coding: utf-8 -*-
"""插件配置：写在插件目录的 config.json，跟着文件夹一起搬走。"""

import copy
import json
import os

from . import paths

DEFAULTS = {
    "enabled": True,
    # OCR 结束后自动翻译（默认关闭）
    "auto_translate": False,
    # auto | zh-en | en-zh
    "direction": "auto",
    # 在 截图OCR 页「设置/记录」右侧注入「翻译」标签
    "embed_button": True,
    # 独立窗口的全局热键
    "hotkey": "ctrl+alt+t",
    "hotkey_enabled": True,
    # 启动后立即预热翻译服务（占用约 700MB 内存）
    "preload": False,
    # block（按段落，质量好） | line（逐行对齐）
    "line_mode": "block",
    "service": {
        "host": "127.0.0.1",
        "port": 17321,
        "idle_timeout": 900,
        "beam_size": 4,
        "threads": 0,
        "compute_type": "int8",
        "start_timeout": 90,
        "request_timeout": 180,
    },
    "window": {
        "width": 760,
        "height": 420,
        "always_on_top": False,
    },
}


def _merge(base, override):
    out = copy.deepcopy(base)
    if not isinstance(override, dict):
        return out
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load():
    data = {}
    if os.path.isfile(paths.CONFIG_PATH):
        try:
            # utf-8-sig: 兼容记事本等工具写入的 BOM
            with open(paths.CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception:  # noqa: BLE001
            data = {}
    return _merge(DEFAULTS, data)


def save(cfg):
    tmp = paths.CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, paths.CONFIG_PATH)


def direction_to_langs(direction):
    """'auto' -> ('auto','auto')；'zh-en' -> ('zh','en')"""
    d = (direction or "auto").lower()
    if d in ("zh-en", "zh_en", "zh2en"):
        return "zh", "en"
    if d in ("en-zh", "en_zh", "en2zh"):
        return "en", "zh"
    return "auto", "auto"
