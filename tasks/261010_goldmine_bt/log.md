# log.md — 軌跡 (261010_goldmine_bt)

## やったこと
1. plan.md に最小設計を書いた (6神なし・理由記録)。
2. `data/fetch.py`, `bt/engine.py`, `bt/strategies.py`, `bt/run.py`, `bt/metrics.py`, `bt/store.py`, `walk_forward.py`, `README.md`, `run.bat`, `requirements.txt` を実装。
3. 環境修復: numpy 2.4.6 + pandas 2.0.1 の binary incompatibility を numpy 1.26.4 downgrade で解消。
4. `python -m bt.run --selftest` ALL PASS (終了コード0)。
5. `python data/fetch.py` で実データ取得 (EURUSD 1301 rows, USDJPY 1301 rows)。
6. 実データで run + walk-forward を両通貨で実行。equity_curve.csv / os_results.csv / trades.db を生成。
7. 実データで SL/TP 絶対値の桁依存バグを検出 → 相対比率に修正し再検証。
8. report.md に正直な要約を転記。

## 検証結果 (自己検証: 必須8項目)
- [必須] fetch 再現性: parser 決定的 (同JSON→同rows を実測確認)。PASS
- [必須] コスト全明示: spread/commission/slippage/swap を計上。selftest で cost>0 を assert。EURUSD cost 3.0 / USDJPY cost 4.8。PASS
- [必須] look-ahead なし: signal は [..i] のみ参照 (未来改変で不変を assert)。約定は翌 open (pending)。PASS
- [必須] walk-forward OS: 3 fold の OS を stdout + os_results.csv に出力。PASS
- [必須] SQLite 全取引記録: trades.db 16 rows (EURUSD)。PASS
- [必須] kill switch: selftest で合成暴落により発火確認 (halted=['K00260'])。実データ USDJPY で23日発火。PASS
- [必須] README/run.bat で再実行可能: 手順どおりに実行済み。PASS
- [必須] --selftest GUIなし終了コード0: PASS (tkinter/matplotlib 不使用。標準lib+csv のみ)
- [任意] equity PNG: 未作成 (csv で代替。正直に未達と記載)

## 軌跡表 (論点/選んだ案/潰した案/理由)
| 論点 | 選んだ案 | 潰した案 | 理由 |
|---|---|---|---|
| 戦略 | Donchian 20/10 + SMA200、longのみ | MAクロス両建て | 自由度2に抑え片側で因果を単純化するため |
| SL/TP単位 | entry比 2%/4% | 絶対値 0.02/0.04 | 絶対値はUSDJPY(約150)で0.013%になり破綻。実データで検出し修正 |
| exit約定 | 翌open (pending_exit) | 当日close | 当日closeは確定足内約定で原則違反のため |
| 依存 | urllib+標準libのみ実行時必須 | requests必須化 | 取得を標準libで書き追加依存ゼロにするため。requirements は requests のみ記載 |
| 最適化 | 探索なし | グリッド探索 | 過剰最適化の禁止。OS乖離の誠実評価を優先 |
| 6神招集 | なし | Gaia/Artemis等 | 単一設計・直線依存・指摘なしのため。plan.md に理由記録 |

## Hayatoゲート4点 (自己適用)
1. 仕様逸脱: 必須8項目のうち7+自白1(任意PNG未達)。必須は全充足。判定 PASS。
   指摘: walk_forward の fold2 OS が 0 trades だが「OS結果が出る」は満たす (0も結果。無取引の水増し調整なし)。
2. 致命傷: 初版 SL/TP 絶対値は USDJPY で口座破綻級 (ret -118% を実測)。FAIL → 相対化で修正し再検証 (USDJPY ret +38% / OS乖離を正直報告)。SQLi なし (parameterized)。GUI/発注なし。修正後 PASS。
3. 手続き違反: plan→実装→selftest→実データ→Hayato→log→commit の順を遵守。push なし。招集判断を plan に記録。判定 PASS。
4. 軌跡品質: 上表 4列すべて非空。判定 PASS。
総合: Hayato WARN (観点2の初版FAILは修正済みだが記録として残す。残課題は軽微: PNG未作成・frankfurter突合が目視未実施)。

## 再アンカー記録
- 2ループ目相当 (SL/TP修正時) に brief へ立ち返り確認した問い: 「この修正は成功基準 (コスト明示・look-aheadなし・勝ち主張なし) に忠実か」。答え: 単位修正は計測の正しさに直結し、数値の改善 (USDJPY +38%) を根拠に使わず OS乖離を報告することで honest を維持した。

## 残課題 (正直記載)
- equity curve PNG 未作成 (任意)。
- frankfurter と Yahoo の突合は単発取得のみで差分検証なし。
- USDJPY の OS 乖離の原因分析なし (次のタスクの燃料。trades.db に特徴量を保存済み)。

<!-- status: complete | agent: kai -->
