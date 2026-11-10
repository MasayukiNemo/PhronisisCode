# plan.md — 実装計画

## アーキテクチャ

Code の scripts/ はフラット構成（lib/ なし）。3本は単体ファイルとして配置する。
web_fetch は requests+bs4 の stage1 が単独で動き、playwright/crawl4ai は fallback。
x_thread は標準ライブラリのみ。note_fetch は playwright。

## タスク分解

1. [ ] task 作成（brief/plan/log）
2. [ ] scripts/web_fetch.py 移植（Code適応注記追加）
3. [ ] scripts/x_thread.py 移植（但し書き・MIT保持、参照先修正、Code適応注記）
4. [ ] scripts/note_fetch.py 移植（Code適応注記）
5. [ ] knowledge/code_knowledge/web_research.md 作成（使うもの/使わないもの、使用条件、依存）
6. [ ] evolution_log.md に拾い捨て記録
7. [ ] 実地検証（web_fetch: example.com + 価格.com、note_fetch: note.com、x_thread: 静的確認）
8. [ ] Hayato手続き検証
9. [ ] commit + push

## 依存関係

```
タスク1 → タスク2,3,4（並列） → タスク5,6 → タスク7 → タスク8 → タスク9
```

## リスク

- crawl4ai v0.9 API依存: 版上がりで黙って壊れる可能性。対策: 依存と「未導入ではstage1のみ」をknowledgeに明記
- playwright/crawl4ai が全端末に無い: 対策: web_fetchはstage1単独で動くことを確認済み。x_threadはstdlibのみ
- x_thread の使用条件違反: 対策: knowledgeに明文。使用此端末は個人回線（WiMAX）
