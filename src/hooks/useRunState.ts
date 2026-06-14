import { useState, useEffect } from 'react';
import { RunState } from '../types/run';
import { apiUrl } from '@/lib/api';

/** How often (ms) to poll the backend for the global run state. */
const POLL_INTERVAL_MS = 1500;

export function useRunState(runId: string) {
  const [runState, setRunState] = useState<RunState | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!runId) return;

    let isMounted = true;
    let intervalId: ReturnType<typeof setInterval>;

    const fetchRunState = async () => {
      try {
        const response = await fetch(apiUrl(`/api/runs/${runId}/state`));
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: RunState = await response.json();
        
        if (isMounted) {
          setRunState(data);
          setError(null);
          setIsLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Unknown error fetching global RunState'));
          setIsLoading(false);
        }
      }
    };

    // Immediate initial fetch to bootstrap the UI
    fetchRunState();

    // Master polling loop every 1.5 seconds to sync the overarching Next.js shell
    // This orchestrates the auto-advancement of TopNav and LayerProgress.
    intervalId = setInterval(fetchRunState, POLL_INTERVAL_MS);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [runId]);

  return { runState, error, isLoading };
}
