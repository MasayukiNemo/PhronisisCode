# PhronisisCode

PhronisisCore から分岐したコーディング専用フロニシス。

## 特徴

- 憲章: `.opencode/rules/phronisis_code.md` v1.0（本家 v7.0 から軽量化・独立進化）
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
├── shared/phronisis_code/
│   ├── orchestration_flow_code.md
│   ├── agents/{gaia,hermes,artemis,daedalus,metis,athena,hayato,yuna}/profile.md
│   └── protocol/evolution_log.md
├── knowledge/
│   ├── handover.md
│   ├── conductor_profile_lite.md
│   ├── decisions/
│   ├── session_log/
│   └── code_knowledge/
├── tasks/
│   └── _template/ (brief.md / plan.md / log.md)
└── hooks/ (pre-commit/pre-push + python_run.sh/utf8_check.py/handover_check.py)
```

## 起動

```powershell
git pull
opencode  # モデルはopencode起動時のピッカーで選択（画面選択に従う）
```

起動後、Kai は `knowledge/handover.md` → `knowledge/conductor_profile_lite.md` → `.opencode/rules/phronisis_code.md` → `shared/phronisis_code/orchestration_flow_code.md` の順に読む。
クローン直後は `git config core.hooksPath hooks` を実行すること。

## 本家との関係

- 本家 PhronisisCore から分岐。憲章は独立進化する
- 有益な改善は手動で cherry-pick する。自動同期はしない
- knowledge は共有しない（drift を許容）

## バージョン

- v1.0 (2026-08-23): 初回構築。Hayatoレビュー9本→6点補正を反映
- v1.0-fix1 (2026-08-23): 6視点大規模レビュー+深層思考でP0/P1 7点修正、Hayato二巡目で残BLOCK再修正。大局観維持・近視眼防止を核に確定
