import { useEffect, useRef } from "react";
import { useDashboardStore } from "../store/useDashboardStore";

const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 10000];

export function useWebSocket(url) {
  const wsRef = useRef(null);
  const attemptRef = useRef(0);
  const setConnection = useDashboardStore((s) => s.setConnection);
  const pushSnapshot = useDashboardStore((s) => s.pushSnapshot);
  const pushExplanation = useDashboardStore((s) => s.pushExplanation);
  const pushDebate = useDashboardStore((s) => s.pushDebate);
  const pushRemediation = useDashboardStore((s) => s.pushRemediation);

  useEffect(() => {
    let cancelled = false;
    let timer;
    const connect = () => {
      if (cancelled) return;
      const ws = new WebSocket(url);
      wsRef.current = ws;
      setConnection("connecting");
      ws.onopen = () => {
        attemptRef.current = 0;
        setConnection("connected");
      };
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "explanation") pushExplanation(msg);
          else if (msg.type === "debate") pushDebate(msg);
          else if (msg.type === "remediation") pushRemediation(msg);
          else pushSnapshot(msg);
        } catch {
          /* drop malformed */
        }
      };
      ws.onclose = () => {
        setConnection("disconnected");
        if (cancelled) return;
        const delay =
          RECONNECT_DELAYS_MS[Math.min(attemptRef.current, RECONNECT_DELAYS_MS.length - 1)];
        attemptRef.current += 1;
        timer = setTimeout(connect, delay);
      };
      ws.onerror = () => {
        /* onclose follows */
      };
    };
    connect();
    return () => {
      cancelled = true;
      clearTimeout(timer);
      wsRef.current?.close();
    };
  }, [url, setConnection, pushSnapshot]);
}
