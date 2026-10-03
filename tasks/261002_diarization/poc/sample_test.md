# sample_test.md - テスト手順書

## 1. サンプル音声の置き方

- 置き場所: tasks/261002_diarization/poc/samples/ を作り、そこに置く (git には上げない)
- 例: poc/samples/meeting_30min.m4a (Google レコーダー由来、30分程度から試す)
- 初回は 5-10分の短い抜粋で試し、次に 30分、最後に 2時間の順で伸ばす
- 中日混じりを含む箇所をメモしておく (確認観点 4 用)

## 2. 実行コマンド2例

例1: 自動言語 + 話者自動 (基本動作確認):
python tasks/261002_diarization/poc/diarize_transcribe.py --input tasks/261002_diarization/poc/samples/meeting_30min.m4a --out-dir tasks/261002_diarization/poc/out

例2: 日本語指定 + 話者2名固定 (分離モデル配置時):
python tasks/261002_diarization/poc/diarize_transcribe.py --input tasks/261002_diarization/poc/samples/meeting_30min.m4a --out-dir tasks/261002_diarization/poc/out --language ja --num-speakers 2

translate 誘導の確認 (エラーになることが正しい):
python tasks/261002_diarization/poc/diarize_transcribe.py --input tasks/261002_diarization/poc/samples/meeting_30min.m4a --task translate

## 3. 確認観点

1. 話者分離: sherpa-onnx なしでは SPEAKER_00 一色になること (フォールバック継続)。ありの場合は話者切替が時刻重なりで付与されること
2. 時刻: SRT をプレイヤーで開き、ずれが 2秒以内か。TXT の [HH:MM:SS] が単調増加か
3. 確信度: JSON の各 segment に avg_logprob / no_speech_prob が残っているか。無音で no_speech_prob が高いか
4. 中日: 中国語発話が文字化けせず原文で残るか。翻訳されていないこと (翻訳は Kai 側の仕事)。日本語訳が必要なら TXT を Kai に渡す手順で確認する

合否目安: 上記 4点がすべて確認できれば PoC 通過。話者分離なしでも起こしと時刻と確信度が正しければ条件付き通過とする。
