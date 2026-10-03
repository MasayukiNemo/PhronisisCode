#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""起こしJSONの後掃除: 幻覚除去・時刻修復・倍速戻し.

whisper系の定番幻覚 (YouTube締め文句の付着) を落とし、壊れた時刻を修復し、
倍速音声の時刻を等倍に戻す。話者ラベルは触らない (分離のやり直しが必要なため)。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HALLUCINATIONS = [
    "ご視聴ありがとうございました",
    "チャンネル登録よろしくお願いします",
    "チャンネル登録お願いします",
    "高評価よろしくお願いします",
    "次回もお楽しみに",
]
PAT = re.compile("^(" + "|".join(re.escape(h) for h in HALLUCINATIONS) + ")+")
LOOP_PAT = re.compile(r"^(.{1,6}?)[、・ 　]+(\1[、・ 　]+){2,}\1?$")


def collapse_loop(text: str) -> tuple[str, bool]:
    m = LOOP_PAT.match(text.strip())
    if m:
        return m.group(1), True
    return text, False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="起こしJSONの後掃除")
    p.add_argument("--input", required=True, help="入力JSON (segments配列)")
    p.add_argument("--out-dir", required=True, help="出力先ディレクトリ")
    p.add_argument("--scale", type=float, default=1.0,
                   help="時刻倍率。1.4倍速音声なら1.4 (既定 1.0)")
    p.add_argument("--stem", default="",
                   help="出力名。空なら入力名+_clean")
    return p.parse_args(argv)


def clean_text(text: str) -> tuple[str, bool]:
    stripped = PAT.sub("", text).strip()
    return stripped, stripped != text.strip()


def repair_time(start: float, end: float, text: str) -> tuple[float, float]:
    if end <= start:
        end = start + max(1.0, len(text) * 0.25)
    return start, end


def format_srt_time(sec: float) -> str:
    total_ms = max(0, int(sec * 1000))
    h = total_ms // 3600000
    m = (total_ms % 3600000) // 60000
    s = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    src = Path(args.input)
    if not src.exists():
        print("エラー: 入力が見つかりません: " + str(src), file=sys.stderr)
        return 2
    scale = float(args.scale)
    if scale <= 0:
        print("エラー: scaleは正数で指定してください", file=sys.stderr)
        return 2
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except Exception as exc:
        print("エラー: JSON読込失敗: " + str(exc), file=sys.stderr)
        return 2
    segs = data.get("segments", []) if isinstance(data, dict) else []
    cleaned: list[dict] = []
    stripped = 0
    dropped = 0
    looped = 0
    merged = 0
    for s in segs:
        text, hit = clean_text(str(s.get("text", "")))
        if hit:
            stripped += 1
        text, looped_hit = collapse_loop(text)
        if looped_hit:
            looped += 1
        if not text:
            dropped += 1
            continue
        st, en = repair_time(float(s.get("start", 0.0)), float(s.get("end", 0.0)), text)
        # 直前と同一の短文はループとみなし結合 (相槌・繰返し対策)
        if cleaned and len(text) <= 6 and cleaned[-1]["text"] == text:
            cleaned[-1]["end"] = round(en * scale, 2)
            merged += 1
            continue
        cleaned.append({
            "index": len(cleaned),
            "start": round(st * scale, 2),
            "end": round(en * scale, 2),
            "speaker": str(s.get("speaker", "SPEAKER_00")),
            "text": text,
            "avg_logprob": float(s.get("avg_logprob", 0.0)),
            "no_speech_prob": float(s.get("no_speech_prob", 0.0)),
        })
    cleaned.sort(key=lambda s: s["start"])
    for i, s in enumerate(cleaned):
        s["index"] = i
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.stem or (src.stem + "_clean")
    meta = {"source": str(src), "scale": scale, "stripped": stripped,
            "loop_collapsed": looped, "loop_merged": merged,
            "dropped": dropped, "kept": len(cleaned),
            "speakers": sorted(set(s["speaker"] for s in cleaned))}
    (out_dir / (stem + ".json")).write_text(
        json.dumps({"meta": meta, "segments": cleaned}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    with open(out_dir / (stem + ".txt"), "w", encoding="utf-8") as f:
        for m in cleaned:
            f.write("[" + format_srt_time(m["start"]) + " " + m["speaker"] + "] "
                    + m["text"] + "\n")
    print("幻覚除去: %d件 / ループ圧縮: %d件 / 短文結合: %d件 / 空落ち: %d件 / 維持: %d件 / 話者: %d種" % (
        stripped, looped, merged, dropped, len(cleaned), len(meta["speakers"])))
    print("出力: " + str(out_dir / (stem + ".json")))
    print("出力: " + str(out_dir / (stem + ".txt")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
