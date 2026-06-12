import { useState, useEffect } from 'react';
import { Layer3State } from '../types/layer3';

export function useSearchStream(runId: string) {
  const [state, setState] = useState<Layer3State | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!runId) return;

    // Establish Server-Sent Events (SSE) connection for live cross-domain search updates
    const eventSource = new EventSource(`http://127.0.0.1:8000/runs/${runId}/layer3/search/stream`);

    eventSource.onmessage = (event) => {
      try {
        const data: Layer3State = JSON.parse(event.data);
        setState(data);
        setError(null);

        // If the backend radar natively locks onto a structural isomorphism,
        // close the search pipeline gracefully.
        if (data.isLocked) {
          eventSource.close();
        }
      } catch (err) {
        console.error('Failed to parse Layer 3 search stream chunk:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('Layer 3 EventSource error:', err);
      setError(new Error('Connection to Layer 3 search stream lost'));
      eventSource.close();
    };

    // Cleanup: strictly close connection to prevent memory leaks if user navigates away
    return () => {
      eventSource.close();
    };
  }, [runId]);

  return { state, error };
}
