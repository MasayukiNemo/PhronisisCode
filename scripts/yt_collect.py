"""yt_collect.py — YouTube チャンネルの差分取得（列挙・メタデータ・自動字幕）

使い方:
  python scripts/yt_collect.py --channel @handle --out scratch/yt --limit 20
  python scripts/yt_collect.py --channel https://www.youtube.com/@handle --out DIR --dry-run

何をするか:
  1. チャンネルの動画一覧を yt-dlp のフラット列挙で取る（IDだけ使う。タイトルは翻訳・切詰めされるため使わない）
  2. 既取得の ID（out/seen.json）と突き合わせ、新着だけを対象にする
  3. 新着のメタデータ（公開日・タイトル・概要欄）と自動字幕（既定 ja-orig）を取る
  4. out/ に追記し、videos.csv を再生成する

出力:
  out/seen.json        取得済み ID（+ 取得時刻）。次回の差分はこれで決まる
  out/videos_meta.tsv  id / 公開日 / 秒 / タイトル(JSON) / 概要欄(JSON)。追記・ID重複なし
  out/videos.csv       読み物用（id / url / 公開日 / 分 / タイトル / 概要欄先頭）
  out/subs/            自動字幕（既定 ja-orig, vtt）
  out/collect.log      実行ログ

注意:
  - yt-dlp 本体は同梱しない。--yt-dlp でパスを渡す（既定は PATH 上の yt-dlp）
  - 字幕は自動生成のみ。手動字幕がある動画では --sub-langs を変える
  - 取得間隔は --sleep で空ける（既定 0.5 秒）
"""

import argparse
import csv
import io
import json
import os
import string
import subprocess
import sys
import time

META_FIELDS = "%(id)s\t%(upload_date)s\t%(duration)s\t%(title)j\t%(description)j"
ID_CHARS = set(string.ascii_letters + string.digits + "_-")


def log(path, message):
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {message}"
    print(line, flush=True)
    with io.open(path, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def channel_url(value):
    if value.startswith("http://") or value.startswith("https://"):
        url = value.rstrip("/")
        if not url.endswith("/videos"):
            url += "/videos"
        return url
    handle = value if value.startswith("@") else "@" + value
    return f"https://www.youtube.com/{handle}/videos"


def run(cmd, log_path):
    with io.open(log_path, "a", encoding="utf-8") as handle:
        handle.write("$ " + " ".join(cmd) + "\n")
        handle.flush()
        completed = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT)
    return completed.returncode


def list_ids(yt_dlp, url, sleep, tmp_path, log_path):
    cmd = [yt_dlp, "--flat-playlist", "--ignore-errors"]
    if sleep:
        cmd += ["--sleep-requests", str(sleep)]
    cmd += ["--print", "%(id)s", url]
    with io.open(tmp_path, "w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT)
    if completed.returncode not in (0, 1):
        return []
    ids = []
    with io.open(tmp_path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            value = line.strip()
            # yt-dlp のログ行（WARNING:/ERROR: など）を ID と取り違えない。
            # YouTube の動画 ID は 11 文字の [A-Za-z0-9_-]（ASCII のみ）。
            if len(value) == 11 and all(c in ID_CHARS for c in value):
                ids.append(value)
    with io.open(log_path, "a", encoding="utf-8") as handle:
        handle.write(f"# listed {len(ids)} ids\n")
    return ids


def fetch_meta(yt_dlp, urls, sleep, out_dir, log_path):
    tmp = os.path.join(out_dir, "meta_run.tsv")
    if os.path.exists(tmp):
        os.remove(tmp)
    cmd = [yt_dlp, "--skip-download", "--ignore-errors"]
    if sleep:
        cmd += ["--sleep-requests", str(sleep)]
    cmd += ["--print-to-file", META_FIELDS, tmp] + urls
    code = run(cmd, log_path)
    records = []
    if os.path.exists(tmp):
        with io.open(tmp, encoding="utf-8") as handle:
            for line in handle:
                fields = line.rstrip("\n").split("\t")
                if len(fields) >= 5 and fields[0]:
                    records.append(fields)
    if os.path.exists(tmp):
        os.remove(tmp)
    return code, records


def fetch_subs(yt_dlp, urls, sleep, out_dir, lang, log_path):
    subs_dir = os.path.join(out_dir, "subs")
    os.makedirs(subs_dir, exist_ok=True)
    cmd = [yt_dlp, "--skip-download", "--ignore-errors", "--write-auto-subs"]
    if sleep:
        cmd += ["--sleep-requests", str(sleep)]
    cmd += [
        "--sub-langs", lang,
        "--sub-format", "vtt",
        "-o", os.path.join(subs_dir, "%(id)s.%(ext)s"),
    ] + urls
    return run(cmd, log_path)


def load_seen(path):
    if not os.path.exists(path):
        return {}
    try:
        with io.open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_seen(path, seen):
    with io.open(path, "w", encoding="utf-8") as handle:
        json.dump(seen, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def load_meta(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) >= 5 and fields[0]:
                rows.append(fields)
    return rows


def write_csv(meta_path, csv_path):
    rows = load_meta(meta_path)
    with io.open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "video_id", "url", "upload_date", "duration_min", "title",
            "description_chars", "description_head",
        ])
        for fields in rows:
            try:
                title = json.loads(fields[3])
                description = json.loads(fields[4])
            except ValueError:
                continue
            writer.writerow([
                fields[0],
                f"https://www.youtube.com/watch?v={fields[0]}",
                fields[1],
                round(int(fields[2] or 0) / 60),
                title,
                len(description),
                description.replace("\n", " ")[:120],
            ])
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="YouTube チャンネルの差分取得")
    parser.add_argument("--channel", required=True, help="@handle か チャンネルURL")
    parser.add_argument("--out", required=True, help="出力ディレクトリ")
    parser.add_argument("--limit", type=int, default=0,
                        help="1回で取る新着の上限（0=無制限、新しい順）")
    parser.add_argument("--sleep", type=float, default=0.5,
                        help="リクエスト間隔 秒（既定 0.5）")
    parser.add_argument("--yt-dlp", default="yt-dlp", help="yt-dlp の実行パス")
    parser.add_argument("--sub-langs", default="ja-orig",
                        help="字幕の言語（既定 ja-orig。カンマ区切り可）")
    parser.add_argument("--no-subs", action="store_true", help="字幕を取らない")
    parser.add_argument("--dry-run", action="store_true",
                        help="新着の列挙だけして終わる（取得しない）")
    args = parser.parse_args()

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    log_path = os.path.join(out_dir, "collect.log")
    seen_path = os.path.join(out_dir, "seen.json")
    meta_path = os.path.join(out_dir, "videos_meta.tsv")
    csv_path = os.path.join(out_dir, "videos.csv")

    url = channel_url(args.channel)
    seen = load_seen(seen_path)
    log(log_path, f"channel={url} out={out_dir} seen={len(seen)}")

    ids = list_ids(args.yt_dlp, url, args.sleep, os.path.join(out_dir, "ids_run.txt"), log_path)
    if not ids:
        log(log_path, "ERROR: 一覧が取れなかった（yt-dlp のパスと出口を確認）")
        return 2

    new_ids = [video_id for video_id in ids if video_id not in seen]
    log(log_path, f"listed={len(ids)} new={len(new_ids)}")
    if args.limit and args.limit > 0:
        new_ids = new_ids[: args.limit]
    if not new_ids:
        log(log_path, "nothing to do")
        return 0
    if args.dry_run:
        log(log_path, "dry-run: " + ",".join(new_ids))
        return 0

    urls = [f"https://www.youtube.com/watch?v={video_id}" for video_id in new_ids]
    code, records = fetch_meta(args.yt_dlp, urls, args.sleep, out_dir, log_path)
    log(log_path, f"metadata rc={code} records={len(records)}")

    known = {fields[0] for fields in load_meta(meta_path)}
    appended = 0
    with io.open(meta_path, "a", encoding="utf-8") as handle:
        for fields in records:
            if fields[0] in known:
                continue
            handle.write("\t".join(fields) + "\n")
            known.add(fields[0])
            appended += 1
    log(log_path, f"appended={appended}")

    if not args.no_subs:
        sub_code = fetch_subs(args.yt_dlp, urls, args.sleep, out_dir, args.sub_langs, log_path)
        log(log_path, f"subtitles rc={sub_code}")

    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    for fields in records:
        seen[fields[0]] = stamp
    save_seen(seen_path, seen)

    total = write_csv(meta_path, csv_path)
    subs = 0
    subs_dir = os.path.join(out_dir, "subs")
    if os.path.isdir(subs_dir):
        subs = len([name for name in os.listdir(subs_dir) if name.endswith(".vtt")])
    log(log_path, f"done: videos={total} subs={subs} new={appended}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
