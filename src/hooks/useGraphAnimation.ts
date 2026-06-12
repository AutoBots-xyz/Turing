import { useEffect, useState } from 'react';
import { CausalGraph } from '../types/graph';

export function useGraphAnimation(runId: string) {
  const [graph, setGraph] = useState<CausalGraph | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!runId) return;

    let isMounted = true;
    let intervalId: ReturnType<typeof setInterval>;

    const fetchGraph = async () => {
      try {
        const response = await fetch(`http://127.0.0.1:8000/runs/${runId}/layer1/graph`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: CausalGraph = await response.json();
        
        if (isMounted) {
          setGraph(data);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Unknown error fetching Layer 1 Causal Graph'));
        }
      }
    };

    // Initial fetch to seed the D3 engine immediately
    fetchGraph();

    // Poll every 2 seconds to capture any real-time topological updates
    // as the causal discovery engine fits structural equations
    intervalId = setInterval(fetchGraph, 2000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [runId]);

  return { graph, error };
}
