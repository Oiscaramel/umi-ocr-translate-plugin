# -*- coding: utf-8 -*-
"""
NLLB-200 + CTranslate2 本地翻译引擎（CPU / int8）。

对外只暴露 NllbEngine.translate()，线程安全。
"""

import os
import re
import threading
import time
from collections import OrderedDict

import segment as segmod
from nllb_tokenizer import NllbTokenizer

_CJK = re.compile(u"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_LATIN = re.compile(r"[A-Za-z]")

LANG_TAG = {"zh": "zho_Hans", "en": "eng_Latn"}
LANG_NAME = {"zh": "中文", "en": "English"}


def detect_lang(text):
    """粗略判断主语言：中 / 英"""
    cjk = len(_CJK.findall(text))
    latin = len(_LATIN.findall(text))
    if cjk == 0 and latin == 0:
        return "en"
    if cjk == 0:
        return "en"
    if latin == 0:
        return "zh"
    return "zh" if cjk >= latin * 0.3 else "en"


class _Cache:
    def __init__(self, ttl=600, maxsize=2000):
        self.ttl = ttl
        self.maxsize = maxsize
        self._d = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key):
        now = time.time()
        with self._lock:
            item = self._d.get(key)
            if not item:
                self.misses += 1
                return None
            ts, val = item
            if now - ts > self.ttl:
                del self._d[key]
                self.misses += 1
                return None
            self._d.move_to_end(key)
            self.hits += 1
            return val

    def put(self, key, val):
        with self._lock:
            self._d[key] = (time.time(), val)
            self._d.move_to_end(key)
            while len(self._d) > self.maxsize:
                self._d.popitem(last=False)


class NllbEngine:
    def __init__(
        self,
        model_dir,
        compute_type="int8",
        threads=0,
        beam_size=4,
        inter_threads=1,
        cache_ttl=600,
    ):
        self.model_dir = model_dir
        self.compute_type = compute_type
        self.threads = int(threads) if threads else self._default_threads()
        self.beam_size = max(1, int(beam_size))
        self.inter_threads = max(1, int(inter_threads))
        self._lock = threading.Lock()
        self._cache = _Cache(ttl=cache_ttl)
        self._translator = None
        self._tok = None
        self.load_seconds = 0.0
        self._load()

    # ------------------------------------------------------------------

    @staticmethod
    def _default_threads():
        cpu = os.cpu_count() or 4
        # 留出余量给 Umi-OCR 本身
        return max(2, min(12, cpu - 4 if cpu > 8 else cpu))

    def _candidates(self):
        ct = (self.compute_type or "int8").strip()
        chain = [ct]
        for fallback in ("int8", "int8_float32", "float32"):
            if fallback not in chain:
                chain.append(fallback)
        return chain

    def _load(self):
        t0 = time.time()
        import ctranslate2

        if not os.path.isdir(self.model_dir):
            raise RuntimeError("模型目录不存在: %s" % self.model_dir)
        if not os.path.isfile(os.path.join(self.model_dir, "model.bin")):
            raise RuntimeError("模型文件缺失: %s\\model.bin" % self.model_dir)

        self._tok = NllbTokenizer(self.model_dir)

        last_err = None
        for compute_type in self._candidates():
            try:
                self._translator = ctranslate2.Translator(
                    self.model_dir,
                    device="cpu",
                    compute_type=compute_type,
                    inter_threads=self.inter_threads,
                    intra_threads=self.threads,
                )
                self.compute_type = compute_type
                break
            except Exception as e:  # noqa: BLE001
                last_err = e
        if self._translator is None:
            raise RuntimeError("加载模型失败: %s" % last_err)

        self.load_seconds = time.time() - t0

    # ------------------------------------------------------------------

    def _translate_batch(self, segments, src_tag, tgt_tag):
        tokens = [self._tok.encode_tokens(s) for s in segments]
        # NLLB 的源端格式：[src_lang] + tokens + [</s>]
        batch = [[src_tag] + t + ["</s>"] for t in tokens]
        max_src = max(len(t) for t in batch)
        max_dec = min(512, max(48, int(max_src * 2.2) + 16))

        results = self._translator.translate_batch(
            batch,
            target_prefix=[[tgt_tag] for _ in batch],
            beam_size=self.beam_size,
            num_hypotheses=1,
            max_batch_size=8,
            batch_type="examples",
            max_decoding_length=max_dec,
            min_decoding_length=1,
            length_penalty=1.0,
            replace_unknowns=True,
            return_scores=False,
        )

        out = []
        for r in results:
            hyp = r.hypotheses[0] if r.hypotheses else []
            if hyp and hyp[0] == tgt_tag:
                hyp = hyp[1:]
            out.append(self._tok.decode_tokens(hyp).strip())
        return out

    # ------------------------------------------------------------------

    def translate(self, text, source="auto", target="auto", mode="block"):
        """
        text    : 原文
        source  : auto | zh | en
        target  : auto | zh | en
        mode    : block | line
        返回 dict
        """
        t0 = time.time()
        text = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text:
            return {
                "ok": False,
                "error": "empty",
                "message": "没有可翻译的文本。",
            }

        src = source if source in ("zh", "en") else detect_lang(text)
        if target in ("zh", "en"):
            tgt = target
        else:
            tgt = "en" if src == "zh" else "zh"
        if tgt == src:
            return {
                "ok": True,
                "text": text,
                "src": src,
                "tgt": tgt,
                "ms": int((time.time() - t0) * 1000),
                "segments": 0,
                "cached": True,
                "note": "源语言与目标语言相同，已原样返回。",
            }

        segments, layout = segmod.build(text, mode=mode, max_chars=280)
        if not segments:
            return {"ok": False, "error": "empty", "message": "没有可翻译的文本。"}

        src_tag = LANG_TAG[src]
        tgt_tag = LANG_TAG[tgt]

        translated = [None] * len(segments)
        missing = []
        cache_hits = 0
        for i, s in enumerate(segments):
            key = (src, tgt, s)
            hit = self._cache.get(key)
            if hit is not None:
                translated[i] = hit
                cache_hits += 1
            else:
                missing.append(i)

        if missing:
            batch = [segments[i] for i in missing]
            with self._lock:
                results = self._translate_batch(batch, src_tag, tgt_tag)
            for i, r in zip(missing, results):
                translated[i] = r
                self._cache.put((src, tgt, segments[i]), r)

        out_text = segmod.rebuild(translated, layout, mode=mode, target=tgt)

        return {
            "ok": True,
            "text": out_text,
            "src": src,
            "tgt": tgt,
            "ms": int((time.time() - t0) * 1000),
            "segments": len(segments),
            "cached": cache_hits == len(segments),
            "compute_type": self.compute_type,
        }

    def info(self):
        return {
            "engine": "nllb",
            "model": "nllb-200-distilled-600M",
            "model_dir": self.model_dir,
            "compute_type": self.compute_type,
            "threads": self.threads,
            "beam_size": self.beam_size,
            "load_seconds": round(self.load_seconds, 2),
        }
