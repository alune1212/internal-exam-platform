import { useEffect, useMemo, useState } from "react";

import type { Attempt } from "@/types/attempt";

export function useAttemptCountdown(attempt: Attempt | undefined) {
  const [now, setNow] = useState(() => Date.now());
  const [serverClock, setServerClock] = useState<{
    serverNow: number;
    clientNow: number;
  } | null>(null);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!attempt) {
      setServerClock(null);
      return;
    }
    const serverNow = new Date(attempt.server_now).getTime();
    setServerClock({
      serverNow: Number.isFinite(serverNow) ? serverNow : Date.now(),
      clientNow: Date.now(),
    });
  }, [attempt]);

  return useMemo(() => {
    if (!attempt) {
      return Number.POSITIVE_INFINITY;
    }
    const endsAt = new Date(attempt.ends_at).getTime();
    const serverOffset = serverClock ? serverClock.clientNow - serverClock.serverNow : 0;
    return Math.max(0, Math.floor((endsAt - (now - serverOffset)) / 1000));
  }, [attempt, now, serverClock]);
}
