"use client";

import React from "react";
import { Activity, Radio } from "lucide-react";

interface TickerInfo {
  symbol: string;
  price: number;
  change_pct: number;
}

interface HeaderProps {
  tickers: Record<string, TickerInfo>;
  isConnected: boolean;
}

export default function Header({ tickers, isConnected }: HeaderProps) {
  const watchlist = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN"];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/[0.08] bg-background/80 backdrop-blur-xl px-6 py-4 flex items-center justify-between">
      {/* Brand Logo */}
      <div className="flex items-center space-x-2">
        <Activity className="h-6 w-6 text-accent animate-pulse" />
        <h1 className="text-xl font-bold tracking-tight text-white">
          Pulse<span className="text-accent">IQ</span>
        </h1>
      </div>

      {/* Marquee Ticker Watchlist */}
      <div className="hidden md:flex flex-1 max-w-2xl mx-8 overflow-hidden relative group">
        <div className="absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-background to-transparent z-10" />
        <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-background to-transparent z-10" />
        
        <div className="animate-marquee flex items-center space-x-8">
          {/* Duplicate list to enable continuous looping */}
          {[...watchlist, ...watchlist].map((symbol, idx) => {
            const data = tickers[symbol] || { symbol, price: 0.0, change_pct: 0.0 };
            const isPos = data.change_pct >= 0;
            return (
              <div
                key={`${symbol}-${idx}`}
                className="flex items-center space-x-2 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.05] hover:border-white/[0.15] transition-all cursor-pointer"
              >
                <span className="font-mono font-bold text-sm text-text-primary">{symbol}</span>
                <span className="font-mono text-sm font-semibold text-white">
                  ${data.price.toFixed(2)}
                </span>
                <span
                  className={`font-mono text-xs font-bold ${
                    isPos ? "text-positive" : "text-negative"
                  }`}
                >
                  {isPos ? "+" : ""}
                  {data.change_pct.toFixed(2)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Connection Heartbeat Indicator */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-white/[0.02] border border-white/[0.08]">
          <Radio className={`h-4 w-4 ${isConnected ? "text-positive animate-pulse" : "text-negative"}`} />
          <span className="text-xs font-semibold text-text-secondary hidden sm:inline">
            {isConnected ? "LIVE FEED" : "OFFLINE"}
          </span>
        </div>
        <div className="relative flex h-3 w-3">
          {isConnected && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-positive opacity-75"></span>
          )}
          <span
            className={`relative inline-flex rounded-full h-3 w-3 ${
              isConnected ? "bg-positive" : "bg-negative"
            }`}
          ></span>
        </div>
      </div>
    </header>
  );
}
