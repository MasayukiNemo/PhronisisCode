"""vtt_to_text.py — 字幕 VTT を平文へ（内容の要約・改変はしない）

使い方:
  python scripts/vtt_to_text.py INPUT.vtt OUTPUT.txt [--mode manual|auto|detect] [--lang ja|en|detect]

整形だけを行う:
  - タイムスタンプと <...> タグの除去
  - 自動字幕の「前の行を繰り返す」重複の除去
  - 文末で段落を入れる（日本語は 。！？ / 英語は . ! ?）
  - 要約・言い換え・誤変換の修正はしない

mode:
  manual — 手動字幕。キュー内の複数行は1つの文として扱う
  auto   — 自動字幕。キューごとの最終行を、直前の文との重なりを差し引いて連結
  detect — 行の重なり方から自動判定（既定）

lang:
  ja / en / detect（既定）。空白の入れ方と段落の切り方が変わる
"""

import argparse
import io
import re
import sys

TAG = re.compile(r"<[^>]*>")
TIME = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3} --> ")
META = ("WEBVTT", "Kind:", "Language:", "NOTE")
CJK = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")


def read_cues(path):
    cues, block = [], []
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


def cue_lines(block):
    return [
        clean(line)
        for line in block
        if not TIME.match(line) and not line.startswith(META)
    ]


def detect_mode(cues):
    """自動判定。YouTube の自動字幕はキュー内に <c> や <00:00:00.000> の
    インライン時刻タグを持つ。手動字幕は持たない。"""
    total = 0
    tagged = 0
    for block in cues:
        text = " ".join(block)
        if TIME.match(block[0] or ""):
            total += 1
            if "<c>" in text or re.search(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", text):
                tagged += 1
    if total and tagged / total > 0.2:
        return "auto"
    return "manual"


def join_lines(lines, lang):
    if lang == "ja":
        return "".join(lines)
    return " ".join(lines)


def overlap_len(accumulated, new):
    limit = min(len(new), len(accumulated))
    for size in range(limit, 0, -1):
        if accumulated.endswith(new[:size]):
            return size
    return 0


def build_text(cues, mode, lang):
    accumulated = ""
    for block in cues:
        lines = [line for line in cue_lines(block) if line]
        if not lines:
            continue
        if mode == "auto":
            new = lines[-1]
        else:
            new = join_lines(lines, lang)
        if not new:
            continue
        if new == accumulated:
            continue
        if mode == "auto":
            piece = new[overlap_len(accumulated, new):]
        else:
            piece = new
            if accumulated and lang == "en" and not accumulated.endswith(" "):
                piece = " " + piece
        if piece:
            accumulated += piece
    return accumulated


def normalize(text, lang):
    if lang == "ja":
        return re.sub(r"\s+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def paragraphs(text, lang, limit=400):
    if lang == "ja":
        stops = "。！？"
        buffer = ""
        out = []
        for char in text:
            buffer += char
            if char in stops and len(buffer) >= 40:
                out.append(buffer)
                buffer = ""
            elif len(buffer) >= 300 and char == "、":
                out.append(buffer)
                buffer = ""
        if buffer:
            out.append(buffer)
        return out
    # English: split on sentence end, gather into paragraph-sized chunks
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out, buffer = [], ""
    for sentence in sentences:
        if not sentence:
            continue
        if buffer and len(buffer) + len(sentence) > limit:
            out.append(buffer.strip())
            buffer = sentence
        else:
            buffer = (buffer + " " + sentence).strip() if buffer else sentence
    if buffer:
        out.append(buffer.strip())
    return out


def main():
    parser = argparse.ArgumentParser(description="字幕VTTを平文へ（整形のみ）")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--mode", choices=["manual", "auto", "detect"], default="detect")
    parser.add_argument("--lang", choices=["ja", "en", "detect"], default="detect")
    args = parser.parse_args()

    cues = read_cues(args.input)
    mode = detect_mode(cues) if args.mode == "detect" else args.mode
    raw = build_text(cues, mode, "ja" if args.lang == "ja" else "en")
    lang = args.lang
    if lang == "detect":
        lang = "ja" if len(CJK.findall(raw)) > len(raw) * 0.2 else "en"
    text = normalize(build_text(cues, mode, lang), lang)
    paras = paragraphs(text, lang)

    with io.open(args.output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n\n".join(paras))
        handle.write("\n")
    print(f"mode={mode} lang={lang} chars={len(text)} paragraphs={len(paras)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
