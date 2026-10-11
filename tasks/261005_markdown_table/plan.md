# plan.md — 実装計画

## アーキテクチャ

単一HTML(docs/markdown-table/index.html)。構成は入力牌・設定牌・出力牌の3ブロック。
変換は入力イベント駆動の純粋関数 parse -> normalize -> toMarkdown で行い、DOMは表示専用にする。
外部通信ゼロ、localStorage不使用(配布コピーの混入汚染を避ける)。

## タスク分解

1. [ ] docs/markdown-table/index.html を作成(入力/設定/出力/変換JS)
2. [ ] 手動検証5件(カンマ/タブ/任意区切り/ヘッダなし/引用符+クリア)
3. [ ] code_health_check --no-color を実行しexit 0を確認
4. [ ] Hayatoゲート(4点照合)を回しlogに記録
5. [ ] commit + push

## 依存関係

```
作成 → 手動検証 → health check → Hayatoゲート → commit/push
```

## リスク

- リスク1: パイプ入りセルで行が壊れる → 出力時に\|へエスケープ、改行はスペース化で対策
- リスク2: Excel貼付けのタブ・末尾空行 → 空行スキップ任意化と列数正規化(不足は空補完、過剰は維持)で対策
- リスク3: UTF-8破損 → pre-commitのutf8_checkに加えReadで目視確認
