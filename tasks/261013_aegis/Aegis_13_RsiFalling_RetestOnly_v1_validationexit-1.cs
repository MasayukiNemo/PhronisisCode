// Aegis_13_RsiFalling_RetestOnly_v1.cs
// Sell-only "Range Retest" bot with:
// - HTF swing-high resistance levels
// - Retest + optional bear-candle confirmation
// - RSI entry quality gate + optional RSI peak evidence + avoid chase
// - ACD (Anti-Chop Detector)
// - RollingHigh (H1) fallback level
// - Exits: Fixed TP / RSI return / Trailing

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
    public class Aegis_RR_S10_RsiWeakReAttack_v1 : Robot
    {
        // ============================================================
        // 1) CORE
        // ============================================================
        [Parameter("Label", DefaultValue = "Aegis_RR_S_MF2", Group = "1. CORE")]
        public string BotLabel { get; set; }

        [Parameter("Volume (Lots)", DefaultValue = 0.02, MinValue = 0.01, Step = 0.01, Group = "1. CORE")]
        public double VolumeLots { get; set; }

        // =================================================================
        // [0] OPTIMIZATION SWITCH
        // =================================================================
        [Parameter("Optimization Mode (use OPT:* values)", DefaultValue = false, Group = "0. OPT")]
        public bool OptimizationMode { get; set; }

        [Parameter("OPT: EMA Retest Max Dist (pips)", DefaultValue = 15.0, MinValue = 0.0, Step = 0.5, Group = "0. OPT")]
        public double Opt_EmaRetestMaxDistancePips { get; set; }

        [Parameter("OPT: Early Deny Close Above (pips)", DefaultValue = 1.6, MinValue = 0.0, Step = 0.1, Group = "0. OPT")]
        public double Opt_EarlyDenyCloseAbovePips { get; set; }

        [Parameter("OPT: Expiry Bars", DefaultValue = 23, MinValue = 1, Step = 1, Group = "0. OPT")]
        public int Opt_ExpiryBars { get; set; }

        [Parameter("OPT: Expiry Cut (pips, negative)", DefaultValue = -5.5, Step = 0.5, Group = "0. OPT")]
        public double Opt_ExpiryCutPips { get; set; }

        [Parameter("OPT: Expiry Never Reached Profit (pips)", DefaultValue = 2.4, MinValue = 0.0, Step = 0.1, Group = "0. OPT")]
        public double Opt_ExpiryNeverReachedProfitPips { get; set; }

        [Parameter("OPT: SpeedCut Adverse (pips)", DefaultValue = 10.0, MinValue = 0.0, Step = 0.5, Group = "0. OPT")]
        public double Opt_SpeedCutAdversePips { get; set; }

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

#if false
        [Parameter("H1 Uptrend Filter Enabled", DefaultValue = true, Group = "1. CORE")]
        public bool H1UptrendFilterEnabled { get; set; }

        [Parameter("H1 Uptrend Window (bars)", DefaultValue = 18, MinValue = 5, Group = "1. CORE")]
        public int H1UptrendWindowBars { get; set; }

        [Parameter("H1 Higher-High Count Min", DefaultValue = 3, MinValue = 1, Group = "1. CORE")]
        public int H1HigherHighCountMin { get; set; }
#endif


        // ===== TREND (for future use / visualization only) =====
        [Parameter("Trend TimeFrame", DefaultValue = "Hour", Group = "1. TREND")]
        public TimeFrame TrendTimeFrame { get; set; }

        [Parameter("Trend EMA Period", DefaultValue = 29, MinValue = 1, Group = "1. TREND")]
        public int TrendEmaPeriod { get; set; }

        [Parameter("Trend EMA Shift Bars (>=0)", DefaultValue = 0, MinValue = 0, Group = "1. TREND")]
        public int TrendEmaShiftBars { get; set; }

        // ===== EMA RETEST (DOWN TREND) =====
        [Parameter("Use EMA Retest Level (Downtrend)", DefaultValue = true, Group = "1. EMA RETEST")]
        public bool UseEmaRetestLevel { get; set; }

        [Parameter("EMA Retest Offset (pips)", DefaultValue = 1.2, MinValue = 0, Group = "1. EMA RETEST")]
        public double EmaRetestOffsetPips { get; set; }

        [Parameter("EMA Retest Max Distance (pips)", DefaultValue = 15.0, MinValue = 1, Group = "1. EMA RETEST")]
        public double EmaRetestMaxDistancePips { get; set; }

        [Parameter("EMA Down Slope Lookback (bars)", DefaultValue = 3, MinValue = 1, Group = "1. EMA RETEST")]
        public int EmaDownSlopeLookbackBars { get; set; }

        [Parameter("EMA Down Slope Min (pips/bar)", DefaultValue = 0.1, MinValue = 0, Group = "1. EMA RETEST")]
        public double EmaDownSlopeMinPipsPerBar { get; set; }

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
        [Parameter("Use Session Filter (JST)", DefaultValue = true, Group = "2. SESSION (JST)")]
        public bool UseSessionFilter { get; set; }

        [Parameter("Session Start Hour (JST)", DefaultValue = 9, MinValue = 0, MaxValue = 23, Group = "2. SESSION (JST)")]
        public int SessionStartHourJst { get; set; }

        [Parameter("Session End Hour (JST)", DefaultValue = 5, MinValue = 0, MaxValue = 23, Group = "2. SESSION (JST)")]
        public int SessionEndHourJst { get; set; }

        // ============================================================
        // 3) LEVELS (HTF swing highs)
        // ============================================================
        [Parameter("HTF", DefaultValue = "Hour4", Group = "3. LEVELS")]
        public TimeFrame Htf { get; set; }

        [Parameter("HTF Lookback Bars", DefaultValue = 210, MinValue = 50, Group = "3. LEVELS")]
        public int HtfLookbackBars { get; set; }

        [Parameter("Swing Left Bars", DefaultValue = 3, MinValue = 1, Group = "3. LEVELS")]
        public int SwingLeftBars { get; set; }

        [Parameter("Swing Right Bars", DefaultValue = 1, MinValue = 1, Group = "3. LEVELS")]
        public int SwingRightBars { get; set; }

        [Parameter("Merge Distance (pips)", DefaultValue = 7.5, MinValue = 0.0, Group = "3. LEVELS")]
        public double MergeDistancePips { get; set; }

        [Parameter("Max Active Levels", DefaultValue = 6, MinValue = 1, Group = "3. LEVELS")]
        public int MaxActiveLevels { get; set; }

        [Parameter("Min Level Above (pips)", DefaultValue = 3.0, MinValue = 0.0, Group = "3. LEVELS")]
        public double MinLevelAbovePips { get; set; }

        [Parameter("Max Level Distance Above (pips)", DefaultValue = 180.0, MinValue = 1.0, Group = "3. LEVELS")]
        public double MaxLevelDistanceAbovePips { get; set; }

        // ============================================================
        // 4) ENTRY (Retest)
        // ============================================================
        [Parameter("Touch Tolerance (pips)", DefaultValue = 8.0, MinValue = 0.0, Group = "4. ENTRY")]
        public double TouchTolerancePips { get; set; }

        [Parameter("Reject Close Below (pips)", DefaultValue = 2.2, MinValue = 0.0, Group = "4. ENTRY")]
        public double RejectCloseBelowLevelPips { get; set; }

        [Parameter("Bear Candle Required", DefaultValue = false, Group = "4. ENTRY")]
        public bool BearCandleRequired { get; set; }

        [Parameter("Bear Min Body (pips)", DefaultValue = 1.2, MinValue = 0.0, Group = "4. ENTRY")]
        public double BearMinBodyPips { get; set; }

        [Parameter("Bear Max Upper Wick Ratio", DefaultValue = 2.4, MinValue = 0.0, Group = "4. ENTRY")]
        public double BearMaxUpperWickRatio { get; set; }



        [Parameter("Reject By Wick", DefaultValue = true, Group = "4. ENTRY")]
        public bool RejectByWick { get; set; }

        [Parameter("Wick Min Above Level (pips)", DefaultValue = 0.8, MinValue = 0.0, Group = "4. ENTRY")]
        public double WickMinAboveLevelPips { get; set; }

        [Parameter("Wick Close Below Level (pips)", DefaultValue = 0.2, MinValue = 0.0, Group = "4. ENTRY")]
        public double WickCloseBelowLevelPips { get; set; }

        
        // ============================================================
        // 4B) ENTRY (Momentum Failure)
        // ============================================================
        [Parameter("Use Momentum Failure Entry", DefaultValue = true, Group = "4B. MF")]
        public bool UseMomentumFailureEntry { get; set; }

        [Parameter("MF Peak Min RSI", DefaultValue = 66.5, MinValue = 40.0, MaxValue = 90.0, Step = 0.5, Group = "4B. MF")]
        public double MomentumFailurePeakMinRsi { get; set; }

        [Parameter("MF Drop Min (pips)", DefaultValue = 2.0, MinValue = 0.0, Step = 0.1, Group = "4B. MF")]
        public double MomentumFailureDropMin { get; set; }

        [Parameter("MF Rebound Min (pips)", DefaultValue = 4.7, MinValue = 0.0, Step = 0.1, Group = "4B. MF")]
        public double MomentumFailureReboundMin { get; set; }

        [Parameter("MF Max Bars Since Peak", DefaultValue = 9, MinValue = 2, MaxValue = 30, Step = 1, Group = "4B. MF")]
        public int MomentumFailureMaxBarsSincePeak { get; set; }

        [Parameter("MF Peak Price Buffer (pips)", DefaultValue = 1.9, MinValue = 0.0, Step = 0.1, Group = "4B. MF")]
        public double MomentumFailurePeakPriceBufferPips { get; set; }

        [Parameter("MF RSI Peak Gap Max", DefaultValue = 2.0, MinValue = 0.0, Step = 0.1, Group = "4B. MF")]
        public double MomentumFailureRsiPeakGapMax { get; set; }

        [Parameter("Use MF Early Failure Entry", DefaultValue = false, Group = "4C. MF-Early")]
        public bool UseMomentumEarlyFailureEntry { get; set; }

        [Parameter("MFE Peak Min RSI", DefaultValue = 65.5, MinValue = 40.0, MaxValue = 90.0, Step = 0.5, Group = "4C. MF-Early")]
        public double MomentumEarlyFailurePeakMinRsi { get; set; }

        [Parameter("MFE Drop Min (pips)", DefaultValue = 2.0, MinValue = 0.0, Step = 0.1, Group = "4C. MF-Early")]
        public double MomentumEarlyFailureDropMin { get; set; }

        [Parameter("MFE Rebound Max (pips)", DefaultValue = 1.0, MinValue = 0.0, Step = 0.1, Group = "4C. MF-Early")]
        public double MomentumEarlyFailureReboundMax { get; set; }

        [Parameter("MFE Max Bars Since Peak", DefaultValue = 6, MinValue = 2, MaxValue = 30, Step = 1, Group = "4C. MF-Early")]
        public int MomentumEarlyFailureMaxBarsSincePeak { get; set; }

        [Parameter("MFE Peak Price Buffer (pips)", DefaultValue = 2.0, MinValue = 0.0, Step = 0.1, Group = "4C. MF-Early")]
        public double MomentumEarlyFailurePeakPriceBufferPips { get; set; }


        // ============================================================
        // 4E) SHARED PRICE LOCATION
        // ============================================================
        [Parameter("Use Near Recent High Filter", DefaultValue = true, Group = "4E. Shared Price")]
        public bool UseNearRecentHighFilter { get; set; }

        [Parameter("Near Recent High Lookback Bars", DefaultValue = 20, MinValue = 5, MaxValue = 100, Step = 1, Group = "4E. Shared Price")]
        public int NearRecentHighLookbackBars { get; set; }

        [Parameter("Near Recent High Max Distance (pips)", DefaultValue = 4.0, MinValue = 0.5, Step = 0.1, Group = "4E. Shared Price")]
        public double NearRecentHighMaxDistancePips { get; set; }

        // ============================================================
        // 4D) ENTRY (Liquidity Sweep)
        // ============================================================
        [Parameter("Use Liquidity Sweep Entry", DefaultValue = false, Group = "4D. LS")]
        public bool UseLiquiditySweepEntry { get; set; }

        [Parameter("LS Lookback Bars", DefaultValue = 20, MinValue = 5, MaxValue = 100, Step = 1, Group = "4D. LS")]
        public int LiquiditySweepLookbackBars { get; set; }

        [Parameter("LS Sweep Buffer (pips)", DefaultValue = 1.5, MinValue = 0.0, Step = 0.1, Group = "4D. LS")]
        public double LiquiditySweepBufferPips { get; set; }

        [Parameter("LS Close Back Buffer (pips)", DefaultValue = 0.3, MinValue = 0.0, Step = 0.1, Group = "4D. LS")]
        public double LiquiditySweepCloseBackBufferPips { get; set; }

        [Parameter("LS Min RSI", DefaultValue = 64.0, MinValue = 30.0, MaxValue = 90.0, Step = 0.5, Group = "4D. LS")]
        public double LiquiditySweepMinRsi { get; set; }

        
// ============================================================
        // 4F) RSI PEAK STRUCTURE FILTER
        // ============================================================
        [Parameter("Use RSI Weak Re-Attack Filter", DefaultValue = true, Group = "4F. RSI Peak Structure")]
        public bool UseRsiWeakReAttackFilter { get; set; }

        [Parameter("RWR Lookback Bars", DefaultValue = 8, MinValue = 5, MaxValue = 30, Step = 1, Group = "4F. RSI Peak Structure")]
        public int RsiWeakReAttackLookbackBars { get; set; }

        [Parameter("RWR Peak Min RSI", DefaultValue = 66.0, MinValue = 30.0, MaxValue = 90.0, Step = 0.5, Group = "4F. RSI Peak Structure")]
        public double RsiWeakReAttackPeakMinRsi { get; set; }

        [Parameter("RWR Drop Min RSI", DefaultValue = 2.0, MinValue = 0.0, MaxValue = 20.0, Step = 0.1, Group = "4F. RSI Peak Structure")]
        public double RsiWeakReAttackDropMinRsi { get; set; }

        [Parameter("RWR Second Peak Min RSI", DefaultValue = 64.0, MinValue = 30.0, MaxValue = 90.0, Step = 0.5, Group = "4F. RSI Peak Structure")]
        public double RsiWeakReAttackSecondPeakMinRsi { get; set; }

        [Parameter("RWR Peak Gap Min RSI", DefaultValue = 1.0, MinValue = 0.0, MaxValue = 20.0, Step = 0.1, Group = "4F. RSI Peak Structure")]
        public double RsiWeakReAttackPeakGapMinRsi { get; set; }

        // ============================================================
        // 4G) RSI TIMING FILTER
        // ============================================================
        [Parameter("Use RSI Falling Filter", DefaultValue = false, Group = "4G. RSI Timing")]
        public bool UseRsiFallingFilter { get; set; }

        [Parameter("RSI Falling Lookback Bars", DefaultValue = 2, MinValue = 1, MaxValue = 5, Step = 1, Group = "4G. RSI Timing")]
        public int RsiFallingLookbackBars { get; set; }


// ============================================================
        // 5) RSI QUALITY
        // ============================================================
        [Parameter("RSI Period", DefaultValue = 12, MinValue = 2, Group = "5. RSI")]
        public int RsiPeriod { get; set; }

        [Parameter("RSI Now Min", DefaultValue = 72.0, Group = "5. RSI")]
        public double RsiNowMin { get; set; }

        [Parameter("RSI Now Max", DefaultValue = 82.0, Group = "5. RSI")]
        public double RsiNowMax { get; set; }

        
        [Parameter("RSI Now Min (Downtrend)", DefaultValue = 68.5, Group = "5. RSI")]
        public double RsiNowMinDown { get; set; }

        [Parameter("RSI Now Max (Downtrend)", DefaultValue = 78.0, Group = "5. RSI")]
        public double RsiNowMaxDown { get; set; }

        [Parameter("Require RSI Peak Evidence (Downtrend)", DefaultValue = false, Group = "5. RSI")]
        public bool RequireRsiPeakEvidenceDown { get; set; }

        [Parameter("Avoid Chase: RSI Min", DefaultValue = 43.0, Group = "5. RSI")]
        public double RsiNowMinAvoidChase { get; set; }

        [Parameter("Require RSI Peak Evidence", DefaultValue = true, Group = "5. RSI")]
        public bool RequireRsiPeakEvidence { get; set; }

        [Parameter("RSI Peak Window Bars", DefaultValue = 34, MinValue = 5, Group = "5. RSI")]
        public int RsiPeakWindowBars { get; set; }

        [Parameter("RSI Peak Min", DefaultValue = 59.0, Group = "5. RSI")]
        public double RsiPeakMin { get; set; }

        [Parameter("Block If RSI Max Above", DefaultValue = 81.5, Group = "5. RSI")]
        public double BlockIfRsiMaxAbove { get; set; }

        // ============================================================
        // 6) ACD (Anti-Chop Detector)
        // ============================================================
        [Parameter("Use ACD", DefaultValue = true, Group = "6. ACD")]
        public bool UseAcd { get; set; }

        [Parameter("ACD TF", DefaultValue = "Hour", Group = "6. ACD")]
        public TimeFrame AcdTf { get; set; }

        [Parameter("ACD Window Bars", DefaultValue = 20, MinValue = 5, Group = "6. ACD")]
        public int AcdWindowBars { get; set; }

        [Parameter("ACD Min Range (pips)", DefaultValue = 4.8, MinValue = 0.0, Group = "6. ACD")]
        public double AcdMinRangePips { get; set; }

        [Parameter("ACD Max Range (pips)", DefaultValue = 100.0, MinValue = 0.0, Group = "6. ACD")]
        public double AcdMaxRangePips { get; set; }

        [Parameter("Draw ACD Box", DefaultValue = true, Group = "6. ACD")]
        public bool DrawAcdBox { get; set; }

        // ============================================================
        // 7) Rolling High (fallback level)
        // ============================================================
        [Parameter("Use Rolling High", DefaultValue = true, Group = "7. RollingHigh")]
        public bool UseRollingHigh { get; set; }

        [Parameter("RH TF", DefaultValue = "Hour", Group = "7. RollingHigh")]
        public TimeFrame RollingHighTf { get; set; }

        [Parameter("RH Bars", DefaultValue = 18, MinValue = 5, Group = "7. RollingHigh")]
        public int RollingHighBars { get; set; }

        [Parameter("RH Max Age (bars)", DefaultValue = 34, MinValue = 0, Group = "7. RollingHigh")]
        public int RollingHighMaxAgeBars { get; set; }

        [Parameter("RH Min RSI", DefaultValue = 73.0, Group = "7. RollingHigh")]
        public double RollingHighMinRsi { get; set; }

        [Parameter("RH Trigger Dist (pips)", DefaultValue = 38.0, MinValue = 0.0, Group = "7. RollingHigh")]
        public double RollingHighTriggerDistancePips { get; set; }

        
        [Parameter("RH Min Above (pips)", DefaultValue = 1.0, MinValue = 0.0, Group = "7. RollingHigh")]
        public double RollingHighMinAbovePips { get; set; }
[Parameter("Draw RH Line", DefaultValue = true, Group = "7. RollingHigh")]
        public bool DrawRollingHighLine { get; set; }

        // ============================================================
        // 8) RISK / EXIT
        // ============================================================
        [Parameter("TP Mode", DefaultValue = TakeProfitMode.FixedPips, Group = "8. EXIT")]
        public TakeProfitMode TpMode { get; set; }

        [Parameter("Fixed TP (pips)", DefaultValue = 10.5, MinValue = 0.0, Group = "8. EXIT")]
        public double FixedTpPips { get; set; }

        [Parameter("SL Mode", DefaultValue = StopLossMode.Atr, Group = "8. EXIT")]
        public StopLossMode SlMode { get; set; }

        [Parameter("SL Above Level (pips)", DefaultValue = 9.0, MinValue = 0.0, Group = "8. EXIT")]
        public double SlAboveLevelPips { get; set; }

        [Parameter("Hard Min SL (pips)", DefaultValue = 7.0, MinValue = 0.0, Group = "8. EXIT")]
        public double HardMinSlPips { get; set; }

        [Parameter("Hard Max SL (pips, 0=off)", DefaultValue = 0.0, MinValue = 0.0, Group = "8. EXIT")]
        public double HardMaxSlPips { get; set; }

        // SL ATR
        [Parameter("SL ATR TF", DefaultValue = "Hour", Group = "8. EXIT")]
        public TimeFrame SlAtrTf { get; set; }

        [Parameter("SL ATR Period", DefaultValue = 11, MinValue = 2, Group = "8. EXIT")]
        public int SlAtrPeriod { get; set; }

        [Parameter("SL ATR Multiplier", DefaultValue = 1.8, MinValue = 0.1, Group = "8. EXIT")]
        public double SlAtrMultiplier { get; set; }

        [Parameter("SL ATR Min (pips, 0=off)", DefaultValue = 0.0, MinValue = 0.0, Group = "8. EXIT")]
        public double SlAtrMinPips { get; set; }

        [Parameter("SL ATR Max (pips, 0=off)", DefaultValue = 0.0, MinValue = 0.0, Group = "8. EXIT")]
        public double SlAtrMaxPips { get; set; }

        // RSI Return Exit
        [Parameter("RSI Exit Level", DefaultValue = 40.0, Group = "8. EXIT")]
        public double RsiExitLevel { get; set; }

        [Parameter("RSI Exit Min Hold Bars", DefaultValue = 4, MinValue = 0, Group = "8. EXIT")]
        public int RsiExitMinHoldBars { get; set; }

        [Parameter("RSI Exit Min Profit (pips)", DefaultValue = 4.8, MinValue = 0.0, Group = "8. EXIT")]
        public double RsiExitMinProfitPips { get; set; }

        // Trailing
        [Parameter("Use Trailing Remainder", DefaultValue = true, Group = "8. EXIT")]
        public bool UseTrailingRemainder { get; set; }

        [Parameter("Trail Start (pips)", DefaultValue = 9.0, MinValue = 0.0, Group = "8. EXIT")]
        public double TrailStartPips { get; set; }

        [Parameter("Trail Step (pips)", DefaultValue = 3.0, MinValue = 0.1, Group = "8. EXIT")]
        public double TrailStepPips { get; set; }

        // Validation Exit (RetestFade only)
        [Parameter("Validation Exit Enabled", DefaultValue = false, Group = "8. EXIT")]
        public bool ValidationExitEnabled { get; set; }

        [Parameter("Validation Exit Retest Only", DefaultValue = true, Group = "8. EXIT")]
        public bool ValidationExitRetestOnly { get; set; }

        [Parameter("Validation Exit Bars (m10)", DefaultValue = 3, MinValue = 1, MaxValue = 8, Group = "8. EXIT")]
        public int ValidationExitBars { get; set; }

        [Parameter("Validation Min Favorable Pips", DefaultValue = 1.5, MinValue = 0.0, Step = 0.1, Group = "8. EXIT")]
        public double ValidationMinFavorablePips { get; set; }

        [Parameter("Validation Close Above Entry (pips)", DefaultValue = 0.3, MinValue = 0.0, Step = 0.1, Group = "8. EXIT")]
        public double ValidationCloseAboveEntryPips { get; set; }

        [Parameter("Validation High Above Entry (pips)", DefaultValue = 1.0, MinValue = 0.0, Step = 0.1, Group = "8. EXIT")]
        public double ValidationHighAboveEntryPips { get; set; }

        // ============================================================
        // 9) DIAG / VIS
        // ============================================================
        [Parameter("Debug Print Reasons", DefaultValue = false, Group = "9. DIAG")]
        public bool DebugPrintReasons { get; set; }

        
        [Parameter("Log Skip Reasons", DefaultValue = true, Group = "9. DIAG")]
        public bool LogSkipReasons { get; set; }

        [Parameter("Log Entry Diagnostics", DefaultValue = false, Group = "9. DIAG")]
        public bool LogEntryDiagnostics { get; set; }
[Parameter("Draw Levels", DefaultValue = false, Group = "9. DIAG")]
        public bool DrawLevels { get; set; }

        [Parameter("Draw Entry Markers", DefaultValue = true, Group = "9. DIAG")]
        public bool DrawEntryMarkers { get; set; }

        // ============================================================
        // INTERNALS
        // ============================================================
        private const int JST_OFFSET_HOURS = 9;

        private RelativeStrengthIndex _rsi;
        private Bars _htfBars;
        private Bars _acdBars;
        private Bars _rhBars;
        private Bars _trendBars;
        private ExponentialMovingAverage _trendEma;

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
        enum EntryKind { Unknown, RetestFade, MomentumFailure, MomentumEarlyFailure, LiquiditySweep }

        // position tracking (positionId -> level used in entry)
        private readonly Dictionary<long, long> _posIdToLevelKey = new Dictionary<long, long>();
        private readonly Dictionary<long, double> _posIdToLevelPrice = new Dictionary<long, double>();
        private readonly Dictionary<long, DateTime> _posIdToEntryTime = new Dictionary<long, DateTime>();
        private readonly Dictionary<long, CloseReason> _posIdPendingCloseReason = new Dictionary<long, CloseReason>();
        private readonly Dictionary<long, EntryKind> _entryKindByPosId = new Dictionary<long, EntryKind>();
        private readonly Dictionary<long, double> _mfPeakRsiByPosId = new Dictionary<long, double>();
        private readonly Dictionary<long, double> _mfReboundRsiByPosId = new Dictionary<long, double>();


        // =================================================================
        // Effective values (supports OptimizationMode using OPT:* parameters)
        // =================================================================
        private double EmaRetestMaxDistancePipsEff => OptimizationMode ? Opt_EmaRetestMaxDistancePips : EmaRetestMaxDistancePips;
        private double EarlyDenyCloseAbovePipsEff => Math.Abs(OptimizationMode ? Opt_EarlyDenyCloseAbovePips : EarlyDenyCloseAboveEntryPips);
        private int ExpiryBarsEff => Math.Max(1, OptimizationMode ? Opt_ExpiryBars : ExpiryBars);

        private double ExpiryCutPipsEff
        {
            get
            {
                var v = OptimizationMode ? Opt_ExpiryCutPips : ExpiryCloseIfPipsBelow;
                // Safety: treat positive input as negative (loss threshold)
                if (v > 0) v = -v;
                return v;
            }
        }
        

        private double ExpiryNeverReachedProfitPipsEff => OptimizationMode ? Opt_ExpiryNeverReachedProfitPips : ExpiryNeverReachedProfitPips;
        private double SpeedCutAdversePipsEff => OptimizationMode ? Opt_SpeedCutAdversePips : SpeedCutAdversePips;

private double Pip => Symbol.PipSize;

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
protected override void OnStart()
        {
            _rsi = Indicators.RelativeStrengthIndex(Bars.ClosePrices, RsiPeriod);

            _htfBars = MarketData.GetBars(Htf, SymbolName);
            _acdBars = MarketData.GetBars(AcdTf, SymbolName);
            _rhBars = MarketData.GetBars(RollingHighTf, SymbolName);

            _trendBars = MarketData.GetBars(TrendTimeFrame, SymbolName);
            _trendEma = Indicators.ExponentialMovingAverage(_trendBars.ClosePrices, TrendEmaPeriod);

            UpdateRollingHigh();

            _slAtrBars = MarketData.GetBars(SlAtrTf, SymbolName);
            _slAtr = Indicators.AverageTrueRange(_slAtrBars, SlAtrPeriod, MovingAverageType.Exponential);

            // Safety guards: keep thresholds in sensible ranges
            if (EarlyDenyBars < 1) EarlyDenyBars = 1;
            // Expect a negative threshold (e.g., -4). If user enters positive, auto-fix to negative.
            RebuildLevels(force: true);
        }

        protected override void OnBar()
        {
            int lastClosed = Bars.Count - 2;

            ResetDailyCaches();

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
            public LevelCandidate(double p, string t) { Price = p; Tag = t; }
        }

#if false
        private bool IsH1Uptrend()
        {
            if (!H1UptrendFilterEnabled)
                return false;

            if (_trendBars == null)
                _trendBars = MarketData.GetBars(TimeFrame.Hour, SymbolName);

            int last = _trendBars.Count - 2;
            if (last < 50)
                return false;

            int window = Math.Max(5, H1UptrendWindowBars);
            int start = Math.Max(0, last - window + 1);

            // ★「rolling max」を更新した回数だけ数える（これが重要）
            int newHighCount = 0;
            double rollingMax = _trendBars.HighPrices[start];

            for (int i = start + 1; i <= last; i++)
            {
                double h = _trendBars.HighPrices[i];
                if (h > rollingMax + (0.1 * Pip))
                {
                    newHighCount++;
                    rollingMax = h;
                }
            }

            return newHighCount >= Math.Max(1, H1HigherHighCountMin);
        }
#endif


        private void TrySell(int lastClosed)
        {
            if (Positions.FindAll(BotLabel, SymbolName, TradeType.Sell).Length >= MaxPositions)
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

#if false
            if (IsH1Uptrend())
            {
                Skip("H1 uptrend filter");
                return;
            }
#endif

            if (_levels.Count == 0){ Skip("No levels"); return; }

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

            if (double.IsNaN(bestLv)){ Skip("No candidate level"); return; }

            // Per-level daily limit (JST)
            if (MaxTradesPerLevelPerDay > 0 && GetTradesCountTodayForLevel(bestLv) >= MaxTradesPerLevelPerDay)
            {
                Skip("Level daily cap reached");
                return;
            }

            bool isDownTrend = IsDownTrendByEma();

            // 1) Existing retest fade has priority
            if (TrySellRetestEntry(lastClosed, bestLv, bestTag, isDownTrend))
                return;

            // 2) Liquidity sweep short (failed breakout / stop run)
            if (TrySellLiquiditySweepEntry(lastClosed, bestLv, bestTag, isDownTrend))
                return;

            // 3) Early momentum-failure entry (weaker second push / early stall)
            if (TrySellMomentumEarlyFailureEntry(lastClosed, bestLv, bestTag, isDownTrend))
                return;

            // 4) Double-top / failed-breakout momentum-failure entry
            if (TrySellMomentumFailureEntry(lastClosed, bestLv, bestTag, isDownTrend))
                return;
        }

        
        
        private bool IsRsiWeakReAttackOk(int lastClosed)
        {
            if (!UseRsiWeakReAttackFilter || _rsi == null)
                return true;

            if (lastClosed < 5)
                return true;

            int lookback = Math.Max(5, RsiWeakReAttackLookbackBars);
            int start = Math.Max(1, lastClosed - lookback);

            double peak1Rsi = double.MinValue;
            int peak1Idx = -1;

            for (int i = start; i <= lastClosed - 2; i++)
            {
                double v = _rsi.Result[i];
                if (v > peak1Rsi)
                {
                    peak1Rsi = v;
                    peak1Idx = i;
                }
            }

            // If the recent RSI never reached the contested "hot" zone,
            // do not block the entry with this filter.
            if (peak1Idx < 0 || peak1Rsi < RsiWeakReAttackPeakMinRsi)
                return true;

            double lowRsi = double.MaxValue;
            int lowIdx = -1;
            for (int i = peak1Idx + 1; i <= lastClosed - 1; i++)
            {
                double v = _rsi.Result[i];
                if (v < lowRsi)
                {
                    lowRsi = v;
                    lowIdx = i;
                }
            }

            if (lowIdx < 0)
                return false;

            double dropFromPeak = peak1Rsi - lowRsi;
            if (dropFromPeak < RsiWeakReAttackDropMinRsi)
                return false;

            double peak2Rsi = double.MinValue;
            int peak2Idx = -1;
            for (int i = lowIdx + 1; i <= lastClosed - 1; i++)
            {
                double v = _rsi.Result[i];
                if (v > peak2Rsi)
                {
                    peak2Rsi = v;
                    peak2Idx = i;
                }
            }

            if (peak2Idx < 0)
                return false;

            if (peak2Rsi < RsiWeakReAttackSecondPeakMinRsi)
                return false;

            // The second attack must be weaker than the first one by at least GapMin.
            if (peak2Rsi > (peak1Rsi - RsiWeakReAttackPeakGapMinRsi))
                return false;

            // Current bar should already be turning down from the second peak.
            if (_rsi.Result[lastClosed] >= peak2Rsi)
                return false;

            return true;
        }


        private bool IsRsiFallingOk(int lastClosed)
        {
            if (!UseRsiFallingFilter || _rsi == null)
                return true;

            int lookback = Math.Max(1, RsiFallingLookbackBars);
            if (lastClosed - lookback < 0)
                return true;

            double rsiNow = _rsi.Result[lastClosed];
            double rsiPrev = _rsi.Result[lastClosed - lookback];

            return rsiNow < rsiPrev;
        }

private bool IsNearRecentHighOk(int lastClosed, int lookbackBars, double maxDistancePips)
        {
            if (!UseNearRecentHighFilter)
                return true;

            if (lastClosed < 1)
                return true;

            int lookback = Math.Max(5, lookbackBars);
            int start = Math.Max(0, lastClosed - lookback);
            double recentHigh = double.MinValue;

            for (int i = start; i <= lastClosed - 1; i++)
                recentHigh = Math.Max(recentHigh, Bars.HighPrices[i]);

            if (recentHigh <= 0 || double.IsNegativeInfinity(recentHigh))
                return true;

            double entryRefPrice = Bars.ClosePrices[lastClosed];
            double distFromHighPips = (recentHigh - entryRefPrice) / Pip;

            return distFromHighPips <= maxDistancePips;
        }


private bool TrySellRetestEntry(int lastClosed, double bestLv, string bestTag, bool isDownTrend)
        {
            double tol = TouchTolerancePips * Pip;
            double reject = RejectCloseBelowLevelPips * Pip;

            double h = Bars.HighPrices[lastClosed];
            double close = Bars.ClosePrices[lastClosed];

            bool touched = h >= (bestLv - tol);

            bool rejectedClose = close <= (bestLv - reject);

            bool rejectedWick = false;
            if (RejectByWick)
            {
                double wickMin = WickMinAboveLevelPips * Pip;
                double wickClose = WickCloseBelowLevelPips * Pip;

                if (h >= (bestLv + wickMin) && close <= (bestLv - wickClose))
                    rejectedWick = true;
            }

            bool rejected = rejectedClose || rejectedWick;

            if (!(touched && rejected))
                return false;

            if (!IsRsiQualityOk(lastClosed, isDownTrend)){ Skip("RSI gate"); return false; }

            if (!IsNearRecentHighOk(lastClosed, NearRecentHighLookbackBars, NearRecentHighMaxDistancePips))
            {
                Skip("Near recent high filter");
                return false;
            }

            if (!IsRsiWeakReAttackOk(lastClosed))
            {
                Skip("RSI weak re-attack filter");
                return false;
            }

            if (!IsRsiFallingOk(lastClosed))
            {
                Skip("RSI falling filter");
                return false;
            }

            if (!IsAcdOk()){ Skip("ACD gate"); return false; }

            if (BearCandleRequired && !IsBearConfirmOk(lastClosed)){ Skip("Bear confirm"); return false; }

            return PlaceSellOrder(lastClosed, bestLv, bestTag, EntryKind.RetestFade, double.NaN, double.NaN, "RETEST");
        }

        private bool TrySellLiquiditySweepEntry(int lastClosed, double bestLv, string bestTag, bool isDownTrend)
        {
            if (!UseLiquiditySweepEntry)
                return false;

            if (!isDownTrend)
            {
                Skip("LS downtrend required");
                return false;
            }

            if (!IsAcdOk())
            {
                Skip("LS ACD gate");
                return false;
            }

            if (lastClosed < 3 || _rsi == null)
                return false;

            int lookback = Math.Max(5, LiquiditySweepLookbackBars);
            if (lastClosed <= lookback)
                return false;

            double recentHigh = double.MinValue;
            for (int i = lastClosed - lookback; i <= lastClosed - 1; i++)
                recentHigh = Math.Max(recentHigh, Bars.HighPrices[i]);

            if (recentHigh <= 0)
                return false;

            double sweepBuffer = LiquiditySweepBufferPips * Pip;
            double closeBackBuffer = LiquiditySweepCloseBackBufferPips * Pip;

            double barHigh = Bars.HighPrices[lastClosed];
            double barClose = Bars.ClosePrices[lastClosed];
            double barRsi = _rsi.Result[lastClosed];

            bool sweepHigh = barHigh > (recentHigh + sweepBuffer);
            bool closeBackInside = barClose < (recentHigh - closeBackBuffer);
            bool rsiOk = barRsi >= LiquiditySweepMinRsi;

            if (!IsNearRecentHighOk(lastClosed, NearRecentHighLookbackBars, NearRecentHighMaxDistancePips))
            {
                Skip("LS near recent high filter");
                return false;
            }

            // RWR filter is intentionally NOT applied to Liquidity Sweep.
            // LS is its own sweep/failure structure and should be evaluated independently.

            // Optional extra quality: prefer a bearish close if enabled globally
            if (BearCandleRequired && !IsBearConfirmOk(lastClosed))
            {
                Skip("LS bear confirm");
                return false;
            }

            if (!(sweepHigh && closeBackInside && rsiOk))
                return false;

            if (DebugPrintReasons && LogEntryDiagnostics)
            {
                Print("[LS] t={0:yyyy-MM-dd HH:mm} recentHigh={1:F5} high={2:F5} close={3:F5} rsi={4:F1} lookback={5}",
                      Server.Time, recentHigh, barHigh, barClose, barRsi, lookback);
            }

            return PlaceSellOrder(lastClosed, recentHigh, bestTag + "+LS", EntryKind.LiquiditySweep, double.NaN, double.NaN, "LS");
        }

        private bool TrySellMomentumEarlyFailureEntry(int lastClosed, double bestLv, string bestTag, bool isDownTrend)
        {
            if (!UseMomentumEarlyFailureEntry)
                return false;

            if (!isDownTrend)
            {
                Skip("MFE downtrend required");
                return false;
            }

            if (!IsAcdOk())
            {
                Skip("MFE ACD gate");
                return false;
            }

            if (lastClosed < 8 || _rsi == null)
                return false;

            int lookback = Math.Max(2, MomentumEarlyFailureMaxBarsSincePeak);
            int scanStart = Math.Max(2, lastClosed - lookback);

            bool found = false;
            int foundPeakIdx = -1;
            int foundLowIdx = -1;
            int foundReboundIdx = -1;
            double foundPeakRsi = double.NaN;
            double foundReboundRsi = double.NaN;

            for (int peakIdx = scanStart; peakIdx <= lastClosed - 2; peakIdx++)
            {
                double peakRsi = _rsi.Result[peakIdx];
                if (peakRsi < MomentumEarlyFailurePeakMinRsi)
                    continue;

                if (!(_rsi.Result[peakIdx] >= _rsi.Result[peakIdx - 1] &&
                      _rsi.Result[peakIdx] >= _rsi.Result[peakIdx + 1]))
                    continue;

                double peakPrice = Bars.HighPrices[peakIdx];

                double lowPrice = double.MaxValue;
                int lowIdx = -1;
                for (int i = peakIdx + 1; i <= lastClosed - 1; i++)
                {
                    if (Bars.LowPrices[i] < lowPrice)
                    {
                        lowPrice = Bars.LowPrices[i];
                        lowIdx = i;
                    }
                }

                if (lowIdx < 0 || lowIdx >= lastClosed - 1)
                    continue;

                double dropPips = (peakPrice - lowPrice) / Pip;
                if (dropPips < MomentumEarlyFailureDropMin)
                    continue;

                double reboundHigh = double.MinValue;
                int reboundIdx = -1;
                for (int i = lowIdx + 1; i <= lastClosed - 1; i++)
                {
                    if (Bars.HighPrices[i] > reboundHigh)
                    {
                        reboundHigh = Bars.HighPrices[i];
                        reboundIdx = i;
                    }
                }

                if (reboundIdx < 0)
                    continue;

                double reboundPips = (reboundHigh - lowPrice) / Pip;
                if (reboundPips > MomentumEarlyFailureReboundMax)
                    continue;

                // The entry should still be relatively close to the original peak;
                // otherwise we are just chasing a move already in progress.
                if (Bars.HighPrices[lastClosed] < (peakPrice - MomentumEarlyFailurePeakPriceBufferPips * Pip))
                    continue;

                double reboundRsi = _rsi.Result[reboundIdx];
                if (reboundRsi > peakRsi)
                    continue;

                if (!IsBearBar(lastClosed))
                    continue;

                if (_rsi.Result[lastClosed] >= _rsi.Result[reboundIdx])
                    continue;

                if ((lastClosed - peakIdx) > MomentumEarlyFailureMaxBarsSincePeak)
                    continue;

                found = true;
                foundPeakIdx = peakIdx;
                foundLowIdx = lowIdx;
                foundReboundIdx = reboundIdx;
                foundPeakRsi = peakRsi;
                foundReboundRsi = reboundRsi;
            }

            if (!found)
                return false;

            if (DebugPrintReasons && LogEntryDiagnostics)
            {
                double dropPipsDiag = (Bars.HighPrices[foundPeakIdx] - Bars.LowPrices[foundLowIdx]) / Pip;
                double reboundPipsDiag = (Bars.HighPrices[foundReboundIdx] - Bars.LowPrices[foundLowIdx]) / Pip;
                Print("[MFE] t={0:yyyy-MM-dd HH:mm} peakIdx={1} peakRsi={2:F1} reboundIdx={3} reboundRsi={4:F1} drop={5:F1} rebound={6:F1} barsSincePeak={7}",
                      Server.Time, foundPeakIdx, foundPeakRsi, foundReboundIdx, foundReboundRsi, dropPipsDiag, reboundPipsDiag, lastClosed - foundPeakIdx);
            }

            return PlaceSellOrder(lastClosed, bestLv, bestTag + "+MFE", EntryKind.MomentumEarlyFailure, foundPeakRsi, foundReboundRsi, "MFE");
        }

        private bool TrySellMomentumFailureEntry(int lastClosed, double bestLv, string bestTag, bool isDownTrend)
        {
            if (!UseMomentumFailureEntry)
                return false;

            // This module is meant for sell-side momentum failure inside a downtrend environment.
            if (!isDownTrend)
            {
                Skip("MF downtrend required");
                return false;
            }

            if (!IsAcdOk())
            {
                Skip("MF ACD gate");
                return false;
            }

            if (lastClosed < 8 || _rsi == null)
                return false;

            // Use only fully closed bars. Current entry bar is lastClosed.
            // We require: peak -> drop -> rebound near peak -> current bar turns down.
            int lookback = Math.Max(2, MomentumFailureMaxBarsSincePeak);
            int scanStart = Math.Max(2, lastClosed - lookback);

            bool found = false;
            int foundPeakIdx = -1;
            int foundLowIdx = -1;
            int foundReboundIdx = -1;
            double foundPeakRsi = double.NaN;
            double foundReboundRsi = double.NaN;

            for (int peakIdx = scanStart; peakIdx <= lastClosed - 2; peakIdx++)
            {
                double peakRsi = _rsi.Result[peakIdx];
                if (peakRsi < MomentumFailurePeakMinRsi)
                    continue;

                // Stable local RSI peak on closed bars only
                if (!(_rsi.Result[peakIdx] >= _rsi.Result[peakIdx - 1] &&
                      _rsi.Result[peakIdx] >= _rsi.Result[peakIdx + 1]))
                    continue;

                double peakPrice = Bars.HighPrices[peakIdx];

                // Find the lowest low after the peak and before the rebound sequence
                double lowPrice = double.MaxValue;
                int lowIdx = -1;
                for (int i = peakIdx + 1; i <= lastClosed - 1; i++)
                {
                    if (Bars.LowPrices[i] < lowPrice)
                    {
                        lowPrice = Bars.LowPrices[i];
                        lowIdx = i;
                    }
                }

                if (lowIdx < 0 || lowIdx >= lastClosed - 1)
                    continue;

                double dropPips = (peakPrice - lowPrice) / Pip;
                if (dropPips < MomentumFailureDropMin)
                    continue;

                // Rebound must happen after the low, before the current bar.
                double reboundHigh = double.MinValue;
                int reboundIdx = -1;
                for (int i = lowIdx + 1; i <= lastClosed - 1; i++)
                {
                    if (Bars.HighPrices[i] > reboundHigh)
                    {
                        reboundHigh = Bars.HighPrices[i];
                        reboundIdx = i;
                    }
                }

                if (reboundIdx < 0)
                    continue;

                double reboundPips = (reboundHigh - lowPrice) / Pip;
                if (reboundPips < MomentumFailureReboundMin)
                    continue;

                // Price-side retest of the peak area (allow slight miss below peak; allow slight sweep above peak)
                if (reboundHigh < (peakPrice - MomentumFailurePeakPriceBufferPips * Pip))
                    continue;

                double reboundRsi = _rsi.Result[reboundIdx];

                // RSI-side re-attack: rebound RSI must come back near the original peak,
                // but still remain a failure (not a stronger second momentum push).
                if (reboundRsi > peakRsi)
                    continue;

                if ((peakRsi - reboundRsi) > MomentumFailureRsiPeakGapMax)
                    continue;

                // Current bar must show turn-down after the rebound
                if (!IsBearBar(lastClosed))
                    continue;

                if (_rsi.Result[lastClosed] >= _rsi.Result[reboundIdx])
                    continue;

                // Optional: keep the setup "fresh" from the peak
                if ((lastClosed - peakIdx) > MomentumFailureMaxBarsSincePeak)
                    continue;

                found = true;
                foundPeakIdx = peakIdx;
                foundLowIdx = lowIdx;
                foundReboundIdx = reboundIdx;
                foundPeakRsi = peakRsi;
                foundReboundRsi = reboundRsi;
            }

            if (!found)
                return false;

            if (DebugPrintReasons && LogEntryDiagnostics)
            {
                double dropPipsDiag = (Bars.HighPrices[foundPeakIdx] - Bars.LowPrices[foundLowIdx]) / Pip;
                double reboundPipsDiag = (Bars.HighPrices[foundReboundIdx] - Bars.LowPrices[foundLowIdx]) / Pip;
                Print("[MF] t={0:yyyy-MM-dd HH:mm} peakIdx={1} peakRsi={2:F1} reboundIdx={3} reboundRsi={4:F1} drop={5:F1} rebound={6:F1} barsSincePeak={7}",
                      Server.Time, foundPeakIdx, foundPeakRsi, foundReboundIdx, foundReboundRsi, dropPipsDiag, reboundPipsDiag, lastClosed - foundPeakIdx);
            }

            return PlaceSellOrder(lastClosed, bestLv, bestTag + "+MF", EntryKind.MomentumFailure, foundPeakRsi, foundReboundRsi, "MF");
        }

        private bool PlaceSellOrder(int lastClosed, double bestLv, string bestTag, EntryKind entryKind, double peakRsi, double reboundRsi, string diagTag)
        {
            long vol = ToVolumeLong(Symbol.QuantityToVolumeInUnits(VolumeLots));

            double desiredSlPrice = bestLv + (SlAboveLevelPips * Pip);

            if (SlMode == StopLossMode.Atr && _slAtr != null)
            {
                double atrValue = _slAtr.Result.LastValue;
                double atrPips = (atrValue / Pip) * SlAtrMultiplier;

                if (SlAtrMinPips > 0)
                    atrPips = Math.Max(atrPips, SlAtrMinPips);
                if (SlAtrMaxPips > 0)
                    atrPips = Math.Min(atrPips, SlAtrMaxPips);

                double atrSlPrice = Symbol.Ask + atrPips * Pip;
                desiredSlPrice = Math.Max(desiredSlPrice, atrSlPrice);
            }

            double slPips = (desiredSlPrice - Symbol.Ask) / Pip;

            if (slPips < HardMinSlPips)
                slPips = HardMinSlPips;

            if (HardMaxSlPips > 0 && slPips > HardMaxSlPips)
            {
                Skip(diagTag + " SL too large");
                return false;
            }

            double? tpPips = null;
            if (TpMode == TakeProfitMode.FixedPips || TpMode == TakeProfitMode.Both)
                tpPips = FixedTpPips;

            if (DebugPrintReasons && LogEntryDiagnostics)
            {
                Print("[ENTRY_{0}] t={1:yyyy-MM-dd HH:mm} bestLv={2} tag={3} slPips={4:F1} tpPips={5} rsi={6:F1} peakRsi={7} reboundRsi={8}",
                      diagTag, Server.Time, bestLv, bestTag, slPips,
                      (tpPips.HasValue ? tpPips.Value.ToString("F1") : "null"),
                      _rsi.Result[lastClosed],
                      double.IsNaN(peakRsi) ? "na" : peakRsi.ToString("F1"),
                      double.IsNaN(reboundRsi) ? "na" : reboundRsi.ToString("F1"));
            }

            var result = ExecuteMarketOrder(TradeType.Sell, SymbolName, vol, BotLabel, slPips, tpPips);

            if (result.IsSuccessful)
            {
                if (result.Position != null)
                {
                    _posIdToLevelKey[result.Position.Id] = LevelKey(bestLv);
                    _posIdToLevelPrice[result.Position.Id] = bestLv;
                    _posIdToEntryTime[result.Position.Id] = result.Position.EntryTime;
                    _entryKindByPosId[result.Position.Id] = entryKind;
                    if (!double.IsNaN(peakRsi)) _mfPeakRsiByPosId[result.Position.Id] = peakRsi;
                    if (!double.IsNaN(reboundRsi)) _mfReboundRsiByPosId[result.Position.Id] = reboundRsi;
                }

                _lastEntryBar = Bars.Count - 1;
                _lastEntryTime = Server.Time;

                MarkTradeTodayForLevel(bestLv);

                try
                {
                    _entryLevelByPosId[result.Position.Id] = bestLv;
                    _aboveCloseCountByPosId[result.Position.Id] = 0;
                }
                catch { }

                if (DrawEntryMarkers)
                    DrawSellMarker(result.Position, bestTag, bestLv, lastClosed);

                return true;
            }

            if (DebugPrintReasons)
                Print("Entry rejected by broker: {0}", result.Error);

            return false;
        }

        private bool IsBearBar(int barIndex)
        {
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

        private bool TryValidationExit(Position pos, int lastClosed)
        {
            if (!ValidationExitEnabled)
                return false;

            if (ValidationExitBars < 1)
                return false;

            EntryKind entryKind;
            if (!_entryKindByPosId.TryGetValue(pos.Id, out entryKind))
                return false;

            if (ValidationExitRetestOnly && entryKind != EntryKind.RetestFade)
                return false;

            int barsOpen = BarsSinceEntryUtc(pos.EntryTime);
            if (barsOpen < ValidationExitBars)
                return false;

            // Judge only once at the validation bar.
            if (barsOpen > ValidationExitBars)
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
                Print("[VALIDATION EXIT] pos#{0} kind={1} barsOpen={2} mfe={3:F1} closeAbove={4:F1} highAbove={5:F1}",
                      pos.Id, entryKind, barsOpen, mfePips, closeAboveEntryPips, highAboveEntryPips);
            }

            return CloseWithReason(
                pos,
                CloseReason.ValidationExit,
                string.Format("ValidationExit mfe={0:F1} closeAbove={1:F1} highAbove={2:F1}",
                              mfePips, closeAboveEntryPips, highAboveEntryPips)
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
            _posIdToEntryTime.Remove(pos.Id);
            _entryKindByPosId.Remove(pos.Id);
            _mfPeakRsiByPosId.Remove(pos.Id);
            _mfReboundRsiByPosId.Remove(pos.Id);

            return true;
        }



        private void ManageOpenPositions()
        {
            var sells = Positions.FindAll(BotLabel, SymbolName, TradeType.Sell);
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

                var keys5 = new List<long>(_mfPeakRsiByPosId.Keys);
                foreach (var k in keys5)
                    if (!openIds.Contains(k)) _mfPeakRsiByPosId.Remove(k);

                var keys6 = new List<long>(_mfReboundRsiByPosId.Keys);
                foreach (var k in keys6)
                    if (!openIds.Contains(k)) _mfReboundRsiByPosId.Remove(k);
            }
            catch { }

            int lastClosed = Bars.Count - 2;
            if (lastClosed < 2)
                return;

            double rNow = _rsi.Result[lastClosed];

            foreach (var pos in sells)
            {
                // v14.1: early post-entry validation (RetestFade only by default)
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
if (EarlyDenyEnabled && EarlyDenyCloseAbovePipsEff > 0)
{
    int bse = BarsSinceEntryUtc(pos.EntryTime);
    if (bse > 0 && bse <= EarlyDenyBars)
    {
        double closePx = Bars.ClosePrices[lastClosed];

        double refLevel;
        if (!_entryLevelByPosId.TryGetValue(pos.Id, out refLevel))
            refLevel = pos.EntryPrice;

        if (closePx > refLevel + (EarlyDenyCloseAbovePipsEff * Pip))
        {

                            var res = ClosePosition(pos);
                            if (res.IsSuccessful)
                            {
                                if (DebugPrintReasons) Print("[EXIT] EarlyDeny: pos#{0} close={1} > entry+{2}p bars={3}", pos.Id, closePx, EarlyDenyCloseAbovePipsEff, bse);
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

    double cutBelow = ExpiryCutPipsEff;
    if (cutBelow > 0) cutBelow = -cutBelow; // safety

    if (bse >= ExpiryBarsEff && maxp < ExpiryNeverReachedProfitPipsEff && pos.Pips <= cutBelow)
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
                if (SpeedCutEnabled && SpeedCutAdversePipsEff > 0)
                {
                    int bse = BarsSinceEntryUtc(pos.EntryTime);
                    if (bse > 0 && bse <= SpeedCutBars && pos.Pips <= -SpeedCutAdversePipsEff)
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
        private bool IsRsiQualityOk(int lastClosed, bool isDownTrend)
        {
            double rNow = _rsi.Result[lastClosed];

            if (rNow < RsiNowMinAvoidChase)
            {
                if (DebugPrintReasons) Print("Skip entry: RSI chase-avoid rNow={0:F1} < {1:F1}", rNow, RsiNowMinAvoidChase);
                return false;
            }

            double minNow = isDownTrend ? RsiNowMinDown : RsiNowMin;
            double maxNow = isDownTrend ? RsiNowMaxDown : RsiNowMax;

            if (rNow < minNow || rNow > maxNow)
            {
                if (DebugPrintReasons) Print("Skip entry: RSI out of band rNow={0:F1} not in [{1:F1}..{2:F1}] (downTrend={3})", rNow, minNow, maxNow, isDownTrend);
                return false;
            }

            // Overheat block
            double maxInWindow = rNow;
            int start = Math.Max(0, lastClosed - Math.Max(5, RsiPeakWindowBars) + 1);
            for (int i = start; i <= lastClosed; i++)
                maxInWindow = Math.Max(maxInWindow, _rsi.Result[i]);

            if (maxInWindow >= BlockIfRsiMaxAbove)
            {
                if (DebugPrintReasons) Print("Skip entry: RSI max in window too high {0:F1} >= {1:F1}", maxInWindow, BlockIfRsiMaxAbove);
                return false;
            }

            bool requirePeak = isDownTrend ? RequireRsiPeakEvidenceDown : RequireRsiPeakEvidence;

            if (requirePeak)
            {
                double peak = double.MinValue;
                for (int i = start; i <= lastClosed; i++)
                    peak = Math.Max(peak, _rsi.Result[i]);

                if (peak < RsiPeakMin)
                {
                    if (DebugPrintReasons) Print("Skip entry: RSI peak evidence insufficient peak={0:F1} < {1:F1}", peak, RsiPeakMin);
                    return false;
                }
            }

            return true;
        }

        private bool IsBearConfirmOk(int lastClosed)
        {
            double open = Bars.OpenPrices[lastClosed];
            double close = Bars.ClosePrices[lastClosed];
            double high = Bars.HighPrices[lastClosed];
            double low = Bars.LowPrices[lastClosed];

            // Must be bearish
            if (close >= open)
                return false;

            double body = Math.Abs(open - close);
            double upperWick = high - Math.Max(open, close);
            double lowerWick = Math.Min(open, close) - low;

            double bodyPips = body / Pip;

            if (bodyPips < BearMinBodyPips)
                return false;

            // Upper wick must not dominate too much
            if (body > 0 && upperWick / body > BearMaxUpperWickRatio)
                return false;

            // (lowerWick unused but kept for possible future constraints)
            return true;
        }

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

        // =========================
        // Rolling high + levels
        // =========================
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

            Chart.DrawHorizontalLine(name, _rollingHigh, Color.Goldenrod, 1, LineStyle.DotsRare);
        }

        private void RebuildLevels(bool force)
        {
            int bar = Bars.Count - 1;
            if (!force && bar - _lastLevelsRebuildBar < 20)
                return;

            if (_htfBars == null)
                _htfBars = MarketData.GetBars(Htf, SymbolName);

            int last = _htfBars.Count - 2;
            if (last < 50)
                return;

            int lookback = Math.Min(HtfLookbackBars, last - 2);
            int start = Math.Max(0, last - lookback);

            var swings = new List<double>();

            for (int i = start + SwingLeftBars; i <= last - SwingRightBars; i++)
            {
                double hi = _htfBars.HighPrices[i];
                bool isSwing = true;

                for (int l = 1; l <= SwingLeftBars; l++)
                {
                    if (_htfBars.HighPrices[i - l] >= hi)
                    {
                        isSwing = false;
                        break;
                    }
                }
                if (!isSwing) continue;

                for (int r = 1; r <= SwingRightBars; r++)
                {
                    if (_htfBars.HighPrices[i + r] >= hi)
                    {
                        isSwing = false;
                        break;
                    }
                }
                if (!isSwing) continue;

                swings.Add(hi);
            }

            // Merge nearby levels
            swings.Sort();
            var merged = new List<double>();

            double mergeDist = MergeDistancePips * Pip;
            foreach (var lv in swings)
            {
                if (merged.Count == 0)
                {
                    merged.Add(lv);
                    continue;
                }

                double lastLv = merged[merged.Count - 1];
                if (Math.Abs(lv - lastLv) <= mergeDist)
                {
                    // keep the higher one for resistance
                    merged[merged.Count - 1] = Math.Max(lastLv, lv);
                }
                else
                {
                    merged.Add(lv);
                }
            }

            // Keep last N (highest)
            merged.Sort();
            merged.Reverse();

            _levels.Clear();
            for (int i = 0; i < merged.Count && i < MaxActiveLevels; i++)
                _levels.Add(merged[i]);

            _levels.Sort(); // ascending for convenience

            if (DrawLevels)
                DrawLevelLines();

            _lastLevelsRebuildBar = bar;
        }

        private void DrawLevelLines()
        {
            // Clear old
            for (int i = 0; i < 50; i++)
                Chart.RemoveObject("LVL_" + i);

            for (int i = 0; i < _levels.Count; i++)
                Chart.DrawHorizontalLine("LVL_" + i, _levels[i], Color.Orange, 1, LineStyle.Solid);
        }

        
        private bool IsDownTrendByEma()
        {
            if (_trendBars == null || _trendEma == null)
                return false;

            var shift = TrendEmaShiftBars;
            var lookback = Math.Max(1, EmaDownSlopeLookbackBars);

            // Need enough bars for Last(shift + lookback)
            if (_trendBars.Count < (shift + lookback + 5))
                return false;

            var emaNow = _trendEma.Result.Last(shift);
            var emaPast = _trendEma.Result.Last(shift + lookback);

            // slope in pips per bar
            var slopePipsPerBar = (emaNow - emaPast) / Symbol.PipSize / lookback;

            // Downtrend: EMA is sloping down enough AND price is below EMA
            var trendClose = _trendBars.ClosePrices.Last(shift);
            var priceBelow = trendClose < emaNow;

            return priceBelow && slopePipsPerBar <= -Math.Abs(EmaDownSlopeMinPipsPerBar);
        }

private List<LevelCandidate> GetLevelCandidates(double bid, int lastClosed)
        {
            var list = new List<LevelCandidate>();

            // HTF levels
            for (int i = 0; i < _levels.Count; i++)
                list.Add(new LevelCandidate(_levels[i], "H4"));

            // Rolling High candidate (optional)
            if (UseRollingHigh && !double.IsNaN(_rollingHigh))
            {
                if (_rollingHighAgeBars <= RollingHighMaxAgeBars)
                {
                    double rsi = _rsi.Result[lastClosed];
                    if (rsi >= RollingHighMinRsi)
                    {
                        double distPips = (_rollingHigh - bid) / Pip;
                        if (distPips <= RollingHighTriggerDistancePips && distPips >= RollingHighMinAbovePips)
                        {
                            // Add only if not too close to an existing level
                            bool tooClose = false;
                            double mergeDist = MergeDistancePips * Pip;

                            foreach (var lv in _levels)
                            {
                                if (Math.Abs(lv - _rollingHigh) <= mergeDist)
                                {
                                    tooClose = true;
                                    break;
                                }
                            }

                            // Also avoid rolling-high when ACD upper is "too near" (keeps logic consistent with your earlier intent)
                            // If ACD box exists, and RH is near upper boundary, skip RH to avoid clutter.
                            if (!tooClose && !double.IsNaN(_acdUpper))
                            {
                                double dUpper = Math.Abs(_acdUpper - _rollingHigh) / Pip;
                                if (dUpper <= 5.0) // fixed small guard
                                    tooClose = true;
                            }

                            if (!tooClose)
                                list.Add(new LevelCandidate(_rollingHigh, "RH"));
                        }
                    }
                }
            }


            // EMA retest level (optional): helps catch pullbacks in a downtrend where fixed resistance levels are too far.
            if (UseEmaRetestLevel && IsDownTrendByEma())
            {
                var ema = _trendEma.Result.Last(TrendEmaShiftBars);
                var level = ema + EmaRetestOffsetPips * Pip;
                var distPips = (level - bid) / Pip;

                if (distPips >= 0 && distPips <= EmaRetestMaxDistancePipsEff)
                    list.Add(new LevelCandidate(level, "EMA"));
            }

            return list;
        }

        // =========================
        // Visuals
        // =========================
        private void DrawSellMarker(Position pos, string tag, double level, int barIndex)
        {
            string name = "SELL_" + pos.Id;
            Chart.RemoveObject(name);

            Chart.DrawIcon(name, ChartIconType.DownArrow, barIndex, pos.EntryPrice, Color.Red);
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