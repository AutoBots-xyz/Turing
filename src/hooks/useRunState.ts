import { useState, useEffect } from 'react';
import { RunState } from '../types/run';

export function useRunState(runId: string) {
  const [runState, setRunState] = useState<RunState | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!runId) return;

    let isMounted = true;
    let intervalId: ReturnType<typeof setInterval>;

    const fetchRunState = async () => {
      try {
        const response = await fetch(`http://127.0.0.1:8000/runs/${runId}/state`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: RunState = await response.json();
        
        if (isMounted) {
          setRunState(data);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Unknown error fetching global RunState'));
        }
      }
    };

    // Immediate initial fetch to bootstrap the UI
    fetchRunState();

    // Master polling loop every 1.5 seconds to sync the overarching Next.js shell
    // This orchestrates the auto-advancement of TopNav and LayerProgress.
    intervalId = setInterval(fetchRunState, 1500);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [runId]);

  return { runState, error };
}
