# brief.md — PhronisisCode 自己検証の昇格

## 課題

`scripts/code_health_check.py`（駆動試験で作成した5検査CLI）を、PhronisisCode 自身の手続きに昇格させる。
宣言と実体の一致を人手ではなく機械で担保し、次回から --help のような実行時バグを Hayatoゲートで自動検出できるようにする。

## 背景

駆動試験 `tasks/260823_driving_test` は全て PASS したが、`python scripts/code_health_check.py --help` が Windows cp932 で落ちるバグは Hayatoゲート4点を全て通過した後に見つかった。
ゲートは仕様忠実性を見たが、実行可能性（CLI が実際に動くか）は見ていなかった。
大局観を維持しながら近視眼を防ぐには、ヘルスチェックを Code 自身の品質ゲートに組み込むのが筋が良い。

## 前提条件

- [ ] PhronisisCode の憲章 `.opencode/rules/phronisis_code.md` とフロー `shared/phronisis_code/orchestration_flow_code.md` に準拠する
- [ ] 6神はプール。必要時のみ招集し、呼ばなかった理由を軌跡に残す
- [ ] L2.5 で回す（推論で進めてみる、実行済み時制、24h差し戻し可）
- [ ] 既存のヘルスチェック `scripts/code_health_check.py` を壊さないこと（--help の em dash 修正は本タスク内で併せて行ってよい）
- [ ] 2ループ目の再アンカー（深層思考で brief に立ち返る）を必須とする

## 成功基準

### 必須

- [ ] `shared/phronisis_code/orchestration_flow_code.md` の「Hayato検証」節に「`python scripts/code_health_check.py --no-color` が exit 0 であることを必須とする」旨を1-2行で追記する
- [ ] `hooks/pre-push` または `hooks/pre-commit` から `python scripts/code_health_check.py --no-color` を呼ぶ配線を1箇所追加する（どちらか一方でよい。pre-push 推奨。失敗時は WARN または BLOCK のいずれかを明記すること）
- [ ] `tasks/260823_driving_test` で見つかった `--help` の em dash（—）を `-` に置換し、`python scripts/code_health_check.py --help` が Windows cp932 で通ることを確認する（本タスク内で直してよい。別タスクに分けない）
- [ ] `tasks/260823_driving_test/plan.md` の未チェック `Daedalus: 実装` を `[x]` に倒すことは本タスクでは不要（駆動試験側の残課題だが、本タスクで直す対象ではない。混同しない）
- [ ] `tasks/260823_code_improve/plan.md` と `log.md` を作成し、判断の軌跡を記録すること

### 任意

- [ ] `knowledge/handover.md` に本改善の要約を1行追記する
- [ ] `shared/phronisis_code/protocol/evolution_log.md` に「ヘルスチェック昇格」の記録を追記する

## 制約

- 技術スタック: Python 3.x のみ、hooks は bash/python_run.sh 経由
- 既存の Code 本体を壊さないこと。新規ファイルは `tasks/260823_code_improve/` 配下以外に作らない（hooks と orchestration_flow の追記は例外）
- 自己検証80%は「必須4項目のうち3つ以上が手動実行で確認できたこと」と定義する
- 出力先制約を守ること

## 判断の軌跡（実行中に記録）

| 論点 | 選んだ案 | 潰した案 | 理由 |
|------|---------|---------|------|
| 配線先: pre-push vs pre-commit |  |  |  |
| 失敗時の扱い: WARN vs BLOCK |  |  |  |
| --help 修正: em dash 置換 vs エンコーディング対策 |  |  |  |
| 招集判断: Gaia を呼ぶか |  |  |  |
| 招集判断: Hermes を呼ぶか |  |  |  |
| 招集判断: Artemis を呼ぶか |  |  |  |
| 招集判断: Daedalus を呼ぶか |  |  |  |
| 招集判断: Metis を呼ぶか |  |  |  |
| 招集判断: Athena を呼ぶか |  |  |  |

## 検証方法

1. `python scripts/code_health_check.py --help` が exit 0 で表示されること（cp932 で落ちない）
2. `python scripts/code_health_check.py --no-color` が exit 0 であること
3. わざと1ファイルを欠落させて `python scripts/code_health_check.py --no-color` が exit 1 になること
4. `shared/phronisis_code/orchestration_flow_code.md` にヘルスチェック必須化の記述があること
5. `hooks/pre-push`（または pre-commit）にヘルスチェック呼び出しがあること
6. `tasks/260823_code_improve/log.md` の自己検証が80%以上であること

## 備考

- このタスクは Code が自身を検証する自己参照の閉じ方を実現する。本家の知識蓄積とは異なる Code らしい進化。
- 大局観を維持しながら、近視眼と端折りを避けることがポイント。再アンカーで「この昇格は brief の成功基準に忠実か」を問い直すこと
- 駆動試験の残課題（plan.md のチェック）は本タスクで直さない。混同してスコープを広げないこと
