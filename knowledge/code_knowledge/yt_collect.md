# yt_collect — YouTube チャンネルの差分取得

`scripts/yt_collect.py`。2026-11-18 の実地テスト（検体19号）を、恒常運用できる形に落としたもの。モコの判断（scripts に残す・差分で更新）による。

## 使い方

```
python scripts/yt_collect.py --channel "@fx_trader_tiritumo" --out scratch/yt/chiritumo --limit 20
python scripts/yt_collect.py --channel "https://www.youtube.com/@handle" --out DIR --dry-run
```

- `--channel`: `@handle` か チャンネルURL（`/videos` は自動で付く）
- `--out`: 出力先。初回は空でよい
- `--limit`: 1回で取る新着の上限（0=無制限、新しい順）
- `--sleep`: リクエスト間隔（既定 0.5 秒）
- `--yt-dlp`: yt-dlp の実行パス（既定は PATH。venv 運用なら明示する）
- `--sub-langs`: 字幕の言語（既定 `ja-orig`）
- `--no-subs`: 字幕を取らない
- `--dry-run`: 新着の列挙だけ

## 出力

- `seen.json` — 取得済み ID。差分はこれで決まる
- `videos_meta.tsv` — id / 公開日 / 秒 / タイトル(JSON) / 概要欄(JSON)。追記・ID重複なし
- `videos.csv` — 読み物用（id / url / 公開日 / 分 / タイトル / 概要欄文字数 / 概要欄先頭120字）
- `subs/` — 自動字幕（vtt）
- `collect.log` — 実行ログ

## 実測（2026-11-18、@fx_trader_tiritumo）

- フラット列挙: 145本（API JSON 4ページ）
- 全件メタデータ: 欠損0・空概要欄0、約12分（sleep 0.5）
- 字幕: 自動字幕 `ja-orig` が取れる。手動字幕は無い
- 差分の動作: `--limit 2` で2本取得 → 再実行で new=143 から次の2本。ID重複なし
- `/shorts` と `/streams` はタブが存在しない（長尺のみのチャンネル）

## 注意

- フラット列挙のタイトルは翻訳・切詰めされる。列挙には ID だけを使い、タイトルは本抽出から取る（実装はそうしている）
- 一覧の行は「11文字の ASCII [A-Za-z0-9_-]」だけを ID として採用する（2026-11-18、モコの検品指摘を受けて）。yt-dlp のログ行を ID と取り違えない
- seen に入れるのは「メタデータが取れた ID」。字幕だけ失敗した動画も seen に入るため、字幕の再取得はされない。字幕のリトライが要るなら見直し箇所
- new=0 のときは一覧取得だけで終了する（実測 7.4 秒、取得0）
- yt-dlp は「JS ランタイムが無い」と警告する。メタデータと字幕は通る。動画本体を取る段階では deno が要る
- 字幕は自動生成なので固有名詞の誤変換がある（例: ちりつも → チり立つ）。原音との突き合わせが要る箇所がある
- 恒常ジョブにはしていない。回すのは依頼があったとき
