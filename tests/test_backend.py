# -*- coding: utf-8 -*-
"""
集成测试：用 Umi-OCR 内置的 Python 3.8 + PySide2 直接加载插件，
验证 QML 窗口、服务自动拉起、信号编组、翻译结果。

用法（在 Umi-OCR 安装目录可用的机器上）：
    set UMI_DATA=<UmiOCR-data 目录>
    <UmiOCR-data>\\runtime\\python.exe tests\\test_backend.py <插件目录>
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

UMI_DATA = os.environ.get("UMI_DATA", "").strip()
if not UMI_DATA or not os.path.isdir(UMI_DATA):
    raise SystemExit(
        "请先设置环境变量 UMI_DATA 指向 UmiOCR-data 目录，例如：\n"
        "  set UMI_DATA=D:\\Umi-OCR\\UmiOCR-data"
    )

PLUGIN = os.path.abspath(
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.join(ROOT, "build", "umi_local_translate")
)
PARENT = os.path.dirname(PLUGIN)

sys.path.insert(0, os.path.join(UMI_DATA, "site-packages"))
sys.path.insert(0, PARENT)

SAMPLE = "本地离线翻译测试：Umi-OCR 的截图识别结果可以直接翻译成英文。"


def main():
    from PySide2.QtCore import QTimer
    from PySide2.QtGui import QGuiApplication
    from PySide2.QtQuick import QQuickView

    app = QGuiApplication(sys.argv[:1])

    print("plugin :", PLUGIN)
    print("umi    :", UMI_DATA)

    import umi_local_translate  # noqa: F401  (触发 bootstrap)
    from umi_local_translate.core import bootstrap, paths

    print("runtime ready:", paths.runtime_ready(), " model ready:", paths.model_ready())

    core = bootstrap.get_app()
    print("core app:", core)
    if core is None:
        print("FAIL: 插件未启动")
        return 1

    # ---- QML 窗口 ----
    core.ui.show_window()
    win = core.ui._win
    errs = [e.toString() for e in win.errors()]
    print("window status:", win.status(), "(Ready=%d)" % QQuickView.Ready)
    print("window root  :", win.rootObject())
    if errs:
        print("QML ERRORS:")
        for e in errs:
            print("  ", e)

    # ---- 翻译链路 ----
    b = core.backend
    b.requestTranslate()  # 先测空文本
    print("empty status:", b.statusText)

    b.sourceText = SAMPLE
    b.requestTranslate()
    print("translate started, busy =", b.busy)

    state = {"done": False, "ok": False}
    t0 = time.time()

    def geometry_test():
        """验证窗口几何能写回 config.json 并在重建窗口时恢复"""
        from PySide2.QtCore import QCoreApplication

        ui = core.ui
        ui.show_window()
        ui._win.resize(700, 400)
        QCoreApplication.processEvents()
        ui.hide_window()

        with open(paths.CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            saved = json.load(f).get("window", {})
        print("saved geometry:", saved)
        if abs(int(saved.get("width", 0)) - 700) > 2 or abs(int(saved.get("height", 0)) - 400) > 2:
            print("FAIL: 窗口尺寸未写入配置")
            return False

        win = ui._win
        win.close()
        win.deleteLater()
        ui._win = None
        ui.show_window()
        got = (ui._win.width(), ui._win.height())
        print("reopened size:", got)
        if abs(got[0] - 700) > 2 or abs(got[1] - 400) > 2:
            print("FAIL: 窗口尺寸未恢复")
            return False
        return True

    def poll():
        if b.busy:
            return
        if state["done"]:
            return
        state["done"] = True
        state["ok"] = bool(b.targetText)
        print("elapsed   : %.1fs" % (time.time() - t0))
        print("statusText:", b.statusText)
        print("targetText:", b.targetText)
        print("service   :", b.serviceText)
        print("geometry  :", "OK" if geometry_test() else "FAILED")
        app.quit()

    timer = QTimer()
    timer.timeout.connect(poll)
    timer.start(150)

    def watchdog():
        if not state["done"]:
            print("FAIL: 翻译超时")
            print("status:", b.statusText)
            app.quit()

    QTimer.singleShot(180000, watchdog)
    app.exec_()

    # 收尾
    try:
        core.service.stop()
    except Exception:  # noqa: BLE001
        pass

    print("RESULT:", "OK" if state["ok"] else "FAILED")
    return 0 if state["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
