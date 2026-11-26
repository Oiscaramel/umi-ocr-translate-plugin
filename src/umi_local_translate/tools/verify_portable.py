# -*- coding: utf-8 -*-
"""
可移植性自检。

检查内容：
  1. 没有 venv 残留（pyvenv.cfg / Scripts 启动器）
  2. 源码与配置里没有写死本机绝对路径
  3. 内置 Python 能独立导入运行时依赖
  4. （可选）把整个插件目录复制到临时位置后跑一次真实翻译

用法：
  1) 基本检查
     runtime\\python\\python.exe tools\\verify_portable.py
  2) 含换目录真实翻译测试（约需 1GB 临时空间）
     runtime\\python\\python.exe tools\\verify_portable.py --relocate
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(TOOLS_DIR)
RUNTIME = os.path.join(PLUGIN, "runtime")
PY_DIR = os.path.join(RUNTIME, "python")
SITE = os.path.join(RUNTIME, "site-packages")
PY = os.path.join(PY_DIR, "python.exe")

SKIP_DIRS = {"logs", "__pycache__", "models", "python", "site-packages"}
TEXT_EXT = {".py", ".json", ".qml", ".ps1", ".bat", ".cfg", ".pth", ".ini"}

# 只找"本机特有的"路径，避免把文档里的相对路径误判
MARKERS = [
    "AppData\\Roaming\\uv",
    "AppData\\Local\\uv",
    "C:\\Users\\",
]

# 任意盘符绝对路径，例如 D:\xxx
ABS_PATH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:" + re.escape(chr(92)))

# 本文件自身含有上面的字符串，跳过
SELF = os.path.abspath(__file__)

ok = True


def say(flag, msg):
    global ok
    if not flag:
        ok = False
    print(("  [OK]   " if flag else "  [FAIL] ") + msg)


def check_venv():
    print("\n[1] venv / 启动器残留")
    leftovers = []
    for root, dirs, files in os.walk(PLUGIN):
        dirs[:] = [d for d in dirs if d not in ("models", "__pycache__", "logs")]
        if "pyvenv.cfg" in files:
            leftovers.append(os.path.join(root, "pyvenv.cfg"))
    say(not leftovers, "无 pyvenv.cfg" if not leftovers else "发现残留: %s" % leftovers)
    scripts = os.path.join(PY_DIR, "Scripts")
    exes = []
    if os.path.isdir(scripts):
        exes = [f for f in os.listdir(scripts) if f.lower().endswith(".exe")]
    say(not exes, "runtime/python/Scripts 无 exe 启动器")


def check_paths():
    print("\n[2] 绝对路径扫描（源码/配置）")
    hits = []
    for root, dirs, files in os.walk(PLUGIN):
        rel = os.path.relpath(root, PLUGIN)
        parts = rel.split(os.sep)
        if any(p in SKIP_DIRS for p in parts):
            continue
        if any(p.endswith(".dist-info") for p in parts):
            continue
        for name in files:
            if os.path.splitext(name)[1].lower() not in TEXT_EXT:
                continue
            path = os.path.join(root, name)
            if os.path.abspath(path) == SELF:
                continue
            try:
                with open(path, "rb") as f:
                    text = f.read().decode("utf-8", errors="ignore")
            except OSError:
                continue
            for m in MARKERS:
                if m in text:
                    hits.append("%s  <- %r" % (os.path.join(rel, name), m))
                    break
            else:
                found = ABS_PATH.search(text)
                if found:
                    hits.append("%s  <- 绝对路径 %r" % (os.path.join(rel, name), found.group(0)))
    say(not hits, "未发现写死的绝对路径" if not hits else "发现: %s" % hits)


def check_import():
    print("\n[3] 内置 Python 独立导入依赖")
    if not os.path.isfile(PY):
        say(False, "runtime/python/python.exe 不存在")
        return
    env = os.environ.copy()
    for k in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"):
        env.pop(k, None)
    code = (
        "import sys; sys.path.insert(0, %r); "
        "import ctranslate2, tokenizers, numpy; "
        "print(ctranslate2.__version__, tokenizers.__version__, numpy.__version__)" % SITE
    )
    r = subprocess.run(
        [PY, "-I", "-c", code], capture_output=True, text=True, env=env,
        cwd=os.path.dirname(PY),
    )
    say(r.returncode == 0, "导入成功: %s" % (r.stdout.strip() or r.stderr.strip()[-300:]))


def check_relocate():
    print("\n[4] 换目录真实翻译")
    tmp = tempfile.mkdtemp(prefix="umi_lt_portable_")
    dst = os.path.join(tmp, "moved_umi_local_translate")
    try:
        print("  复制到:", dst)
        shutil.copytree(PLUGIN, dst)
        py = os.path.join(dst, "runtime", "python", "python.exe")
        test = os.path.join(dst, "service", "selftest.py")
        env = os.environ.copy()
        for k in ("PYTHONPATH", "PYTHONHOME"):
            env.pop(k, None)
        r = subprocess.run([py, test], capture_output=True, text=True, env=env, timeout=600)
        out = (r.stdout or "") + (r.stderr or "")
        say(r.returncode == 0 and "SELFTEST OK" in out, "换目录后自检通过")
        if r.returncode != 0:
            print(out[-1500:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def summary():
    total = 0
    for root, _dirs, files in os.walk(PLUGIN):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    print("\n插件目录: %s" % PLUGIN)
    print("占用空间: %.0f MB" % (total / 1024 / 1024))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relocate", action="store_true", help="复制到临时目录后真实翻译一次")
    args = ap.parse_args()

    print("=" * 60)
    print("Umi-OCR 本地翻译插件 · 可移植性自检")
    print("=" * 60)
    check_venv()
    check_paths()
    check_import()
    if args.relocate:
        check_relocate()
    summary()
    print("\n结果:", "全部通过" if ok else "存在问题")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
