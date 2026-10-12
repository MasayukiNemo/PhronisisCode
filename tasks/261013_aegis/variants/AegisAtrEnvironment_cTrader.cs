using System;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo
{
    [Indicator(IsOverlay = false, AccessRights = AccessRights.None, TimeZone = TimeZones.UTC, AutoRescale = true)]
    public class AegisAtrEnvironment : Indicator
    {
        [Parameter("ATR Period", Group = "1. Core", DefaultValue = 14, MinValue = 2)]
        public int AtrPeriod { get; set; }

        [Parameter("ATR MA Period", Group = "1. Core", DefaultValue = 20, MinValue = 2)]
        public int AtrMaPeriod { get; set; }

        [Parameter("ATR MA Type", Group = "1. Core", DefaultValue = MovingAverageType.Exponential)]
        public MovingAverageType AtrMaType { get; set; }

        [Parameter("ATR Expansion Ratio", Group = "2. Thresholds", DefaultValue = 1.15, MinValue = 0.50, Step = 0.01)]
        public double AtrExpansionRatio { get; set; }

        [Parameter("ATR Compression Ratio", Group = "2. Thresholds", DefaultValue = 0.90, MinValue = 0.10, Step = 0.01)]
        public double AtrCompressionRatio { get; set; }

        [Parameter("Use Slope Check", Group = "2. Thresholds", DefaultValue = true)]
        public bool UseSlopeCheck { get; set; }

        [Parameter("Slope Lookback Bars", Group = "2. Thresholds", DefaultValue = 3, MinValue = 1)]
        public int SlopeLookbackBars { get; set; }

        [Parameter("Show Markers", Group = "3. Display", DefaultValue = true)]
        public bool ShowMarkers { get; set; }

        [Parameter("Show State Line", Group = "3. Display", DefaultValue = true)]
        public bool ShowStateLine { get; set; }

        [Output("ATR (pips)", LineColor = "DodgerBlue", Thickness = 2)]
        public IndicatorDataSeries AtrPipsSeries { get; set; }

        [Output("ATR MA (pips)", LineColor = "Orange", Thickness = 2)]
        public IndicatorDataSeries AtrMaPipsSeries { get; set; }

        [Output("State", LineColor = "Lime", Thickness = 2)]
        public IndicatorDataSeries StateSeries { get; set; }

        [Output("Compression", LineColor = "DeepSkyBlue", PlotType = PlotType.Points, Thickness = 4)]
        public IndicatorDataSeries CompressionSeries { get; set; }

        [Output("Expansion", LineColor = "Red", PlotType = PlotType.Points, Thickness = 4)]
        public IndicatorDataSeries ExpansionSeries { get; set; }

        private AverageTrueRange _atr;
        private MovingAverage _atrMa;

        protected override void Initialize()
        {
            _atr = Indicators.AverageTrueRange(Bars, AtrPeriod, MovingAverageType.Exponential);
            _atrMa = Indicators.MovingAverage(_atr.Result, AtrMaPeriod, AtrMaType);
        }

        public override void Calculate(int index)
        {
            int warmup = Math.Max(AtrMaPeriod, SlopeLookbackBars + 1);
            if (index < warmup)
            {
                AtrPipsSeries[index] = double.NaN;
                AtrMaPipsSeries[index] = double.NaN;
                StateSeries[index] = double.NaN;
                CompressionSeries[index] = double.NaN;
                ExpansionSeries[index] = double.NaN;
                return;
            }

            double atrPips = _atr.Result[index] / Symbol.PipSize;
            double atrMaPips = _atrMa.Result[index] / Symbol.PipSize;
            double ratio = atrMaPips <= 0 ? 1.0 : atrPips / atrMaPips;

            bool slopeUp = true;
            bool slopeDown = true;

            if (UseSlopeCheck)
            {
                int prev = Math.Max(0, index - SlopeLookbackBars);
                slopeUp = _atr.Result[index] > _atr.Result[prev];
                slopeDown = _atr.Result[index] < _atr.Result[prev];
            }

            bool isExpansion = ratio >= AtrExpansionRatio && (!UseSlopeCheck || slopeUp);
            bool isCompression = ratio <= AtrCompressionRatio && (!UseSlopeCheck || slopeDown);

            AtrPipsSeries[index] = atrPips;
            AtrMaPipsSeries[index] = atrMaPips;

            StateSeries[index] = ShowStateLine
                ? (isExpansion ? 1.0 : (isCompression ? -1.0 : 0.0))
                : double.NaN;

            CompressionSeries[index] = (ShowMarkers && isCompression) ? atrPips : double.NaN;
            ExpansionSeries[index] = (ShowMarkers && isExpansion) ? atrPips : double.NaN;
        }
    }
}
