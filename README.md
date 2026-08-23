# PhronisisCode

PhronisisCore から分岐したコーディング専用フロニシス。

## 特徴

- 憲章: ` .opencode/rules/phronisis_code.md` v1.0（本家 v7.0 から軽量化・独立進化）
- エージェント: 6神プール（Gaia/Hermes/Artemis/Daedalus/Metis/Athena）+ Hayato/Yuna。常時全起動せず必要分だけ招集
- フロー: 5ステップ（課題確定 → 前提検証+トライアングル → 実装+検証 → Hayato検証 → 確定）
- 自律度: L1/L2/L2.5（L3なし。反復はL2.5ループで代替）
- Hayatoゲート: 4点チェックリスト（仕様逸脱/致命傷/手続き違反/軌跡品質）。ループ上限3回+再アンカー機構で近視眼化を防止
- 深層思考: Kai適用の認知モード。発散・行き詰まり時に発火
- モデル戦略: 画面選択に従う

## ディレクトリ

```
PhronisisCode/
├── .opencode/rules/phronisis_code.md
├── opencode.json
├── shared/phronisis_code/orchestration_flow_code.md
├── knowledge/
│   ├── handover.md
│   ├── decisions/
│   └── session_log/
├── tasks/
│   └── _template/ (brief.md / plan.md / log.md)
└── hooks/
```

## 起動

```powershell
git pull
opencode
```

## 本家との関係

- 本家 PhronisisCore から分岐。憲章は独立進化する
- 有益な改善は手動で cherry-pick する。自動同期はしない
- knowledge は共有しない（drift を許容）

## バージョン

- v1.0 (2026-08-23): 初回構築。Hayatoレビュー9本→6点補正を反映
