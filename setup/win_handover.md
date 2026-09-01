# PhronisisCode Windows 環境引継ぎマニュアル

> Windows は本ファイルを読め。Mac は `setup/mac_handover.md` を読め。共用リポジトリのため両手順は対称に保つこと。

このマニュアルは、Windows（PC122-00290 / DESKTOP-QCLBNKI 等）に常駐する PhronisisCore の Kai が、PhronisisCode を Windows に立ち上げるための手順書である。
Mac 版 `setup/mac_handover.md` と対をなす Windows 版で、Phase 構成・検証ゲートは同一、コマンドのみ Windows（PowerShell / winget / Git for Windows）に読み替えている。

想定読者: Windows の PhronisisCore を開いている Kai。OpenCode でこのファイルを読み、指示に従って PhronisisCode を構築する。

---

## 前提

- Windows は `PC122-00290`（会社PC）または `DESKTOP-QCLBNKI`（開発拠点）等、PowerShell 利用可。PhronisisCore は導入済みで `opencode` が起動する想定だが、未導入でも本手順で構築可
- PhronisisCode は PhronisisCore から独立したリポジトリで、GitHub `MasayukiNemo/PhronisisCode` に push 済み（2026-08-23、a14806c まで。最新は 306117a hygiene → 334c9e5 Windows追記まで含む）
- Code は軽量構成（6神プール+Hayato/Yuna、5ステップ、L2.5維持、L3なし）。Windows 固有の依存（VC++ランタイム、cert.pfx、Developer Mode）は不要。Node.js も不要

## 全体像

```
Windows C:\Users\<user>\Documents\PhronisisCode  ← 新規クローン（Code 専用）
  .opencode/rules/phronisis_code.md  # 憲章 v1.0
  opencode.json                      # 8 agent（6神+Hayato+Yuna）
  shared/phronisis_code/             # 本体
  knowledge/                         # Lite + handover（Core と共有しない）
  tasks/_template/                   # brief/plan/log
  scripts/code_health_check.py       # 5検査ヘルスチェック（自己検証ゲート）
  hooks/                             # pre-commit/pre-push + health_check配線
```

Code は Core と手動 cherry-pick 以外は同期しない。Windows の Core から認証ファイル等をコピーする必要はない。

### 環境対応表（Mac → Windows 読み替え）

| 項目 | Mac（mac_handover） | Windows（本ファイル） | 備考 |
|------|---------------------|----------------------|------|
| シェル | zsh | PowerShell 5.1 / Git Bash | PowerShell がデフォルト。hooks は Git Bash の bash で実行 |
| パッケージャ | brew | winget | `winget --version` で確認。なければ https://aka.ms/getwinget |
| Python | python3 / pip3 | python / pip / py -3 | `python --version` を優先。`hooks/python_run.sh` は python3→python→py -3 の順で探索 |
| Node | 不要 | 不要 | Code は Electron を使わない |
| 実行権限 | chmod +x hooks/* 必須 | 不要 | Git for Windows がエミュレート。`git config core.hooksPath hooks` のみで可 |
| bash | 標準で存在 | Git for Windows の bash | `C:\Program Files\Git\bin\bash.exe`。PowerShell で `bash` が not found なら Git Bash ターミナルを使うか PATH を通す |
| パス | ~/Documents | C:\Users\<user>\Documents | `~` は PowerShell では `$HOME`。例: `Set-Location $HOME\Documents` |
| 改行 | LF | LF（.gitattributesで固定） | `core.autocrlf=true` でも hooks は LF で checkout される |

---

## 手順

### Phase 0: 環境確認

1. PowerShell で確認:
    ```powershell
    hostname  # PC122-00290 等であること
    systeminfo | Select-String "OS Name"
    git --version
    python --version  # 3.10 以上。失敗なら python3 --version / py -3 --version を試す
    winget --version  # なければスキップ（手動導入）
    rclone version  # あれば表示。なくても Code 動作には不要
    Test-Path "C:\Program Files\Git\bin\bash.exe"  # True であること（hooks 用）
    Get-Command opencode -ErrorAction SilentlyContinue  # なければ後述 Phase 1 で導入
    ```
2. winget が未導入なら導入（既に入っていればスキップ）:
    - Microsoft Store で「アプリ インストーラー」を更新するか、https://aka.ms/getwinget から取得

### Phase 1: 依存導入（winget）

Core と異なり Code は Python 標準のみで動く。追加の pip パッケージは不要だが、以下の CLI は必要:

```powershell
winget install --id Git.Git -e --source winget
winget install --id Python.Python.3.12 -e --source winget  # 既に 3.10 以上があればスキップ。--source winget で msstore 証明書エラーを回避
winget install --id GitHub.cli -e  # gh。push 時にトークン埋め込み済みなら任意。なければ推奨
# opencode: 未導入の場合。既に Core で使っていればスキップ
# https://opencode.ai/docs から OpenCode デスクトップ版を導入するか、winget/scoop で導入
# 例: winget install --id OpenCode.OpenCode -e  # パッケージ名は環境により異なるため docs を参照

# 導入後は新しい PowerShell / OpenCode を再起動して PATH を反映
# 同セッションで反映する場合:
$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')

# 動作確認
git --version
python --version  # 失敗なら python3 --version / py -3 --version
gh --version  # 導入した場合のみ
opencode --version  # または OpenCode.exe が起動すること（C:\Users\<user>\AppData\Local\Programs\opencode\OpenCode.exe）
```

注意:
- `python` は `python` で呼ぶ。Mac の `python3` は Windows では `python`。`pip` も `pip` でよい
- Node.js は Code では不要（Electron を使わない）。Core で使っていても Code には影響しない
- Windows で必要だった VC++ランタイム、cert.pfx、Developer Mode は Code では不要
- `gh` は任意。`git remote -v` にトークン埋め込み済み（`https://MasayukiNemo:ghp_...@github.com/...`）なら `gh auth login` なしでも `git push` 可。失敗時のみ `gh auth login` を実行

### Phase 2: クローン

```powershell
Set-Location $HOME\Documents
# 既に PhronisisCode がある場合は退避
# Move-Item PhronisisCode PhronisisCode.bak

git clone https://github.com/MasayukiNemo/PhronisisCode.git
Set-Location PhronisisCode
git log --oneline -3  # 334c9e5 以降が見えること
git status  # clean であること
```

GitHub 認証（push 時に必要）:

```powershell
gh auth login  # ブラウザで認証（gh を導入した場合）。または
gh auth login --with-token < token.txt  # Core のトークンを流用する場合
# 確認
gh auth status
```

または `git credential` に既存の Core 認証（remote URL にトークン埋め込み）があれば、そのまま `git push` で認証される。失敗した場合は `gh auth login` を実行する。

### Phase 3: Git / Hooks 設定

```powershell
Set-Location $HOME\Documents\PhronisisCode

# ユーザー設定（Core と同じでよい。なければ確認して設定）
git config user.name "Masayuki Nemo"
git config user.email "nemomon@gmail.com"

# hooks 有効化（Windows では chmod 不要。core.hooksPath のみで可）
git config core.hooksPath hooks

# 確認
git config --get core.hooksPath  # hooks と表示されること
Get-ChildItem hooks/  # pre-commit, pre-push, python_run.sh 等が存在すること
# 参考: Mac では chmod +x hooks/pre-commit hooks/pre-push hooks/python_run.sh が必要だが Windows では不要（Git for Windows がエミュレート）
```

### Phase 4: 検証（Code の自己検証ゲート）

```powershell
Set-Location $HOME\Documents\PhronisisCode

# 1. ヘルスチェック（5検査）
python scripts/code_health_check.py --no-color
# 期待: 5/5 PASS、Overall: ALL PASS、exit 0

python scripts/code_health_check.py --help  # exit 0 であること
python scripts/code_health_check.py --json  # JSON valid であること

# 2. hooks ドライラン
git hook run pre-commit  # WARN は出ても BLOCK なしで exit 0 であること
# pre-push は push 時のみ。ローカルでは Git Bash で手動:
& "C:\Program Files\Git\bin\bash.exe" -c "bash hooks/python_run.sh hooks/utf8_check.py"  # exit 0
& "C:\Program Files\Git\bin\bash.exe" -c "bash hooks/python_run.sh hooks/handover_check.py"  # exit 0（初回はリモート未取得で WARN のみ）
& "C:\Program Files\Git\bin\bash.exe" -c "bash hooks/python_run.sh scripts/code_health_check.py --no-color"  # exit 0
# PowerShell で bash が PATH にある場合は以下でも可:
# bash hooks/python_run.sh hooks/utf8_check.py

# 3. opencode 起動確認
opencode  # PhronisisCode がプロジェクト一覧に出ること。出ない場合は「プロジェクト追加」から C:\Users\<user>\Documents\PhronisisCode を選択
# デスクトップ版の場合: C:\Users\<user>\AppData\Local\Programs\opencode\OpenCode.exe を起動
```

失敗時の対処:

- `bash: command not found` → Git for Windows の bash が PATH にない。`C:\Program Files\Git\bin\bash.exe` でフルパス指定するか、Git Bash ターミナルで実行。または `git hook run pre-commit` を使う
- `python: command not found` → `py -3 --version` を試す。`hooks/python_run.sh` は python3→python→py -3 の順で探索するため、hooks 経由ならいずれかが見つかれば可
- `gh auth` 失敗 → ブラウザ認証を再試行。Core の `gh auth status` が通っていればそちらの credential を流用できる。トークン埋め込み済みなら gh 自体不要
- `utf8_check.py` で BLOCK → 対象 md の文字化けを Edit ツールで修正。PowerShell の Get-Content/Set-Content は Shift-JIS で破損するため使用しない（AGENTS.md 最重要事項参照）

### Phase 5: 初回タスク試運転（任意だが推奨）

Code が軽く回ることを Windows でも確認する:

```powershell
# OpenCode で PhronisisCode を開く
# チャットに以下を貼る:

# フロニシスCode起動。
# knowledge/handover.md → knowledge/conductor_profile_lite.md → .opencode/rules/phronisis_code.md → shared/phronisis_code/orchestration_flow_code.md を読め。
# tasks/260823_driving_test/brief.md を実行せよ。L2.5で回せ。5ステップで回せ。Hayatoゲートで検証し、再アンカーを必須とせよ。
```

または hygiene と同様の小タスクを新規に切って回す。Windows でも `python scripts/code_health_check.py --no-color` が exit 0 であれば出荷可。

### Phase 6: 環境登録（任意）

Code は独立進化だが、Windows の存在を handover に残すと追従性が上がる:

```powershell
python scripts/detect_env.py  # 存在すれば実行。なければ hostname を手動で確認（Code には detect_env.py がない場合あり）
hostname
```

`knowledge/handover.md` の「環境定義」に追記（例: `PC122-00290 | Windows 11 Pro 24H2 / 会社PC | python 3.13.5, git 2.54.0.windows.1, rclone 1.74.1, OpenCode.exe 1.18.25, Code 検証済み (5/5 PASS)`）。追記は任意で、なくても動作する。実例は 2026-09-01 に PC122-00290 を追記済み。

---

## Windows 固有の注意

- **hooks の実行権限**: Mac では `chmod +x` が必須だが、Windows では不要。`git config core.hooksPath hooks` のみで可。Git for Windows が bash スクリプトの実行権限をエミュレートする
- **bash の所在**: PowerShell から `bash` を呼ぶと `command not found` になる場合がある。`C:\Program Files\Git\bin\bash.exe` をフルパスで呼ぶか、Git Bash ターミナルで実行するか、`git hook run pre-commit` を使う。`core.hooksPath` 経由の自動実行（commit/push 時）は Git が内部で bash を解決するため問題ない
- **python コマンド**: `python` で呼ぶ。`python3` はエイリアスがない場合がある。`scripts/code_health_check.py` の shebang は `#!/usr/bin/env python3` だが、hooks は `hooks/python_run.sh` 経由で `python3→python→py -3` の順にフォールバックするため Windows でも動作する。直接実行する場合は `python` を使う
- **改行コード**: Code は `.gitattributes` で LF を強制。Windows では `core.autocrlf=true` でも hooks は LF で checkout される。CRLF 変換の警告が出ても無視してよい
- **opencode プロジェクト識別**: Mac と Windows で同一 origin URL（`github.com/MasayukiNemo/PhronisisCode`）なら同一プロジェクトとして扱われる。Windows でクローンしても別プロジェクトにはならない。これは仕様で問題ない
- **gh CLI**: Windows では `winget install GitHub.cli` で導入。`gh auth login` はブラウザ認証が最も確実。remote URL にトークン埋め込み済みなら gh 自体不要
- **UTF-8**: PowerShell の `Get-Content`/`Set-Content`/`Out-File` は Shift-JIS で破損する。md 編集は Edit ツール（バイト安全）を使う。`python script.py > file` も同様に破損するため `open(path, 'w', encoding='utf-8')` で書き込む

## トラブルシュート

| 症状 | 原因 | 対処 |
|------|------|------|
| `git hook run pre-commit` で `No such file: python_run.sh` | `core.hooksPath` が未設定 | `git config core.hooksPath hooks` |
| `pre-push` で `code_health_check failed` と BLOCK | 5検査のいずれかが FAIL | `python scripts/code_health_check.py --no-color` で詳細を確認し、欠落ファイルを復旧 |
| `opencode` に PhronisisCode が出ない | プロジェクトキャッシュ未更新 | OpenCode の「プロジェクト追加」から `C:\Users\<user>\Documents\PhronisisCode` を手動追加 |
| `python scripts/code_health_check.py` が `No such file` | カレントが違う | `Set-Location $HOME\Documents\PhronisisCode` で実行 |
| `bash: command not found` | Git for Windows の bash が PATH にない | `& "C:\Program Files\Git\bin\bash.exe" -c "bash hooks/python_run.sh ..."` でフルパス指定、または Git Bash で実行。commit/push 時の自動実行は問題ない |
| `python: command not found` | Python が PATH にない / python3 のみ存在 | `py -3 --version` を試す。hooks は自動でフォールバックする |
| push 時に `Repository not found` | GitHub リポジトリ未作成または認証失敗 | `gh auth status` と `git remote -v` を確認。リポジトリは作成済み（2026-08-23）のため再作成は不要。トークン埋め込み済みなら gh 不要 |

## 完了条件

- `python scripts/code_health_check.py --no-color` が 5/5 PASS
- `git hook run pre-commit` が BLOCK せず exit 0
- OpenCode で PhronisisCode が開き、Kai が `knowledge/handover.md` を読んでタスクを受け付けられる

完了したら、この Windows の Kai は Code の通常運用（tasks 配下で L2.5→Hayatoゲート→再アンカー）を回せる状態になる。

## 補足: Core との使い分け

- Core: 企画・戦略・文書生成（9神、4層知識、画像前処理あり）
- Code: 実装・検証・バグ修正（6神プール、5ステップ、L2.5、ヘルスチェック自己検証）

両者は独立進化する。Windows では両方を `C:\Users\<user>\Documents\PhronisisCore` と `C:\Users\<user>\Documents\PhronisisCode` として並存させる。Code の改善が有益な場合は手動で Core に cherry-pick するが、自動同期はしない。

---

最終更新: 2026-09-01（Code 334c9e5 Windows追記時点、5/5 PASS 検証済み）
作成者: PC122-00290 の Kai（Windows 構築担当、mac_handover 対称版として作成）
検証: `python scripts/code_health_check.py --no-color` 5/5 PASS、hooks 3ゲート BLOCK 確認済み（Git Bash 経由）
