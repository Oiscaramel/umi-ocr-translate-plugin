# -*- coding: utf-8 -*-
"""翻译服务进程管理：健康检查、按需拉起、请求转发。"""

import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

from . import log, paths


class ServiceError(RuntimeError):
    pass


def _free_port(host, start, tries=24):
    for p in range(start, start + tries):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, p))
        except OSError:
            continue
        else:
            return p
        finally:
            s.close()
    return 0


class ServiceManager:
    def __init__(self, cfg):
        self.cfg = cfg or {}
        svc = self.cfg.get("service", {})
        self.host = svc.get("host", "127.0.0.1")
        self.base_port = int(svc.get("port", 17321) or 17321)
        self.start_timeout = float(svc.get("start_timeout", 90))
        self.request_timeout = float(svc.get("request_timeout", 180))
        self.idle_timeout = int(svc.get("idle_timeout", 900))
        self.beam_size = int(svc.get("beam_size", 2))
        self.threads = int(svc.get("threads", 0))
        self.compute_type = svc.get("compute_type", "int8")

        self.port = 0
        self.token = ""
        self._proc = None
        self._lock = threading.Lock()
        self._stdout = None

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _url(self, path):
        return "http://%s:%d%s" % (self.host, self.port, path)

    def _request(self, path, payload=None, timeout=2.0):
        data = None
        headers = {"Accept": "application/json"}
        if self.token:
            headers["X-Auth-Token"] = self.token
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        req = urllib.request.Request(self._url(path), data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                return resp.getcode(), json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode("utf-8"))
            except Exception:  # noqa: BLE001
                body = {"ok": False, "error": "http_%s" % e.code}
            return e.code, body

    def health(self, timeout=0.8):
        if not self.port:
            return None
        try:
            code, body = self._request("/health", None, timeout=timeout)
            if code == 200 or (isinstance(body, dict) and "status" in body):
                return body
        except Exception:  # noqa: BLE001
            return None
        return None

    # ------------------------------------------------------------------
    # 进程
    # ------------------------------------------------------------------

    def _log_tail(self, n=8):
        p = os.path.join(paths.LOGS_DIR, "service.log")
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            return "".join(lines[-n:]).strip()
        except Exception:  # noqa: BLE001
            return ""

    def _spawn(self):
        if not paths.runtime_ready():
            raise ServiceError(
                "内置运行时不完整：缺少 runtime\\python 或 service\\server.py。"
                "请重新复制整个插件文件夹，或运行 tools\\rebuild_runtime.ps1。"
            )
        if not paths.model_ready():
            raise ServiceError(
                "缺少翻译模型：%s\n请重新完整复制插件文件夹（需要 model.bin）。" % paths.MODEL_DIR
            )
        if not self.port:
            self.port = _free_port(self.host, self.base_port)
            if not self.port:
                raise ServiceError("找不到可用端口（%d 起 24 个都占用）" % self.base_port)
        if not self.token:
            self.token = secrets.token_hex(16)

        os.makedirs(paths.LOGS_DIR, exist_ok=True)
        out_path = os.path.join(paths.LOGS_DIR, "service.stdout.log")
        try:
            self._stdout = open(out_path, "a", encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            self._stdout = None

        cmd = [
            paths.python_exe(),
            paths.SERVER_PY,
            "--host",
            self.host,
            "--port",
            str(self.port),
            "--token",
            self.token,
            "--model",
            paths.MODEL_DIR,
            "--compute-type",
            self.compute_type,
            "--threads",
            str(self.threads),
            "--beam-size",
            str(self.beam_size),
            "--idle-timeout",
            str(self.idle_timeout),
        ]

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)

        flags = 0
        if sys.platform == "win32":
            flags = 0x08000000 | 0x00000200  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP

        log.get().info("启动翻译服务: %s", " ".join(cmd))
        self._proc = subprocess.Popen(
            cmd,
            cwd=paths.SERVICE_DIR,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=self._stdout,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            close_fds=True,
        )
        return self._proc

    def _alive(self):
        return self._proc is not None and self._proc.poll() is None

    def ensure_started(self, on_progress=None):
        """确保服务可用且模型就绪。阻塞调用，请在后台线程里用。"""
        with self._lock:
            h = self.health(timeout=0.6)
            if h and h.get("status") == "ready":
                return h
            if not self._alive():
                if self._proc is not None:
                    # 旧进程已退出，换端口重来
                    self.port = 0
                    self.token = ""
                self._spawn()
            if on_progress:
                on_progress("正在加载翻译模型…")
            return self._wait_ready(on_progress)

    def _wait_ready(self, on_progress=None):
        deadline = time.time() + self.start_timeout
        last_status = None
        while time.time() < deadline:
            if self._proc is not None and self._proc.poll() is not None:
                code = self._proc.returncode
                tail = self._log_tail()
                raise ServiceError(
                    "翻译服务进程退出（code=%s）。\n%s" % (code, tail or "详见 logs/service.log")
                )
            h = self.health(timeout=0.6)
            if h:
                st = h.get("status")
                if st != last_status and on_progress:
                    if st == "loading":
                        on_progress("正在加载翻译模型…")
                    last_status = st
                if st == "ready":
                    return h
                if st == "error":
                    raise ServiceError("模型加载失败：%s" % (h.get("error") or "未知错误"))
            time.sleep(0.35)
        raise ServiceError("翻译服务启动超时（%.0f 秒）。" % self.start_timeout)

    def translate(self, text, source="auto", target="auto", mode="block", on_progress=None):
        h = self.ensure_started(on_progress=on_progress)
        code, body = self._request(
            "/translate",
            {"text": text, "source": source, "target": target, "mode": mode},
            timeout=self.request_timeout,
        )
        if isinstance(body, dict) and body.get("ok"):
            return body
        msg = ""
        if isinstance(body, dict):
            msg = body.get("message") or body.get("error") or ""
        raise ServiceError(msg or "翻译失败（HTTP %s）" % code)

    def stop(self):
        with self._lock:
            if self._alive() and self.port:
                try:
                    self._request("/shutdown", {}, timeout=1.5)
                except Exception:  # noqa: BLE001
                    pass
                try:
                    self._proc.wait(timeout=2.5)
                except Exception:  # noqa: BLE001
                    try:
                        self._proc.terminate()
                    except Exception:  # noqa: BLE001
                        pass
            self._proc = None
            self.port = 0
            if self._stdout:
                try:
                    self._stdout.close()
                except Exception:  # noqa: BLE001
                    pass
                self._stdout = None

    def is_running(self):
        return self._alive()

    def status_text(self):
        h = self.health(timeout=0.5)
        if not h:
            return "未启动"
        st = h.get("status")
        if st == "ready":
            return "运行中 · %s · 端口 %d" % (h.get("compute_type", ""), self.port)
        if st == "loading":
            return "模型加载中…"
        return "异常：%s" % (h.get("error") or st)
