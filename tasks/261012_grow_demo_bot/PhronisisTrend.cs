using System;
using System.Collections.Generic;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    // PhronisisTrend — Donchian breakout + long-term SMA filter, ATR stop, risk-based sizing.
    // Demo-only hard guard. Trading OFF by default. Daily-loss halt. One instance = one symbol.
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class PhronisisTrend : Robot
    {
        [Parameter("Enable Trading", DefaultValue = false)]
        public bool EnableTrading { get; set; }

        [Parameter("Risk per trade (%)", DefaultValue = 0.5, MinValue = 0.05)]
        public double RiskPerTradePct { get; set; }

        [Parameter("Daily loss limit (%)", DefaultValue = 2.0, MinValue = 0.1)]
        public double DailyLossPct { get; set; }

        [Parameter("Max positions", DefaultValue = 1, MinValue = 1, MaxValue = 5)]
        public int MaxPositions { get; set; }

        [Parameter("Entry lookback (bars)", DefaultValue = 20, MinValue = 2)]
        public int EntryPeriod { get; set; }

        [Parameter("Exit lookback (bars)", DefaultValue = 10, MinValue = 1)]
        public int ExitPeriod { get; set; }

        [Parameter("Trend SMA (bars)", DefaultValue = 200, MinValue = 10)]
        public int TrendSmaPeriod { get; set; }

        [Parameter("ATR period", DefaultValue = 14, MinValue = 2)]
        public int AtrPeriod { get; set; }

        [Parameter("ATR stop mult", DefaultValue = 2.0, MinValue = 0.1)]
        public double AtrStopMult { get; set; }

        [Parameter("Reward:Risk (0 = no take profit)", DefaultValue = 0.0, MinValue = 0.0)]
        public double RewardRisk { get; set; }

        [Parameter("Block entry hours (UTC, comma)", DefaultValue = "12,13,14")]
        public string BlockedEntryHoursUtc { get; set; }

        [Parameter("ATR trailing stop", DefaultValue = true)]
        public bool UseTrailing { get; set; }

        [Parameter("Trailing ATR mult", DefaultValue = 2.0, MinValue = 0.1)]
        public double TrailAtrMult { get; set; }

        private AverageTrueRange _atr;
        private SimpleMovingAverage _trend;

        private HashSet<int> _blocked = new HashSet<int>();
        private double _hwHigh;
        private double _hwLow = double.MaxValue;

        private DateTime _day;
        private double _dayStartEquity;
        private bool _dayInit;
        private bool _halted;

        private const string Label = "phronisis-trend";

        protected override void OnStart()
        {
            try
            {
                if (Account == null) { Print("ABORT: Account is null."); Stop(); return; }
                if (Account.IsLive) { Print("ABORT: live account (IsLive=true). Demo only."); Stop(); return; }
                if (Symbol == null) { Print("ABORT: Symbol is null."); Stop(); return; }

                _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple);
                _trend = Indicators.SimpleMovingAverage(Bars.ClosePrices, TrendSmaPeriod);

                _blocked.Clear();
                if (!string.IsNullOrEmpty(BlockedEntryHoursUtc))
                    foreach (var tok in BlockedEntryHoursUtc.Split(','))
                    {
                        int h;
                        if (int.TryParse(tok.Trim(), out h) && h >= 0 && h <= 23) _blocked.Add(h);
                    }

                _day = Server.Time.Date;
                _dayStartEquity = Account.Equity;
                _dayInit = true;
                _halted = false;

                Print("PhronisisTrend start: Account={0} IsLive={1} Asset={2} Balance={3} Equity={4} Symbol={5} TF={6} EnableTrading={7} Risk={8}% DailyLoss={9}% MaxPos={10} Entry={11} SMA={12} ATR={13} StopMult={14} RR={15}",
                    Account.Number, Account.IsLive, Account.Asset, Account.Balance, Account.Equity, Symbol.Name, TimeFrame,
                    EnableTrading, RiskPerTradePct, DailyLossPct, MaxPositions, EntryPeriod, TrendSmaPeriod, AtrPeriod, AtrStopMult, RewardRisk);
            }
            catch (Exception ex) { Print("OnStart EXCEPTION: {0}", ex.Message); }
        }

        protected override void OnBar()
        {
            try
            {
                if (Account == null || Server == null || _atr == null || _trend == null) return;

                DateTime today = Server.Time.Date;
                if (!_dayInit || today != _day)
                {
                    _day = today; _dayStartEquity = Account.Equity; _dayInit = true; _halted = false;
                    Print("New day {0}. dayStartEquity={1:F2} {2}.", _day.ToString("yyyy-MM-dd"), _dayStartEquity, Account.Asset);
                }

                double dailyPnl = Account.Equity - _dayStartEquity;
                double limit = _dayStartEquity * (DailyLossPct / 100.0);
                if (!_halted && dailyPnl <= -limit)
                {
                    _halted = true;
                    Print("HALT: daily P/L {0:F2} <= -limit {1:F2} ({2}%). Flatten + no new entries today.", dailyPnl, limit, DailyLossPct);
                    Flatten();
                    return;
                }
                if (_halted) return;
                if (!EnableTrading) return;

                int need = Math.Max(EntryPeriod, Math.Max(TrendSmaPeriod, AtrPeriod)) + 2;
                if (Bars.Count < need) return;

                int i = Bars.Count - 2; // last closed bar
                double close = Bars.ClosePrices[i];
                double atr = _atr.Result[i];
                double sma = _trend.Result[i];
                if (double.IsNaN(atr) || double.IsNaN(sma) || atr <= 0 || close <= 0) return;

                double priorHigh = double.MinValue;
                double priorLow = double.MaxValue;
                for (int j = i - EntryPeriod; j <= i - 1; j++)
                {
                    if (j < 0) continue;
                    priorHigh = Math.Max(priorHigh, Bars.HighPrices[j]);
                    priorLow = Math.Min(priorLow, Bars.LowPrices[j]);
                }
                if (priorHigh == double.MinValue || priorLow == double.MaxValue) return;

                var openPos = Positions.Find(Label);
                if (openPos != null)
                {
                    UpdateTrailing(openPos, i, atr, close);
                    return;
                }
                if (Positions.Count >= MaxPositions) return;
                if (_blocked.Contains(Server.Time.Hour)) { Print("SKIP entry: hour {0} UTC blocked.", Server.Time.Hour); return; }

                if (close > priorHigh && close > sma)
                    Enter(TradeType.Buy, close, atr, sma);
                else if (close < priorLow && close < sma)
                    Enter(TradeType.Sell, close, atr, sma);
            }
            catch (Exception ex) { Print("OnBar EXCEPTION: {0}", ex.Message); }
        }

        private void Enter(TradeType side, double refPrice, double atr, double sma)
        {
            double pip = Symbol.PipSize;
            if (pip <= 0) { Print("SKIP: PipSize=0"); return; }

            double stopPips = (AtrStopMult * atr) / pip;
            if (stopPips < 1.0) stopPips = 1.0;
            double tpPips = RewardRisk > 0.0 ? stopPips * RewardRisk : 0.0;

            double riskAmount = Account.Equity * (RiskPerTradePct / 100.0);
            double pipValue = Symbol.PipValue;
            if (pipValue <= 0) { Print("SKIP: PipValue=0"); return; }

            double units = Symbol.NormalizeVolumeInUnits(riskAmount / (stopPips * pipValue), RoundingMode.Down);
            if (units < Symbol.VolumeInUnitsMin)
            {
                Print("SKIP entry {0}: units {1:F2} < min {2}.", side, units, Symbol.VolumeInUnitsMin);
                return;
            }

            Print("ENTRY {0} {1}: refClose={2} atr={3} sma={4} stopPips={5:F1} tpPips={6:F1} risk={7:F2} {8} units={9}",
                side, Symbol.Name, refPrice, atr, sma, stopPips, tpPips, riskAmount, Account.Asset, units);

            TradeResult r = ExecuteMarketOrder(side, Symbol.Name, units, Label, stopPips, tpPips);
            if (r == null) { Print("ENTRY FAILED: null result"); return; }
            if (r.IsSuccessful)
            {
                _hwHigh = 0.0;
                _hwLow = double.MaxValue;
                Print("ENTRY OK: {0} units={1} entry={2}", side, units, (r.Position != null ? r.Position.EntryPrice : 0.0));
            }
            else
                Print("ENTRY FAILED: {0}", r.Error);
        }

        private void UpdateTrailing(Position pos, int i, double atr, double close)
        {
            if (!UseTrailing || atr <= 0) return;
            if (pos.TradeType == TradeType.Buy)
            {
                _hwHigh = (_hwHigh <= 0) ? Bars.HighPrices[i] : Math.Max(_hwHigh, Bars.HighPrices[i]);
                double newSl = _hwHigh - TrailAtrMult * atr;
                if (newSl > 0 && newSl < close && (pos.StopLoss == null || newSl > pos.StopLoss.Value))
                {
                    var tr = ModifyPosition(pos, newSl, null, ProtectionType.Absolute);
                    if (tr != null && tr.IsSuccessful) Print("TRAIL Buy {0}: high={1} SL->{2}", Symbol.Name, _hwHigh, newSl);
                }
            }
            else
            {
                _hwLow = (_hwLow == double.MaxValue) ? Bars.LowPrices[i] : Math.Min(_hwLow, Bars.LowPrices[i]);
                double newSl = _hwLow + TrailAtrMult * atr;
                if (newSl > 0 && newSl > close && (pos.StopLoss == null || newSl < pos.StopLoss.Value))
                {
                    var tr = ModifyPosition(pos, newSl, null, ProtectionType.Absolute);
                    if (tr != null && tr.IsSuccessful) Print("TRAIL Sell {0}: low={1} SL->{2}", Symbol.Name, _hwLow, newSl);
                }
            }
        }

        private void ManageExit(Position pos, int i, double close)
        {
            double exitHigh = double.MinValue;
            double exitLow = double.MaxValue;
            for (int j = i - ExitPeriod; j <= i - 1; j++)
            {
                if (j < 0) continue;
                exitHigh = Math.Max(exitHigh, Bars.HighPrices[j]);
                exitLow = Math.Min(exitLow, Bars.LowPrices[j]);
            }
            if (exitHigh == double.MinValue || exitLow == double.MaxValue) return;

            if (pos.TradeType == TradeType.Buy && close < exitLow)
            {
                ClosePosition(pos);
                Print("EXIT Buy {0}: close={1} < exitLow={2}", Symbol.Name, close, exitLow);
            }
            else if (pos.TradeType == TradeType.Sell && close > exitHigh)
            {
                ClosePosition(pos);
                Print("EXIT Sell {0}: close={1} > exitHigh={2}", Symbol.Name, close, exitHigh);
            }
        }

        private void Flatten()
        {
            try
            {
                if (Positions == null) return;
                foreach (var p in Positions.ToList())
                {
                    try { ClosePosition(p); Print("FLATTEN closed {0} {1}", p.SymbolName, p.Id); }
                    catch (Exception ex) { Print("FLATTEN close FAILED {0}: {1}", p.Id, ex.Message); }
                }
            }
            catch (Exception ex) { Print("FLATTEN EXCEPTION: {0}", ex.Message); }
        }

        protected override void OnStop()
        {
            Print("PhronisisTrend stopped. Halted={0} OpenPositions={1}", _halted, Positions != null ? Positions.Count : -1);
        }
    }
}
