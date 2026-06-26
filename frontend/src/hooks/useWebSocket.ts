import { useState, useEffect, useRef, useCallback } from 'react';

export interface SentimentUpdate {
  symbol: string;
  sentiment_score: number;
  price: number;
  change_pct: number;
  volume: number;
  timestamp: string;
}

export function useWebSocket(url: string) {
  const [data, setData] = useState<SentimentUpdate | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectRef = useRef<() => void>(() => {});

  const connect = useCallback(() => {
    if (typeof window === 'undefined') return;
    
    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      wsRef.current = new WebSocket(url);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket connection established.');
      };

      wsRef.current.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          setData(parsed);
        } catch (e) {
          console.error('WS parse error:', e);
        }
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket connection closed. Reconnecting in 3 seconds...');
        // Auto-reconnect after 3 seconds
        if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = setTimeout(() => connectRef.current(), 3000);
      };

      wsRef.current.onerror = (error) => {
        console.warn('WebSocket connection not available:', error);
        wsRef.current?.close();
      };
    } catch (err) {
      console.warn('WebSocket setup failure:', err);
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = setTimeout(() => connectRef.current(), 3000);
    }
  }, [url]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    connectRef.current();
    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return { data, isConnected };
}
