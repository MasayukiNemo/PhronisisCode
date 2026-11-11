# DSH（DeepSeek Harness）bridge

DSH はこの端末で稼働する Web UI（127.0.0.1:3080）。DSH 側カイと対話する。本家 PhronisisCore の bridge を Code に移植済み（2026-11-11）。

## 構成

- 本体: スケジュールタスク `PhronisisDSH`（`C:\Users\nemom\PhronisisDSH\start_dsh.cmd`）が node で `dsh web` を起動
- 認証: トークン。`%LOCALAPPDATA%\PhronisisDSH\start.out`（毎回 `.prev` にローテーション）。`dsh_common.find_token()` が検出
- スクリプト（`scripts/`）:
  - `dsh_common.py` — トークン検出・URL・セッションオープン・本文保存
  - `dsh_send.py` — メッセージ送信
  - `dsh_check.py` — 最新応答を `scratch/dsh_reply.txt` に保存
  - `dsh_answer.py` — Ask the user の択一に回答

## 使い方

```
python scripts/dsh_send.py -m "本文" [-s セッション名の部分文字列] [--new]
python scripts/dsh_check.py [-s セッション名] [-o 出力先]
python scripts/dsh_answer.py -o "選択肢の部分文字列"
```

## Code適応（2026-11-11）

- `dsh_common.find_token` に現行ランチャーのログ（`%LOCALAPPDATA%\PhronisisDSH/start.out` と `.prev`、`start.log`）を追加。それ以外は本家ロジック不変。
- 旧パス（`%TEMP%\dsh_out*`）は互換のため残置。

## 稼働

- DSH v0.1.2-rc.1（`%APPDATA%\npm\node_modules\@deepseek-ai\dsh`）
- タスク `PhronisisDSH`（`C:\Users\nemom\PhronisisDSH\start_dsh.cmd`）

## 既知の状態（2026-11-11）

- 保存本文に `This turn failed ... no configured model "muse-spark-1.3-contributor"` / `UNKNOWN_MODEL` が含まれる。bridge は UI に届くが、DSH側カイは応答不能の可能性。
- 发送往復（dsh_send → dsh_check）は未検証。DSH側カイの復旧と根本さんの承認が要る。

## 注意

- DSH UI は共有リソース（DSH側カイ）。乱打しない
- 送信 → 応答確認で1往復。完了は応答の確認
- 応答は `scratch/dsh_reply.txt` を Read で読む（cp932対策）
- トークンが見つからない場合は `%LOCALAPPDATA%\PhronisisDSH\start.out` と `.prev` を確認
