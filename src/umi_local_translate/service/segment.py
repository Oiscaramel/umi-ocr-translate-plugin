# -*- coding: utf-8 -*-
"""
长文本分段。

OCR 结果通常是「一段话被折成多行」，直接按行翻译会丢掉上下文，
所以默认按「段落」翻译：连续非空行合并成一段，空行作为段落分隔。

保留两种模式：
    block - 按段落翻译，重建时保留空行（默认，质量最好）
    line  - 按行翻译，重建时逐行对齐（适合表格 / 菜单）
"""

import re

# 句子结束符（中英文）
_SENT_END = set("。！？!?…；;")
_SENT_END_WITH_DOT = _SENT_END | {"."}

_PARA_SPLIT = re.compile(r"\n[ \t\u3000]*\n+")


def _hard_split(piece, max_chars):
    """超长片段按尽量自然的位置切开（优先空格，其次标点，最后硬切）"""
    out = []
    rest = piece
    while len(rest) > max_chars:
        window = rest[:max_chars]
        cut = -1
        for ch in (" ", "\u3000", "，", ",", "、", "；", ";", "：", ":"):
            pos = window.rfind(ch)
            if pos > max_chars // 3:
                cut = max(cut, pos + 1)
        if cut <= 0:
            cut = max_chars
        out.append(rest[:cut].strip())
        rest = rest[cut:].lstrip()
    if rest.strip():
        out.append(rest.strip())
    return [x for x in out if x]


def split_long(line, max_chars=280):
    """把一行过长的文本按句子边界切成若干段"""
    line = line.strip()
    if not line:
        return []
    if len(line) <= max_chars:
        return [line]

    # 先按句子结束符切
    pieces = []
    buf = []
    for ch in line:
        buf.append(ch)
        if ch in _SENT_END or (ch == "." and len(buf) > 1 and buf[-2].isdigit() is False):
            pieces.append("".join(buf).strip())
            buf = []
    tail = "".join(buf).strip()
    if tail:
        pieces.append(tail)
    pieces = [p for p in pieces if p]

    # 再把相邻短句合并到不超过 max_chars
    merged = []
    cur = ""
    for p in pieces:
        if not cur:
            cur = p
        elif len(cur) + 1 + len(p) <= max_chars:
            cur = cur + " " + p
        else:
            merged.append(cur)
            cur = p
    if cur:
        merged.append(cur)

    # 仍然超长的片段硬切
    out = []
    for p in merged:
        if len(p) <= max_chars:
            out.append(p)
        else:
            out.extend(_hard_split(p, max_chars))
    return out


def build(text, mode="block", max_chars=280):
    """
    返回 (segments, layout)

    segments : list[str]            待翻译的文本片段（按顺序）
    layout   : list[list[int]|None] 每段输出行的片段下标；None 表示空行
    """
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    segments = []
    layout = []

    if mode == "line":
        for raw in text.split("\n"):
            line = raw.strip()
            if not line:
                layout.append(None)
                continue
            idxs = []
            for seg in split_long(line, max_chars):
                idxs.append(len(segments))
                segments.append(seg)
            layout.append(idxs)
        return segments, layout

    # block 模式
    paragraphs = _PARA_SPLIT.split(text.strip()) if text.strip() else []
    for para in paragraphs:
        joined = " ".join(x.strip() for x in para.split("\n") if x.strip())
        if not joined:
            layout.append(None)
            continue
        idxs = []
        for seg in split_long(joined, max_chars):
            idxs.append(len(segments))
            segments.append(seg)
        layout.append(idxs)
    return segments, layout


def rebuild(translated, layout, mode="block", target="en"):
    """把逐段译文按原结构拼回整段文本"""
    sep_line = " " if target == "en" else ""
    out = []
    if mode == "line":
        for idxs in layout:
            if idxs is None:
                out.append("")
            else:
                out.append(sep_line.join(translated[i] for i in idxs))
        return "\n".join(out).strip("\n")

    paras = []
    for idxs in layout:
        if idxs is None:
            continue
        paras.append(sep_line.join(translated[i] for i in idxs))
    return "\n\n".join(paras)
