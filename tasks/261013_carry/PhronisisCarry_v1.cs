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

        private AverageTrueRange _atr;
        private MovingAverage _atrMa;
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

                var pos = Positions.Find(Lb);
                if (pos != null)
                {
                    // クラッシュ回避: リスクオフ（ボラ急騰）で全撤退
                    if (ratio >= RiskOffRatio) { ClosePosition(pos); Print("EXIT carry: risk-off ratio={0:F2}", ratio); }
                    return;
                }

                if (!EnableTrading || !_carryValid) return;
                if (_blocked.Contains(Server.Time.Hour)) return;
                // リスクオン時のみ保有
                if (ratio > RiskOnRatio) { return; }

                Enter(_carrySide, atr, ratio);
            }
            catch (Exception ex) { Print("OnBar EXCEPTION: {0}", ex.Message); }
        }

        private void Enter(TradeType side, double atr, double ratio)
        {
            double pip = Symbol.PipSize; if (pip <= 0) return;
            double stopPips = (AtrStopMult * atr) / pip; if (stopPips < 1) stopPips = 1;
            double risk = Account.Equity * (RiskPerTradePct / 100.0);
            double pv = Symbol.PipValue; if (pv <= 0) return;
            double units = Symbol.NormalizeVolumeInUnits(risk / (stopPips * pv), RoundingMode.Down);
            if (units < Symbol.VolumeInUnitsMin) return;
            var r = ExecuteMarketOrder(side, Symbol.Name, units, Lb, stopPips, 0);
            if (r != null && r.IsSuccessful) Print("ENTRY carry {0} units={1} ratio={2:F2} swapL={3} swapS={4}", side, units, ratio, Symbol.SwapLong, Symbol.SwapShort);
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
