# -*- coding: utf-8 -*-
"""
本地翻译 HTTP 服务（仅标准库）。

端点：
    GET  /health     -> 服务与模型状态
    POST /translate  -> {"text":..,"source":"auto|zh|en","target":"auto|zh|en","mode":"block|line"}
    POST /shutdown   -> 退出（需要 token）

只监听 127.0.0.1。
"""

import argparse
import json
import logging
import logging.handlers
import os
import signal
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(SERVICE_DIR)
SITE_PACKAGES = os.path.join(PLUGIN_DIR, "runtime", "site-packages")
DEFAULT_MODEL_DIR = os.path.join(PLUGIN_DIR, "models", "nllb-200-distilled-600M-int8")
LOGS_DIR = os.path.join(PLUGIN_DIR, "logs")

for _p in (SITE_PACKAGES, SERVICE_DIR):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

MAX_BODY = 4 * 1024 * 1024  # 4MB


# ============================ 日志 ============================


def setup_logging(level=logging.INFO):
    os.makedirs(LOGS_DIR, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(threadName)s %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    fh = logging.handlers.RotatingFileHandler(
        os.path.join(LOGS_DIR, "service.log"),
        maxBytes=2 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    return root


log = logging.getLogger("translator")


# ============================ 状态 ============================


class State:
    def __init__(self):
        self.status = "loading"
        self.error = ""
        self.engine = None
        self.started_at = time.time()
        self.last_request = time.time()
        self.requests = 0
        self.token = ""
        self.lock = threading.Lock()

    def touch(self):
        self.last_request = time.time()
        with self.lock:
            self.requests += 1


STATE = State()


def load_engine(model_dir, compute_type, threads, beam_size):
    try:
        log.info("开始加载模型: %s", model_dir)
        from engine_nllb import NllbEngine

        eng = NllbEngine(
            model_dir,
            compute_type=compute_type,
            threads=threads,
            beam_size=beam_size,
        )
        STATE.engine = eng
        STATE.status = "ready"
        log.info("模型加载完成，用时 %.2fs，compute_type=%s", eng.load_seconds, eng.compute_type)
    except Exception as e:  # noqa: BLE001
        STATE.status = "error"
        STATE.error = "%s: %s" % (type(e).__name__, e)
        log.exception("模型加载失败")


# ============================ HTTP ============================


class Handler(BaseHTTPRequestHandler):
    server_version = "UmiLocalTranslate/1.0"
    protocol_version = "HTTP/1.1"

    # ---------- 工具 ----------

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _auth_ok(self):
        if not STATE.token:
            return True
        got = self.headers.get("X-Auth-Token", "")
        return got == STATE.token

    def _read_json(self):
        """读取完整请求体并解析 JSON。始终把 body 读完，避免 keep-alive 串包。"""
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            return None
        if length > MAX_BODY:
            self.close_connection = True
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001
            return None

    def log_message(self, fmt, *args):  # noqa: A003
        log.debug("%s - %s", self.address_string(), fmt % args)

    # ---------- GET ----------

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path in ("/health", "/"):
            info = {
                "status": STATE.status,
                "error": STATE.error,
                "uptime": round(time.time() - STATE.started_at, 1),
                "requests": STATE.requests,
            }
            if STATE.engine:
                info.update(STATE.engine.info())
            self._send(200 if STATE.status != "error" else 500, info)
            return
        self._send(404, {"ok": False, "error": "not_found"})

    # ---------- POST ----------

    def do_POST(self):  # noqa: N802
        path = self.path.split("?")[0]

        # 先无条件读完请求体，保证 HTTP/1.1 keep-alive 不串包
        data = self._read_json()

        if path == "/shutdown":
            if not self._auth_ok():
                self._send(403, {"ok": False, "error": "forbidden"})
                return
            self._send(200, {"ok": True})
            log.info("收到 shutdown 请求，1 秒后退出")
            threading.Timer(1.0, _request_exit).start()
            return

        if path != "/translate":
            self._send(404, {"ok": False, "error": "not_found"})
            return

        if not self._auth_ok():
            self._send(403, {"ok": False, "error": "forbidden"})
            return

        if data is None:
            self._send(400, {"ok": False, "error": "bad_request", "message": "请求体不是合法 JSON"})
            return

        STATE.touch()

        if STATE.status == "loading":
            self._send(503, {"ok": False, "error": "loading", "message": "模型正在加载，请稍候。"})
            return
        if STATE.status != "ready" or STATE.engine is None:
            self._send(500, {"ok": False, "error": "error", "message": STATE.error})
            return

        text = data.get("text") or ""
        source = data.get("source") or "auto"
        target = data.get("target") or "auto"
        mode = data.get("mode") or "block"

        try:
            t0 = time.time()
            result = STATE.engine.translate(text, source=source, target=target, mode=mode)
            result["server_ms"] = int((time.time() - t0) * 1000)
            if result.get("ok"):
                log.info(
                    "翻译 %s->%s %d字 %d段 %dms%s",
                    result.get("src"),
                    result.get("tgt"),
                    len(text),
                    result.get("segments", 0),
                    result.get("ms", 0),
                    " (cache)" if result.get("cached") else "",
                )
            self._send(200 if result.get("ok") else 400, result)
        except Exception as e:  # noqa: BLE001
            log.exception("翻译失败")
            self._send(500, {"ok": False, "error": "exception", "message": "%s: %s" % (type(e).__name__, e)})


# ============================ 生命周期 ============================


def _request_exit():
    log.info("服务退出")
    logging.shutdown()
    os._exit(0)


def idle_watchdog(timeout):
    if timeout <= 0:
        return
    while True:
        time.sleep(15)
        idle = time.time() - STATE.last_request
        if STATE.status == "ready" and idle > timeout:
            log.info("空闲 %.0fs，自动退出", idle)
            _request_exit()


def port_is_free(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Umi-OCR 本地翻译服务")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=17321)
    ap.add_argument("--token", default="")
    ap.add_argument("--model", default=DEFAULT_MODEL_DIR)
    ap.add_argument("--compute-type", default="int8")
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--beam-size", type=int, default=4)
    ap.add_argument("--idle-timeout", type=int, default=900, help="空闲多少秒后退出，0 表示不退出")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)

    setup_logging(logging.DEBUG if args.debug else logging.INFO)
    STATE.token = args.token
    log.info(
        "启动翻译服务 port=%s model=%s compute=%s threads=%s idle=%ss",
        args.port,
        args.model,
        args.compute_type,
        args.threads,
        args.idle_timeout,
    )

    if not os.path.isfile(os.path.join(args.model, "model.bin")):
        STATE.status = "error"
        STATE.error = "模型文件不存在: %s" % args.model
        log.error(STATE.error)

    def _sig(*_a):
        _request_exit()

    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        if hasattr(signal, name):
            try:
                signal.signal(getattr(signal, name), _sig)
            except Exception:  # noqa: BLE001
                pass

    threading.Thread(
        target=load_engine,
        args=(args.model, args.compute_type, args.threads, args.beam_size),
        name="loader",
        daemon=True,
    ).start()

    threading.Thread(target=idle_watchdog, args=(args.idle_timeout,), name="idle", daemon=True).start()

    try:
        httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as e:
        log.error("端口 %s 无法监听: %s", args.port, e)
        return 2
    httpd.daemon_threads = True
    log.info("HTTP 服务已就绪: http://%s:%s", args.host, args.port)
    try:
        httpd.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
