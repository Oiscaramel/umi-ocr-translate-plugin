# -*- coding: utf-8 -*-
"""
离线自检：直接加载模型并翻译几句，用于安装后 / 换机器后验证。

用法：
    runtime\\python\\python.exe service\\selftest.py
"""

import os
import sys
import time

SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(SERVICE_DIR)
SITE_PACKAGES = os.path.join(PLUGIN_DIR, "runtime", "site-packages")
MODEL_DIR = os.path.join(PLUGIN_DIR, "models", "nllb-200-distilled-600M-int8")

if os.path.isdir(SITE_PACKAGES) and SITE_PACKAGES not in sys.path:
    sys.path.insert(0, SITE_PACKAGES)
if SERVICE_DIR not in sys.path:
    sys.path.insert(0, SERVICE_DIR)

CASES = [
    ("zh", "en", "你好，世界。这是一个本地离线翻译测试。"),
    ("en", "zh", "The quick brown fox jumps over the lazy dog."),
    ("auto", "auto", "Umi-OCR 是一个开源、免费的离线 OCR 软件。"),
    ("auto", "auto", "Please restart the application after installation."),
]


def main():
    print("plugin dir :", PLUGIN_DIR)
    print("model dir  :", MODEL_DIR)
    if not os.path.isfile(os.path.join(MODEL_DIR, "model.bin")):
        print("!! 模型缺失，跳过自检")
        return 2

    t0 = time.time()
    from engine_nllb import NllbEngine

    eng = NllbEngine(MODEL_DIR, compute_type="int8", beam_size=4)
    print("模型加载完成: %.2fs, compute_type=%s" % (time.time() - t0, eng.compute_type))

    ok = True
    for src, tgt, text in CASES:
        t1 = time.time()
        res = eng.translate(text, source=src, target=tgt)
        dt = (time.time() - t1) * 1000
        print("-" * 60)
        print("原文:", text)
        if res.get("ok"):
            print("译文:", res["text"], " [%s->%s, %dms]" % (res["src"], res["tgt"], dt))
            if not res["text"].strip():
                ok = False
                print("!! 空译文")
        else:
            ok = False
            print("!! 失败:", res)
    print("=" * 60)
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
