import { useState, useEffect } from 'react';
import { Layer2State } from '../types/layer2';
import { apiUrl } from '@/lib/api';

/** How often (ms) to poll for live Layer 2 agent swarm debate updates. */
const POLL_INTERVAL_MS = 1000;

export function useAgentLoop(runId: string) {
  const [state, setState] = useState<Layer2State | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!runId) return;

    let isMounted = true;
    let intervalId: ReturnType<typeof setInterval>;

    const fetchAgentState = async () => {
      try {
        const response = await fetch(apiUrl(`/api/runs/${runId}/layer2/agents`));
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: Layer2State = await response.json();
        
        if (isMounted) {
          setState(data);
          setError(null); // Clear any previous errors on success
          setIsLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Unknown error fetching Layer 2 agent state'));
          setIsLoading(false);
        }
      }
    };

    // Trigger an immediate initial fetch to populate the UI
    fetchAgentState();

    // Establish a 1-second interval loop to poll the FastAPI backend
    // for live updates to the Adversarial Swarm debate tree
    intervalId = setInterval(fetchAgentState, POLL_INTERVAL_MS);

    // Cleanup interval and prevent state updates on unmounted components
    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [runId]);

  return { state, error, isLoading };
}
