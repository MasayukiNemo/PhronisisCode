# plan.md — agy使い方定義

## アーキテクチャ

- orchestration_flow_code.md末尾に「## 外部AI活用（agy）」1節を追記。既存173行に触れない
- 内容は knowledge/code_knowledge/agy.md（手順詳細）へのポインタ＋Kaiの呼出規律のみ。重複させない

## タスク分解

1. [x] 使い方定義案のYuna/Hayato軽量チェック
2. [x] flow末尾に節追記
3. [x] evolution_log追記、health確認、commit/push（Hayato WARNで自律確定）

## 依存関係

```
定義チェック → 追記 → 記録・同期
```

## リスク

- リスク1: 知見と手順の二重管理 → 対策: flow側は規律のみ、手順詳細は知見に一本化
