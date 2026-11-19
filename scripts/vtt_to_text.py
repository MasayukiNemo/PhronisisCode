"""YouTube 自動字幕 VTT → 平文の文字起こし（内容の要約・改変はしない）

YouTube の自動字幕は、各キューが「直前の行の末尾」＋「新しい行」の2行表示になる。
そのため、キューごとの最終行を取り出し、直前の文との重なりを差し引いて連結する。
タイムスタンプと <...> タグは除去する。文末で段落を入れる。内容は変えない。
"""

import io
import os
import re
import sys

TAG = re.compile(r"<[^>]*>")
TIME = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3} --> ")
META = ("WEBVTT", "Kind:", "Language:", "NOTE")


def read_cues(path):
    cues = []
    block = []
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line.strip():
                if block:
                    cues.append(block)
                    block = []
                continue
            block.append(line)
    if block:
        cues.append(block)
    return cues


def clean(text):
    return TAG.sub("", text).replace("\u200b", "").strip()


def last_line(block):
    lines = [
        clean(line)
        for line in block
        if not TIME.match(line) and not line.startswith(META)
    ]
    lines = [line for line in lines if line]
    return lines[-1] if lines else ""


def build_text(path):
    accumulated = ""
    for block in read_cues(path):
        new = last_line(block)
        if not new:
            continue
        if new == accumulated:
            continue
        overlap = 0
        limit = min(len(new), len(accumulated))
        for size in range(limit, 0, -1):
            if accumulated.endswith(new[:size]):
                overlap = size
                break
        piece = new[overlap:]
        if piece:
            accumulated += piece
    return re.sub(r"\s+", "", accumulated)


def to_paragraphs(text, limit=300):
    paragraphs = []
    buffer = ""
    for char in text:
        buffer += char
        if char in "。！？" and len(buffer) >= 40:
            paragraphs.append(buffer)
            buffer = ""
        elif len(buffer) >= limit and char in "、":
            paragraphs.append(buffer)
            buffer = ""
    if buffer:
        paragraphs.append(buffer)
    return paragraphs


def main():
    if len(sys.argv) < 3:
        print("usage: vtt_to_text.py INPUT.vtt OUTPUT.txt", file=sys.stderr)
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    text = build_text(src)
    paragraphs = to_paragraphs(text)
    with io.open(dst, "w", encoding="utf-8") as handle:
        handle.write("\n\n".join(paragraphs))
        handle.write("\n")
    print(os.path.basename(dst), "chars=", len(text), "paragraphs=", len(paragraphs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
