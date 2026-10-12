// Aegis_Breakout_Core_v1_09aa.cs
// Breakout Core v1_09 Event Markers + Staggered Labels
// Sell-only breakout / breakdown-retest research bot with:
// - HTF breakdown bias (H4)
// - LTF breakdown retest entry (core path only)
// - Shared environment guards (session / spread / cooldown / ACD / ATR)
// - Existing exit skeleton retained as breakout-friendly base

using System;
using System.Collections.Generic;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    public enum CooldownMode { Bars, Minutes }
    public enum TakeProfitMode { FixedPips, RsiReturn, Both }
    public enum StopLossMode { Level, Atr }

    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class Aegis_Breakout_Core_v1_09a : Robot
    {
        // ============================================================
        // 1) CORE
        // ============================================================
        [Parameter("Label", DefaultValue = "Aegis_Breakout_Core", Group = "1. CORE")]
        public string BotLabel { get; set; }

        [Parameter("Volume (Lots)", DefaultValue = 0.02, MinValue = 0.01, Step = 0.01, Group = "1. CORE")]
        public double VolumeLots { get; set; }
        [Parameter("Max Spread (pips)", DefaultValue = 3.0, MinValue = 0.0, Group = "1. CORE")]
        public double MaxSpreadPips { get; set; }

        [Parameter("Max Positions", DefaultValue = 3, MinValue = 1, Group = "1. CORE")]
        public int MaxPositions { get; set; }

        [Parameter("Cooldown Bars After Entry", DefaultValue = 4, MinValue = 0, Group = "1. CORE")]
        public int CooldownBars { get; set; }

        [Parameter("Cooldown Mode", DefaultValue = CooldownMode.Bars, Group = "1. CORE")]
        public CooldownMode CooldownModeParam { get; set; }

        [Parameter("Cooldown Minutes After Entry", DefaultValue = 5, MinValue = 0, Group = "1. CORE")]
        public int CooldownMinutes { get; set; }

        // ===== PATCH PARAMETERS =====
        [Parameter("Max Trades Per Level Per Day", DefaultValue = 2, MinValue = 0, Group = "1. CORE")]
        public int MaxTradesPerLevelPerDay { get; set; }

        [Parameter("No-Profit Exit Enabled", DefaultValue = false, Group = "1. CORE")]
        public bool NoProfitExitEnabled { get; set; }

        [Parameter("No-Profit Exit Bars", DefaultValue = 4, MinValue = 1, Group = "1. CORE")]
        public int NoProfitExitBars { get; set; }

        [Parameter("No-Profit Exit Max Pips (<=)", DefaultValue = 1.8, Group = "1. CORE")]
        public double NoProfitExitMaxPips { get; set; }

        // ===== BREAKOUT INVALIDATION (v6) =====
        [Parameter("Breakout Invalidate Enabled", DefaultValue = true, Group = "1. CORE")]
        public bool BreakoutInvalidateEnabled { get; set; }

        [Parameter("Invalidate Early Window Bars (m10)", DefaultValue = 3, MinValue = 1, Group = "1. CORE")]
        public int InvalidateEarlyBars { get; set; }

        [Parameter("Invalidate Early Close Above Level (pips)", DefaultValue = 0.4, MinValue = 0.0, Group = "1. CORE")]
        public double InvalidateEarlyCloseAbovePips { get; set; }

        [Parameter("Invalidate Early Adverse Pips (0=off)", DefaultValue = 7.5, MinValue = 0.0, Group = "1. CORE")]
        public double InvalidateEarlyAdversePips { get; set; }

        [Parameter("Invalidate Late Window Bars (m10)", DefaultValue = 36, MinValue = 0, Group = "1. CORE")]
        public int InvalidateLateBars { get; set; }

        [Parameter("Invalidate Late Close Above Level (pips)", DefaultValue = 3.0, MinValue = 0.0, Group = "1. CORE")]
        public double InvalidateLateCloseAbovePips { get; set; }

        [Parameter("Invalidate Late Consecutive Closes", DefaultValue = 2, MinValue = 1, Group = "1. CORE")]
        public int InvalidateLateConsecutiveCloses { get; set; }

        [Parameter("SpeedCut Enabled", DefaultValue = true, Group = "1. CORE")]
        public bool SpeedCutEnabled { get; set; }

        [Parameter("SpeedCut Bars (m10)", DefaultValue = 8, MinValue = 1, Group = "1. CORE")]
        public int SpeedCutBars { get; set; }

        [Parameter("SpeedCut Adverse Pips", DefaultValue = 10.0, MinValue = 0.0, Group = "1. CORE")]
        public double SpeedCutAdversePips { get; set; }
        
        // ===== DAMAGE CONTROL (simple & safe) =====
        [Parameter("Early Deny Enabled", DefaultValue = true, Group = "1. CORE")]
        public bool EarlyDenyEnabled { get; set; }

        [Parameter("Early Deny Bars (m10)", DefaultValue = 3, MinValue = 1, Group = "1. CORE")]
        public int EarlyDenyBars { get; set; }

        [Parameter("Early Deny Close Above Entry (pips)", DefaultValue = 1.6, MinValue = 0.0, Group = "1. CORE")]
        public double EarlyDenyCloseAboveEntryPips { get; set; }

        [Parameter("Expiry Enabled", DefaultValue = true, Group = "1. CORE")]
        public bool ExpiryEnabled { get; set; }

        [Parameter("Expiry Bars (m10)", DefaultValue = 23, MinValue = 1, Group = "1. CORE")]
        public int ExpiryBars { get; set; }

        [Parameter("Expiry Close If Pips <= (negative)", DefaultValue = -5.5, Group = "1. CORE")]
        public double ExpiryCloseIfPipsBelow { get; set; }
        [Parameter("Expiry Require Never Reached Profit (pips)", DefaultValue = 2.4, MinValue = 0.0, Group = "1. CORE")]
        public double ExpiryNeverReachedProfitPips { get; set; }
        // ==========================================
// ======================================

        // ===========================

        // ============================================================
        // 2) SESSION (JST)
        // ============================================================
        [Parameter("Use Session Filter (JST)", DefaultValue = false, Group = "2. SESSION (JST)")]
        public bool UseSessionFilter { get; set; }

        [Parameter("Session Start Hour (JST)", DefaultValue = 9, MinValue = 0, MaxValue = 23, Group = "2. SESSION (JST)")]
        public int SessionStartHourJst { get; set; }

        [Parameter("Session End Hour (JST)", DefaultValue = 5, MinValue = 0, MaxValue = 23, Group = "2. SESSION (JST)")]
        public int SessionEndHourJst { get; set; }
        // ============================================================
        // 3) ENTRY (Breakdown Retest)
        // ============================================================
        // ============================================================

        [Parameter("HTF Bias TF", DefaultValue = "Hour4", Group = "3. BDR")]
        public TimeFrame Htf { get; set; }

        [Parameter("Use Breakdown Retest Entry", DefaultValue = true, Group = "3. BDR")]
        public bool UseBreakdownRetestEntry { get; set; }

        [Parameter("BDR Lookback Bars", DefaultValue = 12, MinValue = 6, MaxValue = 60, Step = 1, Group = "3. BDR")]
        public int BreakdownRetestLookbackBars { get; set; }

        [Parameter("BDR Use Swing Low Support", DefaultValue = true, Group = "3. BDR")]
        public bool BreakdownRetestUseSwingLowSupport { get; set; }

        [Parameter("BDR Swing Left Bars", DefaultValue = 2, MinValue = 1, MaxValue = 8, Step = 1, Group = "3. BDR")]
        public int BreakdownRetestSwingLeftBars { get; set; }

        [Parameter("BDR Swing Right Bars", DefaultValue = 2, MinValue = 1, MaxValue = 8, Step = 1, Group = "3. BDR")]
        public int BreakdownRetestSwingRightBars { get; set; }

        [Parameter("BDR Max Bars Since Break", DefaultValue = 6, MinValue = 2, MaxValue = 20, Step = 1, Group = "3. BDR")]
        public int BreakdownRetestMaxBarsSinceBreak { get; set; }

        [Parameter("BDR Min Break (pips)", DefaultValue = 1.5, MinValue = 0.0, Step = 0.1, Group = "3. BDR")]
        public double BreakdownRetestMinBreakPips { get; set; }

        [Parameter("BDR Retest Tolerance (pips)", DefaultValue = 2.0, MinValue = 0.0, Step = 0.1, Group = "3. BDR")]
        public double BreakdownRetestTolerancePips { get; set; }

        [Parameter("BDR Max Close Above Level (pips)", DefaultValue = 0.8, MinValue = 0.0, Step = 0.1, Group = "3. BDR")]
        public double BreakdownRetestMaxCloseAboveLevelPips { get; set; }

        [Parameter("BDR Max High Above Level (pips)", DefaultValue = 2.0, MinValue = 0.0, Step = 0.1, Group = "3. BDR")]
        public double BreakdownRetestMaxHighAboveLevelPips { get; set; }

        [Parameter("BDR Break Hold Bars", DefaultValue = 1, MinValue = 0, MaxValue = 6, Step = 1, Group = "3. BDR")]
        public int BreakdownRetestHoldBars { get; set; }

        [Parameter("BDR Require Break Close", DefaultValue = true, Group = "3. BDR")]
        public bool BreakdownRetestRequireBreakClose { get; set; }

        [Parameter("BDR Break Min Body (pips)", DefaultValue = 1.0, MinValue = 0.0, Step = 0.1, Group = "3. BDR")]
        public double BreakdownRetestBreakMinBodyPips { get; set; }

        [Parameter("BDR Break Require Lower Half Close", DefaultValue = true, Group = "3. BDR")]
        public bool BreakdownRetestBreakRequireLowerHalfClose { get; set; }

        [Parameter("BDR Require Bear Bar", DefaultValue = true, Group = "3. BDR")]
        public bool BreakdownRetestRequireBearBar { get; set; }

        [Parameter("BDR Bear Min Body (pips)", DefaultValue = 0.5, MinValue = 0.0, Step = 0.1, Group = "3. BDR")]
        public double BreakdownRetestBearMinBodyPips { get; set; }

        [Parameter("BDR RSI Min", DefaultValue = 45.0, MinValue = 0.0, MaxValue = 100.0, Step = 0.5, Group = "3. BDR")]
        public double BreakdownRetestMinRsi { get; set; }

        [Parameter("BDR RSI Max", DefaultValue = 68.0, MinValue = 0.0, MaxValue = 100.0, Step = 0.5, Group = "3. BDR")]
        public double BreakdownRetestMaxRsi { get; set; }

        [Parameter("Use HTF Breakdown Bias", DefaultValue = true, Group = "3. BDR")]
        public bool UseHtfBreakdownBiasForBdr { get; set; }

        [Parameter("HTF Breakdown Lookback Bars", DefaultValue = 6, MinValue = 3, MaxValue = 40, Step = 1, Group = "3. BDR")]
        public int HtfBreakdownLookbackBars { get; set; }

        [Parameter("HTF Breakdown Min Break (pips)", DefaultValue = 3.0, MinValue = 0.0, Step = 0.1, Group = "3. BDR")]
        public double HtfBreakdownMinBreakPips { get; set; }

        [Parameter("HTF Bias Valid Bars", DefaultValue = 6, MinValue = 1, MaxValue = 20, Step = 1, Group = "3. BDR")]
        public int HtfBreakdownBiasValidBars { get; set; }

        [Parameter("HTF Breakdown Require Close", DefaultValue = true, Group = "3. BDR")]
        public bool HtfBreakdownRequireClose { get; set; }

        [Parameter("BDR Max Distance To HTF Support (pips, 0=off)", DefaultValue = 8.0, MinValue = 0.0, Step = 0.1, Group = "3. BDR")]
        public double BreakdownRetestMaxDistanceToHtfSupportPips { get; set; }

        [Parameter("HTF Bias Use Swing Low Support", DefaultValue = true, Group = "3. BDR")]
        public bool HtfBreakdownUseSwingLowSupport { get; set; }

        [Parameter("HTF Swing Left Bars", DefaultValue = 2, MinValue = 1, MaxValue = 8, Step = 1, Group = "3. BDR")]
        public int HtfBreakdownSwingLeftBars { get; set; }

        [Parameter("HTF Swing Right Bars", DefaultValue = 2, MinValue = 1, MaxValue = 8, Step = 1, Group = "3. BDR")]
        public int HtfBreakdownSwingRightBars { get; set; }

        [Parameter("BDR Direct HTF Retest Mode", DefaultValue = true, Group = "3. BDR")]
        public bool BreakdownRetestDirectHtfRetestMode { get; set; }

        [Parameter("BDR HTF Support Zone Width (pips)", DefaultValue = 1.5, MinValue = 0.0, Step = 0.1, Group = "3. BDR")]
        public double BreakdownRetestHtfZoneWidthPips { get; set; }

        [Parameter("BDR Anchor To HTF Support", DefaultValue = true, Group = "3. BDR")]
        public bool BreakdownRetestAnchorToHtfSupport { get; set; }

        [Parameter("BDR Require LTF Break After HTF Break", DefaultValue = true, Group = "3. BDR")]
        public bool BreakdownRetestRequireLtfBreakAfterHtfBreak { get; set; }

        [Parameter("BDR Require Impulse After Break", DefaultValue = true, Group = "3. BDR")]
        public bool BreakdownRetestRequireImpulseAfterBreak { get; set; }

        [Parameter("BDR Break Impulse Min Pips", DefaultValue = 4.0, MinValue = 0.0, Step = 0.1, Group = "3. BDR")]
        public double BreakdownRetestBreakImpulseMinPips { get; set; }

        [Parameter("BDR Break Impulse Max Bars", DefaultValue = 3, MinValue = 1, MaxValue = 12, Step = 1, Group = "3. BDR")]
        public int BreakdownRetestBreakImpulseMaxBars { get; set; }

        [Parameter("BDR Log Lower High Context", DefaultValue = true, Group = "3. BDR")]
        public bool BreakdownRetestLogLowerHigh { get; set; }

        [Parameter("BDR LH Lookback Bars", DefaultValue = 48, MinValue = 10, MaxValue = 200, Step = 1, Group = "3. BDR")]
        public int BreakdownRetestLowerHighLookbackBars { get; set; }

        [Parameter("BDR LH Swing Left Bars", DefaultValue = 2, MinValue = 1, MaxValue = 8, Step = 1, Group = "3. BDR")]
        public int BreakdownRetestLowerHighSwingLeftBars { get; set; }

        [Parameter("BDR LH Swing Right Bars", DefaultValue = 2, MinValue = 1, MaxValue = 8, Step = 1, Group = "3. BDR")]
        public int BreakdownRetestLowerHighSwingRightBars { get; set; }

        [Parameter("BDR LH Min Gap (pips)", DefaultValue = 1.0, MinValue = 0.0, Step = 0.1, Group = "3. BDR")]
        public double BreakdownRetestLowerHighMinGapPips { get; set; }

        [Parameter("Use Volatility Adaptive Thresholds", DefaultValue = true, Group = "3. BDR")]
        public bool UseVolatilityAdaptiveThresholds { get; set; }

        [Parameter("Adaptive ATR Period", DefaultValue = 14, MinValue = 2, MaxValue = 100, Step = 1, Group = "3. BDR")]
        public int AdaptiveAtrPeriod { get; set; }

        [Parameter("Impulse ATR Mult", DefaultValue = 0.8, MinValue = 0.0, Step = 0.05, Group = "3. BDR")]
        public double BreakdownRetestBreakImpulseAtrMult { get; set; }

        [Parameter("Retest Tolerance ATR Mult", DefaultValue = 0.35, MinValue = 0.0, Step = 0.05, Group = "3. BDR")]
        public double BreakdownRetestToleranceAtrMult { get; set; }

        [Parameter("HTF Zone Width ATR Mult", DefaultValue = 0.15, MinValue = 0.0, Step = 0.01, Group = "3. BDR")]
        public double BreakdownRetestHtfZoneWidthAtrMult { get; set; }

        [Parameter("Max High Above Level ATR Mult", DefaultValue = 0.45, MinValue = 0.0, Step = 0.05, Group = "3. BDR")]
        public double BreakdownRetestMaxHighAboveLevelAtrMult { get; set; }

// ============================================================
        // 4A) RSI
        // ============================================================
        [Parameter("RSI Period", DefaultValue = 12, MinValue = 2, Group = "4A. RSI")]
        public int RsiPeriod { get; set; }

        // ============================================================
        // 4) ACD (Anti-Chop Detector)
        // ============================================================
        [Parameter("Use ACD", DefaultValue = false, Group = "4. ACD")]
        public bool UseAcd { get; set; }

        [Parameter("ACD TF", DefaultValue = "Hour", Group = "4. ACD")]
        public TimeFrame AcdTf { get; set; }

        [Parameter("ACD Window Bars", DefaultValue = 20, MinValue = 5, Group = "4. ACD")]
        public int AcdWindowBars { get; set; }

        [Parameter("ACD Min Range (pips)", DefaultValue = 4.8, MinValue = 0.0, Group = "4. ACD")]
        public double AcdMinRangePips { get; set; }

        [Parameter("ACD Max Range (pips)", DefaultValue = 100.0, MinValue = 0.0, Group = "4. ACD")]
        public double AcdMaxRangePips { get; set; }

        [Parameter("Draw ACD Box", DefaultValue = true, Group = "4. ACD")]
        public bool DrawAcdBox { get; set; }

                // ============================================================
        // 8) RISK / EXIT
        // ============================================================
        [Parameter("TP Mode", DefaultValue = TakeProfitMode.FixedPips, Group = "5. EXIT")]
        public TakeProfitMode TpMode { get; set; }

        [Parameter("Fixed TP (pips)", DefaultValue = 10.5, MinValue = 0.0, Group = "5. EXIT")]
        public double FixedTpPips { get; set; }

        [Parameter("SL Mode", DefaultValue = StopLossMode.Atr, Group = "5. EXIT")]
        public StopLossMode SlMode { get; set; }

        [Parameter("SL Above Level (pips)", DefaultValue = 9.0, MinValue = 0.0, Group = "5. EXIT")]
        public double SlAboveLevelPips { get; set; }

        [Parameter("Hard Min SL (pips)", DefaultValue = 7.0, MinValue = 0.0, Group = "5. EXIT")]
        public double HardMinSlPips { get; set; }

        [Parameter("Hard Max SL (pips, 0=off)", DefaultValue = 0.0, MinValue = 0.0, Group = "5. EXIT")]
        public double HardMaxSlPips { get; set; }

        // SL ATR
        [Parameter("SL ATR TF", DefaultValue = "Hour", Group = "5. EXIT")]
        public TimeFrame SlAtrTf { get; set; }

        [Parameter("SL ATR Period", DefaultValue = 11, MinValue = 2, Group = "5. EXIT")]
        public int SlAtrPeriod { get; set; }

        [Parameter("SL ATR Multiplier", DefaultValue = 1.8, MinValue = 0.1, Group = "5. EXIT")]
        public double SlAtrMultiplier { get; set; }

        [Parameter("SL ATR Min (pips, 0=off)", DefaultValue = 0.0, MinValue = 0.0, Group = "5. EXIT")]
        public double SlAtrMinPips { get; set; }

        [Parameter("SL ATR Max (pips, 0=off)", DefaultValue = 0.0, MinValue = 0.0, Group = "5. EXIT")]
        public double SlAtrMaxPips { get; set; }

        // RSI Return Exit
        [Parameter("RSI Exit Level", DefaultValue = 40.0, Group = "5. EXIT")]
        public double RsiExitLevel { get; set; }

        [Parameter("RSI Exit Min Hold Bars", DefaultValue = 4, MinValue = 0, Group = "5. EXIT")]
        public int RsiExitMinHoldBars { get; set; }

        [Parameter("RSI Exit Min Profit (pips)", DefaultValue = 4.8, MinValue = 0.0, Group = "5. EXIT")]
        public double RsiExitMinProfitPips { get; set; }

        // Trailing
        [Parameter("Use Trailing Remainder", DefaultValue = true, Group = "5. EXIT")]
        public bool UseTrailingRemainder { get; set; }

        [Parameter("Trail Start (pips)", DefaultValue = 9.0, MinValue = 0.0, Group = "5. EXIT")]
        public double TrailStartPips { get; set; }

        [Parameter("Trail Step (pips)", DefaultValue = 3.0, MinValue = 0.1, Group = "5. EXIT")]
        public double TrailStepPips { get; set; }

        // Validation Exit (BDR only by default)
        [Parameter("Validation Exit Enabled", DefaultValue = false, Group = "5. EXIT")]
        public bool ValidationExitEnabled { get; set; }

        [Parameter("Validation Exit Retest Only", DefaultValue = true, Group = "5. EXIT")]
        public bool ValidationExitRetestOnly { get; set; }

        [Parameter("Validation Exit Bars (m10)", DefaultValue = 3, MinValue = 1, MaxValue = 8, Group = "5. EXIT")]
        public int ValidationExitBars { get; set; }

        [Parameter("Validation Exit Window Bars", DefaultValue = 2, MinValue = 1, MaxValue = 3, Group = "5. EXIT")]
        public int ValidationExitWindowBars { get; set; }

        [Parameter("Validation Min Favorable Pips", DefaultValue = 1.5, MinValue = 0.0, Step = 0.1, Group = "5. EXIT")]
        public double ValidationMinFavorablePips { get; set; }

        [Parameter("Validation Close Above Entry (pips)", DefaultValue = 0.3, MinValue = 0.0, Step = 0.1, Group = "5. EXIT")]
        public double ValidationCloseAboveEntryPips { get; set; }

        [Parameter("Validation High Above Entry (pips)", DefaultValue = 1.0, MinValue = 0.0, Step = 0.1, Group = "5. EXIT")]
        public double ValidationHighAboveEntryPips { get; set; }

        // ============================================================
        // 9) DIAG / VIS
        // ============================================================
        [Parameter("Debug Print Reasons", DefaultValue = false, Group = "6. DIAG")]
        public bool DebugPrintReasons { get; set; }

        
        [Parameter("Log Skip Reasons", DefaultValue = true, Group = "6. DIAG")]
        public bool LogSkipReasons { get; set; }

        [Parameter("Log Entry Diagnostics", DefaultValue = false, Group = "6. DIAG")]
        public bool LogEntryDiagnostics { get; set; }

        [Parameter("Draw Entry Arrows", DefaultValue = true, Group = "6. DIAG")]
        public bool DrawEntryArrows { get; set; }

        [Parameter("Draw Entry Labels", DefaultValue = true, Group = "6. DIAG")]
        public bool DrawEntryLabels { get; set; }

        [Parameter("Draw Event Markers", DefaultValue = true, Group = "6. DIAG")]
        public bool DrawEventMarkers { get; set; }

        [Parameter("Entry Label Cluster Bars", DefaultValue = 12, MinValue = 1, Group = "6. DIAG")]
        public int EntryLabelClusterBars { get; set; }

        [Parameter("Entry Label Step (pips)", DefaultValue = 2.4, MinValue = 0.5, Step = 0.1, Group = "6. DIAG")]
        public double EntryLabelStepPips { get; set; }

        [Parameter("Show Live State Panel", DefaultValue = false, Group = "6. DIAG")]
        public bool ShowLiveStatePanel { get; set; }

        // ============================================================
        // INTERNALS
        // ============================================================
        private const int JST_OFFSET_HOURS = 9;
        private double Pip { get { return Symbol.PipSize; } }

        private RelativeStrengthIndex _rsi;
        private Bars _htfBars;
        private Bars _acdBars;

        private double _acdUpper = double.NaN;
        private double _acdLower = double.NaN;

        private Bars _slAtrBars;
        private AverageTrueRange _slAtr;
        private AverageTrueRange _bdrAtr;
        private AverageTrueRange _htfAtr;

        private int _lastEntryBar = -999999;
        private DateTime _lastEntryTime = DateTime.MinValue;

        // Breakout invalidation tracking: positionId -> entryLevelPrice
        private readonly Dictionary<long, double> _entryLevelByPosId = new Dictionary<long, double>();
        private readonly Dictionary<long, double> _maxProfitPipsByPosId = new Dictionary<long, double>();

        // Late invalidation: consecutive closes above level (positionId -> count)
        private readonly Dictionary<long, int> _aboveCloseCountByPosId = new Dictionary<long, int>();

        private DateTime _currentJstDate = DateTime.MinValue;
        private readonly Dictionary<long, int> _levelTradesToday = new Dictionary<long, int>();

        
        private enum CloseReason
        {
            Unknown,
            RsiExit,
            Trailing,
            FixedTp,
            SpeedCut,
            InvalidateEarly,
            InvalidateLate,
            ValidationExit
        }
        enum EntryKind
        {
            Unknown,
            BreakdownRetest
        }

        // position tracking (positionId -> level used in entry)
        private readonly Dictionary<long, long> _posIdToLevelKey = new Dictionary<long, long>();
        private readonly Dictionary<long, double> _posIdToLevelPrice = new Dictionary<long, double>();
        private readonly Dictionary<long, string> _posIdToLevelTag = new Dictionary<long, string>();
        private readonly Dictionary<long, int> _posIdEntryBar = new Dictionary<long, int>();
        private readonly Dictionary<long, DateTime> _posIdToEntryTime = new Dictionary<long, DateTime>();
        private readonly Dictionary<long, CloseReason> _posIdPendingCloseReason = new Dictionary<long, CloseReason>();
        private readonly Dictionary<long, EntryKind> _entryKindByPosId = new Dictionary<long, EntryKind>();
        private string EffectiveBotLabel => string.IsNullOrWhiteSpace(BotLabel) ? "Aegis_Breakout_Core" : BotLabel;

        // Pending entry diagnostics (set by entry logic just before order placement)
        private double _pendingEntryImpulsePips = double.NaN;
        private double _pendingEntryRetestDepthPips = double.NaN;
        private double _pendingEntryHtfDistancePips = double.NaN;
        private int _pendingEntryLowerHighState = -1;

        // Live diagnostic panel state
        private bool _diagHtfBias;
        private bool _diagBreakFound;
        private bool _diagImpulseOk;
        private bool _diagRetestOk;
        private bool _diagTriggerOk;
        private bool _diagEntryOk;
        private readonly List<int> _entryLabelHistory = new List<int>();

        private int BarsSinceEntryUtc(DateTime entryTime)
        {
            var idx = Bars.OpenTimes.GetIndexByTime(entryTime);
            if (idx < 0) return int.MaxValue;
            var lastClosedIndex = Bars.Count - 2;
            return Math.Max(0, lastClosedIndex - idx);
        }

        private void ResetDailyCaches()
        {
            DateTime jst = Server.Time.AddHours(JST_OFFSET_HOURS);
            DateTime today = jst.Date;

            if (_currentJstDate != today)
            {
                _currentJstDate = today;
                _levelTradesToday.Clear();
            }
        }

        private long LevelKey(double levelPrice)
        {
            return (long)Math.Round(levelPrice / Pip);
        }

        private int GetTradesCountTodayForLevel(double levelPrice)
        {
            int n;
            return _levelTradesToday.TryGetValue(LevelKey(levelPrice), out n) ? n : 0;
        }

        private void MarkTradeTodayForLevel(double levelPrice)
        {
            long k = LevelKey(levelPrice);
            int n;
            if (_levelTradesToday.TryGetValue(k, out n))
                _levelTradesToday[k] = n + 1;
            else
                _levelTradesToday[k] = 1;
        }

        

        private void UnmarkTradeTodayForLevel(double levelPrice)
        {
            long k = LevelKey(levelPrice);
            int n;
            if (_levelTradesToday.TryGetValue(k, out n))
            {
                n = Math.Max(0, n - 1);
                if (n == 0) _levelTradesToday.Remove(k);
                else _levelTradesToday[k] = n;
            }
        }
        private double GetBdrAtrPips(int barIndex)
        {
            if (_bdrAtr == null || _bdrAtr.Result == null || barIndex < 0 || barIndex >= _bdrAtr.Result.Count)
                return 0.0;
            return _bdrAtr.Result[barIndex] / Pip;
        }

        private double GetHtfAtrPips(int barIndex)
        {
            if (_htfAtr == null || _htfAtr.Result == null || barIndex < 0 || barIndex >= _htfAtr.Result.Count)
                return 0.0;
            return _htfAtr.Result[barIndex] / Pip;
        }

        private double GetEffectiveBdrImpulseMinPips(int barIndex)
        {
            double floor = Math.Max(0.0, BreakdownRetestBreakImpulseMinPips);
            if (!UseVolatilityAdaptiveThresholds)
                return floor;
            double adaptive = GetBdrAtrPips(barIndex) * Math.Max(0.0, BreakdownRetestBreakImpulseAtrMult);
            return Math.Max(floor, adaptive);
        }

        private double GetEffectiveBdrRetestTolerancePips(int barIndex)
        {
            double floor = Math.Max(0.0, BreakdownRetestTolerancePips);
            if (!UseVolatilityAdaptiveThresholds)
                return floor;
            double adaptive = GetBdrAtrPips(barIndex) * Math.Max(0.0, BreakdownRetestToleranceAtrMult);
            return Math.Max(floor, adaptive);
        }

        private double GetEffectiveBdrMaxHighAboveLevelPips(int barIndex)
        {
            double floor = Math.Max(0.0, BreakdownRetestMaxHighAboveLevelPips);
            if (!UseVolatilityAdaptiveThresholds)
                return floor;
            double adaptive = GetBdrAtrPips(barIndex) * Math.Max(0.0, BreakdownRetestMaxHighAboveLevelAtrMult);
            return Math.Max(floor, adaptive);
        }

        private double GetEffectiveHtfZoneWidthPips(int htfBarIndex)
        {
            double floor = Math.Max(0.0, BreakdownRetestHtfZoneWidthPips);
            if (!UseVolatilityAdaptiveThresholds)
                return floor;
            double adaptive = GetHtfAtrPips(htfBarIndex) * Math.Max(0.0, BreakdownRetestHtfZoneWidthAtrMult);
            return Math.Max(floor, adaptive);
        }

protected override void OnStart()
        {
            _rsi = Indicators.RelativeStrengthIndex(Bars.ClosePrices, RsiPeriod);

            _htfBars = MarketData.GetBars(Htf, SymbolName);
            _acdBars = MarketData.GetBars(AcdTf, SymbolName);

            _slAtrBars = MarketData.GetBars(SlAtrTf, SymbolName);
            _slAtr = Indicators.AverageTrueRange(_slAtrBars, SlAtrPeriod, MovingAverageType.Exponential);
            _bdrAtr = Indicators.AverageTrueRange(Bars, AdaptiveAtrPeriod, MovingAverageType.Exponential);
            _htfAtr = Indicators.AverageTrueRange(_htfBars, AdaptiveAtrPeriod, MovingAverageType.Exponential);

            // Safety guards: keep thresholds in sensible ranges
            if (EarlyDenyBars < 1) EarlyDenyBars = 1;
            // Expect a negative threshold (e.g., -4). If user enters positive, auto-fix to negative.
        }

        protected override void OnBar()
        {
            int lastClosed = Bars.Count - 2;

            ResetLiveDiagnostics();
            ResetDailyCaches();

            if (lastClosed < 10)
                return;

            // keep HTF fresh
            // manage open positions (trail / RSI exit)
            ManageOpenPositions();

            // entry
            TrySell(lastClosed);

            UpdateLiveStatePanel();
        }

private void TrySell(int lastClosed)
        {
            if (Positions.FindAll(EffectiveBotLabel, SymbolName, TradeType.Sell).Length >= MaxPositions)
                return;

            if (CooldownModeParam == CooldownMode.Bars)
            {
                if (Bars.Count - 1 - _lastEntryBar <= CooldownBars){ Skip("Cooldown bars"); return; }
            }
            else
            {
                if (_lastEntryTime != DateTime.MinValue && (Server.Time - _lastEntryTime).TotalMinutes < CooldownMinutes){ Skip("Cooldown minutes"); return; }
            }

            if (!IsSessionOk()){ Skip("Session filter"); return; }

            if (Symbol.Spread / Symbol.PipSize > MaxSpreadPips){ Skip("Spread too high"); return; }

            if (TrySellBreakdownRetestEntry(lastClosed))
                return;

            Skip("No breakout retest setup");
        }

        private bool TryGetHtfSupport(int breakIdx, int lookback, out double support)
        {
            support = double.MaxValue;

            int start = Math.Max(0, breakIdx - lookback);
            int end = breakIdx - 1;
            if (end < start)
                return false;

            if (!HtfBreakdownUseSwingLowSupport)
            {
                for (int i = start; i <= end; i++)
                {
                    if (_htfBars.LowPrices[i] < support)
                        support = _htfBars.LowPrices[i];
                }
                return support != double.MaxValue;
            }

            int left = Math.Max(1, HtfBreakdownSwingLeftBars);
            int right = Math.Max(1, HtfBreakdownSwingRightBars);
            int swingStart = Math.Max(start + left, start);
            int swingEnd = Math.Min(end - right, end);

            for (int i = swingEnd; i >= swingStart; i--)
            {
                double candidate = _htfBars.LowPrices[i];
                bool isSwing = true;

                for (int j = i - left; j <= i + right; j++)
                {
                    if (j == i)
                        continue;
                    if (j < start || j > end)
                        continue;
                    if (_htfBars.LowPrices[j] <= candidate)
                    {
                        isSwing = false;
                        break;
                    }
                }

                if (isSwing)
                {
                    support = candidate;
                    return true;
                }
            }

            return false;
        }

        private bool TryFindRecentLtfBreakAgainstSupport(int lastClosed, double support, DateTime htfBreakTime, double minBreak, int maxBarsSinceBreak, out int breakIdx)
        {
            breakIdx = -1;
            int start = Math.Max(0, lastClosed - Math.Max(2, maxBarsSinceBreak));

            for (int i = lastClosed - 1; i >= start; i--)
            {
                if (BreakdownRetestRequireLtfBreakAfterHtfBreak && htfBreakTime != DateTime.MinValue && Bars.OpenTimes[i] < htfBreakTime)
                    continue;

                bool brokeDown = BreakdownRetestRequireBreakClose
                    ? Bars.ClosePrices[i] <= support - minBreak
                    : (Bars.LowPrices[i] <= support - minBreak || Bars.ClosePrices[i] <= support - minBreak);

                if (brokeDown)
                {
                    breakIdx = i;
                    return true;
                }
            }

            return false;
        }

        private bool HasImpulseAfterBreak(int breakIdx, int lastClosed, double support)
        {
            if (!BreakdownRetestRequireImpulseAfterBreak)
                return true;

            int maxBars = Math.Max(1, BreakdownRetestBreakImpulseMaxBars);
            double minImpulse = BreakdownRetestBreakImpulseMinPips * Pip;
            int end = Math.Min(lastClosed, breakIdx + maxBars);
            double bestDistance = 0.0;

            for (int i = breakIdx; i <= end; i++)
            {
                double distance = (support - Bars.LowPrices[i]);
                if (distance > bestDistance)
                    bestDistance = distance;
            }

            if (bestDistance >= minImpulse)
                return true;

            if (DebugPrintReasons)
                Skip("BDR impulse too small");

            return false;
        }

        private bool IsHtfBreakdownBiasOk(out double brokenSupport, out int breakIdx)
        {
            brokenSupport = double.NaN;
            breakIdx = -1;

            if (!UseHtfBreakdownBiasForBdr)
                return true;

            if (_htfBars == null)
                _htfBars = MarketData.GetBars(Htf, SymbolName);

            if (_htfBars == null || _htfBars.Count < 20)
                return false;

            int last = _htfBars.Count - 2;
            int lookback = Math.Max(3, HtfBreakdownLookbackBars);
            int validBars = Math.Max(1, HtfBreakdownBiasValidBars);
            double minBreak = HtfBreakdownMinBreakPips * Pip;

            int startBreak = Math.Max(lookback, last - validBars + 1);
            for (int i = last; i >= startBreak; i--)
            {
                double support;
                if (!TryGetHtfSupport(i, lookback, out support))
                    continue;

                bool broke = HtfBreakdownRequireClose
                    ? _htfBars.ClosePrices[i] <= support - minBreak
                    : (_htfBars.ClosePrices[i] <= support - minBreak || _htfBars.LowPrices[i] <= support - minBreak);

                if (!broke)
                    continue;

                brokenSupport = support;
                breakIdx = i;
                return true;
            }

            return false;
        }

        private bool TryGetBdrSupport(int breakIdx, int lookback, out double support)
        {
            support = double.MaxValue;

            int start = Math.Max(0, breakIdx - lookback);
            int end = breakIdx - 1;
            if (end < start)
                return false;

            if (!BreakdownRetestUseSwingLowSupport)
            {
                for (int i = start; i <= end; i++)
                {
                    if (Bars.LowPrices[i] < support)
                        support = Bars.LowPrices[i];
                }
                return support != double.MaxValue;
            }

            int left = Math.Max(1, BreakdownRetestSwingLeftBars);
            int right = Math.Max(1, BreakdownRetestSwingRightBars);
            int swingStart = Math.Max(start + left, start);
            int swingEnd = Math.Min(end - right, end);

            for (int i = swingEnd; i >= swingStart; i--)
            {
                double candidate = Bars.LowPrices[i];
                bool isSwing = true;

                for (int j = i - left; j <= i + right; j++)
                {
                    if (j == i)
                        continue;
                    if (j < start || j > end)
                        continue;
                    if (Bars.LowPrices[j] <= candidate)
                    {
                        isSwing = false;
                        break;
                    }
                }

                if (isSwing)
                {
                    support = candidate;
                    return true;
                }
            }

            // Fallback: if no confirmed swing low exists, do not force a weak local minimum.
            return false;
        }

        private bool TryGetRecentSwingHighs(int end, int lookback, int left, int right, out double latestHigh, out double previousHigh)
        {
            latestHigh = double.NaN;
            previousHigh = double.NaN;

            int start = Math.Max(0, end - Math.Max(10, lookback) + 1);
            left = Math.Max(1, left);
            right = Math.Max(1, right);

            int swingStart = Math.Max(start + left, start);
            int swingEnd = Math.Min(end - right, end);
            int found = 0;

            for (int i = swingEnd; i >= swingStart; i--)
            {
                double candidate = Bars.HighPrices[i];
                bool isSwing = true;

                for (int j = i - left; j <= i + right; j++)
                {
                    if (j == i)
                        continue;
                    if (j < start || j > end)
                        continue;
                    if (Bars.HighPrices[j] >= candidate)
                    {
                        isSwing = false;
                        break;
                    }
                }

                if (!isSwing)
                    continue;

                if (found == 0)
                {
                    latestHigh = candidate;
                    found = 1;
                }
                else
                {
                    previousHigh = candidate;
                    return true;
                }
            }

            return false;
        }

        private string GetLowerHighContextTag(int end)
        {
            if (!BreakdownRetestLogLowerHigh)
                return string.Empty;

            double latestHigh;
            double previousHigh;
            bool ok = TryGetRecentSwingHighs(
                end,
                BreakdownRetestLowerHighLookbackBars,
                BreakdownRetestLowerHighSwingLeftBars,
                BreakdownRetestLowerHighSwingRightBars,
                out latestHigh,
                out previousHigh);

            if (!ok)
                return " LH=NA";

            double gapPips = (previousHigh - latestHigh) / Pip;
            bool isLowerHigh = gapPips >= BreakdownRetestLowerHighMinGapPips;

            return string.Format(" LH={0} lhGap={1:F1}", isLowerHigh ? 1 : 0, gapPips);
        }

        private int ParseLowerHighState(string lhTag)
        {
            if (string.IsNullOrWhiteSpace(lhTag))
                return -1;
            if (lhTag.Contains("LH=1"))
                return 1;
            if (lhTag.Contains("LH=0"))
                return 0;
            return -1;
        }

        private double GetBestImpulseDistancePips(int breakIdx, int lastClosed, double support)
        {
            int impulseIdx;
            double bestDistance;
            GetBestImpulseInfo(breakIdx, lastClosed, support, out impulseIdx, out bestDistance);
            return bestDistance;
        }

        private void GetBestImpulseInfo(int breakIdx, int lastClosed, double support, out int impulseIdx, out double bestDistancePips)
        {
            int maxBars = Math.Max(1, BreakdownRetestBreakImpulseMaxBars);
            int end = Math.Min(lastClosed, breakIdx + maxBars);
            impulseIdx = breakIdx;
            bestDistancePips = 0.0;

            for (int i = breakIdx; i <= end; i++)
            {
                double distance = (support - Bars.LowPrices[i]) / Pip;
                if (distance > bestDistancePips)
                {
                    bestDistancePips = distance;
                    impulseIdx = i;
                }
            }

            bestDistancePips = Math.Max(0.0, bestDistancePips);
        }

        private bool TrySellBreakdownRetestEntry(int lastClosed)
        {
            if (!UseBreakdownRetestEntry)
                return false;

            if (_rsi == null)
                return false;

            if (!IsAcdOk())
            {
                Skip("BDR ACD gate");
                return false;
            }

            double htfBrokenSupport;
            int htfBreakIdx;
            if (!IsHtfBreakdownBiasOk(out htfBrokenSupport, out htfBreakIdx))
            {
                Skip("BDR HTF breakdown bias");
                return false;
            }
            _diagHtfBias = true;

            int lookback = Math.Max(6, BreakdownRetestLookbackBars);
            int maxBarsSinceBreak = Math.Max(2, BreakdownRetestMaxBarsSinceBreak);

            if (lastClosed < lookback + maxBarsSinceBreak + 2)
                return false;

            double effectiveRetestTolerancePips = GetEffectiveBdrRetestTolerancePips(lastClosed);
            double effectiveMaxHighAbovePips = GetEffectiveBdrMaxHighAboveLevelPips(lastClosed);
            double tol = effectiveRetestTolerancePips * Pip;
            double minBreak = BreakdownRetestMinBreakPips * Pip;
            double maxCloseAbove = BreakdownRetestMaxCloseAboveLevelPips * Pip;
            double maxHighAbove = effectiveMaxHighAbovePips * Pip;
            int holdBars = Math.Max(0, BreakdownRetestHoldBars);

            double rsiNow = _rsi.Result[lastClosed];
            if (rsiNow < BreakdownRetestMinRsi || rsiNow > BreakdownRetestMaxRsi)
            {
                Skip("BDR RSI range");
                return false;
            }

            if (BreakdownRetestRequireBearBar && !IsBearBar(lastClosed))
            {
                Skip("BDR bear bar required");
                return false;
            }
            _diagTriggerOk = true;

            double bodyPips = Math.Abs(Bars.OpenPrices[lastClosed] - Bars.ClosePrices[lastClosed]) / Pip;
            if (bodyPips < BreakdownRetestBearMinBodyPips)
            {
                Skip("BDR bear body too small");
                return false;
            }

            string lhTag = GetLowerHighContextTag(lastClosed);

            DateTime htfBreakTime = (UseHtfBreakdownBiasForBdr && htfBreakIdx >= 0 && _htfBars != null && htfBreakIdx < _htfBars.Count)
                ? _htfBars.OpenTimes[htfBreakIdx]
                : DateTime.MinValue;

            // HTF-anchored direct retest mode: use the broken HTF support itself as the reference level,
            // and only require a recent LTF close-break after the HTF break. M10 is used for timing, not for redefining support.
            if (UseHtfBreakdownBiasForBdr && BreakdownRetestAnchorToHtfSupport && BreakdownRetestDirectHtfRetestMode && !double.IsNaN(htfBrokenSupport))
            {
                double support = htfBrokenSupport;
                double effectiveHtfZoneWidthPips = GetEffectiveHtfZoneWidthPips(htfBreakIdx);
                double zoneWidth = effectiveHtfZoneWidthPips * Pip;

                int breakIdx;
                if (!TryFindRecentLtfBreakAgainstSupport(lastClosed, support, htfBreakTime, minBreak, maxBarsSinceBreak, out breakIdx))
                {
                    Skip("BDR no recent LTF break against HTF support");
                    return false;
                }
                _diagBreakFound = true;

                double breakOpen = Bars.OpenPrices[breakIdx];
                double breakClose = Bars.ClosePrices[breakIdx];
                double breakHigh = Bars.HighPrices[breakIdx];
                double breakLow = Bars.LowPrices[breakIdx];
                double breakBodyPips = Math.Abs(breakOpen - breakClose) / Pip;

                if (breakClose >= breakOpen)
                {
                    Skip("BDR break bar not bearish");
                    return false;
                }

                if (breakBodyPips < BreakdownRetestBreakMinBodyPips)
                {
                    Skip("BDR break body too small");
                    return false;
                }

                if (BreakdownRetestBreakRequireLowerHalfClose)
                {
                    double breakRange = breakHigh - breakLow;
                    if (breakRange > 0)
                    {
                        double breakClosePos = (breakClose - breakLow) / breakRange;
                        if (breakClosePos > 0.5)
                        {
                            Skip("BDR break close not in lower half");
                            return false;
                        }
                    }
                }

                if (lastClosed - breakIdx < holdBars)
                {
                    Skip("BDR hold bars not reached");
                    return false;
                }

                bool holdOk = true;
                for (int k = breakIdx; k <= lastClosed - 1; k++)
                {
                    if (Bars.ClosePrices[k] > support + maxCloseAbove)
                    {
                        holdOk = false;
                        break;
                    }
                    if (Bars.HighPrices[k] > support + maxHighAbove)
                    {
                        holdOk = false;
                        break;
                    }
                }
                if (!holdOk)
                {
                    Skip("BDR break hold failed");
                    return false;
                }

                if (!HasImpulseAfterBreak(breakIdx, lastClosed, support))
                    return false;
                _diagImpulseOk = true;

                bool retested = Bars.HighPrices[lastClosed] >= support - Math.Max(tol, zoneWidth);
                if (!retested)
                    return false;
                _diagRetestOk = true;

                if (Bars.ClosePrices[lastClosed] > support + maxCloseAbove)
                {
                    Skip("BDR reclaimed above break level");
                    return false;
                }

                if (Bars.HighPrices[lastClosed] > support + Math.Max(maxHighAbove, zoneWidth))
                {
                    Skip("BDR high reclaimed too far above break level");
                    return false;
                }

                if (MaxTradesPerLevelPerDay > 0 && GetTradesCountTodayForLevel(support) >= MaxTradesPerLevelPerDay)
                {
                    Skip("BDR level daily cap reached");
                    return false;
                }

                if (DebugPrintReasons && LogEntryDiagnostics)
                {
                    Print("[BDR-HTF] t={0:yyyy-MM-dd HH:mm} breakIdx={1} support={2:F5} lowBreak={3:F5} highNow={4:F5} closeNow={5:F5} rsi={6:F1} htfBreakIdx={7} htfSupport={8:F5}{9}",
                          Server.Time,
                          breakIdx,
                          support,
                          Bars.LowPrices[breakIdx],
                          Bars.HighPrices[lastClosed],
                          Bars.ClosePrices[lastClosed],
                          rsiNow,
                          htfBreakIdx,
                          htfBrokenSupport,
                          lhTag);
                }

                int impulseIdx;
                double impulsePips;
                GetBestImpulseInfo(breakIdx, lastClosed, support, out impulseIdx, out impulsePips);
                DrawEventMarker(string.Format("evt_B_{0}_{1}", breakIdx, Bars.OpenTimes[breakIdx].Ticks), "B", Bars.OpenTimes[breakIdx], Bars.HighPrices[breakIdx], GetEventLaneOffsetPips(0), Color.DeepSkyBlue);
                DrawEventMarker(string.Format("evt_I_{0}_{1}", impulseIdx, Bars.OpenTimes[impulseIdx].Ticks), string.Format("I:{0:F1}", impulsePips), Bars.OpenTimes[impulseIdx], Bars.HighPrices[impulseIdx], GetEventLaneOffsetPips(1), Color.Gold);
                DrawEventMarker(string.Format("evt_R_{0}_{1}", lastClosed, Bars.OpenTimes[lastClosed].Ticks), "R", Bars.OpenTimes[lastClosed], Bars.HighPrices[lastClosed], GetEventLaneOffsetPips(2), Color.LimeGreen);
                DrawEventMarker(string.Format("evt_T_{0}_{1}", lastClosed, Bars.OpenTimes[lastClosed].Ticks), "T", Bars.OpenTimes[lastClosed], Bars.HighPrices[lastClosed], GetEventLaneOffsetPips(3), Color.Orange);

                _pendingEntryImpulsePips = impulsePips;
                _pendingEntryRetestDepthPips = Math.Max(0.0, (Bars.HighPrices[lastClosed] - support) / Pip);
                _pendingEntryHtfDistancePips = !double.IsNaN(htfBrokenSupport) ? Math.Abs((Bars.ClosePrices[lastClosed] - htfBrokenSupport) / Pip) : double.NaN;
                _pendingEntryLowerHighState = ParseLowerHighState(lhTag);
                _diagEntryOk = true;
                return PlaceSellOrder(lastClosed, support, "BDR", EntryKind.BreakdownRetest, double.NaN, double.NaN, "BDR");
            }

            // Fallback path: local BDR search
            for (int breakIdx = lastClosed - 1; breakIdx >= Math.Max(lookback, lastClosed - maxBarsSinceBreak); breakIdx--)
            {
                if (UseHtfBreakdownBiasForBdr && BreakdownRetestRequireLtfBreakAfterHtfBreak && htfBreakTime != DateTime.MinValue)
                {
                    if (Bars.OpenTimes[breakIdx] < htfBreakTime)
                        continue;
                }

                double support;
                if (UseHtfBreakdownBiasForBdr && BreakdownRetestAnchorToHtfSupport && !double.IsNaN(htfBrokenSupport))
                {
                    support = htfBrokenSupport;
                }
                else
                {
                    if (!TryGetBdrSupport(breakIdx, lookback, out support))
                        continue;
                }

                bool brokeDown = BreakdownRetestRequireBreakClose
                    ? Bars.ClosePrices[breakIdx] <= support - minBreak
                    : (Bars.LowPrices[breakIdx] <= support - minBreak || Bars.ClosePrices[breakIdx] <= support - minBreak);

                if (!brokeDown)
                    continue;
                _diagBreakFound = true;

                double breakOpen = Bars.OpenPrices[breakIdx];
                double breakClose = Bars.ClosePrices[breakIdx];
                double breakHigh = Bars.HighPrices[breakIdx];
                double breakLow = Bars.LowPrices[breakIdx];
                double breakBodyPips = Math.Abs(breakOpen - breakClose) / Pip;

                if (breakClose >= breakOpen)
                {
                    Skip("BDR break bar not bearish");
                    continue;
                }

                if (breakBodyPips < BreakdownRetestBreakMinBodyPips)
                {
                    Skip("BDR break body too small");
                    continue;
                }

                if (BreakdownRetestBreakRequireLowerHalfClose)
                {
                    double breakRange = breakHigh - breakLow;
                    if (breakRange > 0)
                    {
                        double breakClosePos = (breakClose - breakLow) / breakRange; // 0 = low, 1 = high
                        if (breakClosePos > 0.5)
                        {
                            Skip("BDR break close not in lower half");
                            continue;
                        }
                    }
                }

                if (lastClosed - breakIdx < holdBars)
                {
                    Skip("BDR hold bars not reached");
                    continue;
                }

                bool holdOk = true;
                for (int k = breakIdx; k <= lastClosed - 1; k++)
                {
                    if (Bars.ClosePrices[k] > support + maxCloseAbove)
                    {
                        holdOk = false;
                        break;
                    }
                }
                if (!holdOk)
                {
                    Skip("BDR break hold failed");
                    continue;
                }

                if (!HasImpulseAfterBreak(breakIdx, lastClosed, support))
                    continue;

                if (UseHtfBreakdownBiasForBdr && BreakdownRetestMaxDistanceToHtfSupportPips > 0 && !double.IsNaN(htfBrokenSupport))
                {
                    double htfDistPips = Math.Abs(support - htfBrokenSupport) / Pip;
                    if (htfDistPips > BreakdownRetestMaxDistanceToHtfSupportPips)
                    {
                        Skip("BDR local support too far from HTF support");
                        continue;
                    }
                }

                bool retested = Bars.HighPrices[lastClosed] >= support - tol;
                if (!retested)
                    continue;
                _diagRetestOk = true;

                if (Bars.ClosePrices[lastClosed] > support + maxCloseAbove)
                {
                    Skip("BDR reclaimed above break level");
                    continue;
                }

                if (Bars.HighPrices[lastClosed] > support + maxHighAbove)
                {
                    Skip("BDR high reclaimed too far above break level");
                    continue;
                }

                if (MaxTradesPerLevelPerDay > 0 && GetTradesCountTodayForLevel(support) >= MaxTradesPerLevelPerDay)
                {
                    Skip("BDR level daily cap reached");
                    continue;
                }

                if (DebugPrintReasons && LogEntryDiagnostics)
                {
                    string htfInfo = UseHtfBreakdownBiasForBdr
                        ? string.Format(" htfBreakIdx={0} htfSupport={1:F5}", htfBreakIdx, htfBrokenSupport)
                        : string.Empty;

                    Print("[BDR] t={0:yyyy-MM-dd HH:mm} breakIdx={1} support={2:F5} lowBreak={3:F5} highNow={4:F5} closeNow={5:F5} rsi={6:F1}{7}",
                          Server.Time,
                          breakIdx,
                          support,
                          Bars.LowPrices[breakIdx],
                          Bars.HighPrices[lastClosed],
                          Bars.ClosePrices[lastClosed],
                          rsiNow,
                          htfInfo);
                }

                int impulseIdx;
                double impulsePips;
                GetBestImpulseInfo(breakIdx, lastClosed, support, out impulseIdx, out impulsePips);
                DrawEventMarker(string.Format("evt_B_{0}_{1}", breakIdx, Bars.OpenTimes[breakIdx].Ticks), "B", Bars.OpenTimes[breakIdx], Bars.HighPrices[breakIdx], GetEventLaneOffsetPips(0), Color.DeepSkyBlue);
                DrawEventMarker(string.Format("evt_I_{0}_{1}", impulseIdx, Bars.OpenTimes[impulseIdx].Ticks), string.Format("I:{0:F1}", impulsePips), Bars.OpenTimes[impulseIdx], Bars.HighPrices[impulseIdx], GetEventLaneOffsetPips(1), Color.Gold);
                DrawEventMarker(string.Format("evt_R_{0}_{1}", lastClosed, Bars.OpenTimes[lastClosed].Ticks), "R", Bars.OpenTimes[lastClosed], Bars.HighPrices[lastClosed], GetEventLaneOffsetPips(2), Color.LimeGreen);
                DrawEventMarker(string.Format("evt_T_{0}_{1}", lastClosed, Bars.OpenTimes[lastClosed].Ticks), "T", Bars.OpenTimes[lastClosed], Bars.HighPrices[lastClosed], GetEventLaneOffsetPips(3), Color.Orange);

                _pendingEntryImpulsePips = impulsePips;
                _pendingEntryRetestDepthPips = Math.Max(0.0, (Bars.HighPrices[lastClosed] - support) / Pip);
                _pendingEntryHtfDistancePips = !double.IsNaN(htfBrokenSupport) ? Math.Abs((Bars.ClosePrices[lastClosed] - htfBrokenSupport) / Pip) : double.NaN;
                _pendingEntryLowerHighState = ParseLowerHighState(lhTag);
                _diagEntryOk = true;
                return PlaceSellOrder(lastClosed, support, "BDR", EntryKind.BreakdownRetest, double.NaN, double.NaN, "BDR");
            }

            return false;
        }


        private bool IsBearBar(int barIndex)
        {
            if (barIndex < 0 || barIndex >= Bars.Count)
                return false;

            return Bars.ClosePrices[barIndex] < Bars.OpenPrices[barIndex];
        }

        private double GetMaxFavorablePipsSinceEntry(Position pos, int lastClosed)
        {
            int idx = Bars.OpenTimes.GetIndexByTime(pos.EntryTime);
            if (idx < 0)
                return 0.0;

            int start = Math.Max(0, idx);
            int end = Math.Min(lastClosed, Bars.Count - 2);
            if (end < start)
                return 0.0;

            double best = 0.0;
            for (int i = start; i <= end; i++)
            {
                double favorable = (pos.EntryPrice - Bars.LowPrices[i]) / Pip;
                if (favorable > best)
                    best = favorable;
            }

            return best;
        }

        private double GetMaxAdversePipsSinceEntry(Position pos, int lastClosed)
        {
            int idx = Bars.OpenTimes.GetIndexByTime(pos.EntryTime);
            if (idx < 0)
                return 0.0;

            int start = Math.Max(0, idx);
            int end = Math.Min(lastClosed, Bars.Count - 2);
            if (end < start)
                return 0.0;

            double worst = 0.0;
            for (int i = start; i <= end; i++)
            {
                double adverse = (Bars.HighPrices[i] - pos.EntryPrice) / Pip;
                if (adverse > worst)
                    worst = adverse;
            }

            return worst;
        }

        private void DrawSellEntryArrow(string key, DateTime time, double price)
        {
            if (!DrawEntryArrows)
                return;

            try
            {
                Chart.DrawIcon(key, ChartIconType.DownArrow, time, price + (2.0 * Pip), Color.OrangeRed);
            }
            catch
            {
                // non-critical diagnostic drawing only
            }
        }


        private double GetEventLaneOffsetPips(int lane)
        {
            return 2.0 + (Math.Max(0.5, EventMarkerLaneStepPips) * Math.Max(0, lane));
        }

        private double GetEntryLabelOffsetPips(int rank)
        {
            return Math.Max(1.0, EntryLabelBaseOffsetPips) + (Math.Max(0.5, EntryLabelStepPips) * Math.Max(0, rank));
        }

        private void DrawEventMarker(string key, string text, DateTime time, double price, double offsetPips, Color color)
        {
            if (!DrawEventMarkers)
                return;

            try
            {
                Chart.DrawText(key, text, time, price + (offsetPips * Pip), color);
            }
            catch
            {
                // non-critical diagnostic drawing only
            }
        }

        private int GetEntryLabelStackRank(int barIndex)
        {
            int window = Math.Max(1, EntryLabelClusterBars);
            for (int i = _entryLabelHistory.Count - 1; i >= 0; i--)
            {
                if (barIndex - _entryLabelHistory[i] > window)
                    _entryLabelHistory.RemoveAt(i);
            }

            int rank = _entryLabelHistory.Count;
            _entryLabelHistory.Add(barIndex);
            return rank;
        }

        private void DrawEntryDiagnosticLabel(string key, int barIndex, DateTime time, double price, double impulsePips, double retestDepthPips, double htfDistancePips, int lhState)
        {
            if (!DrawEntryLabels)
                return;

            try
            {
                int rank = GetEntryLabelStackRank(barIndex);
                double offsetPips = GetEntryLabelOffsetPips(rank);
                string lhText = lhState < 0 ? "NA" : lhState.ToString();
                string text = string.Format("Imp={0:F1} Ret={1:F1}
Dst={2:F1} LH={3}", impulsePips, retestDepthPips, htfDistancePips, lhText);
                Chart.DrawText(key, text, time, price + (offsetPips * Pip), Color.White);
            }
            catch
            {
                // non-critical diagnostic drawing only
            }
        }

        private void UpdateLiveStatePanel()
        {
            if (!ShowLiveStatePanel)
                return;

            string panel = string.Format(
                "HTF={0}  BRK={1}  IMP={2}  RET={3}  TRG={4}  ENT={5}",
                _diagHtfBias ? "ON" : "--",
                _diagBreakFound ? "ON" : "--",
                _diagImpulseOk ? "ON" : "--",
                _diagRetestOk ? "ON" : "--",
                _diagTriggerOk ? "ON" : "--",
                _diagEntryOk ? "ON" : "--");

            try
            {
                Chart.DrawStaticText("diag_live_panel", panel, VerticalAlignment.Bottom, HorizontalAlignment.Left, Color.White);
            }
            catch
            {
                // non-critical diagnostic drawing only
            }
        }

        private void ResetLiveDiagnostics()
        {
            _diagHtfBias = false;
            _diagBreakFound = false;
            _diagImpulseOk = false;
            _diagRetestOk = false;
            _diagTriggerOk = false;
            _diagEntryOk = false;
        }

        private bool PlaceSellOrder(int lastClosed, double logicalLevel, string levelTag, EntryKind entryKind, double stopLossPipsOverride, double takeProfitPipsOverride, string commentSuffix)
        {
            double volumeInUnits = Symbol.QuantityToVolumeInUnits(VolumeLots);
            long volume = ToVolumeLong(volumeInUnits);

            double slPips;
            if (!double.IsNaN(stopLossPipsOverride) && stopLossPipsOverride > 0)
            {
                slPips = stopLossPipsOverride;
            }
            else if (SlMode == StopLossMode.Level)
            {
                slPips = Math.Max(HardMinSlPips, ((logicalLevel + (SlAboveLevelPips * Pip)) - Symbol.Bid) / Pip);
            }
            else
            {
                double atrPips = HardMinSlPips;
                if (_slAtr != null && _slAtrBars != null && _slAtrBars.Count >= 2)
                {
                    int atrIdx = _slAtrBars.Count - 2;
                    atrPips = (_slAtr.Result[atrIdx] / Pip) * SlAtrMultiplier;
                }
                if (SlAtrMinPips > 0)
                    atrPips = Math.Max(atrPips, SlAtrMinPips);
                slPips = Math.Max(HardMinSlPips, atrPips);
            }

            if (HardMaxSlPips > 0)
                slPips = Math.Min(slPips, HardMaxSlPips);

            double? tpPips = null;
            double chosenTp = (!double.IsNaN(takeProfitPipsOverride) && takeProfitPipsOverride > 0)
                ? takeProfitPipsOverride
                : FixedTpPips;
            if (TpMode == TakeProfitMode.FixedPips || TpMode == TakeProfitMode.Both)
                tpPips = chosenTp;

            string label = EffectiveBotLabel;
            string comment = string.IsNullOrWhiteSpace(commentSuffix) ? levelTag : levelTag + ":" + commentSuffix;

            var result = ExecuteMarketOrder(TradeType.Sell, SymbolName, volume, label, slPips, tpPips, comment);
            if (!result.IsSuccessful || result.Position == null)
            {
                if (DebugPrintReasons)
                    Print("[ENTRY FAIL] kind={0} level={1:F5} err={2}", entryKind, logicalLevel, result.Error);
                return false;
            }

            _entryKindByPosId[result.Position.Id] = entryKind;
            _entryLevelByPosId[result.Position.Id] = logicalLevel;
            _posIdToLevelPrice[result.Position.Id] = logicalLevel;
            _posIdToLevelTag[result.Position.Id] = levelTag;
            _posIdEntryBar[result.Position.Id] = lastClosed;
            _posIdToEntryTime[result.Position.Id] = result.Position.EntryTime;
            _maxProfitPipsByPosId[result.Position.Id] = Math.Max(0.0, result.Position.Pips);
            MarkTradeTodayForLevel(logicalLevel);

            string arrowKey = string.Format("sell_entry_{0}_{1}", result.Position.Id, result.Position.EntryTime.Ticks);
            DrawSellEntryArrow(arrowKey, Bars.OpenTimes[lastClosed], Bars.HighPrices[lastClosed]);
            string labelKey = string.Format("sell_entry_label_{0}_{1}", result.Position.Id, result.Position.EntryTime.Ticks);
            DrawEntryDiagnosticLabel(labelKey, lastClosed, Bars.OpenTimes[lastClosed], Bars.HighPrices[lastClosed], _pendingEntryImpulsePips, _pendingEntryRetestDepthPips, _pendingEntryHtfDistancePips, _pendingEntryLowerHighState);
            DrawEventMarker(string.Format("evt_E_{0}_{1}", result.Position.Id, result.Position.EntryTime.Ticks), "E", Bars.OpenTimes[lastClosed], Bars.HighPrices[lastClosed], GetEventLaneOffsetPips(4), Color.OrangeRed);
            _pendingEntryImpulsePips = double.NaN;
            _pendingEntryRetestDepthPips = double.NaN;
            _pendingEntryHtfDistancePips = double.NaN;
            _pendingEntryLowerHighState = -1;

            if (DebugPrintReasons)
                Print("[ENTRY] kind={0} pos#{1} level={2:F5} sl={3:F1} tp={4}", entryKind, result.Position.Id, logicalLevel, slPips, tpPips.HasValue ? tpPips.Value.ToString("F1") : "na");

            return true;
        }

        private bool TryValidationExit(Position pos, int lastClosed)
        {
            if (!ValidationExitEnabled)
                return false;

            if (ValidationExitBars < 1)
                return false;

            int windowBars = Math.Max(1, ValidationExitWindowBars);

            EntryKind entryKind;
            if (!_entryKindByPosId.TryGetValue(pos.Id, out entryKind))
                return false;

            if (ValidationExitRetestOnly && entryKind != EntryKind.BreakdownRetest)
                return false;

            int barsOpen = BarsSinceEntryUtc(pos.EntryTime);
            if (barsOpen < ValidationExitBars)
                return false;

            // Watch a short validation window instead of judging only once.
            if (barsOpen > ValidationExitBars + (windowBars - 1))
                return false;

            double mfePips = GetMaxFavorablePipsSinceEntry(pos, lastClosed);
            if (mfePips >= ValidationMinFavorablePips)
                return false;

            double closeAboveEntryPips = (Bars.ClosePrices[lastClosed] - pos.EntryPrice) / Pip;
            double highAboveEntryPips = GetMaxAdversePipsSinceEntry(pos, lastClosed);

            bool continuationSign =
                closeAboveEntryPips >= ValidationCloseAboveEntryPips ||
                highAboveEntryPips >= ValidationHighAboveEntryPips;

            if (!continuationSign)
                return false;

            if (DebugPrintReasons)
            {
                Print("[VALIDATION EXIT] pos#{0} kind={1} barsOpen={2} window={3} mfe={4:F1} closeAbove={5:F1} highAbove={6:F1}",
                      pos.Id, entryKind, barsOpen, windowBars, mfePips, closeAboveEntryPips, highAboveEntryPips);
            }

            return CloseWithReason(
                pos,
                CloseReason.ValidationExit,
                string.Format("ValidationExit barsOpen={0} window={1} mfe={2:F1} closeAbove={3:F1} highAbove={4:F1}",
                              barsOpen, windowBars, mfePips, closeAboveEntryPips, highAboveEntryPips)
            );
        }
        private bool CloseWithReason(Position pos, CloseReason reason, string detail)
        {
            _posIdPendingCloseReason[pos.Id] = reason;

            var res = ClosePosition(pos);
            if (!res.IsSuccessful)
            {
                if (DebugPrintReasons) Print("[EXIT FAIL] {0} pos#{1} err={2}", detail, pos.Id, res.Error);
                return false;
            }

            // If we closed due to defensive / invalidation exits, do NOT consume daily level count.
            if (reason == CloseReason.SpeedCut ||
                reason == CloseReason.InvalidateEarly ||
                reason == CloseReason.InvalidateLate ||
                reason == CloseReason.ValidationExit)
            {
                double lv;
                if (_posIdToLevelPrice.TryGetValue(pos.Id, out lv))
                {
                    UnmarkTradeTodayForLevel(lv);
                    if (DebugPrintReasons) Print("[LEVEL_CAP] Unmark due to {0}: pos#{1} level={2}", reason, pos.Id, lv);
                }
            }

            // Cleanup
            _posIdPendingCloseReason.Remove(pos.Id);
            _posIdToLevelKey.Remove(pos.Id);
            _posIdToLevelPrice.Remove(pos.Id);
            _posIdToLevelTag.Remove(pos.Id);
            _posIdEntryBar.Remove(pos.Id);
            _posIdToEntryTime.Remove(pos.Id);
            _entryLevelByPosId.Remove(pos.Id);
            _aboveCloseCountByPosId.Remove(pos.Id);
            _maxProfitPipsByPosId.Remove(pos.Id);
            _entryKindByPosId.Remove(pos.Id);

            return true;
        }

        private void ManageOpenPositions()
        {
            var sells = Positions.FindAll(EffectiveBotLabel, SymbolName, TradeType.Sell);
            if (sells == null || sells.Length == 0)
                return;

            // Prune tracking dictionaries for closed positions
            try
            {
                var openIds = new HashSet<long>();
                foreach (var p in sells) openIds.Add(p.Id);

                var keys1 = new List<long>(_entryLevelByPosId.Keys);
                foreach (var k in keys1)
                    if (!openIds.Contains(k)) _entryLevelByPosId.Remove(k);

                var keys2 = new List<long>(_aboveCloseCountByPosId.Keys);
                foreach (var k in keys2)
                    if (!openIds.Contains(k)) _aboveCloseCountByPosId.Remove(k);

                var keys3 = new List<long>(_maxProfitPipsByPosId.Keys);
                foreach (var k in keys3)
                    if (!openIds.Contains(k)) _maxProfitPipsByPosId.Remove(k);
                var keys4 = new List<long>(_entryKindByPosId.Keys);
                foreach (var k in keys4)
                    if (!openIds.Contains(k)) _entryKindByPosId.Remove(k);
            }
            catch { }

            int lastClosed = Bars.Count - 2;
            if (lastClosed < 2)
                return;

            double rNow = _rsi.Result[lastClosed];

            foreach (var pos in sells)
            {
                // early post-entry validation (BDR only by default)
                if (TryValidationExit(pos, lastClosed))
                    continue;
                // Track max favorable excursion (profit in pips) to support safe Expiry logic
                try
                {
                    double maxp;
                    if (!_maxProfitPipsByPosId.TryGetValue(pos.Id, out maxp) || pos.Pips > maxp)
                        _maxProfitPipsByPosId[pos.Id] = pos.Pips;
                }
                catch { }

                // No-profit time stop: if position fails to get into profit within N bars, exit early.
                if (NoProfitExitEnabled)
                {
                    var barsSinceEntry = BarsSinceEntryUtc(pos.EntryTime);
                    if (barsSinceEntry >= NoProfitExitBars && pos.Pips <= NoProfitExitMaxPips)
                    {
                        var closeResNp = ClosePosition(pos);
                        if (closeResNp.IsSuccessful)
                        {
                            if (DebugPrintReasons) Print("[EXIT] NoProfitExit: pos#{0} pips={1:F1} bars={2}", pos.Id, pos.Pips, barsSinceEntry);
                            continue;
                        }
                        else
                        {
                            if (DebugPrintReasons) Print("[EXIT FAIL] NoProfitExit close failed: pos#{0} err={1}", pos.Id, closeResNp.Error);
                        }
                    }
                }

                // Early Deny (safe):
// Use the ENTRY LEVEL (the level that triggered the sell) if available.
// This avoids cutting many "normal" small wicks above entry that later become winners.
// Fallback to entry price if level isn't available (should be rare).
if (EarlyDenyEnabled && Math.Abs(EarlyDenyCloseAboveEntryPips) > 0)
{
    int bse = BarsSinceEntryUtc(pos.EntryTime);
    if (bse > 0 && bse <= EarlyDenyBars)
    {
        double closePx = Bars.ClosePrices[lastClosed];

        double refLevel;
        if (!_entryLevelByPosId.TryGetValue(pos.Id, out refLevel))
            refLevel = pos.EntryPrice;

        if (closePx > refLevel + (Math.Abs(EarlyDenyCloseAboveEntryPips) * Pip))
        {

                            var res = ClosePosition(pos);
                            if (res.IsSuccessful)
                            {
                                if (DebugPrintReasons) Print("[EXIT] EarlyDeny: pos#{0} close={1} > entry+{2}p bars={3}", pos.Id, closePx, Math.Abs(EarlyDenyCloseAboveEntryPips), bse);
                                _entryLevelByPosId.Remove(pos.Id);
                                _aboveCloseCountByPosId.Remove(pos.Id);
                                _maxProfitPipsByPosId.Remove(pos.Id);
                                continue;
                            }
                            else
                            {
                                if (DebugPrintReasons) Print("[EXIT FAIL] EarlyDeny close failed: pos#{0} err={1}", pos.Id, res.Error);
                            }
                        }
                    }
                }

                // Expiry (taste limit):
// Only exit if the trade has NOT shown meaningful favorable movement.
// This reduces the chance of cutting a trade that would later reach TP after a normal small pullback.
if (ExpiryEnabled)
{
    int bse = BarsSinceEntryUtc(pos.EntryTime);

    double maxp = 0;
    _maxProfitPipsByPosId.TryGetValue(pos.Id, out maxp);

    double cutBelow = ((ExpiryCloseIfPipsBelow > 0) ? -ExpiryCloseIfPipsBelow : ExpiryCloseIfPipsBelow);
    if (cutBelow > 0) cutBelow = -cutBelow; // safety

    if (bse >= Math.Max(1, ExpiryBars) && maxp < ExpiryNeverReachedProfitPips && pos.Pips <= cutBelow)
    {

                        var res = ClosePosition(pos);
                        if (res.IsSuccessful)
                        {
                            if (DebugPrintReasons) Print("[EXIT] Expiry: pos#{0} pips={1:F1} bars={2}", pos.Id, pos.Pips, bse);
                            _entryLevelByPosId.Remove(pos.Id);
                            _aboveCloseCountByPosId.Remove(pos.Id);
                                _maxProfitPipsByPosId.Remove(pos.Id);
                            continue;
                        }
                        else
                        {
                            if (DebugPrintReasons) Print("[EXIT FAIL] Expiry close failed: pos#{0} err={1}", pos.Id, res.Error);
                        }
                    }
                }

                // Breakout invalidation:
                // If the "rejection" premise breaks (price CLOSES above the used level by X pips),
                // exit early to reduce damage on true breakout days (e.g., ID14 / ID28 patterns).
                if (BreakoutInvalidateEnabled)
                {
                    double level;
                    if (_entryLevelByPosId.TryGetValue(pos.Id, out level))
                    {
                        int barsSinceEntry = BarsSinceEntryUtc(pos.EntryTime);
                        double closePx = Bars.ClosePrices[lastClosed];

                        // Early window: very strict (small threshold)
                        if (barsSinceEntry <= InvalidateEarlyBars)
                        {
                            if (InvalidateEarlyAdversePips > 0 && pos.Pips <= -InvalidateEarlyAdversePips)
                            {
                                var res = ClosePosition(pos);
                                if (res.IsSuccessful)
                                {
                                    if (DebugPrintReasons) Print("[EXIT] InvalidateEarlyAdverse: pos#{0} pips={1:F1} bars={2}", pos.Id, pos.Pips, barsSinceEntry);
                                    _entryLevelByPosId.Remove(pos.Id);
                                    _aboveCloseCountByPosId.Remove(pos.Id);
                                _maxProfitPipsByPosId.Remove(pos.Id);
                                    continue;
                                }
                            }

                            if (closePx > level + (InvalidateEarlyCloseAbovePips * Pip))
                            {
                                var res = ClosePosition(pos);
                                if (res.IsSuccessful)
                                {
                                    if (DebugPrintReasons) Print("[EXIT] InvalidateEarlyCloseAbove: pos#{0} close={1} > level+{2}p", pos.Id, closePx, InvalidateEarlyCloseAbovePips);
                                    _entryLevelByPosId.Remove(pos.Id);
                                    _aboveCloseCountByPosId.Remove(pos.Id);
                                _maxProfitPipsByPosId.Remove(pos.Id);
                                    continue;
                                }
                            }
                        }
                        else
                        {
                            // Late window: looser but more reliable (require consecutive closes above higher threshold)
                            if (InvalidateLateBars > 0 && barsSinceEntry <= InvalidateLateBars)
                            {
                                double thr = level + (InvalidateLateCloseAbovePips * Pip);
                                int cnt = 0;
                                _aboveCloseCountByPosId.TryGetValue(pos.Id, out cnt);

                                if (closePx > thr)
                                    cnt++;
                                else
                                    cnt = 0;

                                _aboveCloseCountByPosId[pos.Id] = cnt;

                                if (cnt >= Math.Max(1, InvalidateLateConsecutiveCloses))
                                {
                                    var res = ClosePosition(pos);
                                    if (res.IsSuccessful)
                                    {
                                        if (DebugPrintReasons) Print("[EXIT] InvalidateLateCloseAbove: pos#{0} closesAbove={1} thrPips={2}", pos.Id, cnt, InvalidateLateCloseAbovePips);
                                        _entryLevelByPosId.Remove(pos.Id);
                                        _aboveCloseCountByPosId.Remove(pos.Id);
                                _maxProfitPipsByPosId.Remove(pos.Id);
                                        continue;
                                    }
                                }
                            }
                        }
                    }
                }

                // SpeedCut (adverse move within first N bars): 
                // If position drifts against us early (typical slow-breakout), exit to reduce damage
                // while preserving most winners (which usually do not go deeply negative early).
                if (SpeedCutEnabled && SpeedCutAdversePips > 0)
                {
                    int bse = BarsSinceEntryUtc(pos.EntryTime);
                    if (bse > 0 && bse <= SpeedCutBars && pos.Pips <= -SpeedCutAdversePips)
                    {
                        var res = ClosePosition(pos);
                        if (res.IsSuccessful)
                        {
                            if (DebugPrintReasons) Print("[EXIT] SpeedCut: pos#{0} pips={1:F1} bars={2}", pos.Id, pos.Pips, bse);
                            _entryLevelByPosId.Remove(pos.Id);
                            _aboveCloseCountByPosId.Remove(pos.Id);
                                _maxProfitPipsByPosId.Remove(pos.Id);
                            continue;
                        }
                        else
                        {
                            if (DebugPrintReasons) Print("[EXIT FAIL] SpeedCut close failed: pos#{0} err={1}", pos.Id, res.Error);
                        }
                    }
                }

// RSI exit: if RSI returns to ExitLevel, close
                if (TpMode == TakeProfitMode.RsiReturn || TpMode == TakeProfitMode.Both)
                {
                    var barsSinceEntry = BarsSinceEntryUtc(pos.EntryTime);
                    if (barsSinceEntry >= RsiExitMinHoldBars && rNow <= RsiExitLevel)
                    {
                        // Close only when position has at least small profit to avoid "tiny loss drip" from costs.
                        if (pos.Pips >= RsiExitMinProfitPips)
                        {
                            if (CloseWithReason(pos, CloseReason.RsiExit, "RsiExit"))
                            {
                                if (DebugPrintReasons) Print("[EXIT] RSI return: pos#{0} pips={1:F1} rsi={2:F1}", pos.Id, pos.Pips, rNow);
                                continue;
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
                        {
                            ModifyPosition(pos, desiredSl, pos.TakeProfit);
                        }
                    }
                }
            }
        }

        // =========================
        // RSI / ACD / Confirm helpers
        // =========================
        private bool IsAcdOk()
        {
            if (!UseAcd)
                return true;

            if (_acdBars == null || _acdBars.Count < AcdWindowBars + 5)
                return true; // can't evaluate; don't block

            int last = _acdBars.Count - 2;
            if (last < 10)
                return true;

            int start = Math.Max(0, last - AcdWindowBars + 1);

            double hi = double.MinValue;
            double lo = double.MaxValue;

            for (int i = start; i <= last; i++)
            {
                hi = Math.Max(hi, _acdBars.HighPrices[i]);
                lo = Math.Min(lo, _acdBars.LowPrices[i]);
            }

            double rangePips = (hi - lo) / Pip;

            _acdUpper = hi;
            _acdLower = lo;

            if (DrawAcdBox)
                DrawAcdRangeBox();

            if (rangePips < AcdMinRangePips || (AcdMaxRangePips > 0 && rangePips > AcdMaxRangePips))
            {
                if (DebugPrintReasons) Print("Skip entry: ACD range out of bounds rangePips={0:F1} not in [{1:F1}..{2:F1}]", rangePips, AcdMinRangePips, AcdMaxRangePips);
                return false;
            }

            return true;
        }
        private void DrawAcdRangeBox()
        {
            if (double.IsNaN(_acdUpper) || double.IsNaN(_acdLower))
                return;

            const string name = "ACD_BOX";
            Chart.RemoveObject(name);

            // Draw as two horizontal lines for simplicity
            Chart.DrawHorizontalLine(name + "_U", _acdUpper, Color.DodgerBlue, 1, LineStyle.Dots);
            Chart.DrawHorizontalLine(name + "_L", _acdLower, Color.DodgerBlue, 1, LineStyle.Dots);
        }

        // =========================
        // Session / Utilities
        // =========================
        private bool IsSessionOk()
        {
            if (!UseSessionFilter)
                return true;

            var jst = Server.Time.AddHours(JST_OFFSET_HOURS);
            int h = jst.Hour;

            if (SessionStartHourJst == SessionEndHourJst)
                return true; // all day

            // overnight session supported
            if (SessionStartHourJst < SessionEndHourJst)
            {
                return h >= SessionStartHourJst && h < SessionEndHourJst;
            }
            else
            {
                return (h >= SessionStartHourJst) || (h < SessionEndHourJst);
            }
        }

            private long ToVolumeLong(double volumeInUnits)
            {
                // keep everything in double, then round at the end
                double vol = volumeInUnits;

                double step = Symbol.VolumeInUnitsStep;   // some cTrader builds expose these as double
                double vmin = Symbol.VolumeInUnitsMin;
                double vmax = Symbol.VolumeInUnitsMax;

                if (step <= 0)
                    step = 1;

                // round DOWN to step to avoid "invalid volume" rejection
                vol = Math.Floor(vol / step) * step;

                if (vol < vmin) vol = vmin;
                if (vol > vmax) vol = vmax;

                return (long)Math.Round(vol);
            }

        private void Skip(string reason)
        {
            if (!DebugPrintReasons || !LogSkipReasons)
                return;

            double rsiNow = double.NaN;
            int idx = Bars.Count - 2;
            if (_rsi != null && idx >= 0 && idx < _rsi.Result.Count)
                rsiNow = _rsi.Result[idx];

            Print("[SKIP] {0} | t={1:yyyy-MM-dd HH:mm} bid={2} ask={3} spread(pips)={4:F1} rsi={5:F1}",
                  reason, Server.Time, Symbol.Bid, Symbol.Ask, (Symbol.Spread / Symbol.PipSize), rsiNow);
        }

    }
}