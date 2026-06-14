import { useState, useEffect } from "react";
import { fetchHealth, fetchEngineInfo, HealthStatus } from "@/lib/api";

interface SystemStatus {
  health: HealthStatus;
  version: string | null;
}

const POLL_INTERVAL_MS = 30_000; // re-check every 30 seconds

/**
 * useSystemStatus
 *
 * Checks backend liveness on mount and then every 30 seconds.
 * Also fetches the authoritative version string from GET /.
 *
 * Returns:
 *   health  — "checking" | "online" | "offline"
 *   version — e.g. "1.0.0", or null while loading / unreachable
 */
export function useSystemStatus(): SystemStatus {
  const [health, setHealth] = useState<HealthStatus>("checking");
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      const alive = await fetchHealth();
      if (!cancelled) setHealth(alive ? "online" : "offline");
    };

    // Fetch version once (doesn't need to poll — version only changes on deploy)
    const getVersion = async () => {
      const info = await fetchEngineInfo();
      if (!cancelled && info) setVersion(info.version);
    };

    check();
    getVersion();

    const intervalId = setInterval(check, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, []);

  return { health, version };
}
