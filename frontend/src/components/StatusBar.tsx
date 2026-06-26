"use client";

import React, { useEffect, useState } from "react";
import { Server, ShieldCheck, Database, RefreshCw } from "lucide-react";

interface StatusBarProps {
  lastUpdate: Date | null;
  processedCount: number;
  isPipelineRunning: boolean;
}

export default function StatusBar({
  lastUpdate,
  processedCount,
  isPipelineRunning,
}: StatusBarProps) {
  const [timeAgo, setTimeAgo] = useState<string>("Never");

  useEffect(() => {
    const updateTimeAgo = () => {
      if (!lastUpdate) {
        setTimeAgo("Never");
        return;
      }
      const diffMs = new Date().getTime() - lastUpdate.getTime();
      const diffSecs = Math.floor(diffMs / 1000);
      
      if (diffSecs < 5) {
        setTimeAgo("Just now");
      } else if (diffSecs < 60) {
        setTimeAgo(`${diffSecs}s ago`);
      } else {
        const mins = Math.floor(diffSecs / 60);
        setTimeAgo(`${mins}m ago`);
      }
    };

    updateTimeAgo();
    const interval = setInterval(updateTimeAgo, 1000);
    return () => clearInterval(interval);
  }, [lastUpdate]);

  return (
    <footer className="fixed bottom-0 left-0 right-0 z-40 bg-surface/85 backdrop-blur-md border-t border-white/[0.08] px-6 py-2 flex items-center justify-between text-xs text-text-secondary select-none font-mono">
      {/* System Status Indicators */}
      <div className="flex items-center space-x-5">
        <div className="flex items-center space-x-1.5">
          <Server className="h-3.5 w-3.5 text-text-muted" />
          <span>System Gateway:</span>
          <span className="text-positive font-bold flex items-center">
            ONLINE
            <span className="relative flex h-1.5 w-1.5 ml-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-positive opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-positive"></span>
            </span>
          </span>
        </div>

        <div className="hidden sm:flex items-center space-x-1.5">
          <Database className="h-3.5 w-3.5 text-text-muted" />
          <span>Postgres/Redis/Mongo:</span>
          <span className="text-white font-semibold">LINKED</span>
        </div>

        <div className="hidden md:flex items-center space-x-1.5">
          <ShieldCheck className="h-3.5 w-3.5 text-text-muted" />
          <span>Security Sandbox:</span>
          <span className="text-accent font-semibold">SECURE</span>
        </div>
      </div>

      {/* Real-time counters */}
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-1.5">
          <span>Processed Feed:</span>
          <span className="text-white font-bold">{processedCount} items</span>
        </div>

        <div className="flex items-center space-x-1.5">
          <RefreshCw className={`h-3 w-3 text-text-muted ${isPipelineRunning ? "animate-spin" : ""}`} />
          <span>Last Sync:</span>
          <span className="text-white font-semibold">{timeAgo}</span>
        </div>
      </div>
    </footer>
  );
}
