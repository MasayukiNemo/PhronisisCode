# Evolution Log — PhronisisCode

## v1.0 (2026-08-23)

- PhronisisCore v7.0 から分岐して PhronisisCode v1.0 を創設
- 6神プール化（Gaia/Hermes/Artemis/Daedalus/Metis/Athena）+ Hayato/Yuna。常時全起動せず招集判断で必要分だけ
- フロー5ステップ化（8→5ステップ圧縮）
- L2.5維持、L3廃止
- Hayatoゲート4点チェックリスト化 + 中間軽量チェック + ループ上限3回 + 再アンカー機構（近視眼化防止）
- 独立進化方針: 本家との自動同期なし、手動cherry-pickのみ
- Hayatoレビュー9本の刺しを受け6点補正（ゲート具体化/中間チェック/ループ分離/6神復活+Metis/独立進化/ステップ短縮）
- 深層思考検証: 軽さは判断回数と定義し、fast-path独立節とdrift自動化を見送り7点に絞る判断を確定

## v1.0-fix1 (2026-08-23)

- 6視点大規模レビューでP0 3点（パス破損/hooks欠落/6神profile不在）を検出し修正
  - パス: knowledge/user_profile/conductor_profile_lite.md -> knowledge/conductor_profile_lite.md
  - hooks: python_run.sh/utf8_check.py/handover_check.py/lock_*.py移植、CORE_FILESをphronisis_code.mdに修正、utf8_checkのPHRO_MANDATORYを「判断の基準」に修正
  - 6神profile+templateを本家から移植
- P1修正: 自己検証80%をbrief必須項目通過率と定義、招集基準バイナリ化、Hayatoゲート4点を機械判定（空欄FAIL/PASS/WARN/BLOCK）、ループ3回一本化（再アンカー含む）、fast-path但し書き化、Artemis見積3行追加
- 憲章に手動cherry-pick記録ルールと削った3柱の思想的理由を追記
- Hayato二巡目で残BLOCK（utf8_check残骸/テンプレートのapollo/chronos/conduct.md参照）を検出し再修正

## v1.0-fix2 (2026-08-23)

- health_check昇格（a14806c）: `shared/phronisis_code/orchestration_flow_code.md:120` に `python scripts/code_health_check.py --no-color` 必須化を Hayatoゲート内に1行追記、 `hooks/pre-push:14` に python_run.sh 経由の BLOCK 配線を追加
- --help修正（b18b998）: `scripts/code_health_check.py:4,215` の em dash（—）を - に置換し `python scripts/code_health_check.py --help` が Windows cp932 で exit 0 になることを再検証
- hygiene: `git remote` の平文 token（ghp_）を除去し `https://github.com/MasayukiNemo/PhronisisCode.git` に正規化、露出済み token は GitHub 側で revoke 要。 `orchestration_flow_code.md` に3ゲート表を追記し追従性を向上
