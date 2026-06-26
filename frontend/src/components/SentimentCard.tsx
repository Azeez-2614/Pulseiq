"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface SentimentCardProps {
  symbol: string;
  score: number;
  label: string;
  price: number;
  change_pct: number;
}

export default function SentimentCard({
  symbol,
  score,
  label,
  price,
  change_pct,
}: SentimentCardProps) {
  const [prevScore, setPrevScore] = useState(score);

  useEffect(() => {
    setPrevScore(score);
  }, [score]);

  const isPosSentiment = label.toLowerCase() === "positive" || score >= 0.05;
  const isNegSentiment = label.toLowerCase() === "negative" || score <= -0.05;
  
  const isPosPrice = change_pct >= 0;

  // Decide colors and shadows based on sentiment label
  const glowClass = isPosSentiment
    ? "shadow-glow-green border-positive/30"
    : isNegSentiment
    ? "shadow-glow-red border-negative/30"
    : "border-white/[0.08]";

  const scoreColor = isPosSentiment
    ? "text-positive"
    : isNegSentiment
    ? "text-negative"
    : "text-neutral";

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className={`glass-interactive rounded-2xl p-6 flex flex-col justify-between h-48 relative overflow-hidden ${glowClass}`}
    >
      {/* Background Decorative Accent */}
      <div className={`absolute top-0 right-0 h-24 w-24 rounded-full filter blur-3xl opacity-[0.03] transition-colors duration-500 ${
        isPosSentiment ? "bg-positive" : isNegSentiment ? "bg-negative" : "bg-neutral"
      }`} />

      {/* Header Info */}
      <div className="flex items-center justify-between z-10">
        <span className="font-mono font-bold text-2xl text-white tracking-wider">{symbol}</span>
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.05]">
          {isPosSentiment ? (
            <>
              <TrendingUp className="h-3.5 w-3.5 text-positive" />
              <span className="text-xs font-bold text-positive uppercase">Positive</span>
            </>
          ) : isNegSentiment ? (
            <>
              <TrendingDown className="h-3.5 w-3.5 text-negative" />
              <span className="text-xs font-bold text-negative uppercase">Negative</span>
            </>
          ) : (
            <>
              <Minus className="h-3.5 w-3.5 text-neutral" />
              <span className="text-xs font-bold text-neutral uppercase">Neutral</span>
            </>
          )}
        </div>
      </div>

      {/* Sentiment Score Display */}
      <div className="my-4 flex items-center z-10">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.span
            key={score}
            initial={{ y: 15, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -15, opacity: 0 }}
            transition={{ type: "spring", stiffness: 400, damping: 25 }}
            className={`font-mono text-4xl font-extrabold tracking-tight ${scoreColor}`}
          >
            {score >= 0 ? "+" : ""}
            {score.toFixed(2)}
          </motion.span>
        </AnimatePresence>
        <span className="text-xs font-semibold text-text-muted ml-2 tracking-wide uppercase">SENTIMENT</span>
      </div>

      {/* Stock Price Info */}
      <div className="flex items-end justify-between border-t border-white/[0.05] pt-3 z-10">
        <div>
          <span className="text-xs text-text-secondary block font-medium">STOCK PRICE</span>
          <span className="font-mono text-lg font-bold text-white">${price.toFixed(2)}</span>
        </div>
        <div className="text-right">
          <span className="text-xs text-text-secondary block font-medium">24H CHANGE</span>
          <span
            className={`font-mono text-sm font-bold ${
              isPosPrice ? "text-positive" : "text-negative"
            }`}
          >
            {isPosPrice ? "+" : ""}
            {change_pct.toFixed(2)}%
          </span>
        </div>
      </div>
    </motion.div>
  );
}
