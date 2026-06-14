import { useEffect, useState } from 'react';
import { CausalGraph } from '../types/graph';
import { apiUrl } from '@/lib/api';

/** How often (ms) to poll for live causal graph topology updates. */
const POLL_INTERVAL_MS = 2000;

export function useGraphAnimation(runId: string) {
  const [graph, setGraph] = useState<CausalGraph | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!runId) return;

    let isMounted = true;
    let intervalId: ReturnType<typeof setInterval>;

    const fetchGraph = async () => {
      try {
        const response = await fetch(apiUrl(`/api/runs/${runId}/layer1/graph`));
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: CausalGraph = await response.json();
        
        if (isMounted) {
          setGraph(prev => {
            if (!prev) return data;
            // Only update if the graph actually changed, to prevent D3 from resetting the physics layout
            if (JSON.stringify(prev) === JSON.stringify(data)) {
              return prev;
            }
            return data;
          });
          setError(null);
          setIsLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Unknown error fetching Layer 1 Causal Graph'));
          setIsLoading(false);
        }
      }
    };

    // Initial fetch to seed the D3 engine immediately
    fetchGraph();

    // Poll every 2 seconds to capture any real-time topological updates
    // as the causal discovery engine fits structural equations
    intervalId = setInterval(fetchGraph, POLL_INTERVAL_MS);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [runId]);

  return { graph, error, isLoading };
}
