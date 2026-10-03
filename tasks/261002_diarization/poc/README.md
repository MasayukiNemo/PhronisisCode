# PoC README - 話者分離つき文字起こし

対象: tasks/261002_diarization/poc/diarize_transcribe.py
前提: Windows 11 + Python 3.13.5 + CPU、入力は Google レコーダー由来 m4a (30分-2時間、中日混じり)

## 1. セットアップ (ローカル)

手順:
1. python --version で 3.13 系を確認する
2. pip install -r tasks/261002_diarization/poc/requirements.txt
3. ffmpeg があると m4a/mp3 を 16k mono wav へ自動変換する (推奨、任意)
4. ffmpeg なしの場合、wav 入力のみ soundfile 経由で処理する

m4a 変換コマンド (ffmpeg ありの場合):
ffmpeg -i input.m4a -ac 1 -ar 16000 out_16k.wav

## 2. ローカル実行

基本形 (自動言語、話者自動):
python tasks/261002_diarization/poc/diarize_transcribe.py --input sample.m4a --out-dir tasks/261002_diarization/poc/out

日本語指定の例:
python tasks/261002_diarization/poc/diarize_transcribe.py --input sample.m4a --out-dir tasks/261002_diarization/poc/out --language ja

高速化の例 (CPUバッチ):
python tasks/261002_diarization/poc/diarize_transcribe.py --input sample.m4a --out-dir tasks/261002_diarization/poc/out --language ja --cpu-threads 8 --batch-size 8

注意: 55分音声でRTF約0.77 (約42分) の実測あり。1時間級はColab Pro手順 (colab_diarization.ipynb) を推奨。

出力: out/ に JSON / SRT / TXT ができる。確信度 avg_logprob / no_speech_prob は JSON に保持される。
翻訳はしない。日本語化は TXT を Kai に渡して行う。

## 3. Colab Pro手順 (本線。1時間級は必ずこちら)

colab_diarization.ipynb をColabに上げ、ランタイムをGPUにして上から実行するだけ。
構成は faster-whisper turbo (GPU) + sherpa-onnx分離 (HFトークン不要)。
whisperX流用はしない。pyannoteも使わない (gated承諾が要るため)。
2時間は30-60分に分割して回す。

分割コマンド例 (ローカルで事前に切る場合):
ffmpeg -i input.m4a -ss 00:00:00 -t 00:30:00 -ac 1 -ar 16000 part1.wav

## 4. テスト手順

詳細は sample_test.md を参照。要点は話者分離の有無、時刻ずれ、確信度保持、中日混じりの崩れ確認。

## 5. 制限事項

- turbo モデルは transcribe 専用。translate 指定はエラーにして Kai 翻訳へ誘導する
- sherpa-onnx 未導入またはモデル未配置時は単一話者 (SPEAKER_00) フォールバックで継続する
- ffmpeg なしで m4a/mp3 は処理不可。明示エラーで終了する
- 2時間一括は警告表示のみで続行する。分割を推奨する
- 出力は --out-dir 配下のみ。既定は poc/out でリポジトリ外に書かない
- 秘密情報 (HF トークン等) をコードや出力に含めない
