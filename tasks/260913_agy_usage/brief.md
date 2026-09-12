# brief.md — agyのCodeならではの使い方定義とコンダクト記載

## 課題

agy採用済み（ask/quota+generate手順）に対し、Kaiがいつ・何のために呼ぶかの使い方を定義し、orchestration_flow_code.mdに「外部AI活用（agy）」節として記載する

## 前提条件

- [ ] 前回task（260913_gemini_subscription）の制約を継承する（agy-only、extract不使用、7%以下停止）
- [ ] 記載先はorchestration_flow_code.md末尾（憲章ではなく手順書）。6神profileは変えない

## 成功基準

- [ ] 必須: 呼ぶ主体・ask局面・generate局面・quota扱い・6神分担・記録ルールが節に含まれる
- [ ] 必須: Yuna/Hayato軽量チェックを経る
- [ ] 必須: evolution_logに節新設を追記する

## 制約

- 最小差分: 既存節を変更せず末尾追記のみ
- 運用の苦労を増やさない（定期確認・自動確認を仕込まない）

## 判断の軌跡（実行中に記録）

| 論点 | 選んだ案 | 潰した案 | 理由 |
|------|---------|---------|------|
| 記載先 | orchestration末尾追記 | 憲章追記/新規protocol | 手順は手順書に集約。憲章は原理、profileは6神のものでKaiの手順書はflow |
| ask位置づけ | 確信が上がらない時の外部視点のみ | 常時併用・6神代替 | 6神体制を汚染しない。困っていない備えにしない |
