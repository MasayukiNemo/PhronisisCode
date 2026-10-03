# plan.md — 実装計画

## アーキテクチャ

調査は完了しPoC実装に移行。構成は下記2線。
1. 本線Colab Pro GPU: poc/colab_diarization.ipynb (turbo + sherpa-onnx、HFトークン不要)
2. 従線ローカルCPU: faster-whisper turbo int8 + sherpa-onnx分離 (poc/diarize_transcribe.py、短尺・分割向け)

## タスク分解

1. [x] brief/log/plan作成
2. [x] トライアングル: 深層思考+Yuna+Hayato
3. [x] Hermes調査: Web + GitHub OSS評価
4. [x] 統合して推奨案をチャット報告
5. [x] PoC実装: poc/diarize_transcribe.py + requirements + README + sample_test
6. [x] Metisレビュー3点反映 + HayatoゲートPASS
7. [ ] テスト: サンプル音声での試行 (5-10分抜粋から)

## 依存関係

```
brief確定 → トライアングル → Hermes調査 → 統合報告
```

## リスク

- リスク1: pyannoteはHFトークン・商用条件が絡むため条件整理が必要: 対策としてライセンス明記
- リスク2: 長時間音声のメモリ・速度問題: 対策としてfaster-whisper系を優先評価
