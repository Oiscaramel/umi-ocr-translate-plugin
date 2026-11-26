# -*- coding: utf-8 -*-
"""
与 Umi-OCR 内部模块打交道。

Umi-OCR v2.1.5 的插件加载器（py_src/plugins_controller/plugins_controller.py）
只认 PLUGINS_GROUPS = ["ocr"]。插件被 import 之后才做组名校验，
所以这里在 __init__.py 阶段把 "translate" 组注册进去，
让本插件看起来就是一个合法插件（不会弹错误、不会进 OCR 引擎列表）。
"""

import sys

from . import log

GROUP = "translate"


def _iter_modules():
    for name in list(sys.modules.keys()):
        mod = sys.modules.get(name)
        if mod is not None:
            yield mod


def find_module(pred, suffix=None):
    for mod in _iter_modules():
        try:
            if suffix and not getattr(mod, "__name__", "").endswith(suffix):
                continue
            if pred(mod):
                return mod
        except Exception:  # noqa: BLE001
            continue
    return None


def patch_plugin_group(group=GROUP):
    """把 group 注册进插件加载器，并预建空槽位。返回 True/False。"""
    mod = find_module(
        lambda m: hasattr(m, "PLUGINS_GROUPS") and hasattr(m, "PluginsController"),
        suffix="plugins_controller",
    )
    if mod is None:
        log.get().warning("未找到 Umi 插件加载器，无法注册 %r 组", group)
        return False
    try:
        groups = mod.PLUGINS_GROUPS
        if group not in groups:
            groups.append(group)
        ctrl = mod.PluginsController
        if group not in ctrl.pluginsDict:
            ctrl.pluginsDict[group] = {}
        if group not in ctrl.optionsDict:
            ctrl.optionsDict[group] = {}
        return True
    except Exception:  # noqa: BLE001
        log.get().exception("注册插件组失败")
        return False


def pubsub():
    mod = find_module(lambda m: hasattr(m, "PubSubService"), suffix="pubsub_service")
    return getattr(mod, "PubSubService", None) if mod else None


def subscribe(title, callback):
    svc = pubsub()
    if svc is None:
        log.get().warning("未找到事件总线，无法订阅 %s", title)
        return False
    try:
        svc.subscribe(title, callback)
        return True
    except Exception:  # noqa: BLE001
        log.get().exception("订阅 %s 失败", title)
        return False


def collect_ocr_text(payload):
    """从 <<ScreenshotOcrEnd>> 的 payload 里提取纯文本。"""
    if not payload:
        return ""
    blocks = []
    for res in payload:
        if not isinstance(res, dict):
            continue
        if res.get("code") != 100:
            continue
        lines = []
        for item in res.get("data") or []:
            if isinstance(item, dict):
                t = (item.get("text") or "").strip()
                if t:
                    lines.append(t)
        if lines:
            blocks.append("\n".join(lines))
    return "\n\n".join(blocks).strip()


def qml_import_path():
    """PySide2 自带的 QML 模块路径（新的 QQuickView 需要自己加）。"""
    try:
        import os

        import PySide2

        p = os.path.join(os.path.dirname(os.path.abspath(PySide2.__file__)), "qml")
        return p if os.path.isdir(p) else ""
    except Exception:  # noqa: BLE001
        return ""
