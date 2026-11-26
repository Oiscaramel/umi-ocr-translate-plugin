# -*- coding: utf-8 -*-
"""插件内的固定路径（全部相对插件目录，保证整个文件夹可整体搬移）。"""

import os

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(CORE_DIR)

QML_DIR = os.path.join(PLUGIN_DIR, "qml")
SERVICE_DIR = os.path.join(PLUGIN_DIR, "service")
RUNTIME_DIR = os.path.join(PLUGIN_DIR, "runtime")
PYTHON_DIR = os.path.join(RUNTIME_DIR, "python")
SITE_PACKAGES = os.path.join(RUNTIME_DIR, "site-packages")
MODELS_DIR = os.path.join(PLUGIN_DIR, "models")
MODEL_DIR = os.path.join(MODELS_DIR, "nllb-200-distilled-600M-int8")
LOGS_DIR = os.path.join(PLUGIN_DIR, "logs")
CONFIG_PATH = os.path.join(PLUGIN_DIR, "config.json")
SERVER_PY = os.path.join(SERVICE_DIR, "server.py")
SELFTEST_PY = os.path.join(SERVICE_DIR, "selftest.py")

# pythonw.exe 无控制台；不存在时退回 python.exe（配合 CREATE_NO_WINDOW）
PYTHONW = os.path.join(PYTHON_DIR, "pythonw.exe")
PYTHON = os.path.join(PYTHON_DIR, "python.exe")


def python_exe():
    if os.path.isfile(PYTHONW):
        return PYTHONW
    return PYTHON


def runtime_ready():
    return os.path.isfile(PYTHON) and os.path.isfile(SERVER_PY)


def model_ready():
    return os.path.isfile(os.path.join(MODEL_DIR, "model.bin"))
