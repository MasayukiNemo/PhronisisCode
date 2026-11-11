# plan.md — 実装計画

## アーキテクチャ

Code の scripts/ に4本を配置。Playwright で DSH Web UI（127.0.0.1:3080）を操作する。
トークンは起動ログ（%LOCALAPPDATA%\PhronisisDSH\start.out*）から検出。

## タスク分解

1. [ ] 4本をコピー
2. [ ] dsh_common.py のトークン検出を現行ランチャーに合わせる
3. [ ] 各スクリプトに Code適応注記
4. [ ] scratch/ と .gitignore
5. [ ] dsh_check.py で実地確認（読み取りのみ）
6. [ ] knowledge/code_knowledge/dsh.md
7. [ ] evolution_log / handover
8. [ ] Hayato手続き検証

## 依存関係

```
1 → 2,3 → 4 → 5 → 6,7 → 8
```

## リスク

- DSH UI は共有リソース（DSH側カイ）。乱打しない
- トークンはローテーションされうる。start.out が空のときは .prev を参照
