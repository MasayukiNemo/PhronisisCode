using System;
using System.Linq;
using cAlgo.API;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class GoldmineProbe : Robot
    {
        [Parameter("Enable Order", DefaultValue = false)]
        public bool EnableOrder { get; set; }

        [Parameter("Volume (lots)", DefaultValue = 0.01, MinValue = 0.01)]
        public double Volume { get; set; }

        [Parameter("Stop Loss (pips)", DefaultValue = 20.0, MinValue = 0.0)]
        public double StopLossPips { get; set; }

        [Parameter("Take Profit (pips)", DefaultValue = 40.0, MinValue = 0.0)]
        public double TakeProfitPips { get; set; }

        [Parameter("Max Spread (pips)", DefaultValue = 2.0, MinValue = 0.0)]
        public double MaxSpreadPips { get; set; }

        [Parameter("Max Daily Loss (%)", DefaultValue = 1.0, MinValue = 0.0)]
        public double MaxDailyLossPct { get; set; }

        // Fire-once guards. Order is attempted only in OnStart, never in OnTick.
        private bool _orderAttempted;
        private bool _killSwitched;

        // Equity-anchored daily P/L (realized + floating approximation).
        private DateTime _day;
        private double _dayStartEquity;
        private bool _dayInitialized;

        protected override void OnStart()
        {
            _orderAttempted = false;
            _killSwitched = false;

            try
            {
                // 1. Hard guard: demo only.
                if (Account == null)
                {
                    Print("ABORT: Account is null.");
                    Stop();
                    return;
                }

                // Demo/live is exposed by IAccount.IsLive (AccountType is the Hedged/Netted accounting model, not demo/live).
                if (Account.IsLive)
                {
                    Print("ABORT: live account (IsLive=true). GoldmineProbe runs on demo only.");
                    Stop();
                    return;
                }

                if (Symbol == null)
                {
                    Print("ABORT: Symbol is null.");
                    Stop();
                    return;
                }

                // 2. Connection / spread probe.
                double pipSize = Symbol.PipSize;
                double spreadPips = pipSize != 0 ? Symbol.Spread / pipSize : double.NaN;
                Print("GoldmineProbe start: Account={0} Broker={1} IsLive={2} Asset={3} Type={4} Balance={5} Equity={6} Symbol={7} Spread={8} SpreadPips={9:F2}",
                    Account.Number, Account.BrokerName, Account.IsLive, Account.Asset, Account.AccountType, Account.Balance, Account.Equity, Symbol.Name, Symbol.Spread, spreadPips);

                // Anchor daily P/L to start-of-run equity.
                if (Server != null)
                {
                    _day = Server.Time.Date;
                    _dayStartEquity = Account.Equity;
                    _dayInitialized = true;
                    Print("Daily loss limit: {0:F2}% of day-start equity {1:F2} = {2:F2} {3}", MaxDailyLossPct, _dayStartEquity, _dayStartEquity * MaxDailyLossPct / 100.0, Account.Asset);
                }

                // 4. Probe-only default: no order.
                if (!EnableOrder)
                {
                    Print("Probe-only mode (EnableOrder=false): no order placed. Spread check done.");
                    return;
                }

                // 3. Single-shot order path.
                if (Volume <= 0)
                {
                    Print("SKIP: Volume must be > 0 (got {0}).", Volume);
                    _orderAttempted = true;
                    return;
                }

                if (double.IsNaN(spreadPips))
                {
                    Print("SKIP: cannot compute spread (PipSize=0).");
                    _orderAttempted = true;
                    return;
                }

                if (spreadPips > MaxSpreadPips)
                {
                    Print("SKIP: spread {0:F2} pips exceeds MaxSpreadPips {1:F2} pips. No order.", spreadPips, MaxSpreadPips);
                    _orderAttempted = true;
                    return;
                }

                // cAlgo ExecuteMarketOrder takes volume in UNITS, not lots.
                double volumeInUnits = Symbol.NormalizeVolumeInUnits(Symbol.QuantityToVolumeInUnits(Volume), RoundingMode.ToNearest);
                if (volumeInUnits < Symbol.VolumeInUnitsMin)
                {
                    Print("SKIP: Volume {0} lots -> {1} units is below Symbol.VolumeInUnitsMin ({2}).", Volume, volumeInUnits, Symbol.VolumeInUnitsMin);
                    _orderAttempted = true;
                    return;
                }

                double preBid = Symbol.Bid;
                double preAsk = Symbol.Ask;
                double preMid = (preBid + preAsk) / 2.0;

                // Fix to exactly once even if the call throws.
                _orderAttempted = true;

                TradeResult result = ExecuteMarketOrder(TradeType.Buy, Symbol.Name, volumeInUnits, "goldmine-probe", StopLossPips, TakeProfitPips);

                if (result == null)
                {
                    Print("Order FAILED: TradeResult is null.");
                    return;
                }

                if (result.IsSuccessful)
                {
                    if (result.Position != null)
                    {
                        double entry = result.Position.EntryPrice;
                        double slipPrice = entry - preAsk;
                        double slipPips = pipSize != 0 ? slipPrice / pipSize : double.NaN;
                        Print("Order OK: Buy {0} {1} lots ({2} units) label=goldmine-probe Entry={3} SL={4}pips TP={5}pips PreBid={6} PreAsk={7} PreMid={8} Slippage={9} price ({10:F2} pips)",
                            Symbol.Name, Volume, volumeInUnits, entry, StopLossPips, TakeProfitPips, preBid, preAsk, preMid, slipPrice, slipPips);
                    }
                    else
                    {
                        Print("Order reported success but Position is null. PreBid={0} PreAsk={1}", preBid, preAsk);
                    }
                }
                else
                {
                    Print("Order FAILED: Error={0}", result.Error);
                }
            }
            catch (Exception ex)
            {
                Print("Order EXCEPTION: {0}", ex.Message);
            }
        }

        protected override void OnTick()
        {
            try
            {
                if (Account == null || Server == null)
                    return;

                DateTime today = Server.Time.Date;
                if (!_dayInitialized || today != _day)
                {
                    _day = today;
                    _dayStartEquity = Account.Equity;
                    _dayInitialized = true;
                }

                double dailyPnl = Account.Equity - _dayStartEquity;
                double limit = _dayStartEquity * (MaxDailyLossPct / 100.0);

                if (dailyPnl <= -limit && !_killSwitched)
                {
                    _killSwitched = true;
                    Print("KILL-SWITCH: daily P/L {0:F2} (equity {1:F2} - dayStart {2:F2}) <= -limit {3:F2} ({4}% of dayStart). Blocking new orders and flattening.", dailyPnl, Account.Equity, _dayStartEquity, limit, MaxDailyLossPct);

                    try
                    {
                        if (Positions != null)
                        {
                            foreach (var position in Positions.ToList())
                            {
                                try
                                {
                                    ClosePosition(position);
                                    Print("KILL-SWITCH: closed {0} {1}", position.SymbolName, position.Id);
                                }
                                catch (Exception ex)
                                {
                                    Print("KILL-SWITCH close FAILED for {0}: {1}", position.Id, ex.Message);
                                }
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        Print("KILL-SWITCH flatten EXCEPTION: {0}", ex.Message);
                    }

                    Stop();
                }
            }
            catch (Exception ex)
            {
                Print("OnTick EXCEPTION: {0}", ex.Message);
            }
        }

        protected override void OnStop()
        {
            Print("GoldmineProbe stopped. OrderAttempted={0} KillSwitched={1}", _orderAttempted, _killSwitched);
        }
    }
}
