import { useEffect, useRef, useState } from "react";

import type { WebsocketSnapshot } from "../types";

export function useRealtimeStream(onSnapshot: (payload: WebsocketSnapshot) => void) {
  const [liveConnected, setLiveConnected] = useState(false);
  const [liveLatency, setLiveLatency] = useState("NODE-01 | --");
  const onSnapshotRef = useRef(onSnapshot);

  useEffect(() => {
    onSnapshotRef.current = onSnapshot;
  }, [onSnapshot]);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}/v1/ws/stream`);
    const startedAt = Date.now();

    socket.onopen = () => {
      setLiveConnected(true);
      setLiveLatency(`NODE-01 | ${Date.now() - startedAt}ms`);
    };
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as WebsocketSnapshot;
      if (payload.type === "snapshot") onSnapshotRef.current(payload);
    };
    socket.onerror = () => setLiveConnected(false);
    socket.onclose = () => setLiveConnected(false);

    const timer = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) socket.send("ping");
    }, 5000);

    return () => {
      window.clearInterval(timer);
      socket.close();
    };
  }, []);

  return { liveConnected, liveLatency };
}
