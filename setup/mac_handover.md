# PhronisisCode Mac 環境引継ぎマニュアル

> Windows は本ファイルを読まず `setup/win_handover.md` を読め。共用リポジトリのため両手順は対称に保つこと。

このマニュアルは、Mac（BUF-STMarketingnoMacBook-Air.local）に常駐する PhronisisCore の Kai が、PhronisisCode を Mac に立ち上げるための手順書である。
Windows（DESKTOP-QCLBNKI）で構築・検証済みの Code v1.0（a14806c + 306117a）を Mac に移植する。

想定読者: Mac の PhronisisCore を開いている Kai。OpenCode でこのファイルを読み、指示に従って PhronisisCode を構築する。

---

## 前提

- Mac は `BUF-STMarketingnoMacBook-Air.local`（macOS、homebrew 利用可）。PhronisisCore は導入済みで `opencode` が起動する
- PhronisisCode は PhronisisCore から独立したリポジトリで、GitHub `MasayukiNemo/PhronisisCode` に push 済み（2026-08-23、a14806c まで。最新は 306117a hygiene まで含む）
- Code は軽量構成（6神プール+Hayato/Yuna、5ステップ、L2.5維持、L3なし）。Windows 固有の依存（VC++ランタイム、winget、cert.pfx）は不要

## 全体像

```
Mac ~/Documents/PhronisisCode  ← 新規クローン（Code 専用）
  .opencode/rules/phronisis_code.md  # 憲章 v1.0
  opencode.json                      # 8 agent（6神+Hayato+Yuna）
  shared/phronisis_code/             # 本体
  knowledge/                         # Lite + handover（Core と共有しない）
  tasks/_template/                   # brief/plan/log
  scripts/code_health_check.py       # 5検査ヘルスチェック（自己検証ゲート）
  hooks/                             # pre-commit/pre-push + health_check配線
```

Code は Core と手動 cherry-pick 以外は同期しない。Mac の Core から認証ファイル等をコピーする必要はない。

---

## 手順

### Phase 0: 環境確認

1. ターミナルで確認:
   ```zsh
   hostname  # BUF-STMarketingnoMacBook-Air.local であること
   uname -a  # Darwin
   git --version
   python3 --version  # 3.10 以上
   brew --version
   ```
2. 未導入なら `brew` を入れる（既に入っていればスキップ）:
   ```zsh
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

### Phase 1: 依存導入（brew）

Core と異なり Code は Python 標準のみで動く。追加の pip パッケージは不要だが、以下の CLI は必要:

```zsh
brew install git python@3.12 gh
brew install --cask opencode  # 未導入の場合。既に Core で使っていればスキップ

# 動作確認
git --version
python3 --version
gh --version
opencode --version  # または opencode が起動すること
```

注意:
- `python` は `python3` で呼ぶ。`pip` は `pip3`
- Node.js は Code では不要（Electron を使わない）。Core で使っていても Code には影響しない
- Windows で必要だった VC++ランタイム、Node.js、cert.pfx、Developer Mode は Mac では不要

### Phase 2: クローン

```zsh
cd ~/Documents
# 既に PhronisisCode がある場合は退避
# mv PhronisisCode PhronisisCode.bak

git clone https://github.com/MasayukiNemo/PhronisisCode.git
cd PhronisisCode
git log --oneline -3  # a14806c 以降（最新は 306117a hygiene）が見えること
git status  # clean であること
```

GitHub 認証（push 時に必要）:

```zsh
gh auth login  # ブラウザで認証。または
gh auth login --with-token < token.txt  # Core のトークンを流用する場合
# 確認
gh auth status
```

または `git credential` に既存の Core 認証があれば、そのまま `git push` で認証される。失敗した場合は `gh auth login` を実行する。

### Phase 3: Git / Hooks 設定

```zsh
cd ~/Documents/PhronisisCode

# ユーザー設定（Core と同じでよい。なければ確認して設定）
git config user.name "Masayuki Nemo"
git config user.email "nemomon@gmail.com"

# hooks 有効化（重要: Mac では実行権限が必要）
git config core.hooksPath hooks
chmod +x hooks/pre-commit hooks/pre-push hooks/python_run.sh

# 確認
git config --get core.hooksPath  # hooks と表示されること
ls -l hooks/  # -rwxr-xr-x であること
```

### Phase 4: 検証（Code の自己検証ゲート）

```zsh
cd ~/Documents/PhronisisCode

# 1. ヘルスチェック（5検査）
python3 scripts/code_health_check.py --no-color
# 期待: 5/5 PASS、Overall: ALL PASS、exit 0

python3 scripts/code_health_check.py --help  # cp932 問題は Mac では起きないが、exit 0 であること
python3 scripts/code_health_check.py --json  # JSON valid であること

# 2. hooks ドライラン
git hook run pre-commit  # WARN は出ても BLOCK なしで exit 0 であること
# pre-push は push 時のみ。ローカルでは手動で:
bash hooks/python_run.sh hooks/utf8_check.py  # exit 0
bash hooks/python_run.sh hooks/handover_check.py  # exit 0（初回はリモート未取得で WARN のみ）
bash hooks/python_run.sh scripts/code_health_check.py --no-color  # exit 0

# 3. opencode 起動確認
opencode  # PhronisisCode がプロジェクト一覧に出ること。出ない場合は「プロジェクト追加」から ~/Documents/PhronisisCode を選択
```

失敗時の対処:

- `permission denied` → `chmod +x hooks/*` を再実行
- `python: command not found` → `python3` で呼ぶ。`alias python=python3` を検討
- `gh auth` 失敗 → ブラウザ認証を再試行。Core の `gh auth status` が通っていればそちらの credential を流用できる
- `utf8_check.py` で BLOCK → 対象 md の文字化けを Edit ツールで修正

### Phase 5: 初回タスク試運転（任意だが推奨）

Code が軽く回ることを Mac でも確認する:

```zsh
# OpenCode で PhronisisCode を開く
# チャットに以下を貼る:

# フロニシスCode起動。
# knowledge/handover.md → knowledge/conductor_profile_lite.md → .opencode/rules/phronisis_code.md → shared/phronisis_code/orchestration_flow_code.md を読め。
# tasks/260823_driving_test/brief.md を実行せよ。L2.5で回せ。5ステップで回せ。Hayatoゲートで検証し、再アンカーを必須とせよ。
```

または hygiene と同様の小タスクを新規に切って回す。Mac でも `python3 scripts/code_health_check.py` が exit 0 であれば出荷可。

### Phase 6: 環境登録（任意）

Code は独立進化だが、Mac の存在を handover に残すと追従性が上がる:

```zsh
python3 scripts/detect_env.py  # 存在すれば実行。なければ hostname を手動で確認
```

`knowledge/handover.md` の「環境定義」に追記（例: `BUF-STMarketingnoMacBook-Air.local | Mac | homebrew, gh, opencode | Code 検証済み`）。追記は任意で、なくても動作する。

---

## Mac 固有の注意

- **hooks の実行権限**: Windows では `bash` 経由で呼ぶため +x がなくても動くが、Mac では `chmod +x` が必須。`git config core.hooksPath hooks` だけでは不十分
- **python コマンド**: `python` はない場合がある。常に `python3` を使う。`scripts/code_health_check.py` の shebang は `#!/usr/bin/env python3` で Mac 対応済み
- **改行コード**: Code は `.gitattributes` で LF を強制。Mac では CRLF 変換の警告が出ても無視してよい
- **opencode プロジェクト識別**: Mac と Windows で同一 origin URL（`github.com/MasayukiNemo/PhronisisCode`）なら同一プロジェクトとして扱われる。Mac でクローンしても別プロジェクトにはならない。これは仕様で問題ない
- **gh CLI**: Mac では `brew install gh` で導入。`gh auth login` はブラウザ認証が最も確実。Core のトークンをコピーする手もあるが、ブラウザ認証を推奨

## トラブルシュート

| 症状 | 原因 | 対処 |
|------|------|------|
| `git hook run pre-commit` で `No such file: python_run.sh` | `core.hooksPath` が未設定 | `git config core.hooksPath hooks` |
| `pre-push` で `code_health_check failed` と BLOCK | 5検査のいずれかが FAIL | `python3 scripts/code_health_check.py --no-color` で詳細を確認し、欠落ファイルを復旧 |
| `opencode` に PhronisisCode が出ない | プロジェクトキャッシュ未更新 | OpenCode の「プロジェクト追加」から `~/Documents/PhronisisCode` を手動追加 |
| `python3 scripts/code_health_check.py` が `No such file` | カレントが違う | `cd ~/Documents/PhronisisCode` で実行 |
| push 時に `Repository not found` | GitHub リポジトリ未作成または認証失敗 | `gh auth status` と `git remote -v` を確認。リポジトリは作成済み（2026-08-23）のため再作成は不要 |

## 完了条件

- `python3 scripts/code_health_check.py --no-color` が 5/5 PASS
- `git hook run pre-commit` が BLOCK せず exit 0
- OpenCode で PhronisisCode が開き、Kai が `knowledge/handover.md` を読んでタスクを受け付けられる

完了したら、この Mac の Kai は Code の通常運用（tasks 配下で L2.5→Hayatoゲート→再アンカー）を回せる状態になる。

## 補足: Core との使い分け

- Core: 企画・戦略・文書生成（9神、4層知識、画像前処理あり）
- Code: 実装・検証・バグ修正（6神プール、5ステップ、L2.5、ヘルスチェック自己検証）

両者は独立進化する。Mac では両方を `~/Documents/PhronisisCore` と `~/Documents/PhronisisCode` として並存させる。Code の改善が有益な場合は手動で Core に cherry-pick するが、自動同期はしない。

---

最終更新: 2026-08-23（Code v1.0-fix2 + hygiene 306117a 時点）
作成者: DESKTOP-QCLBNKI の Kai（Windows 構築担当）
検証: `python3 scripts/code_health_check.py --no-color` 5/5 PASS、hooks 3ゲート BLOCK 確認済み
