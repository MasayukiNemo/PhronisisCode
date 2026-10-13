using System;
using System.Collections.Generic;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    // PhronisisCarry — AI/レジーム・ゲート付きキャリー.
    // キャリー方向=スワップがプラスの側を保有。ナイーブの死因=キャリークラッシュを、
    // ボラ・レジームで回避（リスクオン時のみ保有、ボラ急騰で即全撤退）。デモ限定。
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class PhronisisCarry : Robot
    {
        [Parameter("Enable Trading", DefaultValue = false)]
        public bool EnableTrading { get; set; }
        [Parameter("Risk per trade (%)", DefaultValue = 0.5, MinValue = 0.05)]
        public double RiskPerTradePct { get; set; }
        [Parameter("Daily loss limit (%)", DefaultValue = 2.0, MinValue = 0.1)]
        public double DailyLossPct { get; set; }

        [Parameter("Min swap (pips/night)", DefaultValue = 0.05, MinValue = 0.0)]
        public double MinSwapPips { get; set; }
        [Parameter("Risk-on ATR ratio (enter below)", DefaultValue = 1.00, MinValue = 0.1)]
        public double RiskOnRatio { get; set; }
        [Parameter("Risk-off ATR ratio (exit above)", DefaultValue = 1.30, MinValue = 0.2)]
        public double RiskOffRatio { get; set; }
        [Parameter("ATR period", DefaultValue = 14, MinValue = 2)]
        public int AtrPeriod { get; set; }
        [Parameter("ATR MA period", DefaultValue = 20, MinValue = 2)]
        public int AtrMaPeriod { get; set; }
        [Parameter("Protect stop (x ATR)", DefaultValue = 3.0, MinValue = 0.2)]
        public double AtrStopMult { get; set; }
        [Parameter("Block entry hours (UTC, comma)", DefaultValue = "")]
        public string BlockedEntryHoursUtc { get; set; }
        [Parameter("Use trend alignment filter", DefaultValue = false)]
        public bool UseTrendFilter { get; set; }
        [Parameter("Trend MA period", DefaultValue = 100, MinValue = 5)]
        public int TrendMaPeriod { get; set; }
        [Parameter("Target annualized vol (%)", DefaultValue = 8.0, MinValue = 1.0)]
        public double TargetVolPct { get; set; }
        [Parameter("Vol lookback bars", DefaultValue = 60, MinValue = 10)]
        public int VolLookbackBars { get; set; }
        [Parameter("Vol scale min", DefaultValue = 0.5, MinValue = 0.05)]
        public double VolScaleMin { get; set; }
        [Parameter("Vol scale max", DefaultValue = 2.0, MinValue = 0.1)]
        public double VolScaleMax { get; set; }

        private AverageTrueRange _atr;
        private MovingAverage _atrMa;
        private MovingAverage _trendMa;
        private HashSet<int> _blocked = new HashSet<int>();
        private TradeType _carrySide;
        private bool _carryValid;
        private DateTime _day; private double _dayStartEquity; private bool _dayInit; private bool _halted;
        private const string Lb = "phronisis-carry";

        protected override void OnStart()
        {
            try
            {
                if (Account == null) { Print("ABORT: Account null"); Stop(); return; }
                if (Account.IsLive) { Print("ABORT: live account. Demo only."); Stop(); return; }
                if (Symbol == null) { Print("ABORT: Symbol null"); Stop(); return; }

                _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple);
                _atrMa = Indicators.MovingAverage(_atr.Result, AtrMaPeriod, MovingAverageType.Exponential);
                _trendMa = Indicators.MovingAverage(Bars.ClosePrices, TrendMaPeriod, MovingAverageType.Simple);
                _blocked.Clear();
                if (!string.IsNullOrEmpty(BlockedEntryHoursUtc))
                    foreach (var t in BlockedEntryHoursUtc.Split(',')) { int h; if (int.TryParse(t.Trim(), out h) && h >= 0 && h <= 23) _blocked.Add(h); }

                double sl = Symbol.SwapLong, ss = Symbol.SwapShort;
                _carrySide = sl >= ss ? TradeType.Buy : TradeType.Sell;
                double best = Math.Max(sl, ss);
                _carryValid = best >= MinSwapPips;
                _day = Server.Time.Date; _dayStartEquity = Account.Equity; _dayInit = true; _halted = false;
                Print("PhronisisCarry start: Account={0} IsLive={1} Asset={2} Balance={3} Equity={4} Symbol={5} TF={6} Enable={7} SwapL={8} SwapS={9} CarrySide={10} valid={11} MinSwap={12} RiskOn<={13} RiskOff>={14}",
                    Account.Number, Account.IsLive, Account.Asset, Account.Balance, Account.Equity, Symbol.Name, TimeFrame, EnableTrading, sl, ss, _carrySide, _carryValid, MinSwapPips, RiskOnRatio, RiskOffRatio);
            }
            catch (Exception ex) { Print("OnStart EXCEPTION: {0}", ex.Message); }
        }

        protected override void OnBar()
        {
            try
            {
                if (Account == null || Server == null || _atr == null || _atrMa == null) return;

                DateTime today = Server.Time.Date;
                if (!_dayInit || today != _day) { _day = today; _dayStartEquity = Account.Equity; _dayInit = true; _halted = false; }
                double dailyPnl = Account.Equity - _dayStartEquity;
                double limit = _dayStartEquity * (DailyLossPct / 100.0);
                if (!_halted && dailyPnl <= -limit) { _halted = true; Print("HALT {0:F2} <= -{1:F2}", dailyPnl, limit); Flatten(); return; }
                if (_halted) return;

                int i = Bars.Count - 2;
                if (i < AtrMaPeriod + 2) return;
                double atr = _atr.Result[i];
                double atrMa = _atrMa.Result[i];
                if (double.IsNaN(atr) || double.IsNaN(atrMa) || atrMa <= 0 || atr <= 0) return;
                double ratio = atr / atrMa;

                double trendMa = _trendMa.Result[i];
                double close = Bars.ClosePrices[i];
                var pos = Positions.Find(Lb);
                if (pos != null)
                {
                    // クラッシュ回避: リスクオフ（ボラ急騰）で全撤退
                    if (ratio >= RiskOffRatio) { ClosePosition(pos); Print("EXIT carry: risk-off ratio={0:F2}", ratio); return; }
                    // トレンド離反で撤退（キャリー方向と逆行＝大負けの源を切る）
                    if (UseTrendFilter && !double.IsNaN(trendMa))
                    {
                        bool aligned = pos.TradeType == TradeType.Buy ? close > trendMa : close < trendMa;
                        if (!aligned) { ClosePosition(pos); Print("EXIT carry: trend break close={0:F5} ma={1:F5}", close, trendMa); }
                    }
                    return;
                }

                if (!EnableTrading || !_carryValid) return;
                if (_blocked.Contains(Server.Time.Hour)) return;
                // リスクオン時のみ保有
                if (ratio > RiskOnRatio) { return; }
                // キャリー方向にトレンドが沿う時のみ保有
                if (UseTrendFilter && !double.IsNaN(trendMa))
                {
                    bool aligned = _carrySide == TradeType.Buy ? close > trendMa : close < trendMa;
                    if (!aligned) return;
                }

                double rv = RealizedVolPct(i);
                double volScale = 1.0;
                if (rv > 0.01) volScale = Math.Max(VolScaleMin, Math.Min(VolScaleMax, TargetVolPct / rv));
                Enter(_carrySide, atr, ratio, volScale);
            }
            catch (Exception ex) { Print("OnBar EXCEPTION: {0}", ex.Message); }
        }

        private double RealizedVolPct(int i)
        {
            int n = VolLookbackBars;
            if (i < n + 1) return 0;
            double sum = 0, sum2 = 0; int cnt = 0;
            for (int k = i - n + 1; k <= i; k++)
            {
                double p0 = Bars.ClosePrices[k - 1], p1 = Bars.ClosePrices[k];
                if (p0 <= 0 || p1 <= 0) continue;
                double r = Math.Log(p1 / p0);
                sum += r; sum2 += r * r; cnt++;
            }
            if (cnt < 2) return 0;
            double mean = sum / cnt;
            double var = (sum2 / cnt) - mean * mean;
            if (var < 0) var = 0;
            double spanMin = (Bars.OpenTimes[i] - Bars.OpenTimes[i - n]).TotalMinutes;
            if (spanMin <= 0) return 0;
            double minutesPerBar = spanMin / n;
            double barsPerYear = (365.0 * 24.0 * 60.0) / minutesPerBar;
            return Math.Sqrt(var) * Math.Sqrt(barsPerYear) * 100.0;
        }

        private void Enter(TradeType side, double atr, double ratio, double volScale)
        {
            double pip = Symbol.PipSize; if (pip <= 0) return;
            double stopPips = (AtrStopMult * atr) / pip; if (stopPips < 1) stopPips = 1;
            double risk = Account.Equity * (RiskPerTradePct * volScale / 100.0);
            double pv = Symbol.PipValue; if (pv <= 0) return;
            double units = Symbol.NormalizeVolumeInUnits(risk / (stopPips * pv), RoundingMode.Down);
            if (units < Symbol.VolumeInUnitsMin) return;
            var r = ExecuteMarketOrder(side, Symbol.Name, units, Lb, stopPips, 0);
            if (r != null && r.IsSuccessful) Print("ENTRY carry {0} units={1} ratio={2:F2} swapL={3} swapS={4} volScale={5:F4} stopPips={6:F1}", side, units, ratio, Symbol.SwapLong, Symbol.SwapShort, volScale, stopPips);
            else if (r != null) Print("ENTRY FAILED {0}", r.Error);
        }

        private void Flatten()
        {
            try { if (Positions == null) return; foreach (var p in Positions.ToList()) { try { ClosePosition(p); Print("FLATTEN {0} {1}", p.SymbolName, p.Id); } catch (Exception ex) { Print("FLATTEN FAIL {0}", ex.Message); } } }
            catch (Exception ex) { Print("FLATTEN EX {0}", ex.Message); }
        }

        protected override void OnStop() { Print("PhronisisCarry stopped. Halted={0}", _halted); }
    }
}
