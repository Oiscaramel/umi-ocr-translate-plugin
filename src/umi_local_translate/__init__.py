# -*- coding: utf-8 -*-
"""
Umi-OCR 本地离线翻译插件（NLLB-200 + CTranslate2）

安装：把整个 umi_local_translate 文件夹放进 UmiOCR-data/plugins/ ，重启 Umi-OCR。

说明：
Umi-OCR v2.1.5 的插件加载器只内置了 "ocr" 一种插件组，且先 import 再做组名校验。
本插件在 import 阶段把 "translate" 组注册进加载器，因此安装方式与官方示例完全一致，
既不修改 Umi-OCR 的任何文件，也不会出现在 OCR 引擎下拉框里。
"""

# ----------------------------------------------------------------------
# 插件信息：必须先于 bootstrap 定义，保证任何异常情况下加载器都能拿到合法结构
# ----------------------------------------------------------------------


class _TranslateStubApi:
    """占位 API 类。翻译插件不属于 OCR 引擎，永远不会被实例化。"""

    def __init__(self, argd=None):
        self.argd = argd or {}

    def start(self):
        return "[Error] 本地翻译插件不是 OCR 引擎。"

    def stop(self):
        pass

    def runPath(self, path=None, *args, **kwargs):
        return "[Error] 本地翻译插件不是 OCR 引擎。"

    def runBytes(self, data=None, *args, **kwargs):
        return "[Error] 本地翻译插件不是 OCR 引擎。"

    def runBase64(self, data=None, *args, **kwargs):
        return "[Error] 本地翻译插件不是 OCR 引擎。"


PluginInfo = {
    "group": "translate",
    "global_options": None,
    "local_options": None,
    "api_class": _TranslateStubApi,
}


# ----------------------------------------------------------------------
# 启动
# ----------------------------------------------------------------------

try:
    from .core import bootstrap

    bootstrap.install()
except Exception:  # noqa: BLE001
    import traceback

    traceback.print_exc()
    try:
        from umi_log import logger

        logger.error("本地翻译插件初始化失败", exc_info=True, stack_info=True)
    except Exception:  # noqa: BLE001
        pass
