
// Aegis_RR_S6_ACD.cs
// Sell-only "Range Retest" bot with:
// - HTF swing-high (fractal-like) resistance levels (custom detector; no Indicators.Fractals dependency)
// - Retest + optional bear-candle confirmation
// - RSI entry quality gate + optional RSI "peak evidence" + optional "avoid chase"
// - ACD (Anti-Chop Detector): trade only when HTF range is within [MinRange..MaxRange]
// - Exits: Fixed TP and/or RSI return-to-50; optional partial close + trailing for remainder
// - JST session filter (default 09:00 -> 04:00, crosses midnight)
// - Clean chart drawing: short level segments + entry markers (no full-width horizontal lines spam)
//
// Notes:
// - Timezone on Robot is UTC; session filter converts server time -> JST by (UTC+9) offset.
// - This bot is intentionally conservative: it will skip when unsure; aim is "skim tasty parts".
//
using System;
using System.Collections.Generic;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    public enum BearConfirmMode
    {
        Either,         // Any red candle
        StrictBear,     // Red + body >= MinBearBodyPips + close near low
        CloseBelowPrev  // Close < prev close (momentum confirmation)
    }

    public enum TakeProfitMode
    {
        FixedPips,
        RsiReturn,
        Both
    }

    
    public enum StopLossMode
    {
        FixedPips,
        Atr
    }

    public enum CooldownMode { Bars, Minutes }

[Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class Aegis_RR_S7_ACD_RollingHigh : Robot
    {
        // ============================================================
        // 1) CORE
        // ============================================================
        [Parameter("Label", DefaultValue = "Aegis_RR_S6", Group = "1. CORE")]
        public string BotLabel { get; set; }

        [Parameter("Volume (Lots)", DefaultValue = 0.02, MinValue = 0.01, Step = 0.01, Group = "1. CORE")]
        public double VolumeLots { get; set; }

        [Parameter("Max Spread (pips)", DefaultValue = 2.0, MinValue = 0.0, Group = "1. CORE")]
        public double MaxSpreadPips { get; set; }

        [Parameter("Max Positions", DefaultValue = 1, MinValue = 1, Group = "1. CORE")]
        public int MaxPositions { get; set; }

        [Parameter("Cooldown Bars After Entry", DefaultValue = 6, MinValue = 0, Group = "1. CORE")]
        public int CooldownBars { get; set; }

        [Parameter("Cooldown Mode", DefaultValue = CooldownMode.Bars, Group = "1. CORE")]
        public CooldownMode CooldownModeParam { get; set; }

        [Parameter("Cooldown Minutes After Entry", DefaultValue = 30, MinValue = 0, Group = "1. CORE")]
        public int CooldownMinutes { get; set; }

        // ============================================================
        // 2) SESSION (JST)
        // ============================================================
        [Parameter("Use Session Filter (JST)", DefaultValue = true, Group = "2. SESSION (JST)")]
        public bool UseSessionFilter { get; set; }

        [Parameter("Session Start Hour (JST)", DefaultValue = 9, MinValue = 0, MaxValue = 23, Group = "2. SESSION (JST)")]
        public int SessionStartJstHour { get; set; }

        [Parameter("Session End Hour (JST)", DefaultValue = 4, MinValue = 0, MaxValue = 23, Group = "2. SESSION (JST)")]
        public int SessionEndJstHour { get; set; }

        // ============================================================
        // 3) LEVELS (HTF swing highs)
        // ============================================================
        [Parameter("HTF", DefaultValue = "Hour4", Group = "3. LEVELS")]
        public TimeFrame Htf { get; set; }

        [Parameter("HTF Lookback Bars", DefaultValue = 260, MinValue = 50, Group = "3. LEVELS")]
        public int HtfLookbackBars { get; set; }

        [Parameter("Swing Left Bars", DefaultValue = 2, MinValue = 1, Group = "3. LEVELS")]
        public int SwingLeftBars { get; set; }

        [Parameter("Swing Right Bars", DefaultValue = 2, MinValue = 1, Group = "3. LEVELS")]
        public int SwingRightBars { get; set; }

        [Parameter("Merge Distance (pips)", DefaultValue = 8.0, MinValue = 0.0, Group = "3. LEVELS")]
        public double MergeDistancePips { get; set; }

        [Parameter("Max Active Levels", DefaultValue = 12, MinValue = 1, Group = "3. LEVELS")]
        public int MaxActiveLevels { get; set; }

        [Parameter("Max Level Distance Above (pips)", DefaultValue = 220, MinValue = 10, Group = "3. LEVELS")]
        public double MaxLevelDistanceAbovePips { get; set; }

        [Parameter("Min Level Above Price (pips)", DefaultValue = 3.0, MinValue = 0.0, Group = "3. LEVELS")]
        public double MinLevelAbovePips { get; set; }

        // ============================================================
        // 4) ENTRY (retest + bear confirm)
        // ============================================================
        [Parameter("Touch Tolerance (pips)", DefaultValue = 4.0, MinValue = 0.1, Group = "4. ENTRY")]
        public double TouchTolerancePips { get; set; }

        [Parameter("Reject Close Below Level (pips)", DefaultValue = 1.5, MinValue = 0.0, Group = "4. ENTRY")]
        public double RejectCloseBelowLevelPips { get; set; }

        [Parameter("Bear Candle Required", DefaultValue = true, Group = "4. ENTRY")]
        public bool BearCandleRequired { get; set; }

        [Parameter("Bear Confirm Mode", DefaultValue = BearConfirmMode.StrictBear, Group = "4. ENTRY")]
        public BearConfirmMode BearMode { get; set; }

        [Parameter("Min Bear Body (pips)", DefaultValue = 1.2, MinValue = 0.0, Group = "4. ENTRY")]
        public double MinBearBodyPips { get; set; }

        [Parameter("Bear Close Near Low %", DefaultValue = 0.65, MinValue = 0.0, MaxValue = 1.0, Group = "4. ENTRY")]
        public double BearCloseNearLowPct { get; set; }

        [Parameter("Use Rolling High", DefaultValue = true, Group = "4. ENTRY")]
        public bool UseRollingHigh { get; set; }

        [Parameter("Rolling High TF", DefaultValue = "Hour1", Group = "4. ENTRY")]
        public TimeFrame RollingHighTf { get; set; }

        [Parameter("Rolling High Bars", DefaultValue = 60, MinValue = 5, Group = "4. ENTRY")]
        public int RollingHighBars { get; set; }

        [Parameter("RH Trigger Dist (pips)", DefaultValue = 25, MinValue = 0, Group = "4. ENTRY")]
        public double RollingHighTriggerDistPips { get; set; }

        [Parameter("RH Max Age Bars", DefaultValue = 60, MinValue = 1, Group = "4. ENTRY")]
        public int RollingHighMaxAgeBars { get; set; }

        [Parameter("RH Min RSI", DefaultValue = 60, MinValue = 0, MaxValue = 100, Group = "4. ENTRY")]
        public double RollingHighMinRsi { get; set; }

        [Parameter("Draw RH Line", DefaultValue = false, Group = "4. ENTRY")]
        public bool DrawRollingHighLine { get; set; }

        // ============================================================
        // 5) RSI ENTRY QUALITY
        // ============================================================
        [Parameter("Use RSI Quality Gate", DefaultValue = true, Group = "5. RSI QUALITY")]
        public bool UseRsiQuality { get; set; }

        [Parameter("RSI Period", DefaultValue = 14, MinValue = 2, Group = "5. RSI QUALITY")]
        public int RsiPeriod { get; set; }

        [Parameter("RSI Now Min", DefaultValue = 52, MinValue = 0, MaxValue = 100, Group = "5. RSI QUALITY")]
        public int RsiNowMin { get; set; }

        [Parameter("RSI Now Max", DefaultValue = 75, MinValue = 0, MaxValue = 100, Group = "5. RSI QUALITY")]
        public int RsiNowMax { get; set; }

        [Parameter("Avoid Chase: RSI Now Min", DefaultValue = 45, MinValue = 0, MaxValue = 100, Group = "5. RSI QUALITY")]
        public int RsiNowMinAvoidChase { get; set; }

        [Parameter("Require RSI Peak Evidence", DefaultValue = true, Group = "5. RSI QUALITY")]
        public bool RequireRsiPeakEvidence { get; set; }

        [Parameter("RSI Peak Min", DefaultValue = 62, MinValue = 0, MaxValue = 100, Group = "5. RSI QUALITY")]
        public int RsiPeakMin { get; set; }

        [Parameter("RSI Peak Window Bars", DefaultValue = 48, MinValue = 5, Group = "5. RSI QUALITY")]
        public int RsiPeakWindowBars { get; set; }

        [Parameter("Block if RSI Max Above", DefaultValue = 85, MinValue = 0, MaxValue = 100, Group = "5. RSI QUALITY")]
        public int BlockIfRsiMaxAbove { get; set; }

        // ============================================================
        // 6) ACD (Anti-Chop Detector)
        // ============================================================
        [Parameter("Use ACD", DefaultValue = true, Group = "6. ACD")]
        public bool UseAcd { get; set; }

        [Parameter("ACD TF", DefaultValue = "Hour1", Group = "6. ACD")]
        public TimeFrame AcdTf { get; set; }

        [Parameter("ACD Window Bars", DefaultValue = 18, MinValue = 5, Group = "6. ACD")]
        public int AcdWindowBars { get; set; }

        [Parameter("ACD Min Range (pips)", DefaultValue = 22, MinValue = 1, Group = "6. ACD")]
        public int AcdMinRangePips { get; set; }

        [Parameter("ACD Max Range (pips)", DefaultValue = 140, MinValue = 5, Group = "6. ACD")]
        public int AcdMaxRangePips { get; set; }

        // ============================================================
        // 7) SL/TP + MANAGEMENT
        // ============================================================
        [Parameter("SL Above Level (pips)", DefaultValue = 8.0, MinValue = 0.0, Group = "7. RISK")]
        public double SlAboveLevelPips { get; set; }

        [Parameter("Hard Max SL (pips, 0=off)", DefaultValue = 0.0, MinValue = 0.0, Group = "7. RISK")]
        public double HardMaxSlPips { get; set; }

        [Parameter("Hard Min SL (pips)", DefaultValue = 6.0, MinValue = 0.0, Group = "7. RISK")]
        public double HardMinSlPips { get; set; }

        

        [Parameter("SL Mode", DefaultValue = StopLossMode.FixedPips, Group = "7. RISK")]
        public StopLossMode SlMode { get; set; }

        [Parameter("SL ATR TF", DefaultValue = "Hour1", Group = "7. RISK")]
        public TimeFrame SlAtrTimeFrame { get; set; }

        [Parameter("SL ATR Period", DefaultValue = 14, MinValue = 1, Group = "7. RISK")]
        public int SlAtrPeriod { get; set; }

        [Parameter("SL ATR Multiplier", DefaultValue = 1.6, MinValue = 0.1, Group = "7. RISK")]
        public double SlAtrMultiplier { get; set; }

        [Parameter("SL ATR Min (pips, 0=off)", DefaultValue = 0, MinValue = 0, Group = "7. RISK")]
        public double SlAtrMinPips { get; set; }

        [Parameter("SL ATR Max (pips, 0=off)", DefaultValue = 0, MinValue = 0, Group = "7. RISK")]
        public double SlAtrMaxPips { get; set; }
[Parameter("TP Mode", DefaultValue = TakeProfitMode.Both, Group = "7. RISK")]
        public TakeProfitMode TpMode { get; set; }

        [Parameter("Fixed TP (pips)", DefaultValue = 9.0, MinValue = 0.0, Group = "7. RISK")]
        public double FixedTpPips { get; set; }

        [Parameter("RSI Exit Level", DefaultValue = 50, MinValue = 0, MaxValue = 100, Group = "7. RISK")]
        public int RsiExitLevel { get; set; }

        [Parameter("RSI Exit Min Profit (pips)", DefaultValue = 3.0, MinValue = 0.0, Group = "7. RISK")]
        public double RsiExitMinProfitPips { get; set; }

        [Parameter("RSI Exit Min Hold Bars", DefaultValue = 2, MinValue = 0, Group = "7. RISK")]
        public int RsiExitMinHoldBars { get; set; }

        [Parameter("Partial Close % (0..1)", DefaultValue = 0.5, MinValue = 0.0, MaxValue = 1.0, Group = "7. RISK")]
        public double PartialClosePct { get; set; }

        [Parameter("Use Trailing For Remainder", DefaultValue = true, Group = "7. RISK")]
        public bool UseTrailingRemainder { get; set; }

        [Parameter("Trail Start (pips)", DefaultValue = 5.0, MinValue = 0.0, Group = "7. RISK")]
        public double TrailStartPips { get; set; }

        [Parameter("Trail Step (pips)", DefaultValue = 1.0, MinValue = 0.1, Group = "7. RISK")]
        public double TrailStepPips { get; set; }

        // ============================================================
        // 8) VISUAL
        // ============================================================
        [Parameter("Draw Levels", DefaultValue = true, Group = "8. VISUAL")]
        public bool DrawLevels { get; set; }

        [Parameter("Level Line Back Bars", DefaultValue = 120, MinValue = 10, Group = "8. VISUAL")]
        public int LevelLineBackBars { get; set; }

        [Parameter("Level Line Forward Bars", DefaultValue = 20, MinValue = 1, Group = "8. VISUAL")]
        public int LevelLineForwardBars { get; set; }

        [Parameter("Draw Entry Markers", DefaultValue = true, Group = "8. VISUAL")]
        public bool DrawEntryMarkers { get; set; }

        [Parameter("Debug: Print Skip Reasons", DefaultValue = false, Group = "8. VISUAL")]
        public bool DebugPrintReasons { get; set; }

        // ============================================================
        // INTERNALS
        // ============================================================
        private const int JST_OFFSET_HOURS = 9;

        private RelativeStrengthIndex _rsi;
        private Bars _htfBars;
        private Bars _acdBars;
        private Bars _rhBars;

        private double _rollingHigh = double.NaN;
        private int _rollingHighAgeBars = int.MaxValue;


        private double _acdUpper = double.NaN;
        private double _acdLower = double.NaN;

        private Bars _slAtrBars;
        private AverageTrueRange _slAtr;

        private readonly List<double> _levels = new List<double>();
        private int _lastLevelsRebuildBar = -999999;

        private int _lastEntryBar = -999999;

        
        private DateTime _lastEntryTime = DateTime.MinValue;
private int BarsSinceEntryUtc(DateTime entryTime)
        {
            var idx = Bars.OpenTimes.GetIndexByTime(entryTime);
            if (idx < 0) return int.MaxValue;
            var lastClosedIndex = Bars.Count - 2;
            return Math.Max(0, lastClosedIndex - idx);
        }

        protected override void OnStart()
        {
            _rsi = Indicators.RelativeStrengthIndex(Bars.ClosePrices, RsiPeriod);

            _htfBars = MarketData.GetBars(Htf, SymbolName);
            _acdBars = MarketData.GetBars(AcdTf, SymbolName);

            _rhBars = MarketData.GetBars(RollingHighTf, SymbolName);

            UpdateRollingHigh();
            _slAtrBars = MarketData.GetBars(SlAtrTimeFrame, SymbolName);
            _slAtr = Indicators.AverageTrueRange(_slAtrBars, SlAtrPeriod, MovingAverageType.Simple);

            RebuildLevels(force: true);
        }

        protected override void OnBar()
        {
            int lastClosed = Bars.Count - 2;

            UpdateRollingHigh();
            if (lastClosed < 10)
                return;

            // keep HTF fresh
            RebuildLevels(force: false);

            // manage open positions (trail / RSI exit)
            ManageOpenPositions();

            // entry
            TrySell(lastClosed);
        }

        private struct LevelCandidate
        {
            public double Price;
            public string Tag;
            public LevelCandidate(double price, string tag) { Price = price; Tag = tag; }
        }

        private void UpdateRollingHigh()
        {
            if (!UseRollingHigh)
                return;

            if (_rhBars == null)
                _rhBars = MarketData.GetBars(RollingHighTf, SymbolName);

            int last = _rhBars.Count - 2;
            if (last < 10)
                return;

            int lookback = Math.Max(5, RollingHighBars);
            if (last < lookback)
                return;

            int start = Math.Max(0, last - lookback + 1);

            double maxHigh = double.MinValue;
            int maxIdx = -1;
            for (int i = start; i <= last; i++)
            {
                double h = _rhBars.HighPrices[i];
                if (h > maxHigh)
                {
                    maxHigh = h;
                    maxIdx = i;
                }
            }

            if (maxIdx < 0)
                return;

            _rollingHigh = maxHigh;
            _rollingHighAgeBars = last - maxIdx;

            if (DrawRollingHighLine)
                DrawRollingHighSegment();
        }

        private void DrawRollingHighSegment()
        {
            if (double.IsNaN(_rollingHigh))
                return;

            const string name = "RH_LINE";
            Chart.RemoveObject(name);

            int last = Bars.Count - 2;
            int x1 = Math.Max(0, last - LevelLineBackBars);
            int x2 = Math.Min(Bars.Count - 1, last + LevelLineForwardBars);

            Chart.DrawTrendLine(name,
                Bars.OpenTimes[x1], _rollingHigh,
                Bars.OpenTimes[x2], _rollingHigh,
                Color.FromArgb(120, 255, 165, 0), 1, LineStyle.Dots);
        }

        private List<LevelCandidate> GetLevelCandidates(double bid, int lastClosed)
        {
            var list = new List<LevelCandidate>();
            foreach (var lv in _levels)
                list.Add(new LevelCandidate(lv, "LVL"));

            if (!UseRollingHigh)
                return list;

            if (double.IsNaN(_rollingHigh))
                return list;

            if (_rollingHigh <= bid)
                return list;

            // ACD upperが遠すぎる（上げトレンドで売りが止まりがち）時のフォールバック
            if (UseAcd && !double.IsNaN(_acdUpper) && RollingHighTriggerDistPips > 0)
            {
                double distAcdUpperPips = (_acdUpper - bid) / Pip;
                if (distAcdUpperPips <= RollingHighTriggerDistPips)
                    return list;
            }

            if (_rollingHighAgeBars > RollingHighMaxAgeBars)
                return list;

            double r = _rsi.Result[lastClosed];
            if (r < RollingHighMinRsi)
                return list;

            // 既存レベルとほぼ同じなら足さない
            double mergeDist = 2 * Pip;
            foreach (var c in list)
                if (Math.Abs(c.Price - _rollingHigh) <= mergeDist)
                    return list;

            list.Add(new LevelCandidate(_rollingHigh, "RH"));
            return list;
        }

        // ============================================================
        // ENTRY LOGIC
        // ============================================================
        private void TrySell(int lastClosed)
        {
            if (Positions.FindAll(BotLabel, SymbolName, TradeType.Sell).Length >= MaxPositions)
                return;

            if (CooldownModeParam == CooldownMode.Bars)
            {
                if (Bars.Count - 1 - _lastEntryBar <= CooldownBars)
                    return;
            }
            else
            {
                if (_lastEntryTime != DateTime.MinValue && (Server.Time - _lastEntryTime).TotalMinutes < CooldownMinutes)
                    return;
            }


            if (!IsSessionOk())
                return;

            if (Symbol.Spread / Symbol.PipSize > MaxSpreadPips)
                return;

            if (_levels.Count == 0)
                return;

            // Choose the nearest RESISTANCE level ABOVE price (avoid selling at supports)
            double bid = Symbol.Bid;
            double minLv = bid + (MinLevelAbovePips * Pip);
            double maxLv = bid + (MaxLevelDistanceAbovePips * Pip);

            double bestLv = double.NaN;
            string bestTag = "LVL";
            double bestDist = double.MaxValue;

            var candidates = GetLevelCandidates(bid, lastClosed);

            foreach (var c in candidates)
            {
                if (c.Price < minLv || c.Price > maxLv)
                    continue;

                double d = Math.Abs(c.Price - bid);
                if (d < bestDist)
                {
                    bestDist = d;
                    bestLv = c.Price;
                    bestTag = c.Tag;
                }
            }

            if (double.IsNaN(bestLv))
                return;

            // Retest condition on the last closed candle:
            // - High touches level within tolerance (from below)
            // - Close ends below level by RejectCloseBelowLevelPips (rejection)
            double tol = TouchTolerancePips * Pip;
            double reject = RejectCloseBelowLevelPips * Pip;

            double h = Bars.HighPrices[lastClosed];
            double c = Bars.ClosePrices[lastClosed];

            bool touched = h >= (bestLv - tol);
            bool rejected = c <= (bestLv - reject);

            if (!(touched && rejected))
                return;

            // Quality gates (RSI + ACD)
            if (!IsRsiQualityOk(lastClosed))
                return;

            if (!IsAcdOk())
                return;

            // Optional bear-candle confirmation on the same candle
            if (BearCandleRequired && !IsBearConfirmOk(lastClosed))
                return;

            // Place order at market
            long vol = ToVolumeLong(Symbol.QuantityToVolumeInUnits(VolumeLots));

            // IMPORTANT: ExecuteMarketOrder expects SL/TP IN PIPS (not price).
            // We derive SL price from the selected level, then convert to pips from current Ask.
            double desiredSlPrice = bestLv + (SlAboveLevelPips * Pip);

            // Optional ATR-based stop (computed from separate timeframe)
            if (SlMode == StopLossMode.Atr && _slAtr != null)
            {
                double atrValue = _slAtr.Result.LastValue; // price units
                double atrPips = (atrValue / Pip) * SlAtrMultiplier;

                if (SlAtrMinPips > 0)
                    atrPips = Math.Max(atrPips, SlAtrMinPips);
                if (SlAtrMaxPips > 0)
                    atrPips = Math.Min(atrPips, SlAtrMaxPips);

                double atrSlPrice = Symbol.Ask + atrPips * Pip;

                // Use the wider of (level-based SL) and (ATR-based SL) to avoid over-tight stops
                desiredSlPrice = Math.Max(desiredSlPrice, atrSlPrice);
            }

            double slPips = (desiredSlPrice - Symbol.Ask) / Pip;

            // Hard min/max SL (in pips)
            if (slPips < HardMinSlPips)
                slPips = HardMinSlPips;
            if (HardMaxSlPips > 0 && slPips > HardMaxSlPips)
            {
                if (DebugPrintReasons)
                    Print("Skip entry: SL too large. slPips={0:F1} > HardMaxSlPips={1:F1}", slPips, HardMaxSlPips);
                return;
            }

            double? tpPips = null;
            if (TpMode == TakeProfitMode.FixedPips || TpMode == TakeProfitMode.Both)
                tpPips = FixedTpPips;

            var result = ExecuteMarketOrder(TradeType.Sell, SymbolName, vol, BotLabel, slPips, tpPips);

            if (result.IsSuccessful)
            {
                _lastEntryBar = Bars.Count - 1;
            _lastEntryTime = Server.Time;
                if (DrawEntryMarkers)
                    DrawSellMarker(result.Position, bestTag, bestLv, lastClosed);
            }
            else
            {
                if (DebugPrintReasons)
                    Print("Entry rejected by broker: {0}", result.Error);
            }
        }

        private bool IsBearConfirmOk(int index)
        {
            double o = Bars.OpenPrices[index];
            double c = Bars.ClosePrices[index];
            double h = Bars.HighPrices[index];
            double l = Bars.LowPrices[index];

            bool red = c < o;
            if (BearMode == BearConfirmMode.Either)
                return red;

            if (BearMode == BearConfirmMode.CloseBelowPrev)
            {
                if (index - 1 < 0) return false;
                return Bars.ClosePrices[index] < Bars.ClosePrices[index - 1];
            }

            // Strict
            if (!red)
                return false;

            double body = Math.Abs(c - o);
            if (body < MinBearBodyPips * Pip)
                return false;

            double range = Math.Max(Pip, h - l);
            double closePos = (c - l) / range; // 0..1, near 0 means near low
            return closePos <= (1.0 - BearCloseNearLowPct);
        }

        private bool IsRsiQualityOk(int lastClosed)
        {
            if (!UseRsiQuality)
                return true;

            double rNow = _rsi.Result[lastClosed];

            // First: avoid selling when RSI is already too low (chasing).
            if (rNow < RsiNowMinAvoidChase)
                return false;

            // Entry window (retest at resistance should be in "upper-mid")
            if (rNow < RsiNowMin || rNow > RsiNowMax)
                return false;

            // Optional: require that within recent window RSI peaked above threshold,
            // to ensure we're fading a real push, not random noise.
            int start = Math.Max(0, lastClosed - RsiPeakWindowBars);
            double rMax = double.MinValue;
            for (int i = start; i <= lastClosed; i++)
                rMax = Math.Max(rMax, _rsi.Result[i]);

            if (rMax > BlockIfRsiMaxAbove) // too extreme -> can be trend day / squeeze
                return false;

            if (RequireRsiPeakEvidence && rMax < RsiPeakMin)
                return false;

            return true;
        }

        private bool IsAcdOk()
        {
            if (!UseAcd)
                return true;

            if (_acdBars == null || _acdBars.Count < AcdWindowBars + 5)
                return true; // can't evaluate -> don't block

            int last = _acdBars.Count - 2;
            int start = Math.Max(0, last - AcdWindowBars + 1);

            double hi = double.MinValue;
            double lo = double.MaxValue;

            for (int i = start; i <= last; i++)
            {
                hi = Math.Max(hi, _acdBars.HighPrices[i]);
                lo = Math.Min(lo, _acdBars.LowPrices[i]);
            }

            _acdUpper = hi;
            _acdLower = lo;

            double rangePips = (hi - lo) / Pip;

            if (rangePips < AcdMinRangePips) return false; // too flat (chop)
            if (rangePips > AcdMaxRangePips) return false; // too wild (news / trend spike)
            return true;
        }

        // ============================================================
        // POSITION MANAGEMENT (RSI exit + partial + trailing)
        // ============================================================
        private void ManageOpenPositions()
        {
            var sells = Positions.FindAll(BotLabel, SymbolName, TradeType.Sell);
            if (sells == null || sells.Length == 0)
                return;

            int lastClosed = Bars.Count - 2;
            if (lastClosed < 2)
                return;

            double rNow = _rsi.Result[lastClosed];

            foreach (var pos in sells)
            {
                // RSI exit: if RSI returns to 50, close (or partial close)
                if (TpMode == TakeProfitMode.RsiReturn || TpMode == TakeProfitMode.Both)
                {
                    var barsSinceEntry = BarsSinceEntryUtc(pos.EntryTime);
                    if (barsSinceEntry >= RsiExitMinHoldBars && rNow <= RsiExitLevel)
                    {
                        // Close only when position has at least small profit to avoid "tiny loss drip" from costs.
                        if (pos.Pips >= RsiExitMinProfitPips)
                        {
                            var closeRes = ClosePosition(pos);
                            if (closeRes.IsSuccessful)
                            {
                                if (DebugPrintReasons) Print("[EXIT] RSI return: pos#{0} pips={1:F1} rsi={2:F1}", pos.Id, pos.Pips, rNow);
                                continue;
                            }
                            else
                            {
                                if (DebugPrintReasons) Print("[EXIT FAIL] ClosePosition failed: pos#{0} err={1}", pos.Id, closeRes.Error);
                            }
                        }
                        else
                        {
                            if (DebugPrintReasons) Print("[SKIP EXIT] RSI return but not in profit: pos#{0} pips={1:F1} rsi={2:F1}", pos.Id, pos.Pips, rNow);
                        }
                    }
                }

                // Trailing for remainder (sell)
                if (UseTrailingRemainder)
                {
                    double profitPips = (pos.EntryPrice - Symbol.Ask) / Pip;
                    if (profitPips >= TrailStartPips)
                    {
                        double desiredSl = Symbol.Ask + (TrailStepPips * Pip);

                        // For sell: SL should move DOWN only (reduce risk)
                        if (!pos.StopLoss.HasValue || desiredSl < pos.StopLoss.Value - (0.1 * Pip))
                            ModifyPosition(pos, desiredSl, pos.TakeProfit, ProtectionType.Absolute);
                    }
                }
            }
        }

        // ============================================================
        // LEVEL BUILD (custom swing highs)
        // ============================================================
        private void RebuildLevels(bool force)
        {
            // rebuild every ~20 bars on main timeframe, or if HTF updated
            if (!force && Bars.Count - 1 - _lastLevelsRebuildBar < 20)
                return;

            _lastLevelsRebuildBar = Bars.Count - 1;

            if (_htfBars == null || _htfBars.Count < SwingLeftBars + SwingRightBars + 10)
                return;

            int last = _htfBars.Count - 2;
            int start = Math.Max(0, last - HtfLookbackBars);

            var raw = new List<double>();

            for (int i = start + SwingLeftBars; i <= last - SwingRightBars; i++)
            {
                double v = _htfBars.HighPrices[i];

                bool isMax = true;
                for (int k = 1; k <= SwingLeftBars; k++)
                {
                    if (_htfBars.HighPrices[i - k] >= v) { isMax = false; break; }
                }
                if (!isMax) continue;

                for (int k = 1; k <= SwingRightBars; k++)
                {
                    if (_htfBars.HighPrices[i + k] > v) { isMax = false; break; }
                }
                if (!isMax) continue;

                raw.Add(v);
            }

            raw.Sort();

            // merge close levels
            var merged = new List<double>();
            double mergeDist = MergeDistancePips * Pip;

            foreach (var v in raw)
            {
                if (merged.Count == 0)
                {
                    merged.Add(v);
                    continue;
                }

                double lastLv = merged[merged.Count - 1];
                if (Math.Abs(v - lastLv) <= mergeDist)
                {
                    // keep the higher one for resistance
                    merged[merged.Count - 1] = Math.Max(lastLv, v);
                }
                else
                {
                    merged.Add(v);
                }
            }

            // keep only a reasonable number around current price (above)
            double bid = Symbol.Bid;
            double minLv = bid + (MinLevelAbovePips * Pip);
            double maxLv = bid + (MaxLevelDistanceAbovePips * Pip);

            var active = merged.Where(x => x >= minLv && x <= maxLv).ToList();

            // if too few active, also allow slightly below to avoid "no levels" dead bot
            if (active.Count < 3)
            {
                double min2 = bid - (20 * Pip);
                active = merged.Where(x => x >= min2 && x <= maxLv).ToList();
            }

            // pick nearest N to bid
            active = active.OrderBy(x => Math.Abs(x - bid)).Take(MaxActiveLevels).OrderBy(x => x).ToList();

            _levels.Clear();
            _levels.AddRange(active);

            if (DrawLevels)
                DrawLevelSegments();
        }

        private void DrawLevelSegments()
        {
            // remove old drawings
            for (int i = 0; i < 200; i++)
                Chart.RemoveObject("LVL_" + i);

            int last = Bars.Count - 2;
            int x1 = Math.Max(0, last - LevelLineBackBars);
            int x2 = Math.Min(Bars.Count - 1, last + LevelLineForwardBars);

            int idx = 0;
            foreach (var lv in _levels)
            {
                string name = "LVL_" + idx;
                Chart.DrawTrendLine(name,
                    Bars.OpenTimes[x1], lv,
                    Bars.OpenTimes[x2], lv,
                    Color.FromArgb(90, 0, 255, 0), 1, LineStyle.Solid);
                idx++;
                if (idx >= 200) break;
            }
        }

        private void DrawSellMarker(Position pos, string levelTag, double level, int lastClosed)
        {
            string id = "SELL_" + pos.Id;
            double r = _rsi.Result[lastClosed];

            Chart.DrawIcon(id, ChartIconType.DownArrow, Bars.OpenTimes[lastClosed], pos.EntryPrice, Color.Red);

            string txt = string.Format("SELL {0:F5}\n{1} {2:F5}\nRSI {3:F0}", pos.EntryPrice, levelTag, level, r);
            Chart.DrawText(id + "_T", txt, Bars.OpenTimes[lastClosed], pos.EntryPrice, Color.Red);
        }

        // ============================================================
        // VOLUME HELPERS
        // ============================================================
        private long ToVolumeLong(double units)
        {
            // Normalize to broker constraints and ensure long type across cTrader API variations
            var v = Symbol.NormalizeVolumeInUnits(units, RoundingMode.ToNearest);
            long vol = Convert.ToInt64(Math.Round(v));

            vol = Math.Max(vol, Symbol.VolumeInUnitsMin);
            vol = Math.Min(vol, Symbol.VolumeInUnitsMax);
            return vol;
        }

        // ============================================================
        // SESSION (JST)
        // ============================================================
        private bool IsSessionOk()
        {
            if (!UseSessionFilter)
                return true;

            DateTime utc = Server.Time;
            DateTime jst = utc.AddHours(JST_OFFSET_HOURS);

            int h = jst.Hour;

            if (SessionStartJstHour == SessionEndJstHour)
                return true; // 24h

            if (SessionStartJstHour < SessionEndJstHour)
            {
                // same day window
                return h >= SessionStartJstHour && h < SessionEndJstHour;
            }
            else
            {
                // crosses midnight: e.g. 9 -> 4
                return h >= SessionStartJstHour || h < SessionEndJstHour;
            }
        }

        private double Pip => Symbol.PipSize;
    }
}