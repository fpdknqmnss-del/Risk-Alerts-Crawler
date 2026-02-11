"use client";

import { useEffect, useRef } from "react";
import { wsClient } from "@/lib/websocket";

type RealtimeCallback = () => void | Promise<void>;

export function useAlertsRealtime(onAlertsUpdated: RealtimeCallback) {
  const callbackRef = useRef(onAlertsUpdated);

  useEffect(() => {
    callbackRef.current = onAlertsUpdated;
  }, [onAlertsUpdated]);

  useEffect(() => {
    wsClient.connect();
    const unsubscribe = wsClient.on("alerts_updated", () => {
      void callbackRef.current();
    });

    return () => {
      unsubscribe();
      wsClient.disconnect();
    };
  }, []);
}
