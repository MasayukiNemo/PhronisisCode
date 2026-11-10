# plan.md — 実装計画

## アーキテクチャ

単体ファイル・フラット。requests+bs4 のみで動作（playwright 不要）。GASプロキシは外部エンドポイント（env var NOTE_GAS_PROXY_URL で差し替え可）。

## タスク分解

1. [ ] task 作成（brief/plan/log）
2. [ ] scripts/note_extract_gas.py 移植
3. [ ] URL検証を host allowlist に強化
4. [ ] --out をリポジトリ内のみに制限
5. [ ] knowledge/code_knowledge/web_research.md 更新（使うもの・役割分担・罠）
6. [ ] evolution_log.md / handover.md 追記
7. [ ] 実地検証（py_compile + note.com記事取得 + URL検証の否定テスト）
8. [ ] Hayato手続き検証
9. [ ] commit + push

## 依存関係

```
タスク1 → タスク2 → タスク3,4 → タスク5,6 → タスク7 → タスク8 → タスク9
```

## リスク

- GASプロキシ依存: 単一障害点（SLA無し・認証無し・遮断自由）。対策: web_research.md に退場経路（note_fetch.py へ降格）を明文
- note.com DOM結合: 構造変更で黙って壊れる。対策: method 表示と退場経路を明記
- 第三者プロキシ経由のプライバシー: URLリストがプロキシ側ログに残りうる。対策: web_research.md に警告
