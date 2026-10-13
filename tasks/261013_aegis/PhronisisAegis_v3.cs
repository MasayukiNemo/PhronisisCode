using System;
using System.Collections.Generic;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    // PhronisisAegis v2 — Aegis-type rebuild (v1の反省: 選択性こそ資産).
    // 型: H4レベルのレジスタンスへリテスト→弱い再攻撃を売る。
    // 選択性(黙る)の復元: H4レベルの厳選(merge/max) + ATR局面フィルタ + RSI品質ゲート + ベア確認。
    // Sell-only / デモ限定ガード / 日次損失停止 / 早期損傷カット。
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class PhronisisAegis : Robot
    {
        [Parameter("Enable Trading", DefaultValue = false)]
        public bool EnableTrading { get; set; }
        [Parameter("Risk per trade (%)", DefaultValue = 0.5, MinValue = 0.05)]
        public double RiskPerTradePct { get; set; }
        [Parameter("Daily loss limit (%)", DefaultValue = 2.0, MinValue = 0.1)]
        public double DailyLossPct { get; set; }

        [Parameter("Level TF (H1/H4/D1)", DefaultValue = "H4")]
        public string LevelTimeFrame { get; set; }
        [Parameter("Level fractal K", DefaultValue = 2, MinValue = 1)]
        public int LevelFractalK { get; set; }
        [Parameter("Level lookback (bars)", DefaultValue = 210, MinValue = 20)]
        public int LevelLookback { get; set; }
        [Parameter("Level merge (pips)", DefaultValue = 7.5, MinValue = 0.0)]
        public double LevelMergePips { get; set; }
        [Parameter("Max levels", DefaultValue = 6, MinValue = 1)]
        public int MaxLevels { get; set; }
        [Parameter("Min level dist above (pips)", DefaultValue = 3.0, MinValue = 0.0)]
        public double MinLevelDistPips { get; set; }

        [Parameter("Retest tolerance (x ATR)", DefaultValue = 0.5, MinValue = 0.05)]
        public double RetestTolAtr { get; set; }

        [Parameter("RSI period", DefaultValue = 14, MinValue = 2)]
        public int RsiPeriod { get; set; }
        [Parameter("RSI band min", DefaultValue = 55.0)]
        public double RsiBandMin { get; set; }
        [Parameter("RSI band max", DefaultValue = 80.0)]
        public double RsiBandMax { get; set; }
        [Parameter("RSI peak min", DefaultValue = 57.0)]
        public double RsiPeakMin { get; set; }
        [Parameter("RSI avoid-chase min", DefaultValue = 30.0)]
        public double RsiAvoidChaseMin { get; set; }
        [Parameter("RSI peak lookback (bars)", DefaultValue = 12, MinValue = 2)]
        public int RsiPeakLookback { get; set; }

        [Parameter("ATR period", DefaultValue = 14, MinValue = 2)]
        public int AtrPeriod { get; set; }
        [Parameter("ATR MA period", DefaultValue = 20, MinValue = 2)]
        public int AtrMaPeriod { get; set; }
        [Parameter("Trade regime (Any/Expansion/Compression)", DefaultValue = "Any")]
        public string TradeRegime { get; set; }
        [Parameter("ATR expansion ratio", DefaultValue = 1.15, MinValue = 0.5)]
        public double AtrExpansionRatio { get; set; }
        [Parameter("ATR compression ratio", DefaultValue = 0.90, MinValue = 0.1)]
        public double AtrCompressionRatio { get; set; }

        [Parameter("ACD lookback (bars)", DefaultValue = 15, MinValue = 3)]
        public int AcdLookback { get; set; }
        [Parameter("ACD min range (pips)", DefaultValue = 5.6, MinValue = 0.0)]
        public double AcdMinPips { get; set; }
        [Parameter("ACD max range (pips)", DefaultValue = 83.0, MinValue = 1.0)]
        public double AcdMaxPips { get; set; }
        [Parameter("Require lower-low structure", DefaultValue = true)]
        public bool RequireLowerLow { get; set; }
        [Parameter("Structure lookback (bars)", DefaultValue = 20, MinValue = 5)]
        public int StructLookback { get; set; }

        [Parameter("Stop (x ATR)", DefaultValue = 1.5, MinValue = 0.2)]
        public double AtrStopMult { get; set; }
        [Parameter("Early-damage bars", DefaultValue = 6, MinValue = 1)]
        public int EarlyDamageBars { get; set; }
        [Parameter("Early-damage min pips", DefaultValue = 0.5)]
        public double EarlyDamageMinPips { get; set; }
        [Parameter("RSI return exit (short)", DefaultValue = 50.0)]
        public double RsiReturnLevel { get; set; }
        [Parameter("Block entry hours (UTC, comma)", DefaultValue = "12,13,14")]
        public string BlockedEntryHoursUtc { get; set; }

        private Bars _lvBars;
        private RelativeStrengthIndex _rsi;
        private AverageTrueRange _atr;
        private MovingAverage _atrMa;

        private HashSet<int> _blocked = new HashSet<int>();
        private DateTime _day;
        private double _dayStartEquity;
        private bool _dayInit;
        private bool _halted;
        private int _entryBar = -1;
        private const string Label = "phronisis-aegis2";

        protected override void OnStart()
        {
            try
            {
                if (Account == null) { Print("ABORT: Account null"); Stop(); return; }
                if (Account.IsLive) { Print("ABORT: live account. Demo only."); Stop(); return; }
                if (Symbol == null) { Print("ABORT: Symbol null"); Stop(); return; }

                _lvBars = MarketData.GetBars(ParseTF(LevelTimeFrame));
                _rsi = Indicators.RelativeStrengthIndex(Bars.ClosePrices, RsiPeriod);
                _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Simple);
                _atrMa = Indicators.MovingAverage(_atr.Result, AtrMaPeriod, MovingAverageType.Exponential);

                _blocked.Clear();
                if (!string.IsNullOrEmpty(BlockedEntryHoursUtc))
                    foreach (var tok in BlockedEntryHoursUtc.Split(','))
                    { int hh; if (int.TryParse(tok.Trim(), out hh) && hh >= 0 && hh <= 23) _blocked.Add(hh); }

                _day = Server.Time.Date; _dayStartEquity = Account.Equity; _dayInit = true; _halted = false;
                Print("PhronisisAegis v2 start: Account={0} IsLive={1} Asset={2} Balance={3} Equity={4} Symbol={5} TF={6} Enable={7} LvlTF={8}/K{9}lb{10}merge{11}max{12} Tol={13}ATR Regime={14} RSI[{15}-{16}]pk{17}",
                    Account.Number, Account.IsLive, Account.Asset, Account.Balance, Account.Equity, Symbol.Name, TimeFrame, EnableTrading, LevelTimeFrame, LevelFractalK, LevelLookback, LevelMergePips, MaxLevels, RetestTolAtr, TradeRegime, RsiBandMin, RsiBandMax, RsiPeakMin);
            }
            catch (Exception ex) { Print("OnStart EXCEPTION: {0}", ex.Message); }
        }

        protected override void OnBar()
        {
            try
            {
                if (Account == null || Server == null || _lvBars == null || _rsi == null || _atr == null || _atrMa == null) return;

                DateTime today = Server.Time.Date;
                if (!_dayInit || today != _day) { _day = today; _dayStartEquity = Account.Equity; _dayInit = true; _halted = false; }
                double dailyPnl = Account.Equity - _dayStartEquity;
                double limit = _dayStartEquity * (DailyLossPct / 100.0);
                if (!_halted && dailyPnl <= -limit) { _halted = true; Print("HALT: {0:F2} <= -{1:F2}", dailyPnl, limit); Flatten(); return; }
                if (_halted) return;

                int i = Bars.Count - 2;
                if (i < 2) return;
                double close = Bars.ClosePrices[i];
                double high = Bars.HighPrices[i];
                double prevClose = Bars.ClosePrices[i - 1];
                double atr = _atr.Result[i];
                double rsi = _rsi.Result[i];
                if (double.IsNaN(atr) || double.IsNaN(rsi) || atr <= 0) return;

                var pos = Positions.Find(Label);
                if (pos != null) { ManageExit(pos, i, rsi); return; }

                if (!EnableTrading) return;
                if (_blocked.Contains(Server.Time.Hour)) return;

                // ATR regime gate (AegisAtrEnvironment種)
                string regime = TradeRegime.ToUpperInvariant();
                if (regime != "ANY")
                {
                    double atrMa = _atrMa.Result[i];
                    if (double.IsNaN(atrMa) || atrMa <= 0) return;
                    double ratio = atr / atrMa;
                    bool expansion = ratio >= AtrExpansionRatio && _atr.Result[i] > _atr.Result[Math.Max(0, i - 3)];
                    bool compression = ratio <= AtrCompressionRatio && _atr.Result[i] < _atr.Result[Math.Max(0, i - 3)];
                    if (regime == "EXPANSION" && !expansion) { Print("SILENT: not expansion (ratio={0:F2})", ratio); return; }
                    if (regime == "COMPRESSION" && !compression) { Print("SILENT: not compression (ratio={0:F2})", ratio); return; }
                }

                // ACD (Anti-Chop): recent range must sit within [min..max] pips
                if (i < AcdLookback + 1) return;
                double hiR = double.MinValue, loR = double.MaxValue;
                for (int j = i - AcdLookback + 1; j <= i; j++) { hiR = Math.Max(hiR, Bars.HighPrices[j]); loR = Math.Min(loR, Bars.LowPrices[j]); }
                double rangePips = (hiR - loR) / Symbol.PipSize;
                if (rangePips < AcdMinPips || rangePips > AcdMaxPips) { Print("SILENT: ACD range {0:F1} pips out of [{1}..{2}]", rangePips, AcdMinPips, AcdMaxPips); return; }

                // Structure: lower-low (downtrend) confirmation
                if (RequireLowerLow)
                {
                    if (i < 2 * StructLookback + 1) return;
                    double lowRecent = double.MaxValue, lowPrior = double.MaxValue;
                    for (int j = i - StructLookback + 1; j <= i; j++) lowRecent = Math.Min(lowRecent, Bars.LowPrices[j]);
                    for (int j = i - 2 * StructLookback + 1; j <= i - StructLookback; j++) lowPrior = Math.Min(lowPrior, Bars.LowPrices[j]);
                    if (!(lowRecent < lowPrior)) { Print("SILENT: no lower-low structure"); return; }
                }

                // Levels: recent H4 swing highs (fractal K), merged
                var levels = GetLevels(i, atr);
                if (levels.Count == 0) return;

                double tol = RetestTolAtr * atr;
                double pip = Symbol.PipSize;
                bool retest = false; double lv = 0.0;
                foreach (var L in levels)
                {
                    if (L - close < MinLevelDistPips * pip) continue;      // level must be above current (resistance)
                    if (prevClose < L && high >= L - tol && close < L) { retest = true; lv = L; break; }  // approached from below, tagged, rejected
                }
                if (!retest) return;

                // RSI quality gate + weak re-attack
                double peak = double.MinValue;
                for (int j = Math.Max(0, i - RsiPeakLookback); j <= i; j++) peak = Math.Max(peak, _rsi.Result[j]);
                if (double.IsNaN(peak)) return;
                bool band = rsi >= RsiBandMin && rsi <= RsiBandMax;
                bool peakOk = peak >= RsiPeakMin;
                bool noChase = rsi >= RsiAvoidChaseMin;
                bool falling = rsi < peak;
                if (!(band && peakOk && noChase && falling)) return;

                // bear confirmation
                if (close >= prevClose) return;

                Enter(close, atr, lv, rsi, peak);
            }
            catch (Exception ex) { Print("OnBar EXCEPTION: {0}", ex.Message); }
        }

        private List<double> GetLevels(int i, double chartAtr)
        {
            var outL = new List<double>();
            double pip = Symbol.PipSize;
            int lc = _lvBars.Count;
            if (lc < LevelLookback + LevelFractalK + 1) return outL;
            // scan H4 bars for fractal highs, newest first, up to MaxLevels, merged
            for (int c = lc - 2 - LevelFractalK; c >= lc - 1 - LevelLookback && c - LevelFractalK >= 0; c--)
            {
                double h = _lvBars.HighPrices[c];
                bool isHigh = true;
                for (int d = 1; d <= LevelFractalK; d++)
                {
                    if (_lvBars.HighPrices[c - d] >= h || _lvBars.HighPrices[c + d] > h) { isHigh = false; break; }
                }
                if (!isHigh) continue;
                bool merged = false;
                foreach (var e in outL) { if (Math.Abs(e - h) <= LevelMergePips * pip) { merged = true; break; } }
                if (merged) continue;
                outL.Add(h);
                if (outL.Count >= MaxLevels) break;
            }
            return outL;
        }

        private void Enter(double refPrice, double atr, double level, double rsi, double peak)
        {
            double pip = Symbol.PipSize; if (pip <= 0) return;
            double stopPips = (AtrStopMult * atr) / pip; if (stopPips < 1) stopPips = 1;
            double riskAmount = Account.Equity * (RiskPerTradePct / 100.0);
            double pipValue = Symbol.PipValue; if (pipValue <= 0) return;
            double units = Symbol.NormalizeVolumeInUnits(riskAmount / (stopPips * pipValue), RoundingMode.Down);
            if (units < Symbol.VolumeInUnitsMin) { Print("SKIP: units {0} < min", units); return; }

            Print("ENTRY Sell {0}: ref={1:F5} level={2:F5} atr={3:F5} stopPips={4:F1} rsi={5:F1} peak={6:F1} units={7}", Symbol.Name, refPrice, level, atr, stopPips, rsi, peak, units);
            var r = ExecuteMarketOrder(TradeType.Sell, Symbol.Name, units, Label, stopPips, 0);
            if (r == null) { Print("ENTRY FAILED: null"); return; }
            if (r.IsSuccessful) { _entryBar = Bars.Count - 2; Print("ENTRY OK units={0} entry={1}", units, (r.Position != null ? r.Position.EntryPrice : 0.0)); }
            else Print("ENTRY FAILED: {0}", r.Error);
        }

        private void ManageExit(Position pos, int i, double rsi)
        {
            int barsHeld = _entryBar >= 0 ? (i - _entryBar) : 0;
            double pips = pos.Pips;
            if (barsHeld >= EarlyDamageBars && pips < EarlyDamageMinPips) { ClosePosition(pos); Print("EXIT early-damage bars={0} pips={1:F2}", barsHeld, pips); _entryBar = -1; return; }
            if (rsi <= RsiReturnLevel) { ClosePosition(pos); Print("EXIT rsi-return rsi={0:F1} pips={1:F2}", rsi, pips); _entryBar = -1; return; }
        }

        private void Flatten()
        {
            try { if (Positions == null) return; foreach (var p in Positions.ToList()) { try { ClosePosition(p); Print("FLATTEN {0} {1}", p.SymbolName, p.Id); } catch (Exception ex) { Print("FLATTEN FAIL {0}: {1}", p.Id, ex.Message); } } }
            catch (Exception ex) { Print("FLATTEN EX {0}", ex.Message); }
        }

        private TimeFrame ParseTF(string s)
        {
            if (string.IsNullOrEmpty(s)) return TimeFrame;
            switch (s.Trim().ToUpperInvariant())
            {
                case "H1": return TimeFrame.Hour;
                case "H4": return TimeFrame.Hour4;
                case "D1": return TimeFrame.Daily;
                case "W1": return TimeFrame.Weekly;
                default: return TimeFrame;
            }
        }

        protected override void OnStop() { Print("PhronisisAegis v2 stopped. Halted={0}", _halted); }
    }
}
