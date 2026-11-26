# -*- coding: utf-8 -*-
"""
备用引导（仅在运行时注册 "translate" 组失效时使用）。

用法：
  1. 把本文件和 umi_local_translate.pth 复制到 UmiOCR-data/plugins/ 根目录
  2. 把 UmiOCR-data/plugins/umi_local_translate/__init__.py 改名为 __init__.py.disabled
     （这样官方加载器会跳过该文件夹，不会报"插件组未定义"）
  3. 重启 Umi-OCR

原理：Umi 的插件加载器会调用 site.addsitedir("plugins")，
     其中 .pth 里的 import 语句会被执行，从而绕过 PluginInfo 组名校验。
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.join(_HERE, "umi_local_translate")

if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _boot():
    if not os.path.isdir(_PKG):
        return
    try:
        from umi_local_translate.core import bootstrap

        bootstrap.install()
    except Exception:  # noqa: BLE001
        import traceback

        traceback.print_exc()


_boot()
