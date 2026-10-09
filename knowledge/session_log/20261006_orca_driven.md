# 20261006 Orca駆動版（Orca導線＋クイズ リッチWeb UI版）

## 発火点

Core側（PhronisisCore）からの指示。PhronisisCodeを正式リポとしてOrcaで回す試み。以後、CoreのKaiがOrca経由でPhronisisCodeのworkerを駆動する使い方（モード2）が始まる。

## 流れ

- Orca導線の追加: `docs/orca/README.md`（任意・Orca非必須の使い方）＋ `AGENTS.md` に1行導線（`f50085b`）
- 実タスク1: クイズのリッチWeb UI版。worker（opencode）がPhronisisCodeのフローをフルで回した（brief→deep_thought→トライアングル=Yuna/Hayato/Gaia/Artemis→中間Hayato→実装→flow_test 36/36→実agy E2E→Metis→Hayatoゲート）。`scripts/quiz_web.py`＋`scripts/quiz_webui/`。出題ロジックは `quiz_game.py` を単一正本として再利用（quota閾値はcoreに集約）。`7f78dc5`
- 追いタスク: 起動のしやすさ。`quiz_web.bat`／`quiz_web_stub.bat`／`scripts/build_quiz_web.bat`／`docs/quiz_web/README.md`。exeも実際にビルドしE2E検証。`c53c2df`

## 判断

- Orcaは任意。PhronisisCodeはOrca無しでも5ステップを回る
- workerのcommit/pushはリポジトリ実物に効く。masterへのマージは制御して行う
- モード1（根本さんがCodeを直接）／モード2（CoreのKaiがOrcaでworkerを回す）の理解は、Core側の `knowledge/decisions/phronisiscode_orca_two_modes.md` に記録（Code側の基本ルールではない）
- モデル: テストはfreeを既定にする（この回はdeepseek-v4.1-flashで回してしまった。Core側findingsに反省記録）

## 残ったモヤモヤ

- リッチWeb UI版の「リッチな見た目・マウス完走」は根本さんの実機確認が残（Hayatoゲートはコード側PASSのWARN）
- Orcaのopencode readiness timeout、自動更新での中断など、実運用の摩擦は残る
- 本命はTrading bot（Core側で進行）。Code側はその実装基盤になりうる

<!-- status: complete | agent: kai -->
