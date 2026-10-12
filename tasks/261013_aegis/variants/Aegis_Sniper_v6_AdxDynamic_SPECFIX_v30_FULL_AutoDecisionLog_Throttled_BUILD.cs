// =================================================================================================
// Aegis Sniper v6 (AdxDynamic) - SPECFIX v29
// Machine/Instance: Aegis Semi-auto 01 (ID970 base)
// Notes: Fix Timer.Start(seconds) (was mistakenly *1000). Dashboard now appears immediately on start.
// Built: 2026-02-23
// =================================================================================================

using System;
using System.Linq;
using System.Collections.Generic;
using System.Threading;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    public enum TradeDir { SellOnly, BuyOnly, Both, Auto }
    public enum WaveMode { FixedPips, AtrMultiplier }

    public enum SemiAutoMode { FullAuto, SemiAuto }

    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class Aegis_Sniper_v6_AdxDynamic : Robot
    {
        
        // =================================================================
        // BUILD
        // =================================================================
        private const string BUILD_VERSION = "v30";

// =================================================================
        // [9] OPTIMIZATION MODE
        // =================================================================
        [Parameter("⚡ Optimization Mode", DefaultValue = false, Group = "9. OPTIMIZATION")]
        public bool OptimizationMode { get; set; }

        [Parameter("Legacy Skip Dashboard (deprecated)", DefaultValue = true, Group = "9. OPTIMIZATION")]
        public bool SkipDashboard { get; set; }


        [Parameter("Show Dashboard", DefaultValue = false, Group = "9. OPTIMIZATION")]
        public bool ShowDashboard { get; set; }
        [Parameter("Skip Complex Logs", DefaultValue = true, Group = "9. OPTIMIZATION")]
        public bool SkipComplexLogs { get; set; }

        [Parameter("Position Cache Sec", DefaultValue = 5, MinValue = 1, Group = "9. OPTIMIZATION")]
        public int PositionCacheSeconds { get; set; }

        // =================================================================
        // [0] COMMAND
        // =================================================================
        // =================================================================
// [0] SEMI-AUTO (Signal + Manual Entry + Bot Exit)
// =================================================================
[Parameter("Entry Mode", DefaultValue = SemiAutoMode.SemiAuto, Group = "0. SEMI-AUTO")]
public SemiAutoMode EntryMode { get; set; }

[Parameter("Signal Arm Window (min)", DefaultValue = 10, MinValue = 1, Group = "0. SEMI-AUTO")]
public int SignalArmWindowMin { get; set; }

[Parameter("Signal Max Life (min)", DefaultValue = 60, MinValue = 5, Group = "0. SEMI-AUTO")]
public int SignalMaxLifeMin { get; set; }

[Parameter("KeepAlive Email Interval (min)", DefaultValue = 5, MinValue = 1, Group = "0. SEMI-AUTO")]
public int KeepAliveEmailIntervalMin { get; set; }

[Parameter("Notify Start (JST)", DefaultValue = 9.0, Group = "0. SEMI-AUTO")]
public double NotifyStartJst { get; set; }

[Parameter("Notify End (JST)", DefaultValue = 24.0, Group = "0. SEMI-AUTO")]
public double NotifyEndJst { get; set; }

[Parameter("Use cTrader Popup", DefaultValue = true, Group = "0. SEMI-AUTO")]
public bool UseCtraderPopup { get; set; }

[Parameter("Use Email", DefaultValue = true, Group = "0. SEMI-AUTO")]
public bool UseEmailNotify { get; set; }

[Parameter("Email From", DefaultValue = "", Group = "0. SEMI-AUTO")]
public string EmailFrom { get; set; }

[Parameter("Email To", DefaultValue = "", Group = "0. SEMI-AUTO")]
public string EmailTo { get; set; }

[Parameter("Email Subject Prefix", DefaultValue = "[AegisSignal]", Group = "0. SEMI-AUTO")]
public string EmailSubjectPrefix { get; set; }

[Parameter("Signal Prefix", DefaultValue = "AG", Group = "0. SEMI-AUTO")]
public string SignalPrefix { get; set; }

[Parameter("Sell Code", DefaultValue = "S01", Group = "0. SEMI-AUTO")]
public string SellCode { get; set; }

[Parameter("Buy Code", DefaultValue = "B01", Group = "0. SEMI-AUTO")]
public string BuyCode { get; set; }

[Parameter("Adopt Manual Positions", DefaultValue = true, Group = "0. SEMI-AUTO")]
public bool AdoptManualPositions { get; set; }

[Parameter("Initial SL (pips)", DefaultValue = 15, MinValue = 1, Group = "0. SEMI-AUTO")]
public double SemiAutoInitialSlPips { get; set; }

[Parameter("Initial TP (pips)", DefaultValue = 15, MinValue = 0, Group = "0. SEMI-AUTO")]
public double SemiAutoInitialTpPips { get; set; }

[Parameter("Stop managing if user changes SL/TP", DefaultValue = true, Group = "0. SEMI-AUTO")]
public bool StopManagingOnManualChange { get; set; }

[Parameter("Immediate Cancel: VolBlock", DefaultValue = true, Group = "0. SEMI-AUTO")]
public bool ImmediateCancelVolBlock { get; set; }

[Parameter("Immediate Cancel: ManualBounds", DefaultValue = true, Group = "0. SEMI-AUTO")]
public bool ImmediateCancelManualBounds { get; set; }

[Parameter("Immediate Cancel: RangeBreak", DefaultValue = true, Group = "0. SEMI-AUTO")]
public bool ImmediateCancelRangeBreak { get; set; }

[Parameter("Immediate Cancel: SlotBlock", DefaultValue = true, Group = "0. SEMI-AUTO")]
public bool ImmediateCancelSlotBlock { get; set; }

[Parameter("Trade Direction", DefaultValue = TradeDir.Both, Group = "0. COMMAND")]
        public TradeDir Direction { get; set; }

        [Parameter("Base Volume (Units)", DefaultValue = 10000, MinValue = 1, Group = "0. COMMAND")]
        public double BaseVolume { get; set; }

        [Parameter("Magic Number", DefaultValue = 1515, Group = "0. COMMAND")]
        public int MagicNumber { get; set; }

        [Parameter("Max Spread (Pips)", DefaultValue = 3, Group = "0. COMMAND")]
        public double MaxSpread { get; set; }

        // --- Scale Out ---
        [Parameter("Enable Scale Out", DefaultValue = true, Group = "0. COMMAND")]
        public bool EnableScaleOut { get; set; }

        [Parameter("Scale Out Profit (Pips)", DefaultValue = 10, Group = "0. COMMAND")]
        public double ScaleOutPips { get; set; }

        [Parameter("Scale Out Ratio (0.5=50%)", DefaultValue = 0.5, MinValue = 0.1, MaxValue = 0.9, Group = "0. COMMAND")]
        public double ScaleOutRatio { get; set; }

        // --- Dynamic Exit ---
        [Parameter("Use Dynamic TP", DefaultValue = true, Group = "0. COMMAND")]
        public bool UseDynamicTP { get; set; }

        [Parameter("Dynamic TP ATR Multiplier", DefaultValue = 1.5, MinValue = 0.5, Group = "0. COMMAND")]
        public double DynamicTP_ATR_Multiplier { get; set; }

        [Parameter("Dynamic TP Min Pips", DefaultValue = 8, MinValue = 1, Group = "0. COMMAND")]
        public double DynamicTP_MinPips { get; set; }

        [Parameter("Auto Breakeven", DefaultValue = true, Group = "0. COMMAND")]
        public bool AutoBreakeven { get; set; }

        // --- Fixed TP/SL ---
        [Parameter("Take Profit (Pips)", DefaultValue = 15, Group = "0. COMMAND")]
        public double TakeProfitPips { get; set; }

        [Parameter("Stop Loss (Pips)", DefaultValue = 60, Group = "0. COMMAND")]
        public double StopLossPips { get; set; }

        // --- AUTO Direction ---
        [Parameter("AUTO: MA Period (H4)", DefaultValue = 20, MinValue = 1, Group = "0. COMMAND")]
        public int AutoMaPeriod { get; set; }

        [Parameter("AUTO: MA Type (H4)", DefaultValue = MovingAverageType.Exponential, Group = "0. COMMAND")]
        public MovingAverageType AutoMaType { get; set; }

        [Parameter("AUTO: Lookback Bars (H4)", DefaultValue = 3, MinValue = 1, Group = "0. COMMAND")]
        public int AutoLookbackBars { get; set; }

        [Parameter("AUTO: Slope Threshold (Pips/Bar)", DefaultValue = 0.2, MinValue = 0, Group = "0. COMMAND")]
        public double AutoSlopeThresholdPipsPerBar { get; set; }


        [Parameter("AUTO: Log Decision Basis", DefaultValue = false, Group = "0. COMMAND")]
        public bool AutoLogDecisionBasis { get; set; }

        [Parameter("AUTO: Log Only On Change", DefaultValue = true, Group = "0. COMMAND")]
        public bool AutoLogOnlyOnChange { get; set; }

        [Parameter("AUTO: Log Per H4 Bar", DefaultValue = true, Group = "0. COMMAND")]
        public bool AutoLogPerH4Bar { get; set; }

        [Parameter("AUTO: Log Min Interval (Sec)", DefaultValue = 600, MinValue = 0, Group = "0. COMMAND")]
        public int AutoLogMinIntervalSec { get; set; }

        [Parameter("AUTO: Max Logs Per Day", DefaultValue = 120, MinValue = 0, Group = "0. COMMAND")]
        public int AutoMaxLogsPerDay { get; set; }

        // =================================================================
        // [1] MANUAL BOUNDS
        // =================================================================
        [Parameter("Use Manual Bounds", DefaultValue = false, Group = "1. MANUAL BOUNDS")]
        public bool UseManualBounds { get; set; }

        [Parameter("Manual Upper Price", DefaultValue = 0, Group = "1. MANUAL BOUNDS")]
        public double ManualUpperPrice { get; set; }

        [Parameter("Manual Lower Price", DefaultValue = 0, Group = "1. MANUAL BOUNDS")]
        public double ManualLowerPrice { get; set; }

        [Parameter("Manual Upper StopOut (Pips)", DefaultValue = 0, MinValue = 0, Group = "1. MANUAL BOUNDS")]
        public double ManualUpperStopOutPips { get; set; }

        [Parameter("Manual Lower StopOut (Pips)", DefaultValue = 0, MinValue = 0, Group = "1. MANUAL BOUNDS")]
        public double ManualLowerStopOutPips { get; set; }

        [Parameter("Use Auto Bounds Shift", DefaultValue = true, Group = "1. MANUAL BOUNDS")]
        public bool UseAutoBoundsShift { get; set; }

        [Parameter("Auto Shift TF", DefaultValue = "h1", Group = "1. MANUAL BOUNDS")]
        public TimeFrame AutoShiftTimeFrame { get; set; }

        [Parameter("Breakout Buffer (Pips)", DefaultValue = 5, MinValue = 0, Group = "1. MANUAL BOUNDS")]
        public double AutoShiftBreakoutBufferPips { get; set; }

        [Parameter("Shift Cooldown (Min)", DefaultValue = 360, MinValue = 0, Group = "1. MANUAL BOUNDS")]
        public int AutoShiftCooldownMin { get; set; }

        [Parameter("Shift Affects Grid Add", DefaultValue = true, Group = "1. MANUAL BOUNDS")]
        public bool AutoShiftAffectsGridAdd { get; set; }

        [Parameter("Reset Bounds On Start", DefaultValue = true, Group = "1. MANUAL BOUNDS")]
        public bool AutoShiftResetOnStart { get; set; }

        // =================================================================
        // [2] ENVIRONMENT (ADX + ATR)
        // =================================================================
        [Parameter("Use ADX Filter", DefaultValue = true, Group = "2. ENVIRONMENT")]
        public bool UseAdxFilter { get; set; }

        [Parameter("ADX Period", DefaultValue = 14, Group = "2. ENVIRONMENT")]
        public int AdxPeriod { get; set; }

        [Parameter("Min ADX for Trade", DefaultValue = 20, MinValue = 10, Group = "2. ENVIRONMENT")]
        public double MinAdxForTrade { get; set; }

        [Parameter("Max ADX for Counter", DefaultValue = 45, MinValue = 30, Group = "2. ENVIRONMENT")]
        public double MaxAdxForCounter { get; set; }

        [Parameter("ADX Warning Threshold", DefaultValue = 25, MinValue = 10, Group = "2. ENVIRONMENT")]
        public double AdxWarningThreshold { get; set; }

        [Parameter("Auto Suppress on Low/High ADX", DefaultValue = false, Group = "2. ENVIRONMENT")]
        public bool AutoSuppressAdx { get; set; }

        // --- ATR Normalization ---
        [Parameter("Use ATR Normalization", DefaultValue = false, Group = "2. ENVIRONMENT")]
        public bool UseAtrNormalization { get; set; }

        [Parameter("TP ATR Multiplier", DefaultValue = 1, MinValue = 0.5, Group = "2. ENVIRONMENT")]
        public double TpAtrMultiplier { get; set; }

        [Parameter("SL ATR Multiplier", DefaultValue = 3, MinValue = 1.0, Group = "2. ENVIRONMENT")]
        public double SlAtrMultiplier { get; set; }

        [Parameter("Step ATR Multiplier", DefaultValue = 0.5, MinValue = 0.1, Group = "2. ENVIRONMENT")]
        public double StepAtrMultiplier { get; set; }

        // --- ADX Dynamic Adjustments (NEW) ---
        [Parameter("Enable ADX Dynamic TP/SL", DefaultValue = true, Group = "2. ENVIRONMENT")]
        public bool EnableAdxDynamicAdjustment { get; set; }

        [Parameter("ADX Low Threshold (Range)", DefaultValue = 20, MinValue = 10, Group = "2. ENVIRONMENT")]
        public double AdxLowThreshold { get; set; }

        [Parameter("ADX High Threshold (Trend)", DefaultValue = 35, MinValue = 25, Group = "2. ENVIRONMENT")]
        public double AdxHighThreshold { get; set; }

        [Parameter("ADX Range TP/SL Multiplier", DefaultValue = 0.8, MinValue = 0.5, MaxValue = 1.0, Group = "2. ENVIRONMENT")]
        public double AdxRangeMultiplier { get; set; }

        [Parameter("ADX Trend TP/SL Multiplier", DefaultValue = 1.5, MinValue = 1.0, MaxValue = 3.0, Group = "2. ENVIRONMENT")]
        public double AdxTrendMultiplier { get; set; }

        [Parameter("ADX Range Step Multiplier", DefaultValue = 0.7, MinValue = 0.5, MaxValue = 1.0, Group = "2. ENVIRONMENT")]
        public double AdxRangeStepMultiplier { get; set; }

        [Parameter("ADX Trend Step Multiplier", DefaultValue = 1.5, MinValue = 1.0, MaxValue = 3.0, Group = "2. ENVIRONMENT")]
        public double AdxTrendStepMultiplier { get; set; }

        // =================================================================
        // [3] EXIT STRATEGY
        // =================================================================
        [Parameter("Use Time Stop", DefaultValue = false, Group = "3. EXIT STRATEGY")]
        public bool UseTimeStop { get; set; }

        [Parameter("Max Hold (Min)", DefaultValue = 240, MinValue = 1, Group = "3. EXIT STRATEGY")]
        public int MaxHoldMinutes { get; set; }


        [Parameter("Max Hold Buy (Min)", DefaultValue = 90, MinValue = 1, Group = "3. EXIT STRATEGY")]
        public int MaxHoldBuyMinutes { get; set; }
        [Parameter("Time Stop Only If Losing", DefaultValue = true, Group = "3. EXIT STRATEGY")]
        public bool TimeStopOnlyIfLosing { get; set; }

        [Parameter("Time Stop Min Loss (Pips)", DefaultValue = 0, MinValue = 0, Group = "3. EXIT STRATEGY")]
        public double TimeStopMinLossPips { get; set; }

        [Parameter("Time Stop Cooldown (Min)", DefaultValue = 0, MinValue = 0, Group = "3. EXIT STRATEGY")]
        public int TimeStopCooldownMin { get; set; }

        [Parameter("Vol Max Hold (Min)", DefaultValue = 120, MinValue = 1, Group = "3. EXIT STRATEGY")]
        public int VolMaxHoldMinutes { get; set; }

        [Parameter("Enable Expiry TP", DefaultValue = false, Group = "3. EXIT STRATEGY")]
        public bool EnableExpiryTp { get; set; }

        [Parameter("Expiry Minutes", DefaultValue = 0, MinValue = 0, Group = "3. EXIT STRATEGY")]
        public int ExpiryMinutes { get; set; }

        [Parameter("Expiry TakeProfit (Pips)", DefaultValue = 0, MinValue = 0, Group = "3. EXIT STRATEGY")]
        public double ExpiryTakeProfitPips { get; set; }

        // =================================================================
        // [4] GRID & POSITION
        // =================================================================
        [Parameter("Max Layers (Legacy)", DefaultValue = 1, MinValue = 1, Group = "4. GRID & POSITION")]
        public int MaxLayers { get; set; }

        [Parameter("Max Layers Sell (0=Legacy)", DefaultValue = 4, MinValue = 0, Group = "4. GRID & POSITION")]
        public int MaxLayersSell { get; set; }

        [Parameter("Max Layers Buy (0=Legacy)", DefaultValue = 2, MinValue = 0, Group = "4. GRID & POSITION")]
        public int MaxLayersBuy { get; set; }

        [Parameter("Grid Step (Pips)", DefaultValue = 13, Group = "4. GRID & POSITION")]
        public double StepPips { get; set; }

        [Parameter("Enable Grid Add", DefaultValue = false, Group = "4. GRID & POSITION")]
        public bool EnableGridAdd { get; set; }

        [Parameter("Max Grid Adds Sell", DefaultValue = 0, MinValue = 0, Group = "4. GRID & POSITION")]
        public int MaxGridAddsSell { get; set; }

        [Parameter("Max Grid Adds Buy", DefaultValue = 0, MinValue = 0, Group = "4. GRID & POSITION")]
        public int MaxGridAddsBuy { get; set; }

        [Parameter("Max Exposure Sell (Units)", DefaultValue = 0, MinValue = 0, Group = "4. GRID & POSITION")]
        public double MaxExposureUnitsSell { get; set; }

        [Parameter("Max Exposure Buy (Units)", DefaultValue = 0, MinValue = 0, Group = "4. GRID & POSITION")]
        public double MaxExposureUnitsBuy { get; set; }

        [Parameter("Confirmation Wait (Bars)", DefaultValue = 0, MinValue = 0, Group = "4. GRID & POSITION")]
        public int ConfirmationWait { get; set; }

        [Parameter("Virtual TF Multiplier", DefaultValue = 1, MinValue = 1, Group = "4. GRID & POSITION")]
        public int VirtualMultiplier { get; set; }

        // =================================================================
        // [5] TIME LOGIC
        // =================================================================
        [Parameter("Work Time Start (JST)", DefaultValue = 0, Group = "5. TIME LOGIC")]
        public double W1S { get; set; }

        [Parameter("Work Time End (JST)", DefaultValue = 24, Group = "5. TIME LOGIC")]
        public double W1E { get; set; }

        [Parameter("Block Rollover", DefaultValue = true, Group = "5. TIME LOGIC")]
        public bool BlockRollover { get; set; }

        [Parameter("Rollover Block Start (JST)", DefaultValue = 5.8, Group = "5. TIME LOGIC")]
        public double RollBlockStart { get; set; }

        [Parameter("Rollover Block End (JST)", DefaultValue = 7.2, Group = "5. TIME LOGIC")]
        public double RollBlockEnd { get; set; }

        [Parameter("Strategic Pause", DefaultValue = true, Group = "5. TIME LOGIC")]
        public bool UseStrategicPause { get; set; }

        [Parameter("Pause Start (JST)", DefaultValue = 21.2, Group = "5. TIME LOGIC")]
        public double PauseStart { get; set; }

        [Parameter("Pause End (JST)", DefaultValue = 25.75, Group = "5. TIME LOGIC")]
        public double PauseEnd { get; set; }

        [Parameter("Slot 1 (JST)", DefaultValue = 0, Group = "5. TIME LOGIC")]
        public double Slot1 { get; set; }

        [Parameter("Slot 2 (JST)", DefaultValue = 0, Group = "5. TIME LOGIC")]
        public double Slot2 { get; set; }

        [Parameter("Slot 3 (JST)", DefaultValue = 0, Group = "5. TIME LOGIC")]
        public double Slot3 { get; set; }

        [Parameter("Slot 4 (JST)", DefaultValue = -0.2, Group = "5. TIME LOGIC")]
        public double Slot4 { get; set; }

        [Parameter("Slot Duration (Min)", DefaultValue = 15, Group = "5. TIME LOGIC")]
        public int SlotDur { get; set; }

        [Parameter("Use Friday Exit", DefaultValue = true, Group = "5. TIME LOGIC")]
        public bool UseFridayExit { get; set; }

        [Parameter("Friday Exit (JST)", DefaultValue = 28, Group = "5. TIME LOGIC")]
        public double FridayExitJst { get; set; }

        [Parameter("Friday No-New Before (Hours)", DefaultValue = 3, MinValue = 0, Group = "5. TIME LOGIC")]
        public double FridayNoNewBeforeHours { get; set; }

        [Parameter("Friday Exit Close Positions", DefaultValue = true, Group = "5. TIME LOGIC")]
        public bool FridayExitClosePositions { get; set; }

        [Parameter("Friday Exit Hold Until Monday", DefaultValue = true, Group = "5. TIME LOGIC")]
        public bool FridayExitHoldUntilMonday { get; set; }

        [Parameter("Mon Trade", DefaultValue = true, Group = "5. TIME LOGIC")]
        public bool TradeMon { get; set; }

        [Parameter("Fri Trade", DefaultValue = true, Group = "5. TIME LOGIC")]
        public bool TradeFri { get; set; }

        [Parameter("Use PreNY Close", DefaultValue = true, Group = "5. TIME LOGIC")]
        public bool UsePreNyClose { get; set; }

        [Parameter("PreNY Close Mon", DefaultValue = true, Group = "5. TIME LOGIC")]
        public bool PreNyMon { get; set; }

        [Parameter("PreNY Close Tue", DefaultValue = true, Group = "5. TIME LOGIC")]
        public bool PreNyTue { get; set; }

        [Parameter("PreNY Close Wed", DefaultValue = true, Group = "5. TIME LOGIC")]
        public bool PreNyWed { get; set; }

        [Parameter("PreNY Close Thu", DefaultValue = true, Group = "5. TIME LOGIC")]
        public bool PreNyThu { get; set; }

        [Parameter("PreNY Close Fri", DefaultValue = true, Group = "5. TIME LOGIC")]
        public bool PreNyFri { get; set; }

        [Parameter("PreNY Close Time (JST Hour)", DefaultValue = 20, MinValue = 0, MaxValue = 23, Group = "5. TIME LOGIC")]
        public int PreNyCloseHour { get; set; }

        [Parameter("PreNY Close Time (JST Minute)", DefaultValue = 20, MinValue = 0, MaxValue = 59, Group = "5. TIME LOGIC")]
        public int PreNyCloseMinute { get; set; }

        [Parameter("PreNY Cooldown (Min)", DefaultValue = 0, MinValue = 0, Group = "5. TIME LOGIC")]
        public int PreNyCooldownMin { get; set; }

        [Parameter("Close Only If NetProfit >= (CCY)", DefaultValue = -8000, Group = "5. TIME LOGIC")]
        public double PreNyMinNetProfitToClose { get; set; }

        // =================================================================
        // [6] RISK MANAGEMENT
        // =================================================================
        [Parameter("Daily Loss Limit (CCY)", DefaultValue = 7000, Group = "6. RISK MANAGEMENT")]
        public double DailyLossLimit { get; set; }

        [Parameter("Use Basket Stop", DefaultValue = true, Group = "6. RISK MANAGEMENT")]
        public bool UseBasketStop { get; set; }

        [Parameter("Basket Loss Sell (CCY)", DefaultValue = 15000, MinValue = 0, Group = "6. RISK MANAGEMENT")]
        public double BasketLossSell { get; set; }

        [Parameter("Basket Loss Buy (CCY)", DefaultValue = 12000, MinValue = 0, Group = "6. RISK MANAGEMENT")]
        public double BasketLossBuy { get; set; }

        [Parameter("Basket Cooldown Sell (Min)", DefaultValue = 350, MinValue = 0, Group = "6. RISK MANAGEMENT")]
        public int BasketCooldownSellMin { get; set; }

        [Parameter("Basket Cooldown Buy (Min)", DefaultValue = 600, MinValue = 0, Group = "6. RISK MANAGEMENT")]
        public int BasketCooldownBuyMin { get; set; }

        [Parameter("Use Weekly Guard", DefaultValue = true, Group = "6. RISK MANAGEMENT")]
        public bool UseWeeklyGuard { get; set; }

        [Parameter("Weekly Guard Cooldown (Min)", DefaultValue = 1800, Group = "6. RISK MANAGEMENT")]
        public int WeeklyGuardCooldown { get; set; }

        [Parameter("Use Daily Loss Streak Guard", DefaultValue = true, Group = "6. RISK MANAGEMENT")]
        public bool UseDailyLossStreakGuard { get; set; }

        [Parameter("Max Consecutive Losses Sell", DefaultValue = 2, MinValue = 0, Group = "6. RISK MANAGEMENT")]
        public int MaxConsecutiveLossesSell { get; set; }

        [Parameter("Max Consecutive Losses Buy", DefaultValue = 2, MinValue = 0, Group = "6. RISK MANAGEMENT")]
        public int MaxConsecutiveLossesBuy { get; set; }

        [Parameter("Loss Streak Cooldown (Min)", DefaultValue = 360, MinValue = 0, Group = "6. RISK MANAGEMENT")]
        public int LossStreakCooldownMin { get; set; }

        [Parameter("Shockwave Mode", DefaultValue = "1", Group = "6. RISK MANAGEMENT")]
        public WaveMode SwMode { get; set; }

        [Parameter("Shockwave Threshold", DefaultValue = 4, Group = "6. RISK MANAGEMENT")]
        public double BreakerThreshold { get; set; }

        [Parameter("Shockwave Wait (Min)", DefaultValue = 60, Group = "6. RISK MANAGEMENT")]
        public int ShockwaveWaitMin { get; set; }

        // =================================================================
        // [7] FILTERS & BLOCKS
        // =================================================================
        [Parameter("Use Volatility Block", DefaultValue = true, Group = "7. FILTERS & BLOCKS")]
        public bool UseVolatilityBlock { get; set; }

        [Parameter("Vol Block BB Width (Pips)", DefaultValue = 60, MinValue = 0, Group = "7. FILTERS & BLOCKS")]
        public double VolBlockBbWidthPips { get; set; }

        [Parameter("Vol Block BB Width OFF (Pips)", DefaultValue = 55, MinValue = 0, Group = "7. FILTERS & BLOCKS")]
        public double VolBlockBbWidthOffPips { get; set; }

        [Parameter("Vol Block Min Rearm (Min)", DefaultValue = 15, MinValue = 0, Group = "7. FILTERS & BLOCKS")]
        public int VolBlockMinRearmMin { get; set; }

        [Parameter("Min Gap: Vol - Entry (Pips)", DefaultValue = 15, MinValue = 0, Group = "7. FILTERS & BLOCKS")]
        public double MinVolOverEntryGapPips { get; set; }

        [Parameter("Vol Block Cooldown (Min)", DefaultValue = 120, MinValue = 0, Group = "7. FILTERS & BLOCKS")]
        public int VolBlockCooldownMin { get; set; }

        [Parameter("Vol Block Cancels Pending", DefaultValue = true, Group = "7. FILTERS & BLOCKS")]
        public bool VolBlockCancelsPending { get; set; }

        [Parameter("Vol Block Affects Grid Add", DefaultValue = true, Group = "7. FILTERS & BLOCKS")]
        public bool VolBlockAffectsGridAdd { get; set; }

        [Parameter("Use Entry BB Block", DefaultValue = true, Group = "7. FILTERS & BLOCKS")]
        public bool UseEntryBbBlock { get; set; }

        [Parameter("Entry Block BB Width (Pips)", DefaultValue = 55, MinValue = 0, Group = "7. FILTERS & BLOCKS")]
        public double EntryBlockBbWidthPips { get; set; }

        [Parameter("Entry Block BB Width OFF (Pips)", DefaultValue = 50, MinValue = 0, Group = "7. FILTERS & BLOCKS")]
        public double EntryBlockBbWidthOffPips { get; set; }

        [Parameter("Entry Block Min Rearm (Min)", DefaultValue = 15, MinValue = 0, Group = "7. FILTERS & BLOCKS")]
        public int EntryBlockMinRearmMin { get; set; }

        [Parameter("Entry Block Cooldown (Min)", DefaultValue = 120, MinValue = 0, Group = "7. FILTERS & BLOCKS")]
        public int EntryBlockCooldownMin { get; set; }

        [Parameter("Entry Block Cancels Pending", DefaultValue = true, Group = "7. FILTERS & BLOCKS")]
        public bool EntryBlockCancelsPending { get; set; }

        [Parameter("Use Smart Radar", DefaultValue = true, Group = "7. FILTERS & BLOCKS")]
        public bool UseRadar { get; set; }

        [Parameter("Radar Max Abs Slope (Sell, pips)", DefaultValue = 0, Group = "7. FILTERS & BLOCKS")]
        public double RadarMaxAbsSlopeSell { get; set; }

        [Parameter("Radar Max Abs Slope (Buy, pips)", DefaultValue = 0, Group = "7. FILTERS & BLOCKS")]
        public double RadarMaxAbsSlopeBuy { get; set; }

        [Parameter("Apply Radar To Grid", DefaultValue = true, Group = "7. FILTERS & BLOCKS")]
        public bool ApplyRadarToGrid { get; set; }

        [Parameter("Apply Radar To New Entries", DefaultValue = true, Group = "7. FILTERS & BLOCKS")]
        public bool ApplyRadarToEntries { get; set; }

        // =================================================================
        // [8] TECHNICAL
        // =================================================================
        [Parameter("BB Period", DefaultValue = 30, Group = "8. TECHNICAL")]
        public int BbPeriod { get; set; }

        [Parameter("BB SD", DefaultValue = 2, Group = "8. TECHNICAL")]
        public double BbSd { get; set; }

        [Parameter("Sell Min BB Width", DefaultValue = 22, Group = "8. TECHNICAL")]
        public double SellMinBbWidth { get; set; }

        [Parameter("Sell Max BB Width", DefaultValue = 120, Group = "8. TECHNICAL")]
        public double SellMaxBbWidth { get; set; }

        [Parameter("Sell Grind Lookback", DefaultValue = 8, Group = "8. TECHNICAL")]
        public int SellGrindLookback { get; set; }

        [Parameter("Sell Min Continual Bars", DefaultValue = 7, Group = "8. TECHNICAL")]
        public int SellMinContinualBars { get; set; }

        [Parameter("Sell Deviation Pips", DefaultValue = 4.5, Group = "8. TECHNICAL")]
        public double SellMinDeviationPips { get; set; }

        [Parameter("Sell RSI Threshold (>)", DefaultValue = 58, Group = "8. TECHNICAL")]
        public int SellRsiThreshold { get; set; }

        [Parameter("Sell Slope Threshold (<)", DefaultValue = 1, Group = "8. TECHNICAL")]
        public double SellSlopeThreshold { get; set; }

        [Parameter("Buy Min BB Width", DefaultValue = 22, Group = "8. TECHNICAL")]
        public double BuyMinBbWidth { get; set; }

        [Parameter("Buy Max BB Width", DefaultValue = 125, Group = "8. TECHNICAL")]
        public double BuyMaxBbWidth { get; set; }

        [Parameter("Buy Grind Lookback", DefaultValue = 10, Group = "8. TECHNICAL")]
        public int BuyGrindLookback { get; set; }

        [Parameter("Buy Min Continual Bars", DefaultValue = 6, Group = "8. TECHNICAL")]
        public int BuyMinContinualBars { get; set; }

        [Parameter("Buy Deviation Pips", DefaultValue = 4.5, Group = "8. TECHNICAL")]
        public double BuyMinDeviationPips { get; set; }

        [Parameter("Buy RSI Threshold (<)", DefaultValue = 35, Group = "8. TECHNICAL")]
        public int BuyRsiThreshold { get; set; }

        [Parameter("Buy Slope Threshold (>)", DefaultValue = 1, Group = "8. TECHNICAL")]
        public double BuySlopeThreshold { get; set; }

        // =================================================================
        // [10] DEBUG
        // =================================================================
        [Parameter("Timer Interval (Sec)", DefaultValue = 1, MinValue = 1, MaxValue = 10, Group = "10. DEBUG")]
        public int TimerIntervalSec { get; set; }

        [Parameter("Enable Block Reason Log", DefaultValue = false, Group = "10. DEBUG")]
        public bool EnableBlockReasonLog { get; set; }

        [Parameter("Block Log Min Interval (Sec)", DefaultValue = 60, MinValue = 0, Group = "10. DEBUG")]
        public int BlockLogMinIntervalSec { get; set; }

        [Parameter("Diagnostic Mode", DefaultValue = false, Group = "10. DEBUG")]
        public bool DiagnosticMode { get; set; }

        [Parameter("Use Aegis Slot Block", DefaultValue = true, Group = "10. DEBUG")]
        public bool UseAegisSlotBlock { get; set; }

        // =================================================================
        // INTERNALS
        // =================================================================
        private double _dynUpper;
        private double _dynLower;
        private Bars _shiftBars;
        private DateTime _lastShiftBarTime = DateTime.MinValue;
        private DateTime _autoShiftCooldownEnd = DateTime.MinValue;

        private BollingerBands _bb;
        private RelativeStrengthIndex _rsi;
        private MovingAverage _devMa;
        private ExponentialMovingAverage _h4Ma;
        private AverageTrueRange _atr;
        private DirectionalMovementSystem _adx;
        private double _currentAdxValue = 0;

        private Bars _autoH4Bars;
        private MovingAverage _autoH4Ma;
        private TradeDir _effectiveDirection = TradeDir.Both;
        private double _lastAutoSlopePipsPerBar = 0;
        private DateTime _lastAutoLogTime = DateTime.MinValue;
        private TradeDir _lastAutoLoggedDecision = TradeDir.Both;
        private DateTime _lastAutoLoggedH4BarTime = DateTime.MinValue;
        private DateTime _autoLogDay = DateTime.MinValue;
        private int _autoLogCountToday = 0;

        private bool _lastAdxOkForTrade = true;

        private readonly HashSet<long> _expiryTpAdjustedPositionIds = new HashSet<long>();
        private readonly HashSet<long> _scaledOutPositionIds = new HashSet<long>();
        private readonly HashSet<long> _dynamicTpAppliedPositionIds = new HashSet<long>();

        private bool _manualBoundsStopOutTriggered = false;
        private DateTime _manualBoundsStopOutTime = DateTime.MinValue;

        private bool _manualBoundsSwapWarned = false;

        private string _label;
        private bool _isExecuting;
        private readonly object _tradeLock = new object();

        private bool _blockNewSellNow;
        private bool _blockNewBuyNow;

        private bool _dailyLimitHit;
        private double _dailyRealizedPL;
        private DateTime _currentDayStart;

        private DateTime _breakerCooldownEnd;

        private double _prevWeekHigh;
        private double _prevWeekLow;
        private bool _isWeeklyGuardActive;
        private DateTime _weeklyGuardCooldownEnd = DateTime.MinValue;


        private DateTime _lastWeekStart = DateTime.MinValue;
        private TimeZoneInfo _jstZone;

        private DateTime _sellBasketCooldownEnd = DateTime.MinValue;
        private DateTime _buyBasketCooldownEnd = DateTime.MinValue;

        private DateTime _timeStopCooldownEndSell = DateTime.MinValue;
        private DateTime _timeStopCooldownEndBuy = DateTime.MinValue;

        private DateTime _preNyCooldownEnd = DateTime.MinValue;
        private DateTime _lastPreNyCloseDay = DateTime.MinValue;

        private DateTime _volBlockEnd = DateTime.MinValue;
        private bool _volBbAbovePrev = false;
        private DateTime _lastVolBlockArm = DateTime.MinValue;

        private DateTime _entryBbBlockEnd = DateTime.MinValue;
        private bool _entryBbAbovePrev = false;
        private DateTime _lastEntryBlockArm = DateTime.MinValue;

        private int _sellLossStreak = 0;
        private int _buyLossStreak = 0;
        private DateTime _sellLossStreakEnd = DateTime.MinValue;
        private DateTime _buyLossStreakEnd = DateTime.MinValue;

        private DateTime _fridayNoNewEnd = DateTime.MinValue;
        private DateTime _fridayExitHoldEnd = DateTime.MinValue;
        private DateTime _lastFridayExitFridayDate = DateTime.MinValue;

        private bool _blockNewOrders = false;

        private PendingSignal _pendingSell;
        private PendingSignal _pendingBuy;
        private int _sellWaitCounter;
        private int _buyWaitCounter;
// =================================================================
// SEMI-AUTO runtime state
// =================================================================
private readonly HashSet<long> _semiManagedPositions = new HashSet<long>();
private readonly Dictionary<long, Tuple<double?, double?>> _semiLastBotSetSlTp = new Dictionary<long, Tuple<double?, double?>>();

private SemiSignal _semiSell = new SemiSignal { Direction = TradeType.Sell };
private SemiSignal _semiBuy = new SemiSignal { Direction = TradeType.Buy };

private struct SemiSignal
{
    public bool Active;
    public TradeType Direction;
    public string Id;
    public DateTime ArmedAt;
    public DateTime LastQualifiedAt;
    public DateTime AcceptUntil;
    public DateTime LastKeepAliveEmailAt;
    public bool FilledNotified;
    public bool EndNotified;
    public bool AdoptWindowOpen;
}


        private Position[] _cachedBotPositions;
        private DateTime _lastPositionCacheTime;

        private DateTime _lastTimeStopCheck = DateTime.MinValue;

        private struct PendingSignal
        {
            public bool Active;
            public TradeType TradeType;
            public double Volume;
            public int WaitBars;
            public string Reason;
        }

        protected override void OnStart()
        {
            _label = "Aegis_" + MagicNumber;

            _bb = Indicators.BollingerBands(Bars.ClosePrices, BbPeriod, BbSd, MovingAverageType.Simple);
            _rsi = Indicators.RelativeStrengthIndex(Bars.ClosePrices, 14);
            _devMa = Indicators.MovingAverage(Bars.ClosePrices, 20, MovingAverageType.Simple);
            _atr = Indicators.AverageTrueRange(14, MovingAverageType.Exponential);
            _adx = Indicators.DirectionalMovementSystem(AdxPeriod);

            var h4Series = MarketData.GetBars(TimeFrame.Hour4);
            _h4Ma = Indicators.ExponentialMovingAverage(h4Series.ClosePrices, 20);

            try
            {
                _autoH4Bars = MarketData.GetBars(TimeFrame.Hour4);
                _autoH4Ma = Indicators.MovingAverage(_autoH4Bars.ClosePrices, AutoMaPeriod, AutoMaType);
                _effectiveDirection = GetEffectiveDirection(Server.Time);
            }
            catch (Exception ex)
            {
                if (!OptimizationMode && !SkipComplexLogs)
                    Print("[WARN] Failed to init AUTO direction: {0}", ex.Message);
                _autoH4Bars = null;
                _autoH4Ma = null;
                _effectiveDirection = TradeDir.Both;
            }

            _shiftBars = MarketData.GetBars(AutoShiftTimeFrame);

            if (AutoShiftResetOnStart || (_dynUpper == 0 && _dynLower == 0))
            {
                _dynUpper = ManualUpperPrice;
                _dynLower = ManualLowerPrice;
            }

            ValidateManualBoundsOrDisable();
            // Draw manual bounds/stopout lines once on start (if enabled).
            RedrawManualBounds();

            try { _jstZone = TimeZoneInfo.FindSystemTimeZoneById("Tokyo Standard Time"); }
            catch { _jstZone = TimeZoneInfo.FindSystemTimeZoneById("Asia/Tokyo"); }

            _currentDayStart = TimeZoneInfo.ConvertTime(Server.Time, TimeZoneInfo.Utc, _jstZone).Date;
            _dailyRealizedPL = 0;
            _dailyLimitHit = false;

            _pendingSell = new PendingSignal { Active = false };
            _pendingBuy = new PendingSignal { Active = false };

            if (!OptimizationMode)
            {
                UpdateWeeklyGuardIfNeeded(Server.Time);
// Draw once immediately so the user sees it right after start
                // (live users often expect the panel instantly, not after the first timer tick).
                if (ShowDashboard || !SkipDashboard)
                    DrawDashboard();
            }

            // cTrader/cAlgo Timer.Start(int) expects **seconds** (not milliseconds).
            // Multiplying by 1000 would delay OnTimer heavily (e.g., 1 sec -> 1000 sec),
            // which makes Dashboard/housekeeping look "broken" in live usage.
            int timerInterval = OptimizationMode ? Math.Max(TimerIntervalSec, 5) : TimerIntervalSec;
            Timer.Start(timerInterval);
            Positions.Closed += OnPositionsClosed;
            // Some cTrader API versions do not support overriding OnPositionOpened.
            // Use event subscription instead.
            Positions.Opened += OnPositionsOpened;
        }

        protected override void OnStop()
        {
            Timer.Stop();
            Positions.Closed -= OnPositionsClosed;
            Positions.Opened -= OnPositionsOpened;
        }

        // NOTE: Do NOT use `override` here; not all API versions expose OnPositionOpened override.
        private void OnPositionsOpened(PositionOpenedEventArgs args)
        {
            try
            {
                if (args == null || args.Position == null) return;
                if (args.Position.SymbolName != SymbolName) return;

                if (AdoptManualPositions && !_semiManagedPositions.Contains(args.Position.Id))
                {
                    TryAdoptManualPosition(args.Position, Server.Time);
                }
            }
            catch { /* ignore */ }
        }

private Position[] GetCachedPositions(DateTime serverTime)
        {
            if (_cachedBotPositions != null &&
                (serverTime - _lastPositionCacheTime).TotalSeconds < PositionCacheSeconds)
            {
                return _cachedBotPositions;
            }

            _cachedBotPositions = Positions.Where(p => p.Label == _label && p.SymbolName == SymbolName).ToArray();
            _lastPositionCacheTime = serverTime;
            return _cachedBotPositions;
        }
        // =================================================================
        // SEMI-AUTO: position aggregation helpers
        // =================================================================
        private Position[] GetAegisManagedPositions(DateTime serverTime)
        {
            // Bot-labeled positions + semi-auto adopted manual positions (tagged by SignalId)
            var bot = GetCachedPositions(serverTime) ?? Array.Empty<Position>();
            if (_semiManagedPositions == null || _semiManagedPositions.Count == 0) return bot;

            var extra = Positions
                .Where(p => p.SymbolName == SymbolName && _semiManagedPositions.Contains(p.Id))
                .ToArray();

            if (extra.Length == 0) return bot;

            return bot.Concat(extra).Distinct().ToArray();
        }

        private Position[] GetAllAegisPositionsForSymbol()
        {
            // Used for protective close-all routines (Friday exit / PreNY close, etc.)
            if (_semiManagedPositions == null || _semiManagedPositions.Count == 0)
                return Positions.Where(p => p.SymbolName == SymbolName && p.Label == _label).ToArray();

            return Positions.Where(p => p.SymbolName == SymbolName && (p.Label == _label || _semiManagedPositions.Contains(p.Id))).ToArray();
        }


        protected override void OnTimer()
        {
            DateTime serverTime = Server.Time;

            // Weekly Guard lines/levels should be available in backtest/live even when the start time is Sunday or week roll.
            UpdateWeeklyGuardIfNeeded(serverTime);
            // Ensure cooldown is released as soon as it expires.
            UpdateWeeklyGuardCooldown(serverTime);

            // Semi-auto signal lifecycle maintenance
            SemiSignalMaintenance();

            // Semi-auto: adopt manual positions (safety net)
            if (AdoptManualPositions)
            {
                foreach (var p in Positions)
                {
                    if (p.SymbolName != SymbolName) continue;
                    if (_semiManagedPositions.Contains(p.Id)) continue;
                    TryAdoptManualPosition(p, serverTime);
                }
            }
                        // Cleanup: remove ids for positions that are no longer open (avoid stale ids accumulating)
            if (_semiManagedPositions.Count > 0)
            {
                // Some API versions expose Position.Id as int; normalize to long.
                var openIds = new HashSet<long>(Positions.Where(pp => pp.SymbolName == SymbolName).Select(pp => (long)pp.Id));

                // Remove stale managed ids
                _semiManagedPositions.RemoveWhere(id => !openIds.Contains(id));

                // Keep SL/TP tracking dict consistent
                var staleKeys = _semiLastBotSetSlTp.Keys.Where(id => !openIds.Contains(id)).ToList();
                foreach (var k in staleKeys) _semiLastBotSetSlTp.Remove(k);
            }

            // SemiAuto manual-change guard

            if (StopManagingOnManualChange && _semiManagedPositions.Count > 0)
            {
                foreach (var p in Positions)
                {
                    if (!_semiManagedPositions.Contains(p.Id)) continue;

                    if (_semiLastBotSetSlTp.TryGetValue(p.Id, out var last))
                    {
                        var lastSl = last.Item1;
                        var lastTp = last.Item2;

                        // If user changed SL/TP away from what the bot last set, stop managing to avoid conflicts.
                        bool changed = false;
                        if (lastSl.HasValue && p.StopLoss.HasValue && Math.Abs(p.StopLoss.Value - lastSl.Value) > Symbol.PipSize * 0.2) changed = true;
                        if (lastTp.HasValue && p.TakeProfit.HasValue && Math.Abs(p.TakeProfit.Value - lastTp.Value) > Symbol.PipSize * 0.2) changed = true;

                        // Also detect if bot expects SL/TP but they were removed.
                        if (lastSl.HasValue && !p.StopLoss.HasValue) changed = true;
                        if (lastTp.HasValue && !p.TakeProfit.HasValue) changed = true;

                        if (changed)
                        {
                            _semiManagedPositions.Remove(p.Id);
                            _semiLastBotSetSlTp.Remove(p.Id);

                            if (!OptimizationMode)
                            {
                                var subj = $"{(string.IsNullOrWhiteSpace(EmailSubjectPrefix) ? "[AegisSignal]" : EmailSubjectPrefix.Trim())} {SymbolName} {(p.TradeType == TradeType.Sell ? "S" : "B")} MANUAL-OVERRIDE";
                                var body =
$@"Position {p.Id} was modified manually (SL/TP). Bot management stopped for this position.

Entry: {p.EntryPrice}";
                                Notify("[WARN] " + subj, body);
                            }
                        }
                    }
                }
            }


            if (_adx != null && _adx.ADX.Count > 1)
                _currentAdxValue = _adx.ADX.Last(1);

            var botPositions = GetCachedPositions(serverTime);
            var managedPositions = GetAegisManagedPositions(serverTime);

            if (CheckManualBoundsStopOut(serverTime, managedPositions))
                return;

            ApplyExpiryTpIfNeeded(serverTime, managedPositions);
            ManageDynamicExit(managedPositions, serverTime);
            _effectiveDirection = GetEffectiveDirection(serverTime);

            if (UseBasketStop && botPositions.Length > 0)
            {
                var sells = botPositions.Where(p => p.TradeType == TradeType.Sell).ToArray();
                var buys = botPositions.Where(p => p.TradeType == TradeType.Buy).ToArray();

                if (BasketLossSell > 0 && sells.Length > 0 && serverTime >= _sellBasketCooldownEnd)
                {
                    if (sells.Sum(p => p.NetProfit) <= -BasketLossSell)
                    {
                        ExecuteWithLock(() => CloseAll(sells));
                        _pendingSell.Active = false;
                        _sellWaitCounter = 0;
                        _sellBasketCooldownEnd = serverTime.AddMinutes(BasketCooldownSellMin);
                    }
                }

                if (BasketLossBuy > 0 && buys.Length > 0 && serverTime >= _buyBasketCooldownEnd)
                {
                    if (buys.Sum(p => p.NetProfit) <= -BasketLossBuy)
                    {
                        ExecuteWithLock(() => CloseAll(buys));
_pendingBuy.Active = false;
                        _buyWaitCounter = 0;
                        _buyBasketCooldownEnd = serverTime.AddMinutes(BasketCooldownBuyMin);
                    }
                }
            }

            TryApplyTimeStop(serverTime, managedPositions);
            HandleFridayExit(serverTime);
            HandlePreNyClose(serverTime);

            if (!OptimizationMode && (ShowDashboard || !SkipDashboard))
                DrawDashboard();
        }

        protected override void OnBar()
        {
            DateTime serverTime = Server.Time;

            // Ensure Weekly Guard levels/lines are refreshed on week roll (backtest/live).
            UpdateWeeklyGuardIfNeeded(serverTime);
            // Ensure cooldown is released as soon as it expires.
            UpdateWeeklyGuardCooldown(serverTime);
            var dir = (Direction == TradeDir.Auto) ? _effectiveDirection : Direction;
            var botPositions = GetCachedPositions(serverTime);
            var managedPositions = GetAegisManagedPositions(serverTime);
            DateTime jst = TimeZoneInfo.ConvertTime(serverTime, TimeZoneInfo.Utc, _jstZone);
            double jstHour = jst.Hour + (jst.Minute / 60.0);

            if (UseManualBounds && UseAutoBoundsShift)
                TryAutoShiftBounds(serverTime);

            double slope = GetH4Slope();
            double bbWidth = _bb.Top.Count > 1 ? (_bb.Top.Last(1) - _bb.Bottom.Last(1)) / Symbol.PipSize : 0;

            bool adxOk = true;
            if (UseAdxFilter && !OptimizationMode)
            {
                if (_currentAdxValue < MinAdxForTrade || _currentAdxValue > MaxAdxForCounter)
                {
                    adxOk = false;
                    if (AutoSuppressAdx)
                    {
                        _blockNewSellNow = true;
                        _blockNewBuyNow = true;
                    }
                }
            }

            HandleVolatilityBlock(serverTime, bbWidth);
            HandleEntryBbBlock(serverTime, bbWidth);
            HandleDailyReset(serverTime);

            if (DailyLossLimit > 0 && _dailyRealizedPL <= -DailyLossLimit)
            {
                _dailyLimitHit = true;
                return;
            }

            var sells = botPositions.Where(p => p.TradeType == TradeType.Sell).ToArray();
            var buys = botPositions.Where(p => p.TradeType == TradeType.Buy).ToArray();

            HandleGridAdd(sells, buys, slope);

            bool noNewNow = CheckNoNewConditions(serverTime);
            UpdateBlockFlags(noNewNow, slope);

            // Optional: log which blocks are active (throttled) to help analysis.
            LogBlockStateChanges(serverTime, slope, adxOk);

            if (ProcessPending(ref _pendingSell, ref _sellWaitCounter) ||
                ProcessPending(ref _pendingBuy, ref _buyWaitCounter))
                return; 

            if (BlockRollover && jstHour >= RollBlockStart && jstHour < RollBlockEnd) return;
            if (IsStrategicPauseActive(jstHour)) return;

            double range = (Bars.HighPrices.Last(1) - Bars.LowPrices.Last(1)) / Symbol.PipSize;
            double th = (SwMode == WaveMode.AtrMultiplier)
                ? (_atr.Result.Last(1) / Symbol.PipSize) * BreakerThreshold
                : BreakerThreshold;

            if (range >= th)
            {
                _breakerCooldownEnd = serverTime.AddMinutes(ShockwaveWaitMin);
                _pendingSell.Active = false;
                _pendingBuy.Active = false;
            }

            if (noNewNow) return;
            if (jstHour < W1S || jstHour >= W1E) return;
            if (Symbol.Spread / Symbol.PipSize > MaxSpread) return;
            if (!IsDayAllowed(jst.DayOfWeek)) return;
            if (UseAegisSlotBlock && IsAegisTriggered(jst)) return;
            if (VirtualMultiplier > 1 && (Bars.Count % VirtualMultiplier != 0)) return;

            HandleNewEntries(dir, sells, buys, slope, bbWidth, adxOk);
        }

        // =================================================================
        // ✅ NEW: ADX Dynamic Adjustments
        // =================================================================
        private double GetAdxAdjustedTpPips(double baseTpPips)
        {
            if (!EnableAdxDynamicAdjustment || !UseAdxFilter)
                return baseTpPips;

            if (_currentAdxValue < AdxLowThreshold)
                return baseTpPips * AdxRangeMultiplier; // Range is shallow
            else if (_currentAdxValue > AdxHighThreshold)
                return baseTpPips * AdxTrendMultiplier; // Trend is deep
            return baseTpPips;
        }

        private double GetAdxAdjustedSlPips(double baseSlPips)
        {
            if (!EnableAdxDynamicAdjustment || !UseAdxFilter)
                return baseSlPips;

            if (_currentAdxValue < AdxLowThreshold)
                return baseSlPips * AdxRangeMultiplier; // Range is narrow
            else if (_currentAdxValue > AdxHighThreshold)
                return baseSlPips * AdxTrendMultiplier; // Trend is wide
            return baseSlPips;
        }

        private double GetAdxAdjustedStepPips(double baseStepPips)
        {
            if (!EnableAdxDynamicAdjustment || !UseAdxFilter)
                return baseStepPips;

            if (_currentAdxValue < AdxLowThreshold)
                return baseStepPips * AdxRangeStepMultiplier; // Range is narrow step
            else if (_currentAdxValue > AdxHighThreshold)
                return baseStepPips * AdxTrendStepMultiplier; // Trend is wide step
            return baseStepPips;
        }

        // =================================================================
        // Exit Management
        // =================================================================
        private void ManageDynamicExit(Position[] positions, DateTime serverTime)
        {
            if (positions == null || positions.Length == 0) return;

            foreach (var p in positions)
            {
                if (EnableScaleOut && !_scaledOutPositionIds.Contains(p.Id))
                {
                    if (p.Pips >= ScaleOutPips)
                    {
                        // --- Scale Out volume calculation (robust & broker-safe) ---
                        // Raw target volume (in units)
                        double rawCloseUnits = p.VolumeInUnits * ScaleOutRatio;

                        // Normalize down to broker step
                        long closeVolume = (long)Symbol.NormalizeVolumeInUnits(rawCloseUnits, RoundingMode.Down);

	                        // NOTE: Some cTrader builds expose VolumeInUnitsMin as double.
	                        // Keep all volume comparisons in long units.
	                        long minVol = (long)Symbol.VolumeInUnitsMin;
	                        long curVol = (long)p.VolumeInUnits;

                        // Ensure we don't try to close too little or leave a "dust" remainder below minimum.
                        // If we cannot perform a real partial close (e.g., BaseVolume=1000 with min=1000),
                        // we fall back to a "virtual scale-out": mark as scaled-out and apply BE / DynamicTP logic.
                        bool canRealPartialClose =
                            closeVolume >= minVol &&
                            closeVolume < curVol &&
                            (curVol - closeVolume) >= minVol;

                        if (canRealPartialClose)
                        {
                            var result = ClosePosition(p, closeVolume);
                            if (result != null && result.IsSuccessful)
                            {
                                _scaledOutPositionIds.Add(p.Id);

	                                if (AutoBreakeven)
	                                    ModifyPosition(p, p.EntryPrice, p.TakeProfit, ProtectionType.None);
                            }
                        }
                        else
                        {
                            // Virtual scale-out: no volume change, but we still want the post-scale-out risk behavior.
	                            _scaledOutPositionIds.Add(p.Id);

	                            if (AutoBreakeven)
	                                ModifyPosition(p, p.EntryPrice, p.TakeProfit, ProtectionType.None);
                        }
                    }
                }if (UseDynamicTP && _scaledOutPositionIds.Contains(p.Id) && !_dynamicTpAppliedPositionIds.Contains(p.Id))
                {
                    double atrPips = _atr.Result.Last(1) / Symbol.PipSize;
                    double dynamicTpPips = Math.Max(DynamicTP_MinPips, atrPips * DynamicTP_ATR_Multiplier);

                    double targetTpPrice = p.TradeType == TradeType.Buy
                        ? p.EntryPrice + (dynamicTpPips * Symbol.PipSize)
                        : p.EntryPrice - (dynamicTpPips * Symbol.PipSize);

	                    var tr = ModifyPosition(p, p.StopLoss, targetTpPrice, ProtectionType.None);
                    if (tr != null && tr.IsSuccessful)
                        _dynamicTpAppliedPositionIds.Add(p.Id);
                }
            }
        }

        private void ExecuteWithLock(TradeType type, double volume)
        {
            ExecuteWithLock(() =>
            {
                double tpPips = TakeProfitPips;
                double slPips = StopLossPips;

                // ATR Normalization
                if (UseAtrNormalization && _atr != null)
                {
                    double atrPips = _atr.Result.Last(1) / Symbol.PipSize;
                    tpPips = Math.Max(1.0, atrPips * TpAtrMultiplier);
                    slPips = Math.Max(1.0, atrPips * SlAtrMultiplier);
                }

                // ✅ ADX Dynamic Adjustment
                if (EnableAdxDynamicAdjustment && UseAdxFilter)
                {
                    tpPips = GetAdxAdjustedTpPips(tpPips);
                    slPips = GetAdxAdjustedSlPips(slPips);
                }

                long v = (long)Math.Round(Symbol.NormalizeVolumeInUnits(volume, RoundingMode.ToNearest));
                v = Math.Max(v, (long)Symbol.VolumeInUnitsMin);
                v = Math.Min(v, (long)Symbol.VolumeInUnitsMax);

                var r = ExecuteMarketOrder(type, SymbolName, v, _label, slPips, tpPips);
                if (!r.IsSuccessful && !OptimizationMode && !SkipComplexLogs)
                    Print("Order failed: {0}", r.Error);
            });
        }

        
        // =================================================================
        // SEMI-AUTO helpers
        // =================================================================
        private DateTime ToJst(DateTime utc) => utc.AddHours(9);

        private bool IsInHourWindowExtended(double currentHour, double start, double end)
        {
            // start==end -> treat as disabled window (no notifications)
            if (Math.Abs(start - end) < 1e-9) return false;

            // Support extended hours (e.g., 25.0 = 01:00 next day)
            // Normalize currentHour into [0, 48) by allowing "next day" representation.
            double ch = currentHour;

            // If end is <= start, we assume crossing midnight by adding 24 to end.
            double s = start;
            double e = end;
            if (e <= s) e += 24.0;

            // Try also "next day" current hour
            if (ch < s) ch += 24.0;

            return ch >= s && ch < e;
        }

        private bool IsWithinNotifyWindow(DateTime serverUtc)
        {
            var jst = ToJst(serverUtc);
            double h = jst.Hour + (jst.Minute / 60.0) + (jst.Second / 3600.0);
            return IsInHourWindowExtended(h, NotifyStartJst, NotifyEndJst);
        }

        private string BuildSignalId(TradeType dir)
        {
            // Example: "AG EURUSD S01"
            var codePart = dir == TradeType.Sell ? (SellCode ?? "S01") : (BuyCode ?? "B01");
            var prefix = string.IsNullOrWhiteSpace(SignalPrefix) ? "AG" : SignalPrefix.Trim();
            return $"{prefix} {SymbolName} {codePart}".Trim();
        }

        // NOTE: cTrader API overloads differ by version. Use the simplest popup/email methods.
        private void Notify(string subject, string body)
        {
            if (OptimizationMode) return; // Notifications don't work during optimization/backtesting

            if (!IsWithinNotifyWindow(Server.Time)) return;

            if (UseCtraderPopup)
            {
                // Older API versions may only have the 2-argument overload.
                try { Notifications.ShowPopup(subject, body, (PopupNotificationState)0); }
                catch { try { Notifications.ShowPopup(subject, body, (PopupNotificationState)0); } catch { /* ignore */ } }
            }

            if (UseEmailNotify &&
                !string.IsNullOrWhiteSpace(EmailFrom) &&
                !string.IsNullOrWhiteSpace(EmailTo))
            {
                try { Notifications.SendEmail(EmailFrom.Trim(), EmailTo.Trim(), subject, body); }
                catch { /* ignore */ }
            }
        }

        private void SemiSignalArmOrKeepAlive(TradeType dir, string reason)
        {
            if (EntryMode == SemiAutoMode.FullAuto) return;

            var now = Server.Time;
            ref var s = ref (dir == TradeType.Sell ? ref _semiSell : ref _semiBuy);

            var sid = BuildSignalId(dir);

            // If a signal was filled but the adoption window is still open, do not re-arm (avoid spam).
            if (!s.Active && s.AdoptWindowOpen && now <= s.AcceptUntil)
                return;

            if (!s.Active)
            {
                s.Active = true;
                s.Id = sid;
                s.ArmedAt = now;
                s.LastQualifiedAt = now;
                s.AcceptUntil = now.AddMinutes(SignalArmWindowMin);
                s.LastKeepAliveEmailAt = DateTime.MinValue;
                s.FilledNotified = false;
                s.EndNotified = false;
                s.AdoptWindowOpen = true;

                var subj = $"{(string.IsNullOrWhiteSpace(EmailSubjectPrefix) ? "[AegisSignal]" : EmailSubjectPrefix.Trim())} {SymbolName} {(dir == TradeType.Sell ? "S" : "B")} ARMED";
                var body =
$@"SIGNAL ID:
{sid}

Symbol: {SymbolName} {TimeFrame}
Dir: {(dir == TradeType.Sell ? "SELL" : "BUY")}
Valid: {SignalArmWindowMin} min (rolling) / MaxLife: {SignalMaxLifeMin} min
Reason: {reason}";
                Notify(subj, body);
            }
            else
            {
                // keepalive/extend window
                s.LastQualifiedAt = now;
                s.AcceptUntil = now.AddMinutes(SignalArmWindowMin);

                if (KeepAliveEmailIntervalMin > 0 && now - s.LastKeepAliveEmailAt >= TimeSpan.FromMinutes(KeepAliveEmailIntervalMin))
                {
                    s.LastKeepAliveEmailAt = now;

                    var subj = $"{(string.IsNullOrWhiteSpace(EmailSubjectPrefix) ? "[AegisSignal]" : EmailSubjectPrefix.Trim())} {SymbolName} {(dir == TradeType.Sell ? "S" : "B")} ACTIVE";
                    var body =
$@"SIGNAL ID:
{sid}

Status: ACTIVE (env OK)
Extended Until: {ToJst(s.AcceptUntil):yyyy-MM-dd HH:mm} JST
Reason: {reason}";
                    Notify(subj, body);
                }
            }
        }

        private void SemiSignalEnd(TradeType dir, string status, string reason, string levelTag)
        {
            ref var s = ref (dir == TradeType.Sell ? ref _semiSell : ref _semiBuy);
            if (!s.Active || s.EndNotified) return;

            s.EndNotified = true;
            s.Active = false;

            s.AdoptWindowOpen = false;

            var sid = s.Id ?? BuildSignalId(dir);
            var subj = $"{(string.IsNullOrWhiteSpace(EmailSubjectPrefix) ? "[AegisSignal]" : EmailSubjectPrefix.Trim())} {SymbolName} {(dir == TradeType.Sell ? "S" : "B")} {status}";
            var body =
$@"SIGNAL ID:
{sid}

Status: {status}
Reason: {reason}";
            if (!string.IsNullOrWhiteSpace(levelTag)) subj = levelTag + " " + subj;
            Notify(subj, body);
        }

        private void SemiSignalMaintenance()
        {
            if (EntryMode == SemiAutoMode.FullAuto) return;

            var now = Server.Time;

            void check(ref SemiSignal s, TradeType dir)
            {
                // Adoption window cleanup (may remain open after FILLED)
                if (s.AdoptWindowOpen && now > s.AcceptUntil)
                    s.AdoptWindowOpen = false;

                if (!s.Active) return;

                // Hard max life
                if (now - s.ArmedAt >= TimeSpan.FromMinutes(SignalMaxLifeMin))
                {
                    SemiSignalEnd(dir, "EXPIRED", $"Max life reached ({SignalMaxLifeMin} min).", "[WARN]");
                    return;
                }

                // Immediate cancel conditions (environment safety)
                var jst = ToJst(now);

                if (ImmediateCancelSlotBlock && UseAegisSlotBlock && IsAegisTriggered(jst))
                {
                    SemiSignalEnd(dir, "END", "SlotBlock triggered.", "[WARN]");
                    return;
                }

                if (ImmediateCancelVolBlock && UseVolatilityBlock && now < _volBlockEnd)
                {
                    SemiSignalEnd(dir, "END", "Volatility Block active.", "[WARN]");
                    return;
                }

                if (ImmediateCancelManualBounds && _manualBoundsStopOutTriggered)
                {
                    SemiSignalEnd(dir, "END", "ManualBounds StopOut triggered.", "[ERROR]");
                    return;
                }

                if (ImmediateCancelRangeBreak && _breakerCooldownEnd > now)
                {
                    SemiSignalEnd(dir, "END", "Range Break cooldown active.", "[WARN]");
                    return;
                }

                // Rolling expiry (no keepalive)
                if (now > s.AcceptUntil)
                {
                    SemiSignalEnd(dir, "EXPIRED", $"No qualifying refresh within {SignalArmWindowMin} min.", "[WARN]");
                    return;
                }
            }

            check(ref _semiSell, TradeType.Sell);
            check(ref _semiBuy, TradeType.Buy);
        }

        private bool TryAdoptManualPosition(Position p, DateTime serverTime)
        {
            if (!AdoptManualPositions) return false;
            if (p == null) return false;
            if (p.SymbolName != SymbolName) return false;

            // Ignore positions opened by this bot label already (if any)
            if (!string.IsNullOrWhiteSpace(_label) && string.Equals(p.Label, _label, StringComparison.OrdinalIgnoreCase))
                return false;

            var comment = p.Comment ?? string.Empty;
            var tagSell = BuildSignalId(TradeType.Sell);
            var tagBuy = BuildSignalId(TradeType.Buy);

// Adopt while the semi-signal adoption window is open (can remain open after FILLED until AcceptUntil).
// This prevents accidentally adopting old/manual positions outside the window.
bool IsAdoptionWindowOpen(TradeType dir)
{
    if (EntryMode == SemiAutoMode.FullAuto) return true;
    ref var ss = ref (dir == TradeType.Sell ? ref _semiSell : ref _semiBuy);
    if (!ss.AdoptWindowOpen) return false;
    if (serverTime > ss.AcceptUntil) return false;
    if (SignalMaxLifeMin > 0 && (serverTime - ss.ArmedAt).TotalMinutes > SignalMaxLifeMin) return false;
    return true;
}


            var cmt = comment.Trim();
            bool matchSell = string.Equals(cmt, tagSell, StringComparison.OrdinalIgnoreCase);
            bool matchBuy  = string.Equals(cmt, tagBuy,  StringComparison.OrdinalIgnoreCase);

            if ((matchSell && IsAdoptionWindowOpen(TradeType.Sell)) ||
                (matchBuy  && IsAdoptionWindowOpen(TradeType.Buy)))
            {
_semiManagedPositions.Add(p.Id);

                // Initial SL/TP anchored to entry price to avoid instant self-destruction.
                double? slPrice = null;
                double? tpPrice = null;

                if (SemiAutoInitialSlPips > 0)
                {
                    var slP = GetAdxAdjustedSlPips(SemiAutoInitialSlPips);
                    slPrice = p.TradeType == TradeType.Buy
                        ? p.EntryPrice - slP * Symbol.PipSize
                        : p.EntryPrice + slP * Symbol.PipSize;
                }

                if (SemiAutoInitialTpPips > 0)
                {
                    var tpP = SemiAutoInitialTpPips;
                    tpPrice = p.TradeType == TradeType.Buy
                        ? p.EntryPrice + tpP * Symbol.PipSize
                        : p.EntryPrice - tpP * Symbol.PipSize;
                }

                try
                {
                    var tr = ModifyPosition(p, slPrice, tpPrice, ProtectionType.None);
                    if (tr != null && tr.IsSuccessful)
                        _semiLastBotSetSlTp[p.Id] = Tuple.Create(slPrice, tpPrice);
                }
                catch { /* ignore */ }

                // Notify filled
                if (EntryMode != SemiAutoMode.FullAuto)
                {
                    var sid = cmt;
                    var subj = $"{(string.IsNullOrWhiteSpace(EmailSubjectPrefix) ? "[AegisSignal]" : EmailSubjectPrefix.Trim())} {SymbolName} {(p.TradeType == TradeType.Sell ? "S" : "B")} FILLED";
                    var body =
$@"SIGNAL ID:
{sid}

Status: FILLED (manual position adopted)
Entry: {p.EntryPrice}
Volume: {p.VolumeInUnits}";
                    Notify("[OK] " + subj, body);
                }

                // Mark as filled: stop further keepalive/expiry notifications, but keep adoption window open until AcceptUntil.
                if (EntryMode != SemiAutoMode.FullAuto)
                {
                    ref var ss = ref (p.TradeType == TradeType.Sell ? ref _semiSell : ref _semiBuy);
                    ss.FilledNotified = true;
                    ss.Active = false;
                    ss.EndNotified = true;
                    ss.AdoptWindowOpen = true;
                }

                return true;
            }

            return false;
        }


private void ExecuteWithLock(Action action)
        {
            if (_dailyLimitHit) return;
            if (!Monitor.TryEnter(_tradeLock)) return;

            try
            {
                if (_isExecuting) return;
                _isExecuting = true;
                action();
            }
            finally
            {
                _isExecuting = false;
                Monitor.Exit(_tradeLock);
            }
        }

        private void OnPositionsClosed(PositionClosedEventArgs args)
        {
            if (args.Position.SymbolName != SymbolName) return;
            if (args.Position.Label != _label && !_semiManagedPositions.Contains(args.Position.Id)) return;

            var jst = TimeZoneInfo.ConvertTime(Server.Time, TimeZoneInfo.Utc, _jstZone);
            
            // Thread-safe update of daily PL
            lock (_tradeLock)
            {
                if (jst.Date > _currentDayStart)
                {
                    _currentDayStart = jst.Date;
                    _dailyRealizedPL = 0;
                    _dailyLimitHit = false;
                }

                _dailyRealizedPL += args.Position.NetProfit;
            }

            _scaledOutPositionIds.Remove(args.Position.Id);
            _dynamicTpAppliedPositionIds.Remove(args.Position.Id);
            _expiryTpAdjustedPositionIds.Remove(args.Position.Id);

            if (UseDailyLossStreakGuard)
            {
                bool isLoss = args.Position.NetProfit < 0;
                if (args.Position.TradeType == TradeType.Sell)
                {
                    _sellLossStreak = isLoss ? _sellLossStreak + 1 : 0;
                    if (_sellLossStreak >= MaxConsecutiveLossesSell && MaxConsecutiveLossesSell > 0)
                        _sellLossStreakEnd = Server.Time.AddMinutes(LossStreakCooldownMin);
                }
                else
                {
                    _buyLossStreak = isLoss ? _buyLossStreak + 1 : 0;
                    if (_buyLossStreak >= MaxConsecutiveLossesBuy && MaxConsecutiveLossesBuy > 0)
                        _buyLossStreakEnd = Server.Time.AddMinutes(LossStreakCooldownMin);
                }
            }
        }

        private void CloseAll(Position[] positions)
        {
            foreach (var p in positions)
                ClosePosition(p);
        }

        private bool ProcessPending(ref PendingSignal pending, ref int counter)
        {
            if (!pending.Active) return false;
            counter++;

            if (counter >= pending.WaitBars)
            {
                if ((pending.TradeType == TradeType.Sell && _blockNewSellNow) ||
                    (pending.TradeType == TradeType.Buy && _blockNewBuyNow))
                {
                    pending.Active = false;
                    counter = 0;
                    return false;
                }

                ExecuteWithLock(pending.TradeType, pending.Volume);
                pending.Active = false;
                counter = 0;
                return true;
            }
            return false;
        }

        
private void RegisterSignal(TradeType tradeType, double volume, string reason)
{
    // Centralized entry point for new signals.
    // FullAuto: behaves as before (pending + immediate execution).
    // SemiAuto: DOES NOT place orders. Emits/extends a signal window for manual entry; exits are managed by the bot.

    var r = reason ?? string.Empty;

    if (EntryMode != SemiAutoMode.FullAuto)
    {
        // Treat every qualifying signal as a keep-alive refresh (rolling window).
        SemiSignalArmOrKeepAlive(tradeType, r);

        // Ensure no pending auto-execution remains armed.
        if (tradeType == TradeType.Sell)
        {
            _pendingSell.Active = false;
            _sellWaitCounter = 0;
        }
        else
        {
            _pendingBuy.Active = false;
            _buyWaitCounter = 0;
        }

        if (!OptimizationMode && !SkipComplexLogs && !string.IsNullOrEmpty(r))
            Print("[SEMI-SIGNAL] {0} {1}", tradeType, r);

        return;
    }

    // -----------------------------
    // FullAuto legacy behavior
    // -----------------------------
    var ps = new PendingSignal
    {
        Active = true,
        TradeType = tradeType,
        Volume = volume,
        WaitBars = 0,
        Reason = r
    };

    if (tradeType == TradeType.Sell)
    {
        _pendingSell = ps;
        _sellWaitCounter = 0;
    }
    else
    {
        _pendingBuy = ps;
        _buyWaitCounter = 0;
    }

    // Execute immediately when there is no configured delay.
    if (ps.WaitBars <= 0)
    {
        if ((tradeType == TradeType.Sell && !_blockNewSellNow) ||
            (tradeType == TradeType.Buy && !_blockNewBuyNow))
        {
            ExecuteWithLock(tradeType, volume);
        }

        if (tradeType == TradeType.Sell)
            _pendingSell.Active = false;
        else
            _pendingBuy.Active = false;
    }

    if (!OptimizationMode && !SkipComplexLogs && !string.IsNullOrEmpty(ps.Reason))
        Print("[SIGNAL] {0} vol={1} {2}", tradeType, volume, ps.Reason);
}


private double GetH4Slope()
        {
            if (_h4Ma.Result.Count < 5) return 999;
            return (_h4Ma.Result.Last(1) - _h4Ma.Result.Last(4)) / 3.0 / Symbol.PipSize;
        }

        private TradeDir GetEffectiveDirection(DateTime serverTime)
        {
            if (Direction != TradeDir.Auto)
            {
                _lastAutoSlopePipsPerBar = 0;
                return Direction;
            }
            if (_autoH4Ma == null || _autoH4Bars == null) return TradeDir.Both;
            if (_autoH4Bars.Count < AutoLookbackBars + 3) return TradeDir.Both;

            double now = _autoH4Ma.Result.Last(1);
            double past = _autoH4Ma.Result.Last(AutoLookbackBars + 1);
            double slope = ((now - past) / Symbol.PipSize) / AutoLookbackBars; // pips/bar
            _lastAutoSlopePipsPerBar = slope;

            TradeDir decision;
            if (slope >= AutoSlopeThresholdPipsPerBar) decision = TradeDir.BuyOnly;
            else if (slope <= -AutoSlopeThresholdPipsPerBar) decision = TradeDir.SellOnly;
            else decision = TradeDir.Both;

            // log basis with throttling
            DateTime h4NowTime = _autoH4Bars.OpenTimes.Last(1);
            DateTime h4PastTime = _autoH4Bars.OpenTimes.Last(AutoLookbackBars + 1);
            MaybeLogAutoDecision(serverTime, h4NowTime, h4PastTime, now, past, slope, decision);

            return decision;
        }

        
        private void MaybeLogAutoDecision(DateTime serverTime, DateTime h4NowTime, DateTime h4PastTime,
                                          double now, double past, double slopePipsPerBar, TradeDir decision)
        {
            if (!AutoLogDecisionBasis) return;
            if (OptimizationMode) return;
            if (SkipComplexLogs) return;

            // daily cap
            var day = serverTime.Date;
            if (_autoLogDay != day)
            {
                _autoLogDay = day;
                _autoLogCountToday = 0;
            }
            if (AutoMaxLogsPerDay > 0 && _autoLogCountToday >= AutoMaxLogsPerDay) return;

            bool changed = decision != _lastAutoLoggedDecision;
            bool newH4Bar = h4NowTime != _lastAutoLoggedH4BarTime;

            bool shouldLog = true;
            if (AutoLogOnlyOnChange)
                shouldLog = changed;

            if (AutoLogPerH4Bar)
                shouldLog = shouldLog || newH4Bar;

            if (!shouldLog) return;

            // interval throttle (do not block changes)
            if (!changed && AutoLogMinIntervalSec > 0)
            {
                if ((serverTime - _lastAutoLogTime).TotalSeconds < AutoLogMinIntervalSec)
                    return;
            }

            _lastAutoLogTime = serverTime;
            _lastAutoLoggedDecision = decision;
            if (newH4Bar)
                _lastAutoLoggedH4BarTime = h4NowTime;

            _autoLogCountToday++;

            // slope is pips/bar already
            Print("[AUTO] t={0:yyyy-MM-dd HH:mm:ss} Decision={1} MA({2},{3}) now={4:F5}({5:MM-dd HH:mm}) past={6:F5}({7:MM-dd HH:mm}) lookback={8} slope={9:F3} pips/bar th={10:F3}",
                serverTime, decision, AutoMaType, AutoMaPeriod, now, h4NowTime, past, h4PastTime, AutoLookbackBars, slopePipsPerBar, AutoSlopeThresholdPipsPerBar);
        }

private 
        void DrawDashboard()
        {
            // Dashboard is UI overlay. Never draw during optimization.
            // Legacy support:
            //  - If ShowDashboard=true => always show (even if SkipDashboard=true)
            //  - Else ShowDashboard=false => follow SkipDashboard (true = hide)
            if (OptimizationMode) return;
            if (!ShowDashboard && SkipDashboard) return;

            var nl = Environment.NewLine;

            
// Compute "internal allowed directions" for tuning based on backtests.
// - Param direction: user setting
// - Effective direction: Auto result OR Param (if not Auto)
// - Allowed (runtime): blocked flags / basket cooldown / adx state etc.

var serverTime = Server.Time;
var slope = GetH4Slope();

var effective = (Direction == TradeDir.Auto) ? _effectiveDirection : Direction;

bool sellAllowedRuntime =
    (effective == TradeDir.SellOnly || effective == TradeDir.Both) &&
    !_blockNewSellNow &&
    serverTime >= _sellBasketCooldownEnd;

bool buyAllowedRuntime =
    (effective == TradeDir.BuyOnly || effective == TradeDir.Both) &&
    !_blockNewBuyNow &&
    serverTime >= _buyBasketCooldownEnd;

// Slope bias (what the strategy is *inclined* to consider), independent of blocks.
bool sellBiasBySlope = (slope < SellSlopeThreshold);
bool buyBiasBySlope = (slope > -BuySlopeThreshold);

string internalDirSummary;
if (sellAllowedRuntime && buyAllowedRuntime) internalDirSummary = "Both";
else if (sellAllowedRuntime) internalDirSummary = "SellOnly";
else if (buyAllowedRuntime) internalDirSummary = "BuyOnly";
else internalDirSummary = "Blocked";

string slopeBiasSummary;
if (sellBiasBySlope && buyBiasBySlope) slopeBiasSummary = "Both";
else if (sellBiasBySlope) slopeBiasSummary = "Sell";
else if (buyBiasBySlope) slopeBiasSummary = "Buy";
else slopeBiasSummary = "None";

var lines = new List<string>
{
    $"Aegis Sniper {BUILD_VERSION}",
    $"Dir: Param={Direction} / Effective={effective} / Internal={internalDirSummary} (SlopeBias={slopeBiasSummary})",
    (Direction == TradeDir.Auto
        ? $"AutoSlope(pips/bar): {_lastAutoSlopePipsPerBar:F3} (th={AutoSlopeThresholdPipsPerBar:F3})"
        : "AutoSlope(pips/bar): n/a"),
    $"ADX: {_currentAdxValue:F1} (min {MinAdxForTrade}, warn {AdxWarningThreshold}, maxCounter {MaxAdxForCounter}) ok={_lastAdxOkForTrade}",
    $"Daily P/L: {_dailyRealizedPL:C}"
};

// Weekly Guard thresholds (values actually used for the guard decision)
if (UseWeeklyGuard && _prevWeekHigh > 0 && _prevWeekLow > 0)
{
    var cd = _weeklyGuardCooldownEnd;
    string cdText;
    if (cd == DateTime.MinValue) cdText = "n/a";
    else cdText = $"{cd:MM/dd HH:mm} (rem {Math.Max(0, (int)Math.Ceiling((cd - serverTime).TotalMinutes))}m)";

    // Show cooldown only when it is relevant (active or still in cooldown window)
    if (_isWeeklyGuardActive || (cd != DateTime.MinValue && serverTime < cd))
        lines.Add($"WeeklyGuard: High={_prevWeekHigh:F5}  Low={_prevWeekLow:F5}  Active={_isWeeklyGuardActive}  CooldownUntil={cdText}");
    else
        lines.Add($"WeeklyGuard: High={_prevWeekHigh:F5}  Low={_prevWeekLow:F5}  Active={_isWeeklyGuardActive}");
}

            
// Internal breakout guard (Shockwave / Range Breaker)
if (_breakerCooldownEnd != DateTime.MinValue)
{
    bool shockActive = serverTime < _breakerCooldownEnd;
    int rem = Math.Max(0, (int)Math.Ceiling((_breakerCooldownEnd - serverTime).TotalMinutes));
    if (shockActive)
        lines.Add($"ShockwaveGuard: Active=True  CooldownUntil={_breakerCooldownEnd:MM/dd HH:mm} (rem {rem}m)");
    else
        lines.Add($"ShockwaveGuard: Active=False  LastUntil={_breakerCooldownEnd:MM/dd HH:mm}");
}
string text = string.Join(nl, lines);

            var shockActiveNow = (Server.Time < _breakerCooldownEnd);
            var dashColor = _isWeeklyGuardActive ? Color.Red : (shockActiveNow ? Color.Yellow : Color.White);

            Chart.DrawStaticText("AegisDashboard", text, VerticalAlignment.Top, HorizontalAlignment.Left, dashColor);
        }


        
        private DateTime GetStartOfWeekMonday(DateTime t)
        {
            var d = t.Date;
            int diff = ((int)t.DayOfWeek - (int)DayOfWeek.Monday + 7) % 7; // works even when DayOfWeek is Sunday
            return d.AddDays(-diff);
        }

        private void UpdateWeeklyGuardIfNeeded(DateTime serverTime)
        {
            if (!UseWeeklyGuard) return;
            if (OptimizationMode) return; // never draw/update UI in optimization

            var weekStart = GetStartOfWeekMonday(serverTime);

            // Recalculate if week changed OR if values are not initialized
            if (_lastWeekStart != weekStart || _prevWeekHigh <= 0 || _prevWeekLow <= 0)
            {
                _lastWeekStart = weekStart;
                CalculateLastWeekHighLow();
                DrawWeeklyLines();
            }
        }

private void UpdateWeeklyGuardCooldown(DateTime serverTime)
{
    if (!UseWeeklyGuard) return;

    // If weekly guard cooldown has elapsed, resume trading immediately.
    if (_isWeeklyGuardActive && _weeklyGuardCooldownEnd != DateTime.MinValue && serverTime >= _weeklyGuardCooldownEnd)
        _isWeeklyGuardActive = false;
}


        private void DrawWeeklyLines()
        {
            if (!UseWeeklyGuard) return;

            // clear then redraw (safe for backtest / week roll)
            Chart.RemoveObject("PrevWeekHigh");
            Chart.RemoveObject("PrevWeekLow");

            if (_prevWeekHigh > 0)
                Chart.DrawHorizontalLine("PrevWeekHigh", _prevWeekHigh, Color.Red, 1, LineStyle.Dots);

            if (_prevWeekLow > 0)
                Chart.DrawHorizontalLine("PrevWeekLow", _prevWeekLow, Color.Blue, 1, LineStyle.Dots);
        }

        private void CalculateLastWeekHighLow()
        {
            DateTime now = Server.Time;
            DateTime startOfWeek = GetStartOfWeekMonday(now);
            DateTime prevWeekStart = startOfWeek.AddDays(-7);
            DateTime prevWeekEnd = startOfWeek.AddTicks(-1);

            var dailyBars = MarketData.GetBars(TimeFrame.Daily);
            if (dailyBars == null) return;

            double high = double.MinValue, low = double.MaxValue;
            bool found = false;

            for (int i = dailyBars.Count - 1; i >= 0; i--)
            {
                var t = dailyBars.OpenTimes[i];
                if (t >= prevWeekStart && t <= prevWeekEnd)
                {
                    high = Math.Max(high, dailyBars.HighPrices[i]);
                    low = Math.Min(low, dailyBars.LowPrices[i]);
                    found = true;
                }
            }

            if (found)
            {
                _prevWeekHigh = high;
                _prevWeekLow = low;
            }
        }


        private void HandleFridayExit(DateTime serverTime)
        {
            if (UseFridayExit && FridayExitClosePositions)
            {
                DateTime jstNow = TimeZoneInfo.ConvertTime(serverTime, TimeZoneInfo.Utc, _jstZone);
                double jstHourNow = jstNow.Hour + (jstNow.Minute / 60.0) + (jstNow.Second / 3600.0);

                if (jstNow.DayOfWeek == DayOfWeek.Friday || jstNow.DayOfWeek == DayOfWeek.Saturday)
                {
                    double timelineHour = (jstNow.DayOfWeek == DayOfWeek.Saturday) ? (jstHourNow + 24.0) : jstHourNow;
                    DateTime fridayDate = (jstNow.DayOfWeek == DayOfWeek.Saturday) ? jstNow.Date.AddDays(-1) : jstNow.Date;

                    if (timelineHour >= FridayExitJst && _lastFridayExitFridayDate.Date != fridayDate.Date)
                    {
                        var pos = GetAllAegisPositionsForSymbol();
                        if (pos.Length > 0)
                            ExecuteWithLock(() => CloseAll(pos));

                        _pendingSell.Active = false;
                        _sellWaitCounter = 0;
                        _pendingBuy.Active = false;
                        _buyWaitCounter = 0;

                        _lastFridayExitFridayDate = fridayDate.Date;

                        if (FridayExitHoldUntilMonday)
                        {
                            int daysAhead = ((int)DayOfWeek.Monday - (int)jstNow.DayOfWeek + 7) % 7;
                            if (daysAhead == 0) daysAhead = 7;
                            DateTime nextMondayJst = jstNow.Date.AddDays(daysAhead);
                            _fridayExitHoldEnd = TimeZoneInfo.ConvertTimeToUtc(nextMondayJst, _jstZone);
                        }
                    }
                }
            }

            if (UseFridayExit && FridayNoNewBeforeHours > 0)
            {
                DateTime jstNow2 = TimeZoneInfo.ConvertTime(serverTime, TimeZoneInfo.Utc, _jstZone);
                double jstHour2 = jstNow2.Hour + (jstNow2.Minute / 60.0) + (jstNow2.Second / 3600.0);

                if (IsFridayNoNewWindow(jstNow2, jstHour2))
                {
                    _fridayNoNewEnd = serverTime.AddSeconds(2);
                }
                else
                {
                    if (serverTime >= _fridayExitHoldEnd)
                        _fridayNoNewEnd = DateTime.MinValue;
                }
            }
            else
            {
                if (serverTime >= _fridayExitHoldEnd)
                    _fridayNoNewEnd = DateTime.MinValue;
            }

            if (serverTime < _fridayExitHoldEnd)
                _fridayNoNewEnd = _fridayExitHoldEnd;
        }

        private void HandlePreNyClose(DateTime serverTime)
        {
            if (UsePreNyClose)
            {
                DateTime jst = TimeZoneInfo.ConvertTime(serverTime, TimeZoneInfo.Utc, _jstZone);

                if (_lastPreNyCloseDay.Date == jst.Date)
                    return;

                if (!IsPreNyDayEnabled(jst.DayOfWeek))
                    return;

                if (jst.Hour != PreNyCloseHour || jst.Minute != PreNyCloseMinute)
                    return;

                var positions = GetCachedPositions(serverTime) ?? Array.Empty<Position>();
                double net = positions.Sum(p => p.NetProfit);

                if (positions.Length > 0 && net >= PreNyMinNetProfitToClose)
                {
                    ExecuteWithLock(() => CloseAll(positions));
                    _pendingSell.Active = false;
                    _sellWaitCounter = 0;
                    _pendingBuy.Active = false;
                    _buyWaitCounter = 0;
                }

                _lastPreNyCloseDay = jst.Date;
                _preNyCooldownEnd = serverTime.AddMinutes(Math.Max(0, PreNyCooldownMin));
            }
        }

        private void HandleVolatilityBlock(DateTime serverTime, double bbWidth)
        {
            if (UseVolatilityBlock && VolBlockBbWidthPips > 0)
            {
                // NOTE:
                // Volatility Block thresholds must be driven by its own parameters.
                // Entry BB Block parameters should NOT affect VolBlock when UseEntryBbBlock is OFF.
                double volOn = VolBlockBbWidthPips;
                double volOff = VolBlockBbWidthOffPips;

                if (UseEntryBbBlock)
                {
                    double entryOn = EntryBlockBbWidthPips;
                    double entryOff = EntryBlockBbWidthOffPips;
                    if (entryOff > entryOn) entryOff = entryOn;

                    double gap = Math.Max(0, MinVolOverEntryGapPips);

                    volOn = Math.Max(volOn, entryOn + gap);
                    volOff = Math.Max(volOff, entryOff + gap);
                }

                if (volOff > volOn) volOff = volOn;

                bool volAboveNow = _volBbAbovePrev ? (bbWidth >= volOff) : (bbWidth >= volOn);

                if (volAboveNow && !_volBbAbovePrev)
                {
                    bool rearmOk = (VolBlockMinRearmMin <= 0) ||
                                   (serverTime - _lastVolBlockArm).TotalMinutes >= VolBlockMinRearmMin;
                    if (rearmOk)
                    {
                        _volBlockEnd = serverTime.AddMinutes(Math.Max(0, VolBlockCooldownMin));
                        _lastVolBlockArm = serverTime;

                        if (VolBlockCancelsPending)
                        {
                            _pendingSell.Active = false;
                            _sellWaitCounter = 0;
                            _pendingBuy.Active = false;
                            _buyWaitCounter = 0;
                        }
                    }
                }

                _volBbAbovePrev = volAboveNow;
            }
        }

        private void HandleEntryBbBlock(DateTime serverTime, double bbWidth)
        {
            if (UseEntryBbBlock && EntryBlockBbWidthPips > 0)
            {
                double entryOn = EntryBlockBbWidthPips;
                double entryOff = EntryBlockBbWidthOffPips;
                if (entryOff > entryOn) entryOff = entryOn;

                bool entryAboveNow = _entryBbAbovePrev ? (bbWidth >= entryOff) : (bbWidth >= entryOn);

                if (entryAboveNow && !_entryBbAbovePrev)
                {
                    bool rearmOk = (EntryBlockMinRearmMin <= 0) ||
                                   (serverTime - _lastEntryBlockArm).TotalMinutes >= EntryBlockMinRearmMin;
                    if (rearmOk)
                    {
                        _entryBbBlockEnd = serverTime.AddMinutes(Math.Max(0, EntryBlockCooldownMin));
                        _lastEntryBlockArm = serverTime;

                        if (EntryBlockCancelsPending)
                        {
                            _pendingSell.Active = false;
                            _sellWaitCounter = 0;
                            _pendingBuy.Active = false;
                            _buyWaitCounter = 0;
                        }
                    }
                }

                _entryBbAbovePrev = entryAboveNow;
            }
        }

        private void HandleDailyReset(DateTime serverTime)
        {
            if (TimeZoneInfo.ConvertTime(serverTime, TimeZoneInfo.Utc, _jstZone).Date > _currentDayStart)
            {
                _currentDayStart = TimeZoneInfo.ConvertTime(serverTime, TimeZoneInfo.Utc, _jstZone).Date;
                _dailyRealizedPL = 0;
                _dailyLimitHit = false;

                _pendingSell.Active = false;
                _pendingBuy.Active = false;
                _sellWaitCounter = 0;
                _buyWaitCounter = 0;

                if (!OptimizationMode)
                    CalculateLastWeekHighLow();
            }
        }

        private void HandleGridAdd(Position[] sells, Position[] buys, double slope)
        {
            // ✅ ADX Dynamic Max Layers
            int dynamicMaxSell = GetDynamicMaxLayers((MaxLayersSell > 0) ? MaxLayersSell : MaxLayers);
            int dynamicMaxBuy = GetDynamicMaxLayers((MaxLayersBuy > 0) ? MaxLayersBuy : MaxLayers);

            // ✅ ADX Dynamic Step Width
            double dynamicStep = GetAdxAdjustedStepPips(StepPips);

            bool gridBlocked =
                !EnableGridAdd ||
                (UseVolatilityBlock && UseVolatilityBlock && VolBlockAffectsGridAdd && Server.Time < _volBlockEnd);


            // ✅ Spec fixes: block grid adds when global no-new conditions are active,
            // and when ADX filter is enabled but ADX is outside the allowed range.
            if (CheckNoNewConditions(Server.Time))
                gridBlocked = true;

            if (UseAdxFilter && !OptimizationMode)
            {
                bool adxOk = _currentAdxValue >= MinAdxForTrade && _currentAdxValue <= MaxAdxForCounter;
                if (!adxOk) gridBlocked = true;
            }

            double sellExposure = sells.Sum(p => p.VolumeInUnits);
            double buyExposure = buys.Sum(p => p.VolumeInUnits);

            if (MaxExposureUnitsSell > 0 && sellExposure >= MaxExposureUnitsSell)
                gridBlocked = true;
            if (MaxExposureUnitsBuy > 0 && buyExposure >= MaxExposureUnitsBuy)
                gridBlocked = true;

            if (ApplyRadarToGrid && UseRadar)
            {
                if (RadarMaxAbsSlopeSell > 0 && Math.Abs(slope) > RadarMaxAbsSlopeSell)
                    gridBlocked = true;
                if (RadarMaxAbsSlopeBuy > 0 && Math.Abs(slope) > RadarMaxAbsSlopeBuy)
                    gridBlocked = true;
            }

            if (!gridBlocked)
            {
                if (sells.Length > 0 && (!AutoShiftAffectsGridAdd || IsPriceWithinBounds(TradeType.Sell)))
                {
                    int addsUsed = Math.Max(0, sells.Length - 1);
                    if (addsUsed < dynamicMaxSell)
                    {
                        var last = sells.OrderByDescending(p => p.EntryTime).First();
                        double distPips = (Symbol.Bid - last.EntryPrice) / Symbol.PipSize;

                        if (distPips >= dynamicStep)
                        {
                            if (!_blockNewSellNow)
                                ExecuteWithLock(TradeType.Sell, BaseVolume);
                        }
                    }
                }

                if (buys.Length > 0 && (!AutoShiftAffectsGridAdd || IsPriceWithinBounds(TradeType.Buy)))
                {
                    int addsUsed = Math.Max(0, buys.Length - 1);
                    if (addsUsed < dynamicMaxBuy)
                    {
                        var last = buys.OrderByDescending(p => p.EntryTime).First();
                        double distPips = (last.EntryPrice - Symbol.Ask) / Symbol.PipSize;

                        if (distPips >= dynamicStep)
                        {
                            if (!_blockNewBuyNow)
                                ExecuteWithLock(TradeType.Buy, BaseVolume);
                        }
                    }
                }
            }
        }

        private int GetDynamicMaxLayers(int baseMax)
        {
            if (!UseAdxFilter) return baseMax;
            // ✅ FIXED: Hardcoded values replaced with parameters
            if (_currentAdxValue > AdxHighThreshold) return 1;
            if (_currentAdxValue > AdxLowThreshold) return Math.Max(1, baseMax - 1);
            return baseMax;
        }

        private bool CheckNoNewConditions(DateTime serverTime)
        {
            return _manualBoundsStopOutTriggered ||
                   serverTime < _breakerCooldownEnd ||
                   serverTime < _preNyCooldownEnd ||
                   (UseVolatilityBlock && serverTime < _volBlockEnd) ||
                   serverTime < _fridayNoNewEnd ||
                   (UseEntryBbBlock && serverTime < _entryBbBlockEnd) ||
                   _isWeeklyGuardActive ||
                   _blockNewOrders ||
                   _isExecuting ||
                   _dailyLimitHit;
        }

        private void UpdateBlockFlags(bool noNewNow, double slope)
        {
            _blockNewSellNow = noNewNow ||
                (UseDailyLossStreakGuard && Server.Time < _sellLossStreakEnd) ||
                (ApplyRadarToEntries && UseRadar && RadarMaxAbsSlopeSell > 0 && Math.Abs(slope) > RadarMaxAbsSlopeSell);

            _blockNewBuyNow = noNewNow ||
                (UseDailyLossStreakGuard && Server.Time < _buyLossStreakEnd) ||
                (ApplyRadarToEntries && UseRadar && RadarMaxAbsSlopeBuy > 0 && Math.Abs(slope) > RadarMaxAbsSlopeBuy);
        }

        private void HandleNewEntries(TradeDir dir, Position[] sells, Position[] buys, double slope, double bbWidth, bool adxOk)
        {
            bool sellAllowedByBasket = Server.Time >= _sellBasketCooldownEnd;
            bool buyAllowedByBasket = Server.Time >= _buyBasketCooldownEnd;

            if ((dir == TradeDir.SellOnly || dir == TradeDir.Both) && sells.Length == 0 && sellAllowedByBasket && !_blockNewSellNow && adxOk)
            {
                bool sellSignal = false;

                if (DiagnosticMode)
                {
                    sellSignal = IsPriceWithinBounds(TradeType.Sell) && Bars.HighPrices.Last(1) > _bb.Top.Last(1);
                }
                else
                {
                    if (slope < SellSlopeThreshold)
                    {
                        if (!(UseRadar && RadarMaxAbsSlopeSell > 0 && Math.Abs(slope) > RadarMaxAbsSlopeSell))
                        {
                            if (bbWidth >= SellMinBbWidth && bbWidth <= SellMaxBbWidth)
                            {
                                if (IsPriceWithinBounds(TradeType.Sell))
                                {
                                    if (IsGrindingUp(SellGrindLookback, SellMinContinualBars)
                                          && IsDeviationMet(TradeType.Sell, SellMinDeviationPips)
                                          && _rsi.Result.Last(1) > SellRsiThreshold
                                          && Bars.HighPrices.Last(1) > _bb.Top.Last(1))
                                    {
                                        sellSignal = true;
                                    }
                                }
                            }
                        }
                    }
                }

                if (sellSignal)
                {
                    if (UseWeeklyGuard && _prevWeekHigh > 0 && Bars.HighPrices.Last(1) >= _prevWeekHigh)
                    {
                        _isWeeklyGuardActive = true;
                        _weeklyGuardCooldownEnd = Server.Time.AddMinutes(WeeklyGuardCooldown);
                        return;
                    }

                    RegisterSignal(TradeType.Sell, BaseVolume, DiagnosticMode ? "SELL signal (DIAG)" : "SELL signal");
                }
            }

            if ((dir == TradeDir.BuyOnly || dir == TradeDir.Both) && buys.Length == 0 && buyAllowedByBasket && !_blockNewBuyNow && adxOk)
            {
                bool buySignal = false;

                if (DiagnosticMode)
                {
                    buySignal = IsPriceWithinBounds(TradeType.Buy) && Bars.LowPrices.Last(1) < _bb.Bottom.Last(1);
                }
                else
                {
                    if (slope > -BuySlopeThreshold)
                    {
                        if (!(UseRadar && RadarMaxAbsSlopeBuy > 0 && Math.Abs(slope) > RadarMaxAbsSlopeBuy))
                        {
                            if (bbWidth >= BuyMinBbWidth && bbWidth <= BuyMaxBbWidth)
                            {
                                if (IsPriceWithinBounds(TradeType.Buy))
                                {
                                    if (IsGrindingDown(BuyGrindLookback, BuyMinContinualBars)
                                          && IsDeviationMet(TradeType.Buy, BuyMinDeviationPips)
                                          && _rsi.Result.Last(1) < BuyRsiThreshold
                                          && Bars.LowPrices.Last(1) < _bb.Bottom.Last(1))
                                    {
                                        buySignal = true;
                                    }
                                }
                            }
                        }
                    }
                }

                if (buySignal)
                {
                    if (UseWeeklyGuard && _prevWeekLow > 0 && Bars.LowPrices.Last(1) <= _prevWeekLow)
                    {
                        _isWeeklyGuardActive = true;
                        _weeklyGuardCooldownEnd = Server.Time.AddMinutes(WeeklyGuardCooldown);
                        return;
                    }

                    RegisterSignal(TradeType.Buy, BaseVolume, DiagnosticMode ? "BUY signal (DIAG)" : "BUY signal");
                }
            }
        }

        private void TryApplyTimeStop(DateTime serverTime, Position[] botPositions)
        {
            if (!UseTimeStop) return;
            if (_lastTimeStopCheck != DateTime.MinValue && (serverTime - _lastTimeStopCheck).TotalSeconds < 10) return;

            var positions = botPositions ?? Array.Empty<Position>();
            if (positions.Length == 0) return;

            _lastTimeStopCheck = serverTime;

            int maxHoldMinSell = MaxHoldMinutes;
            int maxHoldMinBuy = (MaxHoldBuyMinutes > 0 ? MaxHoldBuyMinutes : MaxHoldMinutes);

            bool volActive = (_volBlockEnd != DateTime.MinValue && serverTime < _volBlockEnd);
            if (volActive)
            {
                maxHoldMinSell = Math.Min(maxHoldMinSell, VolMaxHoldMinutes);
                maxHoldMinBuy = Math.Min(maxHoldMinBuy, VolMaxHoldMinutes);
            }

            if (!Monitor.TryEnter(_tradeLock)) return;

            try
            {
                foreach (var p in positions)
                {
                    double ageMin = (serverTime - p.EntryTime).TotalMinutes;
                    int holdMin = (p.TradeType == TradeType.Buy ? maxHoldMinBuy : maxHoldMinSell);
                    if (ageMin < holdMin) continue;
                    if (TimeStopOnlyIfLosing && p.NetProfit >= 0) continue;
                    if (TimeStopMinLossPips > 0 && p.Pips > -TimeStopMinLossPips) continue;

                    var tr = ClosePosition(p);
                    if (tr == null || !tr.IsSuccessful) continue;

                    if (p.TradeType == TradeType.Sell)
                    {
                        _pendingSell.Active = false;
                        _sellWaitCounter = 0;
                        if (TimeStopCooldownMin > 0)
                        {
                            var end = serverTime.AddMinutes(TimeStopCooldownMin);
                            if (end > _timeStopCooldownEndSell) _timeStopCooldownEndSell = end;
                        }
                    }
                    else if (p.TradeType == TradeType.Buy)
                    {
                        _pendingBuy.Active = false;
                        _buyWaitCounter = 0;
                        if (TimeStopCooldownMin > 0)
                        {
                            var end = serverTime.AddMinutes(TimeStopCooldownMin);
                            if (end > _timeStopCooldownEndBuy) _timeStopCooldownEndBuy = end;
                        }
                    }
                }
            }
            finally
            {
                Monitor.Exit(_tradeLock);
            }
        }

        private void ApplyExpiryTpIfNeeded(DateTime serverTime, Position[] botPositions)
        {
            if (!EnableExpiryTp || ExpiryMinutes <= 0 || ExpiryTakeProfitPips <= 0) return;
            if (botPositions == null || botPositions.Length == 0) return;

            foreach (var p in botPositions)
            {
                if (_expiryTpAdjustedPositionIds.Contains(p.Id)) continue;

                double ageMin = (serverTime - p.EntryTime).TotalMinutes;
                if (ageMin < ExpiryMinutes) continue;

                double targetTpPrice = p.TradeType == TradeType.Buy
                    ? p.EntryPrice + (ExpiryTakeProfitPips * Symbol.PipSize)
                    : p.EntryPrice - (ExpiryTakeProfitPips * Symbol.PipSize);

	            var tr = ModifyPosition(p, p.StopLoss, targetTpPrice, ProtectionType.None);
                if (tr != null && tr.IsSuccessful)
                    _expiryTpAdjustedPositionIds.Add(p.Id);
                else
                    _expiryTpAdjustedPositionIds.Add(p.Id);
            }
        }

        private void TryAutoShiftBounds(DateTime serverTime)
        {
            if (!UseManualBounds || !UseAutoBoundsShift) return;
            if (_dynUpper <= 0 || _dynLower <= 0 || _dynUpper <= _dynLower) return;
            if (serverTime < _autoShiftCooldownEnd) return;

            if (_shiftBars == null || _shiftBars.Count < 3)
                _shiftBars = MarketData.GetBars(AutoShiftTimeFrame);
            if (_shiftBars == null || _shiftBars.Count < 3) return;

            var lastClosedTime = _shiftBars.OpenTimes.Last(1);
            if (lastClosedTime == _lastShiftBarTime) return;
            _lastShiftBarTime = lastClosedTime;

            double close = _shiftBars.ClosePrices.Last(1);
            double buffer = AutoShiftBreakoutBufferPips * Symbol.PipSize;
            double width = _dynUpper - _dynLower;
            if (width <= 0) return;

            if (close > _dynUpper + buffer)
            {
                _dynUpper += width;
                _dynLower += width;
                _autoShiftCooldownEnd = serverTime.AddMinutes(Math.Max(0, AutoShiftCooldownMin));
                RedrawManualBounds();
                return;
            }

            if (close < _dynLower - buffer)
            {
                _dynUpper -= width;
                _dynLower -= width;
                _autoShiftCooldownEnd = serverTime.AddMinutes(Math.Max(0, AutoShiftCooldownMin));
                RedrawManualBounds();
                return;
            }
        }

        private void RedrawManualBounds()
        {
            // Chart objects are meaningless in optimization / when dashboard is skipped.
            if (OptimizationMode || (!ShowDashboard && SkipDashboard)) return;

            // Manual bounds must be enabled and have valid effective values.
            if (!UseManualBounds) return;

            if (_dynUpper > 0)
                Chart.DrawHorizontalLine("ManualHigh", _dynUpper, Color.Magenta, 2, LineStyle.Solid);
            if (_dynLower > 0)
                Chart.DrawHorizontalLine("ManualLow", _dynLower, Color.Cyan, 2, LineStyle.Solid);

            // Optional StopOut lines (outer kill-switch). These are *not* the trade SL.
            // Upper: above upper bound; Lower: below lower bound.
            if (_dynUpper > 0 && ManualUpperStopOutPips > 0)
            {
                var upperStop = _dynUpper + ManualUpperStopOutPips * Symbol.PipSize;
                Chart.DrawHorizontalLine("ManualStopOutHigh", upperStop, Color.Red, 1, LineStyle.Dots);
            }

            if (_dynLower > 0 && ManualLowerStopOutPips > 0)
            {
                var lowerStop = _dynLower - ManualLowerStopOutPips * Symbol.PipSize;
                Chart.DrawHorizontalLine("ManualStopOutLow", lowerStop, Color.Blue, 1, LineStyle.Dots);
            }
        }

        private void ValidateManualBoundsOrDisable()
{
    if (!UseManualBounds) return;

    // Validate using the effective dynamic bounds (these are what the bot actually uses),
    // but DO NOT silently disable Manual Bounds. If upper/lower are reversed, auto-swap and warn once.
    if (_dynUpper > 0 && _dynLower > 0 && _dynLower >= _dynUpper)
    {
        // Auto-swap to keep feature effective and avoid "silently not working" accidents.
        double tmp = _dynUpper;
        _dynUpper = _dynLower;
        _dynLower = tmp;

        // Mirror the swap into the user-facing parameters for runtime clarity (not persisted by cTrader).
        double ptmp = ManualUpperPrice;
        ManualUpperPrice = ManualLowerPrice;
        ManualLowerPrice = ptmp;

        if (!_manualBoundsSwapWarned)
        {
            Print("[ManualBounds] Upper/Lower were reversed (Lower >= Upper). Auto-swapped at runtime. Upper={0}, Lower={1}", _dynUpper, _dynLower);
            _manualBoundsSwapWarned = true;
        }

        // Re-draw lines after correction
        RedrawManualBounds();
    }
}


        private bool CheckManualBoundsStopOut(DateTime serverTime, Position[] botPositions)
        {
            if (_manualBoundsStopOutTriggered) return true;
            if (!UseManualBounds) return false;

            double upStop = 0;
            double loStop = 0;

            if (_dynUpper > 0 && ManualUpperStopOutPips > 0)
                upStop = _dynUpper + ManualUpperStopOutPips * Symbol.PipSize;
            if (_dynLower > 0 && ManualLowerStopOutPips > 0)
                loStop = _dynLower - ManualLowerStopOutPips * Symbol.PipSize;

            if (upStop <= 0 && loStop <= 0) return false;

            bool hit = (upStop > 0 && Symbol.Ask >= upStop) || (loStop > 0 && Symbol.Bid <= loStop);
            if (!hit) return false;

            if (botPositions != null && botPositions.Length > 0)
                ExecuteWithLock(() => CloseAll(botPositions));

            _pendingSell.Active = false;
            _sellWaitCounter = 0;
            _pendingBuy.Active = false;
            _buyWaitCounter = 0;

            _manualBoundsStopOutTriggered = true;
            _manualBoundsStopOutTime = serverTime;

            return true;
        }

        private bool IsDayAllowed(DayOfWeek d)
        {
            if (d == DayOfWeek.Monday) return TradeMon;
            if (d == DayOfWeek.Friday) return TradeFri;
            return (d != DayOfWeek.Saturday && d != DayOfWeek.Sunday);
        }

        private bool IsGrindingUp(int lookback, int minBars)
        {
            if (lookback <= 0 || minBars <= 0) return false;
            if (Bars.Count < lookback + 2) return false;

            int c = 0;
            for (int i = 1; i <= lookback; i++)
                if (Bars.ClosePrices.Last(i) > Bars.OpenPrices.Last(i)) c++;

            return c >= minBars;
        }

        private bool IsGrindingDown(int lookback, int minBars)
        {
            if (lookback <= 0 || minBars <= 0) return false;
            if (Bars.Count < lookback + 2) return false;

            int c = 0;
            for (int i = 1; i <= lookback; i++)
                if (Bars.ClosePrices.Last(i) < Bars.OpenPrices.Last(i)) c++;

            return c >= minBars;
        }

        private bool IsDeviationMet(TradeType type, double minDev)
        {
            if (type == TradeType.Sell)
                return (Bars.ClosePrices.Last(1) - _devMa.Result.Last(1)) / Symbol.PipSize >= minDev;
            return (_devMa.Result.Last(1) - Bars.ClosePrices.Last(1)) / Symbol.PipSize >= minDev;
        }

        private bool IsAegisTriggered(DateTime jst)
        {
            double h = jst.Hour + jst.Minute / 60.0;
            return IsInSlotExtended(h, Slot1, SlotDur) || IsInSlotExtended(h, Slot2, SlotDur) ||
                   IsInSlotExtended(h, Slot3, SlotDur) || IsInSlotExtended(h, Slot4, SlotDur);
        }

        private bool IsInSlotExtended(double current, double start, int durMin)
{
    // Slot "0" means DISABLED (avoid accidental 00:00 block). Negative values are allowed (e.g., -0.2 for near-midnight).
    if (Math.Abs(start) < 1e-9) return false;

    double end = start + durMin / 60.0;

            // Supports "25.0" style hours (25.0 = 01:00 next day)
            if (start <= 24.0 && end <= 24.0)
                return current >= start && current < end;

            // Treat window as [start, end) on a 0..48 axis
            double cut = (end > 24.0) ? (end - 24.0) : (start > 24.0 ? (start - 24.0) : 0.0);
            double currentExt = current;
            if (cut > 0.0 && current < cut) currentExt += 24.0;
            return currentExt >= start && currentExt < end;
        }

        private bool IsInTimeRangeExtended(double current, double start, double end)
        {
            // Supports "25.0" style hours (25.0 = 01:00 next day)
            if (start <= 24.0 && end <= 24.0)
            {
                if (start < end)
                    return current >= start && current < end;
                return current >= start || current < end;
            }

            // Treat range as [start, end) on a 0..48 axis
            double cut = (end > 24.0) ? (end - 24.0) : (start > 24.0 ? (start - 24.0) : 0.0);
            double currentExt = current;
            if (cut > 0.0 && current < cut) currentExt += 24.0;
            return currentExt >= start && currentExt < end;
        }

        private bool IsPriceWithinBounds(TradeType type)
        {
            // Spec: When manual bounds are enabled, ANY trade direction is forbidden outside [Lower, Upper].
            // We check both sides regardless of trade type.
            if (!UseManualBounds) return true;
            if (_dynUpper > 0 && Symbol.Bid > _dynUpper) return false;
            if (_dynLower > 0 && Symbol.Ask < _dynLower) return false;
            return true;
        }

        private bool IsStrategicPauseActive(double jstHour)
        {
            if (!UseStrategicPause) return false;
            return IsInTimeRangeExtended(jstHour, PauseStart, PauseEnd);
        }

        private bool IsFridayNoNewWindow(DateTime jst, double jstHour)
        {
            if (!(jst.DayOfWeek == DayOfWeek.Friday || jst.DayOfWeek == DayOfWeek.Saturday)) return false;
            if (FridayNoNewBeforeHours <= 0) return false;

            double t = jstHour;
            if (jst.DayOfWeek == DayOfWeek.Saturday) t += 24.0;

            double start = FridayExitJst - FridayNoNewBeforeHours;
            if (start < 0) start = 0;

            return t >= start && t < FridayExitJst;
        }

        private bool IsPreNyDayEnabled(DayOfWeek d)
        {
            switch (d)
            {
                case DayOfWeek.Monday: return PreNyMon;
                case DayOfWeek.Tuesday: return PreNyTue;
                case DayOfWeek.Wednesday: return PreNyWed;
                case DayOfWeek.Thursday: return PreNyThu;
                case DayOfWeek.Friday: return PreNyFri;
                default: return false;
            }
        }

        // =================================================================
        // Simplified Log Method (Optimization Mode Support)
        // =================================================================
        
private DateTime _lastBlockLogTime = DateTime.MinValue;
private string _lastBlockSignature = "";

private void LogBlockStateChanges(DateTime serverTime, double slope, bool adxOk)
{
    if (OptimizationMode || SkipComplexLogs || !EnableBlockReasonLog) return;

    // Throttle
    if (BlockLogMinIntervalSec > 0 && _lastBlockLogTime != DateTime.MinValue &&
        (serverTime - _lastBlockLogTime).TotalSeconds < BlockLogMinIntervalSec)
        return;

    var reasons = new List<string>();

    // Global blocks
    if (_manualBoundsStopOutTriggered) reasons.Add("ManualBoundsStopOut");
    if (serverTime < _breakerCooldownEnd) reasons.Add("Shockwave");
    if (serverTime < _preNyCooldownEnd) reasons.Add("PreNY");
    if (UseVolatilityBlock && serverTime < _volBlockEnd) reasons.Add("VolBlock");
    if (UseEntryBbBlock && serverTime < _entryBbBlockEnd) reasons.Add("EntryBBBlock");
    if (serverTime < _fridayNoNewEnd) reasons.Add("FridayNoNew");
    if (_isWeeklyGuardActive) reasons.Add("WeeklyGuard");
    if (_blockNewOrders) reasons.Add("BlockNewOrders");
    if (_dailyLimitHit) reasons.Add("DailyLimit");

    // ADX gate (if enabled, adxOk tells whether trading is allowed)
    if (UseAdxFilter && !adxOk) reasons.Add($"ADXGate({_currentAdxValue:F1})");

    // Radar (directional)
    bool radarSell = (ApplyRadarToEntries && UseRadar && RadarMaxAbsSlopeSell > 0 && Math.Abs(slope) > RadarMaxAbsSlopeSell);
    bool radarBuy  = (ApplyRadarToEntries && UseRadar && RadarMaxAbsSlopeBuy > 0 && Math.Abs(slope) > RadarMaxAbsSlopeBuy);
    if (radarSell) reasons.Add($"RadarSell(|slope|={Math.Abs(slope):F2} > {RadarMaxAbsSlopeSell:F2})");
    if (radarBuy)  reasons.Add($"RadarBuy(|slope|={Math.Abs(slope):F2} > {RadarMaxAbsSlopeBuy:F2})");

    // Basket cooldowns (directional)
    if (serverTime < _sellBasketCooldownEnd) reasons.Add("SellBasketCD");
    if (serverTime < _buyBasketCooldownEnd) reasons.Add("BuyBasketCD");

    // Loss streak guards (directional)
    if (UseDailyLossStreakGuard && serverTime < _sellLossStreakEnd) reasons.Add("SellLossStreak");
    if (UseDailyLossStreakGuard && serverTime < _buyLossStreakEnd) reasons.Add("BuyLossStreak");

    // If nothing blocks, do nothing.
    if (reasons.Count == 0) return;

    string sig = string.Join("+", reasons);

    // Log only when state changes OR at throttle interval
    if (sig != _lastBlockSignature)
    {
        Print($"[BLOCK] {sig}");
        _lastBlockSignature = sig;
        _lastBlockLogTime = serverTime;
    }
}
    }
}