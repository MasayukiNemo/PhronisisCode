# brief.md — DSH bridge のCode移植

## 課題

本家 PhronisisCore の DSH（DeepSeek Harness）bridge スクリプト4本を Code に移植し、Code から DSH 側カイと対話できるようにする。

## 前提条件

- [x] DSH がこの端末で稼働中（127.0.0.1:3080・トークン認証）
- [x] Playwright が導入済み
- [x] 根本さんの選択: 場合2（Codeにbridgeを移植）

## 成功基準

- [x] 必須: dsh_common.py / dsh_send.py / dsh_check.py / dsh_answer.py が Code に配置される
- [x] 必須: トークン検出が現行の DSH ログ（%LOCALAPPDATA%\PhronisisDSH\start.out*）を拾える
- [x] 必須: dsh_check.py が実際に DSH UI を開いて本文を保存できる
- [x] 必須: knowledge/code_knowledge/dsh.md に使い方を記録
- [x] 必須: evolution_log に取込を記録
- [x] 必須: Yuna/Hayato の三角形チェックを経る
- [ ] 任意: dsh_send.py の往復（送信→応答確認）が確認できる（DSH側カイの応答が必要なため、要根本さんの承認）

## 判断の軌跡（実行中に記録）

| 論点 | 選んだ案 | 潰した案 | 理由 |
|------|---------|---------|------|
| トークン検出 | %LOCALAPPDATA%\PhronisisDSH\start.out* を走査 | 本家の旧パス（%TEMP%\dsh_out*）をそのまま | 現行ランチャーは LOCALAPPDATA に start.out を出す。旧パスは空 |
| 保存先 | scratch/dsh_reply.txt（.gitignoreに scratch/*.txt） | tasks/ 配下 | 本家と同形式。作業ファイルは scratch |
| 責務 | Core のスクリプトを直接叩かない | 直接叩く | 独立進化。Code に副本を置く |
