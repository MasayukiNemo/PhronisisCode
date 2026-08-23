# brief.md — PhronisisCode 駆動試験

## 課題

PhronisisCode 自身の健全性を検証する CLI `scripts/code_health_check.py` を実装する。
このタスクで Code の思想（大局観維持・近視眼防止・端折り防止）がコードに落ちているか検証する。
成果が見えて、必要なら修正ポイントが浮かぶ試運転とする。

## 背景

v1.0-fix1 までで雛形は完成。P0 BLOCK は解消したが、Hayato 三巡で24本の残論点は「全て見送りでOK」と判断した。
次の実戦で「本当に軽く回るか」「近視眼にならないか」「端折らないか」を測る必要がある。
自身を検証するヘルスチェックは、Code の全機構を一巡させるのに最適な題材。

## 前提条件

- [ ] PhronisisCode の憲章 `.opencode/rules/phronisis_code.md` とフロー `shared/phronisis_code/orchestration_flow_code.md` に準拠する
- [ ] 6神はプール。必要時のみ招集し、呼ばなかった理由を軌跡に残す
- [ ] L2.5 で回す（推論で進めてみる、実行済み時制、24h差し戻し可）
- [ ] Hayatoゲート4点（仕様逸脱/致命傷/手続き違反/軌跡品質）で検証する
- [ ] 2ループ目の再アンカー（深層思考で brief に立ち返る）を必須とする。大局観を見失わないこと

## 成功基準

### 必須

- [ ] `scripts/code_health_check.py` が `python scripts/code_health_check.py` で実行できる
- [ ] 5つの検査を実装する:
  1. conductor_profile_lite パスが `knowledge/conductor_profile_lite.md` に存在し、参照破損がないこと
  2. hooks 依存（python_run.sh / utf8_check.py / handover_check.py / lock_*.py）が揃っていること
  3. 6神プロファイル（gaia/hermes/artemis/daedalus/metis/athena）が `shared/phronisis_code/agents/*/profile.md` に存在すること
  4. `opencode.json` が JSON として valid で 8 agent 定義があること
  5. `tasks/_template/brief.md` と `log.md` が必須フィールド（成功基準/軌跡表/自己検証欄）を持つこと
- [ ] CLI 出力は 5検査ごとに PASS/FAIL を表示し、1つでも FAIL があれば exit 1、全て PASS なら exit 0
- [ ] 存在しないファイルを扱ってもクラッシュせず、FAIL として報告すること（バグ・セキュリティ致命傷の観点）
- [ ] `tasks/260823_driving_test/plan.md` と `log.md` を作成し、判断の軌跡を記録すること

### 任意

- [ ] --verbose で詳細を表示、--json で機械可読出力
- [ ] 色付き出力（PASS 緑 / FAIL 赤）

## 制約

- 技術スタック: Python 3.x のみ（外部依存なし）
- 既存の hooks / knowledge を壊さないこと
- 出力先は `scripts/code_health_check.py` のみ。新規ファイルは `tasks/260823_driving_test/` 配下以外に作らないこと
- 自己検証80%は「必須5検査のうち4つ以上が手動実行で確認できたこと」と定義する

## 判断の軌跡（実行中に記録）

| 論点 | 選んだ案 | 潰した案 | 理由 |
|------|---------|---------|------|
| 招集判断: Gaia を呼ぶか | 呼ばない | 呼ぶ（設計2案提示） | 単一スクリプトでアーキテクチャ分岐なし。深層思考で代替。思想的一貫性のため過剰設計を避けた |
| 招集判断: Hermes を呼ぶか | 呼ぶ（軽量調査としてKaiが代行） | 呼ばない | 既存6ファイル/8agent/テンプレート等の事実確認が必要。Hermes相当の調査をKaiがbash/readで実行し結果をplanに反映 |
| 招集判断: Artemis を呼ぶか | 呼ばない | 呼ぶ（3ファイル以上分解） | 変更は実質1ファイル（scripts/code_health_check.py）。plan/logは記録用。依存関係は直列1本でクリティカルパス単純 |
| 招集判断: Daedalus を呼ぶか | 呼ぶ（Kaiが代行、実装担当） | 呼ばない | バグ・セキュリティ致命傷（クラッシュせずFAIL）の実装が核。Daedalus視点のロバスト性検証が必須 |
| 招集判断: Metis を呼ぶか | 呼ぶ（Kaiが代行、レビュー） | 呼ばない | 実装を伴うタスクは原則招集（フロー規定）。可読性・保守性3観点以上あり |
| 招集判断: Athena を呼ぶか | 呼ぶ（Kaiが統合） | 呼ばない | Hermes/Daedalus/Metisの出力を統合しCLI出力整形に収束が必要 |
| 出力形式: テキスト vs JSON | 両立（デフォルトテキスト、--jsonで機械可読） | 片方のみ | 任意要件を「選ぶことは捨てること」で片方を捨てず、フラグで両立。追従性と実用の均衡 |

## 検証方法

1. `python scripts/code_health_check.py` を実行し、全て PASS になること
2. わざと1ファイル（例: `knowledge/conductor_profile_lite.md` を一時リネーム）で FAIL になること
3. `tasks/260823_driving_test/log.md` の自己検証欄が 80% 以上であること
4. Hayatoゲート4点を `log.md` に記録し PASS/WARN/BLOCK を判定すること

## 備考

- このタスクは Code の全機構（トライアングル→招集判断→実装→Hayato検証→再アンカー）を一巡させることを目的とする。軽微タスクの fast-path は使わず、フルで回すこと
- 大局観を維持しながら、近視眼と端折りを避けることがポイント。2ループ目の再アンカーで「この実装は brief の成功基準に忠実か」を問い直すこと
