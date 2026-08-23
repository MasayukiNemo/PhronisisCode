# plan.md — サウンド6点 実装計画

## アーキテクチャ

```
docs/tetris/index.html（1247行→~1320行目安）
├── <script> IIFE 内に Web Audio セクション追加:
│   ├── 状態: audioCtx, masterGain, audioEnabled, audioReady
│   ├── 初期化: function ensureAudio() — 初回ユーザ操作（keydown/click）で AudioContext生成（window.AudioContext || window.webkitAudioContext）、masterGain + DynamicsCompressorを接続、audioEnabled=true。失敗時は audioEnabled=false で静かに無効化
│   ├── 共通: function playTone(freq, type, duration, gain, slideTo?) — isPaused/isCountdown/isGameOverなら即return、audioEnabledとctxチェック、resumeIfSuspended、Oscillator+Gainを生成、和音時はgainを/numOscで正規化、onendedでdisconnect、try/catchでクラッシュ防止
│   ├── 6音:
│   │   ├── playDrop: 120Hz sine 80ms gain0.13
│   │   ├── playClear: 3ライン 440+880Hz(×2) / 4ライン 550+880+1100Hz(×3) 各120ms gain0.12/num
│   │   ├── playGaugeFull: 300→600Hz sweep 200ms sine
│   │   ├── playArmed: 800Hz square + 1200Hz overtone 150ms
│   │   ├── playConvert: 400→900Hz sweep 180ms sine + 軽いsquare
│   │   └── playBurst: 350→80Hz sawtooth下降 300ms
│   └── 統合: doLock/clearLines(消去時)/tryArm成功時/tryConvertToT成功時/showBurst時に各playを呼ぶ。カウント中/ポーズ中はガードで鳴らさない
└── UI: 任意2のミュートは今回は見送り、将来MキーでaudioEnabledトグル可能にする余白を残す
```

- Hayato指摘5点を全て計画に反映: fallback/ガード/正規化/resume/webkit対応を必須化

## 招集判断

| 知性体 | 招集 | 理由 |
|--------|------|------|
| Gaia | しない | 音色設計はbriefで収束 |
| Hermes | しない | Web Audioは既知API |
| Artemis | しない（Kaiが本planで代替） | 1ファイル変更 |
| Daedalus | する | 実装・バグ検出: Web Audioの現実化（suspended/resume/クリップ対策）を委任 |
| Metis | する | 実装を伴うため原則招集。6音のバランスと可読性レビューを委任 |
| Athena | しない | 2体逐次をKai統合 |

→ 逐次: Daedalus → Metis

## タスク分解

1. [x] T1: Daedalus — Web Audio基盤（AudioContext生成、masterGain+Compressor、ensureAudio/resume、playTone共通、ガード、fallback、disconnect）
2. [x] T2: Daedalus — 6音の個別実装と統合（doLock/clearLines/tryArm/tryConvert/showBurstへの組み込み）
3. [x] T3: Metisレビュー + Kai統合
4. [x] T4: 自己検証（6音の手動確認、ポーズ/カウント中の無音確認、同時発火時のクリップ確認 + code_health）

## 依存関係

```
T1 → T2 → T3 → T4
```

## リスク

- リスク1: AudioContext生成失敗 → 対策: try/catchでaudioEnabled=false、以降のplayは早期return
- リスク2: 自動再生制限 → 対策: 各play先頭で if(ctx.state==='suspended') ctx.resume()
- リスク3: 同時発火で爆音 → 対策: 和音はgainを/numOscで正規化、masterGain 0.18でクリップ、DynamicsCompressorで抑える
- リスク4: カウント中の誤鳴動 → 対策: playTone先頭で isPaused/isCountdown/isGameOverガード
- リスク5: メモリリーク → 対策: oscillator.onendedでdisconnect、Gainもdisconnect

