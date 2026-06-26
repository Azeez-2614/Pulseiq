"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ExternalLink, MessageSquare, Newspaper, AlertCircle } from "lucide-react";

interface Article {
  title: string;
  source: string;
  published_at: string;
  symbol: string;
  sentiment: {
    compound: number;
    label: string;
  };
  url?: string;
}

interface ArticleFeedProps {
  articles: Article[];
}

export default function ArticleFeed({ articles }: ArticleFeedProps) {
  // Format timestamp (e.g. "2 hours ago" or absolute time)
  const formatTime = (timeStr: string) => {
    try {
      if (!timeStr) return "Just now";
      const date = new Date(timeStr);
      if (isNaN(date.getTime())) return timeStr;
      
      const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
      if (seconds < 60) return "Just now";
      const minutes = Math.floor(seconds / 60);
      if (minutes < 60) return `${minutes}m ago`;
      const hours = Math.floor(minutes / 60);
      if (hours < 24) return `${hours}h ago`;
      return date.toLocaleDateString([], { month: "short", day: "numeric" });
    } catch {
      return timeStr;
    }
  };

  const getSentimentPill = (label: string) => {
    const cleanLabel = label.toLowerCase();
    if (cleanLabel === "positive") {
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-positive/10 text-positive border border-positive/20">
          POSITIVE
        </span>
      );
    } else if (cleanLabel === "negative") {
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-negative/10 text-negative border border-negative/20">
          NEGATIVE
        </span>
      );
    } else {
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-neutral/10 text-neutral border border-neutral/20">
          NEUTRAL
        </span>
      );
    }
  };

  return (
    <div className="glass rounded-2xl p-6 flex flex-col h-[400px]">
      {/* Title Header */}
      <div className="flex items-center space-x-2.5 mb-4 shrink-0">
        <Newspaper className="h-5 w-5 text-accent" />
        <div>
          <h3 className="font-semibold text-white tracking-wide">Live Sentiment Feed</h3>
          <p className="text-xs text-text-secondary">Scored articles and social posts sliding in real-time</p>
        </div>
      </div>

      {/* Feed Container */}
      <div className="flex-1 overflow-y-auto pr-1 space-y-3 no-scrollbar">
        {articles.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-2">
            <AlertCircle className="h-8 w-8 text-text-muted" />
            <span className="text-sm font-semibold text-text-secondary">Awaiting stream ingestion...</span>
            <span className="text-xs text-text-muted">Trigger the pipeline to start gathering updates</span>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {articles.map((article, idx) => {
              const url = article.url || `https://finance.yahoo.com/quote/${article.symbol}`;
              const isReddit = article.source.toLowerCase().includes("reddit") || article.source.toLowerCase().includes("r/");
              
              return (
                <motion.a
                  key={`${article.title}-${idx}`}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  initial={{ opacity: 0, y: -20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ type: "spring", stiffness: 300, damping: 25 }}
                  className="flex items-start justify-between p-4 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.06] hover:border-white/[0.12] hover:shadow-lg transition-all group block"
                >
                  <div className="flex-1 pr-4">
                    {/* Source and Time Meta */}
                    <div className="flex items-center space-x-2 mb-1.5 flex-wrap gap-y-1">
                      {isReddit ? (
                        <span className="flex items-center text-[10px] font-bold text-orange-400 font-mono tracking-wider">
                          <MessageSquare className="h-3 w-3 mr-1" />
                          {article.source.toUpperCase()}
                        </span>
                      ) : (
                        <span className="flex items-center text-[10px] font-bold text-indigo-400 font-mono tracking-wider">
                          <Newspaper className="h-3 w-3 mr-1" />
                          {article.source.toUpperCase()}
                        </span>
                      )}
                      
                      <span className="text-[10px] font-mono text-text-muted">•</span>
                      <span className="text-[10px] font-mono text-text-muted">{formatTime(article.published_at)}</span>
                      
                      <span className="text-[10px] font-mono text-text-muted">•</span>
                      <span className="px-1.5 py-0.5 rounded bg-white/[0.04] text-[9px] font-bold text-text-secondary font-mono">
                        {article.symbol}
                      </span>
                    </div>

                    {/* Headline */}
                    <p className="text-sm font-medium text-text-primary group-hover:text-white line-clamp-2 transition-colors">
                      {article.title}
                    </p>
                  </div>

                  {/* Sentiment Pill */}
                  <div className="flex flex-col items-end space-y-1.5 shrink-0">
                    {getSentimentPill(article.sentiment.label)}
                    <span className="font-mono text-[10px] text-text-muted font-semibold">
                      {article.sentiment.compound >= 0 ? "+" : ""}
                      {article.sentiment.compound.toFixed(2)}
                    </span>
                    <ExternalLink className="h-3.5 w-3.5 text-text-muted group-hover:text-accent opacity-0 group-hover:opacity-100 transition-all" />
                  </div>
                </motion.a>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
