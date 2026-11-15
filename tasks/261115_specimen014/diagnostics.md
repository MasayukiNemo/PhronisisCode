# specimen 014 — overlap verification diagnostics (CKai side)

- date: 2026-11-15
- gate: EURUSD weekly first 3 points × 20 paths (60 rows)
- verdict: **不一致（不合格扱い）。XAUUSD は開始していない。**

## 1. ハッシュ

| 対象 | 値 |
|---|---|
| こちらの CSV（ヘッダ除く・LF終端） | `2f489bb29596fd58647766da16bcb92239b9da5b9c273fa652d6ad7563c03464` |
| 期待値（OVERLAP_VERIFICATION.md） | `273e0f1999d5b6b08e769183811eb57f57f16ed7453eb9974954e0a742a98d81` |

書式ゆれ（CRLF、末尾改行、ヘッダ込み）で一致するかも試した。全パターン不一致。値そのものが違う。

## 2. 同一性の確認（すべて一致）

| 対象 | 結果 |
|---|---|
| パッケージ zip | `9c4e411f...bddb5` 一致 |
| `src/specimen014_generate.py` | `f4eb43e9...858369` 一致（無改変） |
| `data/processed/XAUUSD_M1.parquet` | `5396c11f...d5a3cb` 一致 |
| `data/processed_eurusd/EURUSD_D1.parquet` | `f2858c07...7030e1` 一致 |
| Kronos ツリー | ピン留めコミットのツリーのまま |
| モデル snapshot | `901c26c1...bea320` 一致 |
| トークナイザ snapshot | `0e011738...e22426` 一致 |

## 3. 決定性（同一マシン内）

同じコマンドを3回（既定スレッド2回、`OMP_NUM_THREADS=1`＋`torch.set_num_threads(1)` 1回）。3回とも上のハッシュに一致。行単位の差分ゼロ。

つまりこちらは決定的。決定的であることと、マシン間で可搬であることは別だった。

## 4. 環境

| 項目 | CKai 側 | モコ側（RUNNER.md の記載） |
|---|---|---|
| Python | 3.11.1 | 3（詳細不明） |
| torch | 2.15.0+cpu | 2.15.0+cpu |
| numpy | 2.4.6 | 2.5.4 |
| pandas | 2.2.2 | 2.2.2 |
| einops | 0.8.1 | 0.8.1 |
| huggingface_hub | 0.33.1 | 0.33.1 |
| matplotlib | 3.9.3 | 3.9.3 |
| tqdm | 4.67.1 | 4.67.1 |
| safetensors | 0.6.2 | 0.6.2 |
| pyarrow | 26.0.1 | 26.0.1 |
| CPU | Intel i7-10510U（4C/8T、AVX2。numpy SIMD: baseline X86_V2 / found X86_V3） | 不明 |

numpy 2.5.4 は PyPI の索引にも存在しない（最大 2.4.6）。報告された版が別物か、版記録のずれの可能性がある。

## 5. 所要時間

- 1点あたり 22.37〜22.49 秒（既定スレッド）
- 1点あたり 48.33 秒（1スレッド固定）
- 3点で 67.1 秒（モデル取得を除く）
- 385点の外挿: 約 2 時間 24 分（既定スレッド）

## 6. 原因の候補（本命）

Kronos の `predict()` は前処理でこうしている。

```python
x = df[price_cols + [vol, amt]].values.astype(np.float32)   # 512 x 6
x_mean, x_std = np.mean(x, axis=0), np.std(x, axis=0)
x = (x - x_mean) / (x_std + 1e-5)
```

`np.mean` / `np.std` の float32 リダクションは、CPU の SIMD 幅（SSE/AVX2/AVX512）で丸めの順序が変わる。torch の CPU カーネルも同じ理由で最終ビットが変わる。すると正規化入力が 1e-8 程度ずれ、同じシードでも `torch.multinomial` の確率が僅かに違い、選ばれるトークンが分岐する。分岐した後は自己回帰なので、経路全体が別物になる。

値のずれが小さい（数値ノイズ）ではなく、経路が別になる（サンプリング分岐）タイプの不一致と見ている。

## 7. 切り分けの提案（1点で決まる）

`src/preproc_digest.py`（同梱）を Box に置いた。モデルを読まず、1点目（τ=2020-08-20）の前処理だけを再現して、`x_mean` / `x_std` の6値を10進とfloat32 hexで出し、正規化配列（512×6 float32）の SHA256 を出す。

こちらの値:

```
mean.open  = 1.1175358295440674  hex=3f8f0b6a
mean.high  = 1.1205074787139893  hex=3f8f6cca
mean.low   = 1.1145908832550049  hex=3f8eaaea
mean.close = 1.1176093816757202  hex=3f8f0dd3
std.open   = 0.021554114297032356 hex=3cb09241
std.high   = 0.021725129336118698 hex=3cb1f8e6
std.low    = 0.021560775116086006 hex=3cb0a039
std.close  = 0.02171754278242588  hex=3cb1e8fd
x_norm sha256 = 3275d145798efdfee0dee3536d07e0871779c12cb95c73288e411abb2e5983f1
```

ここが 1 ビットでも違えば確定。同じなら原因はモデル推論側に移る（torch のカーネル差）。

## 8. 選択肢

1. 同一 ISA の環境を用意する。こちらの CPU を差し替えるのは不可。
2. 片方のマシンで両資産を回す。こちらで EURUSD 週次（78点、約29分）も回せば、XAUUSD 385点（約2時間24分）と合わせて約3時間で、全数が同一環境に揃う。凍結仕様を触らず、測定の内部整合が保たれる。
3. 完全一致を諦め、分布の一致に合格基準を変える。凍結仕様の改訂になるので、そちらの判断が要る。

CKai の推しは 2。理由は、ゼロショットの地位も条件も変えずに済み、分担の前提（同一生成環境）を満たせるため。手元に計算余力はある。
