# -*- coding: utf-8 -*-
"""
NLLB 分词器封装。

只依赖 tokenizers（Rust 实现，读取 tokenizer.json），
不需要 transformers / torch / sentencepiece。

NLLB 的输入格式（与 HF 的 NllbTokenizer 一致）：

    [src_lang] + <文本token> + [</s>]

目标语言通过 CTranslate2 的 target_prefix 强制作为第一个解码 token。
"""

import os

from tokenizers import Tokenizer


class NllbTokenizer:
    def __init__(self, model_dir):
        path = os.path.join(model_dir, "tokenizer.json")
        if not os.path.isfile(path):
            raise FileNotFoundError("找不到分词器文件: %s" % path)
        self._tok = Tokenizer.from_file(path)
        self._unk_id = self._tok.token_to_id("<unk>")
        if self._unk_id is None:
            self._unk_id = 0
        self._id_cache = {}

    # ------------------------------------------------------------------

    def has_token(self, token):
        return self._tok.token_to_id(token) is not None

    def token_id(self, token):
        i = self._tok.token_to_id(token)
        if i is None:
            raise KeyError("词表里没有 token: %s" % token)
        return i

    def encode_tokens(self, text):
        """文本 -> token 字符串列表（不含任何特殊 token）"""
        enc = self._tok.encode(text, add_special_tokens=False)
        return list(enc.tokens)

    def decode_tokens(self, tokens):
        """token 字符串列表 -> 文本"""
        ids = []
        cache = self._id_cache
        for t in tokens:
            i = cache.get(t)
            if i is None:
                i = self._tok.token_to_id(t)
                if i is None:
                    i = self._unk_id
                cache[t] = i
            ids.append(i)
        return self._tok.decode(ids, skip_special_tokens=True)
