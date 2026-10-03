#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""話者分離つき文字起こし PoC (CPU / faster-whisper + sherpa-onnx任意).

仕様メモ:
- turbo モデルは transcribe 専用で translate 不可のため、本スクリプトは起こしのみ。
  日本語化が必要な場合は出力を Kai に渡して翻訳する運用とする。
  --task translate が来たら明示エラーで Kai 翻訳へ誘導する。
- 長時間 (2時間一括) は vad_filter 前提でもメモリ・時間を消費するため警告表示する。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SUPPORTED_EXTS = {".m4a", ".mp3", ".wav"}
TARGET_SR = 16000
FALLBACK_SPEAKER = "SPEAKER_00"

PIP_BASE = "pip install faster-whisper soundfile numpy"
PIP_SHERPA = "pip install sherpa-onnx"


def eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="diarize + transcribe PoC (CPU)")
    p.add_argument("--input", required=True, help="入力音声 m4a/mp3/wav")
    p.add_argument("--out-dir", default="tasks/261002_diarization/poc/out",
                   help="出力先ディレクトリ (既定はリポジトリ内 poc/out)")
    p.add_argument("--model", default="turbo", help="faster-whisper モデル名 (既定 turbo)")
    p.add_argument("--language", default="auto", choices=["auto", "ja", "zh"],
                   help="起こし言語 auto/ja/zh (翻訳はしない)")
    p.add_argument("--task", default="transcribe", choices=["transcribe", "translate"],
                   help="transcribe のみ対応。translate はエラー誘導用")
    p.add_argument("--num-speakers", type=int, default=0,
                   help="話者数。0 は自動 (既定 0)")
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda"],
                   help="実行デバイス (既定 cpu)")
    p.add_argument("--cpu-threads", type=int, default=0,
                   help="CPUスレッド数。0 は自動 (論理コア数)。遅い場合は明示指定")
    p.add_argument("--batch-size", type=int, default=0,
                   help="バッチ推論。0 は通常経路。CPUでも8程度で高速化する場合あり")
    return p.parse_args(argv)


def check_translate_request(task: str) -> None:
    if task == "translate":
        raise ValueError(
            "turbo モデルは translate 不可 (transcribe 専用仕様)。"
            "transcribe 出力の TXT/JSON を Kai に渡して日本語化してください。")


def validate_input(input_path: Path) -> Path:
    if not input_path.exists():
        raise FileNotFoundError("入力ファイルが見つかりません: " + str(input_path))
    if input_path.suffix.lower() not in SUPPORTED_EXTS:
        raise ValueError("対応拡張子は m4a/mp3/wav です: " + input_path.suffix)
    return input_path.resolve()


def warn_long_audio(input_path: Path) -> None:
    size_mb = input_path.stat().st_size / (1024 * 1024)
    if size_mb < 25:
        return
    print("注意: 長時間一括 (30分-2時間) は CPU で時間がかかります。")
    print("推奨: 30-60分に事前分割すると安定します。")
    if size_mb > 100:
        print("警告: ファイルサイズ %.1f MB。メモリ不足時は分割してください。" % size_mb)


def to_wav_16k_mono(src: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / (src.stem + "_16k.wav")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is not None:
        cmd = [ffmpeg, "-y", "-i", str(src), "-ac", "1", "-ar", str(TARGET_SR),
               "-c:a", "pcm_s16le", str(dst)]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            tail = (proc.stderr or "")[-1500:]
            raise RuntimeError("ffmpeg 変換に失敗しました: " + tail)
        return dst
    return _to_wav_without_ffmpeg(src, dst)


def _to_wav_without_ffmpeg(src: Path, dst: Path) -> Path:
    try:
        import soundfile as sf
    except ImportError:
        raise ValueError(
            "ffmpeg がなく soundfile も未導入のため変換できません。"
            "対処1: ffmpeg を導入して再実行 / "
            "対処2: " + PIP_BASE + " を実行し wav 入力で再実行")
    try:
        import numpy as np
    except ImportError:
        raise ValueError("numpy 未導入のためリサンプルできません。対処: " + PIP_BASE)
    if src.suffix.lower() != ".wav":
        raise ValueError(
            "ffmpeg なしでは m4a/mp3 を読み込めません。"
            "ffmpeg を導入するか、事前に wav へ変換してください。"
            "例: ffmpeg -i input.m4a -ac 1 -ar 16000 out.wav")
    try:
        data, sr = sf.read(str(src), always_2d=True)
    except Exception as exc:
        raise RuntimeError("wav 読込に失敗しました: " + str(exc))
    mono = data.mean(axis=1)
    if int(sr) != TARGET_SR:
        src_idx = [float(i) / float(len(mono)) for i in range(len(mono))]
        dst_len = int(len(mono) * TARGET_SR / float(sr))
        dst_idx = [float(i) / float(dst_len) for i in range(dst_len)]
        mono = np.interp(dst_idx, src_idx, mono).astype("float32")
    sf.write(str(dst), mono, TARGET_SR, subtype="PCM_16")
    print("注意: ffmpeg 未使用のため soundfile 経由で変換しました (wav 入力のみ対応)。")
    return dst


def transcribe_whisper(wav_path: Path, model_name: str, language: str, device: str,
                       cpu_threads: int = 0, batch_size: int = 0) -> list[dict]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ValueError("faster-whisper 未導入のため起こしを実行できません。対処: " + PIP_BASE)
    lang_opt: str | None = None if language == "auto" else language
    try:
        import soundfile as sf
    except ImportError:
        raise ValueError("soundfile 未導入のため音声を読めません。対処: " + PIP_BASE)
    try:
        import numpy as np
    except ImportError:
        raise ValueError("numpy 未導入のため音声を読めません。対処: " + PIP_BASE)
    try:
        threads = cpu_threads if cpu_threads > 0 else (os.cpu_count() or 4)
        model = WhisperModel(model_name, device=device, compute_type="int8",
                             cpu_threads=threads)
    except Exception as exc:
        raise RuntimeError("モデル読込に失敗しました (%s): %s" % (model_name, str(exc)))
    print("起こし開始: model=%s language=%s device=%s" % (model_name, language, device))
    try:
        data, sr = sf.read(str(wav_path), dtype="float32", always_2d=True)
    except Exception as exc:
        raise RuntimeError("wav 読込に失敗しました: " + str(exc))
    if int(sr) != TARGET_SR:
        raise RuntimeError("サンプルレート異常: %d (16k wavを期待)" % int(sr))
    audio = np.ascontiguousarray(data.mean(axis=1), dtype=np.float32)
    try:
        # ndarray渡しに固定。パス渡しはPyAV経由になりav版非互換を踏むため使わない。
        if batch_size > 0:
            from faster_whisper import BatchedInferencePipeline
            pipe = BatchedInferencePipeline(model=model)
            segments_iter, _info = pipe.transcribe(
                audio, batch_size=batch_size, beam_size=1, vad_filter=True,
                language=lang_opt)
        else:
            segments_iter, _info = model.transcribe(
                audio, beam_size=1, vad_filter=True,
                word_timestamps=False, language=lang_opt)
    except Exception as exc:
        raise RuntimeError("transcribe に失敗しました: " + str(exc))
    out: list[dict] = []
    for seg in segments_iter:
        out.append({
            "start": float(seg.start),
            "end": float(seg.end),
            "text": str(seg.text).strip(),
            "avg_logprob": float(getattr(seg, "avg_logprob", 0.0)),
            "no_speech_prob": float(getattr(seg, "no_speech_prob", 0.0)),
        })
    if not out:
        print("警告: セグメントが0件でした。無音区間のみか、音量を確認してください。")
    return out


def try_diarize(wav_path: Path, num_speakers: int) -> list[dict] | None:
    try:
        import sherpa_onnx  # noqa: F401
    except ImportError:
        print("注意: sherpa-onnx 未導入のため単一話者フォールバックで継続します。")
        print("話者分離を使う場合: " + PIP_SHERPA)
        return None
    model_path = _locate_segmentation_model()
    if model_path is None:
        print("注意: sherpa-onnx 分離モデル未配置のため単一話者フォールバックで継続します。")
        print("配置後に num-speakers 指定で再実行できます (0=自動)。")
        return None
    print("分離モデル検出: " + str(model_path) + " (PoC簡易結合を使用)")
    return _run_sherpa_segmentation(wav_path, model_path, num_speakers)


def _locate_segmentation_model() -> Path | None:
    import os
    env_path = os.environ.get("SHERPA_SEGMENT_MODEL", "")
    if env_path:
        cand = Path(env_path)
        if cand.exists():
            return cand
    base = Path(__file__).resolve().parent / "models"
    if base.is_dir():
        for child in base.iterdir():
            if child.suffix == ".onnx" and "segment" in child.name.lower():
                return child
    return None


def _run_sherpa_segmentation(wav_path: Path, model_path: Path, num_speakers: int) -> list[dict] | None:
    # TODO: sherpa-onnx 実機結合は未実装。モデル配置後の本結合で差し替える。
    eprint("注意: sherpa-onnx 実機結合は PoC 範囲外のためフォールバックします。")
    eprint("モデル配置済み: " + str(model_path) + " / num_speakers=" + str(num_speakers))
    return None


def assign_speakers(whisper_segs: list[dict], diar_segs: list[dict] | None) -> list[dict]:
    merged: list[dict] = []
    for idx, ws in enumerate(whisper_segs):
        speaker = FALLBACK_SPEAKER
        if diar_segs:
            best = FALLBACK_SPEAKER
            best_overlap = 0.0
            for ds in diar_segs:
                overlap = max(0.0, min(float(ws["end"]), float(ds["end"]))
                              - max(float(ws["start"]), float(ds["start"])))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best = str(ds.get("speaker", FALLBACK_SPEAKER))
            if best_overlap > 0:
                speaker = best
        merged.append({
            "index": idx,
            "start": float(ws["start"]),
            "end": float(ws["end"]),
            "speaker": speaker,
            "text": str(ws["text"]),
            "avg_logprob": float(ws.get("avg_logprob", 0.0)),
            "no_speech_prob": float(ws.get("no_speech_prob", 0.0)),
        })
    return merged


def format_srt_time(sec: float) -> str:
    total_ms = max(0, int(sec * 1000))
    h = total_ms // 3600000
    m = (total_ms % 3600000) // 60000
    s = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def write_outputs(merged: list[dict], out_dir: Path, stem: str,
                  meta: dict) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / (stem + ".json")
    srt_path = out_dir / (stem + ".srt")
    txt_path = out_dir / (stem + ".txt")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "segments": merged}, f, ensure_ascii=False, indent=2)
    with open(srt_path, "w", encoding="utf-8") as f:
        for seg in merged:
            f.write(str(seg["index"] + 1) + "\n")
            f.write(format_srt_time(seg["start"]) + " --> " + format_srt_time(seg["end"]) + "\n")
            f.write("[" + seg["speaker"] + "] " + seg["text"] + "\n\n")
    with open(txt_path, "w", encoding="utf-8") as f:
        for seg in merged:
            f.write("[" + format_srt_time(seg["start"]) + " " + seg["speaker"] + "] "
                    + seg["text"] + "\n")
    return {"json": json_path, "srt": srt_path, "txt": txt_path}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        check_translate_request(args.task)
        src = validate_input(Path(args.input))
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        warn_long_audio(src)
        wav_path = to_wav_16k_mono(src, out_dir)
        whisper_segs = transcribe_whisper(wav_path, args.model, args.language,
                                            args.device, int(args.cpu_threads),
                                            int(args.batch_size))
        diar_segs = try_diarize(wav_path, int(args.num_speakers))
        merged = assign_speakers(whisper_segs, diar_segs)
        meta = {
            "input": str(src),
            "model": args.model,
            "language": args.language,
            "device": args.device,
            "num_speakers": int(args.num_speakers),
            "diarization": bool(diar_segs),
            "count": len(merged),
        }
        paths = write_outputs(merged, out_dir, src.stem, meta)
        print("完了: %d 件 / 分離=%s" % (len(merged), "あり" if diar_segs else "なし(単一話者)"))
        for key in ["json", "srt", "txt"]:
            print("出力: " + str(paths[key]))
        return 0
    except FileNotFoundError as exc:
        eprint("エラー: " + str(exc))
        return 2
    except ValueError as exc:
        eprint("エラー: " + str(exc))
        return 2
    except RuntimeError as exc:
        eprint("エラー: " + str(exc))
        return 1
    except KeyboardInterrupt:
        eprint("中断: ユーザー操作により中断しました。")
        return 130


if __name__ == "__main__":
    sys.exit(main())
