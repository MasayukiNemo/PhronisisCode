using System;
using System.Collections.Generic;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    // PhronisisMR — mean-reversion: buy oversold at lower Bollinger + low RSI, sell overbought at upper + high RSI.
    // Exit at the middle band (mean). Catastrophic ATR stop. Demo-only guard, daily halt, blocked entry hours.
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class PhronisisMR : Robot
    {
        [Parameter("Enable Trading", DefaultValue = false)]
        public bool EnableTrading { get; set; }

        [Parameter("Risk per trade (%)", DefaultValue = 0.5, MinValue = 0.05)]
        public double RiskPerTradePct { get; set; }

        [Parameter("Daily loss limit (%)", DefaultValue = 2.0, MinValue = 0.1)]
        public double DailyLossPct { get; set; }

        [Parameter("Max positions", DefaultValue = 1, MinValue = 1, MaxValue = 5)]
        public int MaxPositions { get; set; }

        [Parameter("BB period", DefaultValue = 20, MinValue = 2)]
        public int BbPeriod { get; set; }

        [Parameter("BB std dev", DefaultValue = 2.0, MinValue = 0.1)]
        public double BbStd { get; set; }

        [Parameter("RSI period", DefaultValue = 14, MinValue = 2)]
        public int RsiPeriod { get; set; }

        [Parameter("RSI buy below", DefaultValue = 30.0)]
        public double RsiBuy { get; set; }

        [Parameter("RSI sell above", DefaultValue = 70.0)]
        public double RsiSell { get; set; }

        [Parameter("ATR period", DefaultValue = 14, MinValue = 2)]
        public int AtrPeriod { get; set; }

        [Parameter("ATR stop mult", DefaultValue = 2.0, MinValue = 0.1)]
        public double AtrStopMult { get; set; }

        [Parameter("ATR trailing stop", DefaultValue = false)]
        public bool UseTrailing { get; set; }

        [Parameter("Trailing ATR mult", DefaultValue = 2.0, MinValue = 0.1)]
        public double TrailAtrMult { get; set; }

        [Parameter("Block entry hours (UTC, comma)", DefaultValue = "12,13,14")]
        public string BlockedEntryHoursUtc { get; set; }

        private BollingerBands _bb;
        private RelativeStrengthIndex _rsi;
        private AverageTrueRange _atr;

        private HashSet<int> _blocked = new HashSet<int>();
        private double _hwHigh;
        private double _hwLow = double.MaxValue;

        private DateTime _day;
        private double _dayStartEquity;
        private bool _dayInit;
        private bool _halted;

        private const string Label = "phronisis-mr";

        protected override void OnStart()
        {
            try
            {
                if (Account == null) { Print("ABORT: Account is null."); Stop(); return; }
                if (Account.IsLive) { Print("ABORT: live account (IsLive=true). Demo only."); Stop(); return; }
                if (Symbol == null) { Print("ABORT: Symbol is null."); Stop(); return; }

                _bb = Indicators.BollingerBands(Bars.ClosePrices, BbPeriod, BbStd, MovingAverageType.Simple);
                _rsi = Indicators.RelativeStrengthIndex(Bars.ClosePrices, RsiPeriod);
                _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple);

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

                Print("PhronisisMR start: Account={0} IsLive={1} Asset={2} Balance={3} Equity={4} Symbol={5} TF={6} EnableTrading={7} Risk={8}% DailyLoss={9}% BB={10}/{11} RSI={12}[{13}/{14}] ATR={15}x{16} Trail={17} Blocked={18}",
                    Account.Number, Account.IsLive, Account.Asset, Account.Balance, Account.Equity, Symbol.Name, TimeFrame,
                    EnableTrading, RiskPerTradePct, DailyLossPct, BbPeriod, BbStd, RsiPeriod, RsiBuy, RsiSell, AtrPeriod, AtrStopMult, UseTrailing, BlockedEntryHoursUtc);
            }
            catch (Exception ex) { Print("OnStart EXCEPTION: {0}", ex.Message); }
        }

        protected override void OnBar()
        {
            try
            {
                if (Account == null || Server == null || _bb == null || _rsi == null || _atr == null) return;

                DateTime today = Server.Time.Date;
                if (!_dayInit || today != _day)
                {
                    _day = today; _dayStartEquity = Account.Equity; _dayInit = true; _halted = false;
                }

                double dailyPnl = Account.Equity - _dayStartEquity;
                double limit = _dayStartEquity * (DailyLossPct / 100.0);
                if (!_halted && dailyPnl <= -limit)
                {
                    _halted = true;
                    Print("HALT: daily P/L {0:F2} <= -limit {1:F2} ({2}%). Flatten.", dailyPnl, limit, DailyLossPct);
                    Flatten();
                    return;
                }
                if (_halted || !EnableTrading) return;

                int need = Math.Max(BbPeriod, Math.Max(RsiPeriod, AtrPeriod)) + 2;
                if (Bars.Count < need) return;

                int i = Bars.Count - 2;
                double close = Bars.ClosePrices[i];
                double atr = _atr.Result[i];
                double rsi = _rsi.Result[i];
                double top = _bb.Top[i], bottom = _bb.Bottom[i], main = _bb.Main[i];
                if (double.IsNaN(atr) || double.IsNaN(rsi) || double.IsNaN(main) || atr <= 0) return;

                var pos = Positions.Find(Label);
                if (pos != null)
                {
                    if (pos.TradeType == TradeType.Buy && close > main) { ClosePosition(pos); Print("EXIT Buy(mean) {0}: close={1} > main={2}", Symbol.Name, close, main); return; }
                    if (pos.TradeType == TradeType.Sell && close < main) { ClosePosition(pos); Print("EXIT Sell(mean) {0}: close={1} < main={2}", Symbol.Name, close, main); return; }
                    UpdateTrailing(pos, i, atr, close);
                    return;
                }
                if (Positions.Count >= MaxPositions) return;
                if (_blocked.Contains(Server.Time.Hour)) { Print("SKIP entry: hour {0} UTC blocked.", Server.Time.Hour); return; }

                if (close < bottom && rsi < RsiBuy)
                    Enter(TradeType.Buy, close, atr);
                else if (close > top && rsi > RsiSell)
                    Enter(TradeType.Sell, close, atr);
            }
            catch (Exception ex) { Print("OnBar EXCEPTION: {0}", ex.Message); }
        }

        private void Enter(TradeType side, double refPrice, double atr)
        {
            double pip = Symbol.PipSize;
            if (pip <= 0) return;
            double stopPips = (AtrStopMult * atr) / pip;
            if (stopPips < 1.0) stopPips = 1.0;

            double riskAmount = Account.Equity * (RiskPerTradePct / 100.0);
            double pipValue = Symbol.PipValue;
            if (pipValue <= 0) return;

            double units = Symbol.NormalizeVolumeInUnits(riskAmount / (stopPips * pipValue), RoundingMode.Down);
            if (units < Symbol.VolumeInUnitsMin) { Print("SKIP entry {0}: units {1} < min {2}", side, units, Symbol.VolumeInUnitsMin); return; }

            Print("ENTRY {0} {1}: ref={2} atr={3} stopPips={4:F1} rsi={5:F1} units={6}", side, Symbol.Name, refPrice, atr, stopPips, _rsi.Result.Last(1), units);

            TradeResult r = ExecuteMarketOrder(side, Symbol.Name, units, Label, stopPips, 0);
            if (r == null) { Print("ENTRY FAILED: null result"); return; }
            if (r.IsSuccessful)
            {
                _hwHigh = 0.0; _hwLow = double.MaxValue;
                Print("ENTRY OK: {0} units={1} entry={2}", side, units, (r.Position != null ? r.Position.EntryPrice : 0.0));
            }
            else Print("ENTRY FAILED: {0}", r.Error);
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
                    if (tr != null && tr.IsSuccessful) Print("TRAIL Buy SL->{0}", newSl);
                }
            }
            else
            {
                _hwLow = (_hwLow == double.MaxValue) ? Bars.LowPrices[i] : Math.Min(_hwLow, Bars.LowPrices[i]);
                double newSl = _hwLow + TrailAtrMult * atr;
                if (newSl > 0 && newSl > close && (pos.StopLoss == null || newSl < pos.StopLoss.Value))
                {
                    var tr = ModifyPosition(pos, newSl, null, ProtectionType.Absolute);
                    if (tr != null && tr.IsSuccessful) Print("TRAIL Sell SL->{0}", newSl);
                }
            }
        }

        private void Flatten()
        {
            try
            {
                if (Positions == null) return;
                foreach (var p in Positions.ToList())
                {
                    try { ClosePosition(p); Print("FLATTEN {0} {1}", p.SymbolName, p.Id); }
                    catch (Exception ex) { Print("FLATTEN FAIL {0}: {1}", p.Id, ex.Message); }
                }
            }
            catch (Exception ex) { Print("FLATTEN EX {0}", ex.Message); }
        }

        protected override void OnStop()
        {
            Print("PhronisisMR stopped. Halted={0}", _halted);
        }
    }
}
