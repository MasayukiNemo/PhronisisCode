"""単純トレンドフォロー1本: ドンチャンブレイク + SMAフィルタ.

自由度は2 (entry_n, exit_n)。sma_n=200 は固定フィルタであり最適化対象外。
look-ahead禁止: signal(df, i) は df.iloc[:i+1] (当日終値まで) のみ参照する。
"""


def sma(values, n, end):
    """values[0..end] (end含む) の単純移動平均。データ不足時は None."""
    if end + 1 < n:
        return None
    return sum(values[end - n + 1:end + 1]) / n


def signal(donchian_breakout, df_close, df_high, df_low, i, entry_n=20, exit_n=10, sma_n=200):
    """i 日終値確定時点のシグナルを返す: +1 (long), -1 (short/flat-exit), 0 (維持).

    実装はロング専用に単純化: +1=新規long可, -1=保有longの手仕舞い, 0=何もしない。
    判定に使うのは high/low/close の [i-entry_n+1 .. i] と sma([..i]) のみ。
    i+1 以降は一切参照しない (look-aheadなし)。
    """
    _ = donchian_breakout  # 将来の拡張用プレースホルダ (未使用であることを明示)
    if i < max(entry_n, exit_n, sma_n):
        return 0
    closes = df_close
    highs = df_high
    lows = df_low
    # 当日を除く過去N本の高値/安値 (ブレイク判定の古典形: 当日close が過去N本高値を上抜け)
    past_high = max(highs[i - entry_n:i])
    past_low = min(lows[i - exit_n:i])
    c = closes[i]
    trend = sma(closes, sma_n, i)
    if trend is None:
        return 0
    if c > past_high and c > trend:
        return 1
    if c < past_low:
        return -1
    return 0
