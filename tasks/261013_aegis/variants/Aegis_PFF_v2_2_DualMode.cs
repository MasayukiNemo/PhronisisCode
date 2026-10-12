using System;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class Aegis_PFF_v2_2_DualMode : Robot
    {
        [Parameter("Label", DefaultValue = "Aegis_PFF_v2_2", Group = "1. CORE")]
        public string BotLabel { get; set; }

        [Parameter("Volume (Lots)", DefaultValue = 0.02, MinValue = 0.01, Step = 0.01, Group = "1. CORE")]
        public double VolumeLots { get; set; }

        [Parameter("One Position Max", DefaultValue = true, Group = "1. CORE")]
        public bool OnePositionMax { get; set; }

        [Parameter("Min Bars Between Entries", DefaultValue = 3, MinValue = 0, Group = "1. CORE")]
        public int MinBarsBetweenEntries { get; set; }

        [Parameter("Draw Entry Arrows", DefaultValue = true, Group = "1. CORE")]
        public bool DrawEntryArrows { get; set; }

        [Parameter("Arrow Offset (pips)", DefaultValue = 2.0, MinValue = 0.1, Step = 0.1, Group = "1. CORE")]
        public double ArrowOffsetPips { get; set; }

        [Parameter("Use Session Filter", DefaultValue = true, Group = "2. SESSION")]
        public bool UseSessionFilter { get; set; }

        [Parameter("Session Start (JST)", DefaultValue = 8, MinValue = 0, MaxValue = 23, Group = "2. SESSION")]
        public int SessionStartJst { get; set; }

        [Parameter("Session End (JST)", DefaultValue = 23, MinValue = 0, MaxValue = 23, Group = "2. SESSION")]
        public int SessionEndJst { get; set; }

        [Parameter("Use Spread Filter", DefaultValue = true, Group = "2. SESSION")]
        public bool UseSpreadFilter { get; set; }

        [Parameter("Max Spread (pips)", DefaultValue = 1.6, MinValue = 0.1, Step = 0.1, Group = "2. SESSION")]
        public double MaxSpreadPips { get; set; }

        [Parameter("ATR Period", DefaultValue = 14, MinValue = 2, Group = "3. ATR")]
        public int AtrPeriod { get; set; }

        [Parameter("ATR MA Period", DefaultValue = 20, MinValue = 2, Group = "3. ATR")]
        public int AtrMaPeriod { get; set; }

        [Parameter("ATR MA Type", DefaultValue = MovingAverageType.Exponential, Group = "3. ATR")]
        public MovingAverageType AtrMaType { get; set; }

        [Parameter("ATR Entry Ratio Min", DefaultValue = 1.05, MinValue = 0.50, Step = 0.01, Group = "3. ATR")]
        public double AtrEntryRatioMin { get; set; }

        [Parameter("ATR Quiet Ratio Max", DefaultValue = 0.95, MinValue = 0.10, Step = 0.01, Group = "3. ATR")]
        public double AtrQuietRatioMax { get; set; }

        [Parameter("ATR Slope Lookback", DefaultValue = 3, MinValue = 1, Group = "3. ATR")]
        public int AtrSlopeLookback { get; set; }

        [Parameter("Use Dual ATR Mode", DefaultValue = true, Group = "3. ATR")]
        public bool UseDualAtrMode { get; set; }

        [Parameter("Rising ATR Cluster Min", DefaultValue = 3, MinValue = 1, MaxValue = 20, Group = "3. ATR")]
        public int RisingAtrClusterMin { get; set; }

        [Parameter("Falling ATR Cluster Min", DefaultValue = 2, MinValue = 1, MaxValue = 20, Group = "3. ATR")]
        public int FallingAtrClusterMin { get; set; }

        [Parameter("Block First Peak In Rising ATR", DefaultValue = true, Group = "3. ATR")]
        public bool BlockFirstPeakInRisingAtr { get; set; }

        [Parameter("Impulse Lookback Bars", DefaultValue = 20, MinValue = 2, Group = "4. IMPULSE")]
        public int ImpulseLookbackBars { get; set; }

        [Parameter("Impulse Min Pips", DefaultValue = 15.0, MinValue = 0.1, Step = 0.1, Group = "4. IMPULSE")]
        public double ImpulseMinPips { get; set; }

        [Parameter("Recent High Lookback", DefaultValue = 40, MinValue = 5, Group = "5. PRICE")]
        public int RecentHighLookback { get; set; }

        [Parameter("High Proximity (pips)", DefaultValue = 8.0, MinValue = 0.5, Step = 0.1, Group = "5. PRICE")]
        public double HighProximityPips { get; set; }

        [Parameter("Cluster Lookback Bars", DefaultValue = 12, MinValue = 2, Group = "5. PRICE")]
        public int ClusterLookbackBars { get; set; }

        [Parameter("Cluster Band (pips)", DefaultValue = 3.0, MinValue = 0.1, Step = 0.1, Group = "5. PRICE")]
        public double ClusterBandPips { get; set; }

        [Parameter("Peak Price Buffer (pips)", DefaultValue = 1.5, MinValue = 0.0, Step = 0.1, Group = "5. PRICE")]
        public double PeakPriceBufferPips { get; set; }

        [Parameter("RSI Period", DefaultValue = 12, MinValue = 2, Group = "6. RSI")]
        public int RsiPeriod { get; set; }

        [Parameter("RSI Peak1 Min", DefaultValue = 68.0, MinValue = 0.0, MaxValue = 100.0, Step = 0.1, Group = "6. RSI")]
        public double RsiPeak1Min { get; set; }

        [Parameter("RSI Drop Min", DefaultValue = 6.0, MinValue = 0.1, Step = 0.1, Group = "6. RSI")]
        public double RsiDropMin { get; set; }

        [Parameter("RSI Peak Gap Min", DefaultValue = 2.0, MinValue = 0.1, Step = 0.1, Group = "6. RSI")]
        public double RsiPeakGapMin { get; set; }

        [Parameter("RSI Search Lookback Bars", DefaultValue = 15, MinValue = 6, Group = "6. RSI")]
        public int RsiSearchLookbackBars { get; set; }

        [Parameter("Max Bars Since Peak2", DefaultValue = 4, MinValue = 1, Group = "6. RSI")]
        public int MaxBarsSincePeak2 { get; set; }

        [Parameter("Need Bear Candle", DefaultValue = true, Group = "7. ENTRY")]
        public bool NeedBearCandle { get; set; }

        [Parameter("Use Midpoint Rejection", DefaultValue = true, Group = "7. ENTRY")]
        public bool UseMidpointRejection { get; set; }

        [Parameter("Fixed TP (pips)", DefaultValue = 10.5, MinValue = 0.1, Step = 0.1, Group = "8. EXIT")]
        public double FixedTakeProfitPips { get; set; }

        [Parameter("Use H1 ATR Stop", DefaultValue = true, Group = "8. EXIT")]
        public bool UseH1AtrStop { get; set; }

        [Parameter("H1 ATR Period", DefaultValue = 11, MinValue = 2, Group = "8. EXIT")]
        public int H1AtrPeriod { get; set; }

        [Parameter("H1 ATR Multiplier", DefaultValue = 1.5, MinValue = 0.1, Step = 0.1, Group = "8. EXIT")]
        public double H1AtrMultiplier { get; set; }

        [Parameter("Hard Min SL (pips)", DefaultValue = 6.5, MinValue = 0.1, Step = 0.1, Group = "8. EXIT")]
        public double HardMinStopLossPips { get; set; }

        [Parameter("Hard Max SL (pips, 0=off)", DefaultValue = 0.0, MinValue = 0.0, Step = 0.1, Group = "8. EXIT")]
        public double HardMaxStopLossPips { get; set; }

        [Parameter("Use Time Decay Exit", DefaultValue = true, Group = "8. EXIT")]
        public bool UseTimeDecayExit { get; set; }

        [Parameter("Decay Bars", DefaultValue = 12, MinValue = 1, Group = "8. EXIT")]
        public int DecayBars { get; set; }

        [Parameter("Decay Min Profit (pips)", DefaultValue = 2.0, MinValue = 0.0, Step = 0.1, Group = "8. EXIT")]
        public double DecayMinProfitPips { get; set; }

        [Parameter("Use Trailing", DefaultValue = true, Group = "8. EXIT")]
        public bool UseTrailing { get; set; }

        [Parameter("Trail Start (pips)", DefaultValue = 9.0, MinValue = 0.1, Step = 0.1, Group = "8. EXIT")]
        public double TrailStartPips { get; set; }

        [Parameter("Trail Step (pips)", DefaultValue = 3.0, MinValue = 0.1, Step = 0.1, Group = "8. EXIT")]
        public double TrailStepPips { get; set; }

        private RelativeStrengthIndex _rsi;
        private AverageTrueRange _atr;
        private MovingAverage _atrMa;
        private Bars _h1Bars;
        private AverageTrueRange _atrH1;
        private int _lastEntryBarIndex = -100000;

        protected override void OnStart()
        {
            _rsi = Indicators.RelativeStrengthIndex(Bars.ClosePrices, RsiPeriod);
            _atr = Indicators.AverageTrueRange(Bars, AtrPeriod, MovingAverageType.Exponential);
            _atrMa = Indicators.MovingAverage(_atr.Result, AtrMaPeriod, AtrMaType);
            _h1Bars = MarketData.GetBars(TimeFrame.Hour);
            _atrH1 = Indicators.AverageTrueRange(_h1Bars, H1AtrPeriod, MovingAverageType.Exponential);
        }

        protected override void OnBar()
        {
            ManageOpenPositions();

            int signalBar = Bars.Count - 2;
            int warmup = Math.Max(Math.Max(RecentHighLookback, ImpulseLookbackBars), Math.Max(RsiSearchLookbackBars, AtrMaPeriod + AtrSlopeLookback));
            if (signalBar < warmup)
                return;

            if (OnePositionMax && HasOpenShortPosition())
                return;

            if ((signalBar - _lastEntryBarIndex) < MinBarsBetweenEntries)
                return;

            if (!PassesSessionFilter() || !PassesSpreadFilter())
                return;

            if (!IsSignal(signalBar))
                return;

            double stopLossPips = ComputeStopLossPips();
            if (stopLossPips <= 0)
                return;

            double rawVolume = Symbol.QuantityToVolumeInUnits(VolumeLots);
            double volume = Symbol.NormalizeVolumeInUnits(rawVolume, RoundingMode.Down);

            TradeResult result = ExecuteMarketOrder(TradeType.Sell, SymbolName, volume, BotLabel, stopLossPips, FixedTakeProfitPips);

            if (result != null && result.IsSuccessful)
            {
                _lastEntryBarIndex = signalBar;
                if (DrawEntryArrows)
                    DrawEntryArrow(signalBar);
            }
        }

        private bool IsSignal(int signalBar)
        {
            AtrMode atrMode;
            if (!TryGetAtrMode(signalBar, out atrMode))
                return false;

            if (!PassImpulseContext(signalBar))
                return false;

            double recentHigh = GetHighestHigh(signalBar - 1, RecentHighLookback);
            double distanceToHighPips = (recentHigh - Bars.ClosePrices[signalBar]) / Symbol.PipSize;
            if (distanceToHighPips < 0 || distanceToHighPips > HighProximityPips)
                return false;

            int clusterCount = CountHighTests(signalBar - 1, recentHigh, ClusterBandPips, ClusterLookbackBars);
            int minCluster = atrMode == AtrMode.Rising ? RisingAtrClusterMin : FallingAtrClusterMin;
            if (clusterCount < minCluster)
                return false;

            if (atrMode == AtrMode.Rising && BlockFirstPeakInRisingAtr)
            {
                // First-touch block: require at least two distinct local highs near the band before selling.
                int distinctPeaks = CountDistinctHighPeaks(signalBar - 1, recentHigh, ClusterBandPips, ClusterLookbackBars);
                if (distinctPeaks < 2)
                    return false;
            }

            RsiStructure s;
            if (!TryGetRsiWeakeningStructure(signalBar, out s))
                return false;

            if ((signalBar - s.Peak2Bar) > MaxBarsSincePeak2)
                return false;

            double highestSincePeak2 = GetHighestHighRange(s.Peak2Bar, signalBar);
            if (highestSincePeak2 > s.Peak2Price + PeakPriceBufferPips * Symbol.PipSize)
                return false;

            if (NeedBearCandle && Bars.ClosePrices[signalBar] >= Bars.OpenPrices[signalBar])
                return false;

            if (UseMidpointRejection)
            {
                double mid = (Bars.HighPrices[signalBar] + Bars.LowPrices[signalBar]) * 0.5;
                bool rejection = Bars.ClosePrices[signalBar] < mid || Bars.ClosePrices[signalBar] < Bars.ClosePrices[signalBar - 1];
                if (!rejection)
                    return false;
            }

            return true;
        }

        private bool TryGetAtrMode(int signalBar, out AtrMode mode)
        {
            mode = AtrMode.Quiet;

            double atrNow = _atr.Result[signalBar];
            double atrMaNow = _atrMa.Result[signalBar];
            if (atrMaNow <= 0)
                return false;

            double ratio = atrNow / atrMaNow;
            if (ratio < AtrQuietRatioMax)
                return false;

            if (ratio < AtrEntryRatioMin)
                return false;

            if (!UseDualAtrMode)
            {
                mode = AtrMode.Rising;
                return true;
            }

            int prev = Math.Max(0, signalBar - AtrSlopeLookback);
            if (_atr.Result[signalBar] >= _atr.Result[prev])
                mode = AtrMode.Rising;
            else
                mode = AtrMode.Falling;

            return true;
        }

        private bool PassImpulseContext(int signalBar)
        {
            int start = Math.Max(0, signalBar - ImpulseLookbackBars + 1);
            double lowest = double.MaxValue;

            for (int i = start; i <= signalBar; i++)
            {
                if (Bars.LowPrices[i] < lowest)
                    lowest = Bars.LowPrices[i];
            }

            double impulsePips = (Bars.HighPrices[signalBar] - lowest) / Symbol.PipSize;
            return impulsePips >= ImpulseMinPips;
        }

        private bool TryGetRsiWeakeningStructure(int signalBar, out RsiStructure s)
        {
            s = new RsiStructure();
            int start = Math.Max(3, signalBar - RsiSearchLookbackBars);
            int end = Math.Min(signalBar - 1, Bars.Count - 3);

            int peak2 = -1;
            for (int i = end; i >= start; i--)
            {
                if (IsLocalPeak(i))
                {
                    peak2 = i;
                    break;
                }
            }
            if (peak2 < 0)
                return false;

            int trough = -1;
            for (int i = peak2 - 1; i >= start; i--)
            {
                if (IsLocalTrough(i))
                {
                    trough = i;
                    break;
                }
            }
            if (trough < 0)
                return false;

            int peak1 = -1;
            for (int i = trough - 1; i >= start; i--)
            {
                if (IsLocalPeak(i))
                {
                    peak1 = i;
                    break;
                }
            }
            if (peak1 < 0)
                return false;

            double p1 = _rsi.Result[peak1];
            double tr = _rsi.Result[trough];
            double p2 = _rsi.Result[peak2];

            if (p1 < RsiPeak1Min)
                return false;

            if ((p1 - tr) < RsiDropMin)
                return false;

            if (p2 > (p1 - RsiPeakGapMin))
                return false;

            s.Peak1Bar = peak1;
            s.TroughBar = trough;
            s.Peak2Bar = peak2;
            s.Peak1Rsi = p1;
            s.TroughRsi = tr;
            s.Peak2Rsi = p2;
            s.Peak1Price = Bars.HighPrices[peak1];
            s.Peak2Price = Bars.HighPrices[peak2];
            return true;
        }

        private bool IsLocalPeak(int bar)
        {
            if (bar < 1 || bar >= Bars.Count - 1)
                return false;

            return _rsi.Result[bar] > _rsi.Result[bar - 1] && _rsi.Result[bar] >= _rsi.Result[bar + 1];
        }

        private bool IsLocalTrough(int bar)
        {
            if (bar < 1 || bar >= Bars.Count - 1)
                return false;

            return _rsi.Result[bar] < _rsi.Result[bar - 1] && _rsi.Result[bar] <= _rsi.Result[bar + 1];
        }

        private int CountDistinctHighPeaks(int endBar, double referenceHigh, double bandPips, int lookback)
        {
            int start = Math.Max(1, endBar - lookback + 1);
            double band = bandPips * Symbol.PipSize;
            int count = 0;

            for (int i = start; i < endBar; i++)
            {
                bool localHigh = Bars.HighPrices[i] >= Bars.HighPrices[i - 1] && Bars.HighPrices[i] > Bars.HighPrices[i + 1];
                bool inBand = Bars.HighPrices[i] >= referenceHigh - band && Bars.HighPrices[i] <= referenceHigh + band;

                if (localHigh && inBand)
                    count++;
            }

            return count;
        }

        private void DrawEntryArrow(int signalBar)
        {
            string name = string.Format("{0}_ENTRY_{1}_{2}", BotLabel, Bars.OpenTimes[signalBar].Ticks, signalBar);
            double y = Bars.HighPrices[signalBar] + ArrowOffsetPips * Symbol.PipSize;
            Chart.DrawIcon(name, ChartIconType.DownArrow, Bars.OpenTimes[signalBar], y, Color.Red);
        }

        private double ComputeStopLossPips()
        {
            double sl = HardMinStopLossPips;

            if (UseH1AtrStop)
            {
                double atrPips = (_atrH1.Result.LastValue / Symbol.PipSize) * H1AtrMultiplier;
                sl = Math.Max(sl, atrPips);
            }

            if (HardMaxStopLossPips > 0)
                sl = Math.Min(sl, HardMaxStopLossPips);

            return sl;
        }

        private void ManageOpenPositions()
        {
            foreach (var position in Positions)
            {
                if (position.SymbolName != SymbolName || position.TradeType != TradeType.Sell || position.Label != BotLabel)
                    continue;

                if (UseTimeDecayExit)
                    TryTimeDecayExit(position);

                if (UseTrailing)
                    TryTrailing(position);
            }
        }

        private void TryTimeDecayExit(Position position)
        {
            int barsOpen = GetBarsSinceEntry(position.EntryTime);
            if (barsOpen < DecayBars)
                return;

            double profitPips = GetPositionProfitPips(position);
            if (profitPips >= DecayMinProfitPips)
                return;

            ClosePosition(position);
        }

        private void TryTrailing(Position position)
        {
            double profitPips = GetPositionProfitPips(position);
            if (profitPips < TrailStartPips)
                return;

            double desiredStop = Symbol.Ask + TrailStepPips * Symbol.PipSize;

            if (position.StopLoss == null || desiredStop < position.StopLoss.Value - (0.1 * Symbol.PipSize))
                ModifyPosition(position, desiredStop, position.TakeProfit);
        }

        private bool HasOpenShortPosition()
        {
            foreach (var position in Positions)
            {
                if (position.SymbolName == SymbolName && position.TradeType == TradeType.Sell && position.Label == BotLabel)
                    return true;
            }

            return false;
        }

        private bool PassesSpreadFilter()
        {
            return !UseSpreadFilter || ((Symbol.Ask - Symbol.Bid) / Symbol.PipSize) <= MaxSpreadPips;
        }

        private bool PassesSessionFilter()
        {
            if (!UseSessionFilter)
                return true;

            DateTime jst = Server.Time.AddHours(9);
            int hour = jst.Hour;

            if (SessionStartJst <= SessionEndJst)
                return hour >= SessionStartJst && hour < SessionEndJst;

            return hour >= SessionStartJst || hour < SessionEndJst;
        }

        private double GetPositionProfitPips(Position position)
        {
            return (position.EntryPrice - Symbol.Ask) / Symbol.PipSize;
        }

        private int GetBarsSinceEntry(DateTime entryTimeUtc)
        {
            int bars = 0;
            for (int i = Bars.Count - 2; i >= 0; i--)
            {
                if (Bars.OpenTimes[i] <= entryTimeUtc)
                    break;
                bars++;
            }

            return bars;
        }

        private double GetHighestHigh(int endBar, int lookback)
        {
            int start = Math.Max(0, endBar - lookback + 1);
            double highest = double.MinValue;

            for (int i = start; i <= endBar; i++)
            {
                if (Bars.HighPrices[i] > highest)
                    highest = Bars.HighPrices[i];
            }

            return highest;
        }

        private double GetHighestHighRange(int startBar, int endBar)
        {
            startBar = Math.Max(0, startBar);
            endBar = Math.Min(Bars.Count - 1, endBar);
            double highest = double.MinValue;

            for (int i = startBar; i <= endBar; i++)
            {
                if (Bars.HighPrices[i] > highest)
                    highest = Bars.HighPrices[i];
            }

            return highest;
        }

        private int CountHighTests(int endBar, double referenceHigh, double bandPips, int lookback)
        {
            int start = Math.Max(0, endBar - lookback + 1);
            double band = bandPips * Symbol.PipSize;
            int count = 0;

            for (int i = start; i <= endBar; i++)
            {
                if (Bars.HighPrices[i] >= referenceHigh - band && Bars.HighPrices[i] <= referenceHigh + band)
                    count++;
            }

            return count;
        }

        private struct RsiStructure
        {
            public int Peak1Bar;
            public int TroughBar;
            public int Peak2Bar;
            public double Peak1Rsi;
            public double TroughRsi;
            public double Peak2Rsi;
            public double Peak1Price;
            public double Peak2Price;
        }

        private enum AtrMode
        {
            Quiet = 0,
            Rising = 1,
            Falling = 2
        }
    }
}
