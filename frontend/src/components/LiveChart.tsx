"use client";

import React, { useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Area,
} from "recharts";
import { LineChart as ChartIcon } from "lucide-react";

interface HistoricalDataPoint {
  time: string;
  AAPL: number;
  TSLA: number;
  GOOGL: number;
  MSFT: number;
  AMZN: number;
  price: number;
  volume: number;
  activeSymbolPrice?: number;
}

import { TooltipProps } from "recharts";
import { NameType, ValueType } from "recharts/types/component/DefaultTooltipContent";

interface LiveChartProps {
  data: HistoricalDataPoint[];
}

const formatXAxis = (tickItem: string) => {
  try {
    const date = new Date(tickItem);
    if (isNaN(date.getTime())) return tickItem;
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return tickItem;
  }
};

const CustomTooltip = ({ active, payload, label }: TooltipProps<ValueType, NameType>) => {
  if (active && payload && payload.length) {
    const timeStr = formatXAxis(label as string);
    return (
      <div className="glass rounded-xl p-4 shadow-xl border border-white/10 text-xs flex flex-col space-y-1.5 min-w-[150px]">
        <span className="text-text-muted font-mono">{timeStr}</span>
        {payload.map((p) => (
          <div key={p.name} className="flex items-center justify-between space-x-4">
            <span className="font-semibold text-text-secondary" style={{ color: p.color || p.fill }}>
              {p.name}:
            </span>
            <span className="font-mono font-bold text-white">
              {p.name && p.name.includes("Price") ? `$${Number(p.value).toFixed(2)}` : Number(p.value).toFixed(4)}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function LiveChart({ data }: LiveChartProps) {
  const [selectedSymbol, setSelectedSymbol] = useState<string>("ALL");
  const watchlist = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN"];

  // Color mapping per ticker
  const colors: Record<string, string> = {
    AAPL: "#60a5fa", // Blue
    TSLA: "#f87171", // Red
    GOOGL: "#34d399", // Emerald
    MSFT: "#fbbf24", // Yellow
    AMZN: "#a78bfa", // Purple
  };

  return (
    <div className="glass rounded-2xl p-6 flex flex-col justify-between h-[450px]">
      {/* Chart Headers */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2.5">
          <ChartIcon className="h-5 w-5 text-accent" />
          <div>
            <h3 className="font-semibold text-white tracking-wide">Live Intelligence Stream</h3>
            <p className="text-xs text-text-secondary">Real-time dynamic overlay of market sentiment and asset movements</p>
          </div>
        </div>

        {/* View Toggle */}
        <div className="flex items-center space-x-2 bg-white/[0.02] border border-white/[0.08] p-1 rounded-xl">
          <button
            onClick={() => setSelectedSymbol("ALL")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              selectedSymbol === "ALL"
                ? "bg-accent text-white shadow-glow-indigo"
                : "text-text-secondary hover:text-white"
            }`}
          >
            All Sentiments
          </button>
          {watchlist.map((symbol) => (
            <button
              key={symbol}
              onClick={() => setSelectedSymbol(symbol)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide font-mono transition-all ${
                selectedSymbol === symbol
                  ? "bg-white/[0.08] text-white border border-white/15"
                  : "text-text-secondary hover:text-white"
              }`}
            >
              {symbol}
            </button>
          ))}
        </div>
      </div>

      {/* Recharts Container */}
      <div className="flex-1 w-full min-h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: -5, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" vertical={false} />
            
            <XAxis
              dataKey="time"
              tickFormatter={formatXAxis}
              stroke="#475569"
              tickLine={false}
              axisLine={false}
              dy={10}
              className="text-[10px] font-mono"
            />
            
            {/* Sentiment Y Axis */}
            <YAxis
              yAxisId="sentiment"
              domain={[-1, 1]}
              stroke="#475569"
              tickLine={false}
              axisLine={false}
              dx={-5}
              className="text-[10px] font-mono"
            />
            
            {/* Price Y Axis */}
            <YAxis
              yAxisId="price"
              orientation="right"
              domain={["auto", "auto"]}
              stroke="#475569"
              tickLine={false}
              axisLine={false}
              dx={5}
              className="text-[10px] font-mono"
            />

            <Tooltip content={<CustomTooltip />} />
            <Legend verticalAlign="top" height={36} className="text-xs" />

            {selectedSymbol === "ALL" ? (
              // Multi-line sentiment plot
              watchlist.map((symbol) => (
                <Line
                  key={symbol}
                  yAxisId="sentiment"
                  type="monotone"
                  dataKey={symbol}
                  name={`${symbol} Sentiment`}
                  stroke={colors[symbol]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                  animationDuration={300}
                />
              ))
            ) : (
              // Specific Ticker Detailed View (Sentiment Line + Price Area + Volume Bar)
              <>
                <Area
                  yAxisId="price"
                  type="monotone"
                  dataKey="activeSymbolPrice"
                  name={`${selectedSymbol} Price`}
                  stroke="#6366f1"
                  fillOpacity={1}
                  fill="url(#colorPrice)"
                  strokeWidth={2}
                  animationDuration={300}
                />
                <Line
                  yAxisId="sentiment"
                  type="monotone"
                  dataKey={selectedSymbol}
                  name={`${selectedSymbol} Sentiment`}
                  stroke={colors[selectedSymbol]}
                  strokeWidth={3}
                  dot={false}
                  activeDot={{ r: 5 }}
                  animationDuration={300}
                />
                <Bar
                  yAxisId="price"
                  dataKey="volume"
                  name="Volume"
                  fill="#ffffff05"
                  radius={[4, 4, 0, 0]}
                  barSize={12}
                  animationDuration={300}
                />
              </>
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
