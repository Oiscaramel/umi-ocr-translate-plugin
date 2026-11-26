# -*- coding: utf-8 -*-
"""插件安装入口（由 umi_local_translate/__init__.py 调用）。"""

from . import compat, config, log, paths

_state = {"app": None}


def install():
    """只执行一次。任何异常都不应影响 Umi-OCR 启动。"""
    if _state["app"] is not None:
        return _state["app"]

    log.init()
    lg = log.get()
    lg.info("=" * 60)
    lg.info("加载本地翻译插件: %s", paths.PLUGIN_DIR)

    # 1) 先让加载器认识 "translate" 组（必须在 PluginInfo 校验之前完成）
    ok = compat.patch_plugin_group()
    lg.info("注册 translate 插件组: %s", "成功" if ok else "失败（将显示加载失败提示）")

    # 2) 读取配置
    cfg = config.load()
    if not cfg.get("enabled", True):
        lg.info("插件已在 config.json 中禁用")
        return None

    # 3) 环境检查（只记录，不阻塞）
    if not paths.runtime_ready():
        lg.error("运行时缺失: %s", paths.PYTHON_DIR)
    if not paths.model_ready():
        lg.error("模型缺失: %s", paths.MODEL_DIR)

    # 4) 启动应用
    from .app import App

    app = App(cfg)
    _state["app"] = app
    app.start()
    return app


def get_app():
    return _state["app"]
