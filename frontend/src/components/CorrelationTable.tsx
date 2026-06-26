"use client";

import React from "react";
import { motion } from "framer-motion";
import { Scale } from "lucide-react";

interface CorrelationInfo {
  correlation: number;
  p_value: number;
  data_points: number;
  significant: boolean;
  status: string;
}

interface CorrelationTableProps {
  correlations: Record<string, CorrelationInfo>;
  avgSentiments: Record<string, number>;
}

export default function CorrelationTable({ correlations, avgSentiments }: CorrelationTableProps) {
  const watchlist = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN"];

  const getSignal = (corr: number, pVal: number) => {
    if (pVal >= 0.05 || isNaN(pVal)) {
      return {
        text: "Neutral (Insignificant)",
        color: "bg-neutral/5 text-neutral/80 border-neutral/10",
      };
    }
    if (corr >= 0.3) {
      return {
        text: "Strong Buy Signal",
        color: "bg-positive/10 text-positive border-positive/20 font-semibold shadow-glow-green",
      };
    }
    if (corr <= -0.3) {
      return {
        text: "Strong Sell Signal",
        color: "bg-negative/10 text-negative border-negative/20 font-semibold shadow-glow-red",
      };
    }
    return {
      text: "Neutral (Weak)",
      color: "bg-neutral/5 text-neutral/80 border-neutral/10",
    };
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, x: -10 },
    show: { opacity: 1, x: 0 },
  };

  return (
    <div className="glass rounded-2xl p-6 flex flex-col h-[400px]">
      {/* Table Header */}
      <div className="flex items-center space-x-2.5 mb-5 shrink-0">
        <Scale className="h-5 w-5 text-accent" />
        <div>
          <h3 className="font-semibold text-white tracking-wide">Correlation & Intelligence Table</h3>
          <p className="text-xs text-text-secondary">Statistically verified Pearson correlation vs price (7-day window)</p>
        </div>
      </div>

      {/* Table Container */}
      <div className="flex-1 overflow-x-auto no-scrollbar">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/[0.08] pb-3 text-text-muted text-[10px] uppercase font-bold tracking-wider font-mono">
              <th className="py-3 px-4">Symbol</th>
              <th className="py-3 px-4">Avg Sentiment</th>
              <th className="py-3 px-4">Correlation</th>
              <th className="py-3 px-4">P-Value</th>
              <th className="py-3 px-4 text-right">Signal</th>
            </tr>
          </thead>
          <motion.tbody
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="divide-y divide-white/[0.03]"
          >
            {watchlist.map((symbol) => {
              const corrData = correlations[symbol] || {
                correlation: 0.0,
                p_value: 1.0,
                data_points: 0,
                significant: false,
                status: "awaiting_data",
              };
              const avgSent = avgSentiments[symbol] || 0.0;
              const signal = getSignal(corrData.correlation, corrData.p_value);

              return (
                <motion.tr
                  key={symbol}
                  variants={itemVariants}
                  className="hover:bg-white/[0.03] transition-colors group cursor-pointer text-sm"
                >
                  {/* Symbol */}
                  <td className="py-3 px-4 font-mono font-bold text-white tracking-wide">
                    {symbol}
                  </td>
                  
                  {/* Avg Sentiment */}
                  <td className="py-3 px-4 font-mono">
                    <span className={avgSent > 0 ? "text-positive" : avgSent < 0 ? "text-negative" : "text-neutral"}>
                      {avgSent >= 0 ? "+" : ""}
                      {avgSent.toFixed(2)}
                    </span>
                  </td>

                  {/* Correlation */}
                  <td className="py-3 px-4 font-mono font-semibold">
                    {corrData.status === "awaiting_data" ? (
                      <span className="text-text-muted text-xs">--</span>
                    ) : (
                      <span className={corrData.correlation > 0 ? "text-positive" : corrData.correlation < 0 ? "text-negative" : "text-neutral"}>
                        {corrData.correlation.toFixed(3)}
                      </span>
                    )}
                  </td>

                  {/* P-Value */}
                  <td className="py-3 px-4 font-mono text-text-secondary">
                    {corrData.status === "awaiting_data" ? (
                      <span className="text-text-muted text-xs">--</span>
                    ) : (
                      <span>{corrData.p_value.toFixed(4)}</span>
                    )}
                  </td>

                  {/* Signal Badge */}
                  <td className="py-3 px-4 text-right">
                    <span className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${signal.color}`}>
                      {signal.text}
                    </span>
                  </td>
                </motion.tr>
              );
            })}
          </motion.tbody>
        </table>
      </div>
    </div>
  );
}
