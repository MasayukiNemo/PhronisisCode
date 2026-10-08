# 話者分離つき文字起こしフロー (実戦版)

最終更新: 2026-10-03 / 実績: 10月2日55分・9月19日83分・9月8日91分・10月3日理事会

## 構成

- Colabノート: tasks/261002_diarization/poc/colab_diarization.ipynb (本線)
- 掃除: tasks/261002_diarization/poc/clean_output.py
- ローカルPoC: tasks/261002_diarization/poc/diarize_transcribe.py (短尺のみ)
- 窓: Gdrive_code/to_colab (入力) / from_colab (出力)。rclone起点はフロニシス直下

## 定番フロー

1. m4a (等倍) とPixel版txtをto_colabに置く。zipのままでよい
2. ColabでGPUランタイム、ノートを上から実行。NUM_SPEAKERSは人数確定なら固定
3. from_colabのjson/txtをrcloneで取得
4. clean_output.pyで掃除 (幻覚・ループ・時刻修復。倍速なら--scale)
5. Pixel正+whisper時刻話者で話者分離補正起こしと議事録を作成

## 運用判断

- 起こし: transformers版whisper turbo (GPU)。faster-whisperはColabでcuBLAS罠あり使用禁止
- 分離: sherpa-onnx (seg int8 + Titanet small、HFトークン不要)。pyannoteは使わない
- turboはtranscribe専用。翻訳はKai側。中国語も起こしは原文+Kai訳
- 等倍で入れる。倍速は時刻破損・幻覚・話者分裂を招く。使うなら--scaleで戻す
- 人数確定ならNUM_SPEAKERS固定が最強。不明なら自動+threshold 0.6-0.7
- 長尺は30分自動分割 (起こしのみ)。分離は一括 (話者番号割れ防止)。チャンクJSONで再開可
- Pixel版txtはzip同梱を自動複写。突合せはPixel正、時刻話者はwhisper
- Colab backend過負荷はGPU変更か時間をおく。T4で十分
- GPUなし検出で停止、完了ブザーあり、進捗は分離5%刻み

## 落とし穴

- av19とfaster-whisper非互換。ローカルはndarray渡しに固定済み
- ローカルCPU全文はRTF0.77で実用外。短尺検証のみに使う
- Colab mountはマイドライブのみ。パソコン欄は見えない
- rclone起点はフロニシス直下 (gdrive:Gdrive_code = フロニシス/Gdrive_code)
- ノート変更時はスタブ実行でフロー検証 (TEMPのcelltest_settings.py参照)

## ローカル道具 (各端末で用意)

- ffmpeg: winget install Gyan.FFmpeg。m4a→16k wav変換と時刻調べ。PATH更新後は新シェルで有効
- Python 3.13 + pip: requirements.txt (faster-whisper/sherpa-onnx/soundfile/numpy)。全文起こしはしない前提
- rclone gdrive:: 本家方式を流用。browser認証または既存rclone.conf持込。root_folder_idでフロニシス限定推奨
- 使うコマンド: rclone ls/lsd (確認)、rclone copy (取得)、rclone mkdir (窓作成)
- 出力はリポジトリ内のみ。Drive配布はrclone copyで後配布 (本家ルール8方式)

## 複数端末運用

- PhronisisCodeは複数端末の別個体として動く。知識は端末非依存に書くこと
- 端末固有 (PATH・ドライブ文字・認証状態) は知識に埋め込まない。確認コマンドを添える
- 窓 (Gdrive_code) が真実の受渡し点。端末間の直接受渡しはしない
- 音声・出力物はgit管理外。知識とコードのみSCする

## v3方向 (Pixel前提の最適化・2026-10-03調査)

- 最大レバーは全文デコード省略。Pixel正ならstable-ts alignかwav2vec2 CTC alignに切替え
- 2026-10-03実測で棄却: 5分音声で起こし586秒に対しalignは80%時点で18分超。速くならない
- 分離はGPU pyannote系+人数固定が定石。不明でもmin/max必須 (未実施・将来課題)
- 突合せは低信頼区間のみLLM修正。全面リライトは固有名詞改悪の恐れ
- 名寄せは役割語抽出+LLM分類+多数決が近道 (DiarizationLM/CASCA流)
- 注意: Pixel誤り伝播・OOV・重なり・gated条件。日本語会議の改善率は自前計測必須
