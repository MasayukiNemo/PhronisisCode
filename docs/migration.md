# PhronisisCode 環境移行手順

別端末へ PhronisisCode 環境を移行するための手順。推奨は git clone 方式。

## 前提

| 項目 | 要件 | 確認コマンド |
|------|------|-------------|
| Git | 2.x 以上 | `git --version` |
| Python | 3.x（hooks 実行に必要） | `python --version` または `python3 --version` または `py -3 --version` |
| opencode | 最新版 | `opencode --version`（未導入なら https://opencode.ai/docs から導入） |

本リポジトリは絶対パス依存なし。`hooks/*` / `opencode.json` / `shared/*` はすべて相対パス参照。

- hooks: `hooks/pre-commit`, `hooks/pre-push`, `hooks/python_run.sh` は `dirname` 基準で解決
- 設定: `opencode.json` の agent 定義は `shared/phronisis_code/agents/...` 相対参照
- remote: `https://github.com/MasayukiNemo/PhronisisCode.git`

本家 PhronisisCore とは別リポジトリ・独立進化（`.opencode/rules/phronisis_code.md` 115行参照）。同一端末に両方を共存させても競合しない。

## 推奨: git clone 方式

### 1. クローン

```powershell
git clone https://github.com/MasayukiNemo/PhronisisCode.git
Set-Location -LiteralPath "PhronisisCode"
```

### 2. hooks 有効化（初回のみ必須）

```powershell
git config core.hooksPath hooks
git config core.hooksPath  # 出力が hooks であることを確認
```

`README.md` 44行および `AGENTS.md` 起動時手順で定義された必須設定。
`hooks/pre-commit`（UTF-8破損検出）と `hooks/pre-push`（handover整合性 + `scripts/code_health_check.py` 5検査）が有効になる。

### 3. 依存確認

```powershell
git status --short          # clean であること
python --version            # 3.x が見つかること（見つからなければ python3 / py -3 を試す）
```

Python が見つからない場合は `hooks/python_run.sh` の探索順（python3 → python → py -3）に準じて導入する。

### 4. opencode 起動

```powershell
opencode
# 起動時のモデルピッカーで使用モデルを選択（画面選択に従う）
```

起動後、Kai が自動で以下を読み込む：

1. `knowledge/handover.md`
2. `knowledge/conductor_profile_lite.md`
3. `.opencode/rules/phronisis_code.md`
4. `shared/phronisis_code/orchestration_flow_code.md`

読み込み完了後、チャットで「起動完了」が表示されれば移行成功。

### 5. 動作検証（任意だが推奨）

```powershell
bash hooks/python_run.sh hooks/utf8_check.py
bash hooks/python_run.sh hooks/handover_check.py
bash hooks/python_run.sh scripts/code_health_check.py --no-color
# いずれも exit 0 であること。失敗時は pre-push で BLOCK される
```

## 代替: フォルダコピー方式

技術的には動作するが、以下の理由で非推奨。

- 未コミットの差分・一時ファイル（`.locks/`, `tmp/`）まで複製される
- `.git/config` 内の `core.hooksPath` はコピーされるが、改行コードや実行権限が環境差で崩れる場合がある

フォルダコピーで移行した場合も、移行先で必ず以下を実行すること：

```powershell
git status --short
git config core.hooksPath hooks
git pull  # 最新化
```

## 本家 PhronisisCore が既にある端末への移行

- 別ディレクトリとして配置すれば共存可能。例：

```
C:\Users\owner\Documents\PhronisisCode      # Code
C:\Users\owner\Documents\PhronisisCore      # 本家（存在する場合）
```

- `knowledge/` は共有しない（drift を許容）。相互に自動同期はしない。有益な改善のみ手動で cherry-pick する（憲章 127-129行）。
- `knowledge/handover.md` 22行の `DESKTOP-QCLBNKI` は初期構築端末の記録であり、機能には影響しない。移行先で書き換える必要はない。

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| `opencode: command not found` | opencode 未導入 | https://opencode.ai/docs から導入し PATH を通す |
| `Python interpreter not found` | Python 未導入 / PATH 未設定 | Python 3.x を導入。`python`, `python3`, `py -3` のいずれかで `python -c "import sys; print(sys.version)"` が通ることを確認 |
| `pre-commit` が実行されない | `core.hooksPath` 未設定 | `git config core.hooksPath hooks` を再実行 |
| `code_health_check.py` で BLOCK | 既存コードの健全性エラー | 出力されたエラーを修正してから `git push`。詳細は `scripts/code_health_check.py --help` |
| 文字化け（UTF-8破損） | Shift-JIS で保存された | Edit ツールで再保存する。PowerShell の `Get-Content`/`Set-Content` は Shift-JIS で破損するため使用しない（AGENTS.md 最重要事項参照） |

## 移行後の日常運用

```powershell
git pull                          # 作業開始前に必ず pull（憲章 Git安全運用 参照）
opencode                          # 起動
# 作業後
git status
git diff
git add <intentional files only>
git commit -m "chore: <message>"
git push
```

push 時に `hooks/pre-push` が自動で handover 整合性と health check を検証する。失敗した場合は BLOCK され push が中断される。
