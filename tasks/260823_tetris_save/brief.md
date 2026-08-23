# brief.md — ステートセーブ拡張

## 課題

現行 `docs/tetris/index.html` に「延々と遊べる」ためのステートセーブ機能を追加する。任意のタイミングで盤面を保存し、保存した状態から何回でもリスタート（リトライ）できることで、練習・研究用途の再現性を担保する。

## 前提条件

- [x] ベースは `docs/tetris/index.html`（ガイドライン準拠982行版を直前のSpace/DAS修正込みで拡張）
- [x] 既存の必須8点（SRS/HOLD/NEXT3/DAS等）および直前のバグ修正（Space開始・ソフトドロップリピート）を後退させない
- [x] 単一HTML / file:// 直開き / Vanilla / localStorage のみで完結（サーバ不要）

## 成功基準

- [x] 必須1: セーブ — プレイ中（isStarted=true かつ isGameOver=false）に Sキー または SAVEボタン で、盤面(board)、現ミノ(current type/matrix/pos/rot/color)、NEXTキュー3、HOLD(holdType/holdLocked)、BAG、スコア/レベル/ライン、ロック状態(lockTime/lockResets/lastRotated/dropCounter)が localStorage `phronisis_tetris_save_v1` に保存され、保存時に「SAVED」フラッシュとUIインジケータが表示される。dropCounterは保存するがロード時に0へリセットする
- [x] 必須2: ロード — いつでも（タイトル/ポーズ/ゲームオーバー含む） Lキー または LOADボタン で、保存されたステートが復元され、保存時と同一の盤面・ミノ・NEXT/HOLD・スコアから即座に再開できる。ロードは保存データを消費せず、何回でも繰り返し実行できる（冪等）
- [x] 必須3: 永続性 — ページ再読み込み（F5/Ctrl+F5）後も localStorage のセーブが残り、Lで復元できる。Chromiumの file:// と http で動作を保証し、Safari等のfile://制限時は「SAVE FAILED」/「NO SAVE」で誠実に通知する（必須4の分岐で担保）
- [x] 必須4: 未セーブ/破損時の挙動 — セーブが存在しない場合は「NO SAVE」、JSON破損/容量超過/無効時は「CORRUPTED」または「SAVE FAILED」を1.5秒表示しクラッシュしない。破損時は localStorage を削除せず保持し次回Sで上書き可能とする
- [x] 必須5: 上書きと冪等性 — Sを再押下で既存セーブを上書きでき、Lは何回押しても同じ状態から開始できる（冪等）。セーブ後にプレイを進めても保存データは変化しない
- [x] 必須6: UI完全性 — SIDEに SAVE/LOADボタンとキー説明（S/L）が追加され、既存のレイアウト（HOLD/NEXT/STATUS/CONTROLS）を崩さない
- [x] 必須7: リグレッションなし — 既存操作（移動/回転/HOLD/DAS/ロック等）と Space開始・ソフトドロップリピートが引き続きPASSする
- [ ] 任意1: オートセーブ（10ライン毎に自動保存）
- [ ] 任意2: セーブクリア（Shift+S等で削除）

## 制約

- 技術スタック: 単一HTML / IIFE / Canvas 2D。外部ライブラリ不使用。localStorage のみ（IndexedDB不使用）
- 配置: `docs/tetris/index.html` を上書き。行数は1100-1200行を目安とし、セクション見出しで分割
- キー体系: 既存8キーに S/L を追加。S/L は単押しでブラウザの Ctrl+S 保存ダイアログとは衝突しない。Shiftなしの単押しで判定し preventDefault不要
- 品質: `scripts/code_health_check.py --no-color` 5/5 PASS 維持。保存データの JSON は try/catch で破損時に「CORRUPTED」を表示しクラッシュしない

## 判断の軌跡（実行中に記録）

| 論点 | 選んだ案 | 潰した案 | 理由 |
|------|---------|---------|------|
| 保存先 | localStorage `phronisis_tetris_save_v1` | IndexedDB / ファイルDL | file:// でも使える最シンプルな永続化。IndexedDBはAPI複雑、DLは手動で煩雑。localStorage 1キーで要件を満たす |
| 保存範囲 | board/current/nextQueue/hold/bag/score/level/lines/lock/dropCounter/isStarted/isPaused等を丸ごと（lastRotated含む）。時間系(dropCounter)は保存するがロード時に0へリセットして重力暴走を防ぐ | boardのみ | boardだけではNEXT/HOLD/スコアの再現性が欠け「延々と遊べる」にならない。現ミノの rot/matrix/pos/colorまで含めて完全再現。時間系は保存値を使わず0リセットする意図を明記 |
| 消費モデル | 何回でもロード可能（非消費）、Sで1スロット上書き | 複数スロット | ロードの冪等性を正とする。セーブは1スロット上書きを許容しシンプルさを優先 |
| タイミング | プレイ中のみSで保存可、Lは常時可 | 常時S可 | ゲームオーバー/タイトルで保存しても意味がない。プレイ中のみに絞り誤操作を防ぐ |
| 未セーブ/破損時 | 「NO SAVE」/「CORRUPTED」/「SAVE FAILED」で分岐表示、非クラッシュ | 無反応/握り潰し | 空と破損と容量超過を区別して通知。try/catchで証拠隠滅せず原因を伝える |
| 永続キー | バージョン付き `v1`、Chromium保証+Safari等は失敗通知 | 素の `tetris_save` | 将来フォーマット変更時にマイグレーション可能にするためバージョン付与 |

