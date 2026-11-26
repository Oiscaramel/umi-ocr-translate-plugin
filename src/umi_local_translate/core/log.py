# -*- coding: utf-8 -*-
"""插件日志：写插件目录下的 logs/plugin.log，同时尽量同步给 Umi 的日志。"""

import logging
import logging.handlers
import os

from . import paths

_logger = None


def init():
    global _logger
    if _logger is not None:
        return _logger
    os.makedirs(paths.LOGS_DIR, exist_ok=True)
    log = logging.getLogger("umi_local_translate")
    log.setLevel(logging.DEBUG)
    log.propagate = False
    if not log.handlers:
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(threadName)s %(message)s", "%Y-%m-%d %H:%M:%S"
        )
        try:
            fh = logging.handlers.RotatingFileHandler(
                os.path.join(paths.LOGS_DIR, "plugin.log"),
                maxBytes=1024 * 1024,
                backupCount=2,
                encoding="utf-8",
            )
            fh.setFormatter(fmt)
            log.addHandler(fh)
        except Exception:  # noqa: BLE001
            pass
    _logger = log
    return log


def get():
    return _logger or init()


def umi_logger():
    """Umi 自己的 logger（可能不存在）。"""
    try:
        from umi_log import logger  # noqa: F401

        return logger
    except Exception:  # noqa: BLE001
        return None
