import { useState, useEffect, useRef } from 'react';
import { Layer3State } from '../types/layer3';
import { apiUrl } from '@/lib/api';

const MAX_RETRIES = 5;
const BASE_RETRY_DELAY_MS = 1000; // doubles each attempt (exponential backoff)

export function useSearchStream(runId: string) {
  const [state, setState] = useState<Layer3State | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const retryCount = useRef(0);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!runId) return;

    let es: EventSource;
    let cancelled = false;

    const connect = () => {
      // Establish Server-Sent Events (SSE) connection for live cross-domain search updates
      es = new EventSource(apiUrl(`/api/runs/${runId}/layer3/search/stream`));

      es.onopen = () => {
        if (!cancelled) {
          setIsConnected(true);
          setError(null);
          retryCount.current = 0; // reset backoff on successful connection
        }
      };

      es.onmessage = (event) => {
        try {
          const data: Layer3State = JSON.parse(event.data);
          if (!cancelled) setState(data);
          setError(null);

          // If the backend radar natively locks onto a structural isomorphism,
          // close the search pipeline gracefully.
          if (data.isLocked) {
            es.close();
            if (!cancelled) setIsConnected(false);
          }
        } catch (err) {
          console.error('Failed to parse Layer 3 search stream chunk:', err);
        }
      };

      es.onerror = () => {
        es.close();
        if (cancelled) return;

        setIsConnected(false);

        if (retryCount.current >= MAX_RETRIES) {
          setError(new Error('Connection to Layer 3 search stream lost after max retries'));
          return;
        }

        // Exponential backoff reconnect
        const delay = BASE_RETRY_DELAY_MS * Math.pow(2, retryCount.current);
        retryCount.current += 1;
        retryTimer.current = setTimeout(() => {
          if (!cancelled) connect();
        }, delay);
      };
    };

    connect();

    return () => {
      cancelled = true;
      es?.close();
      if (retryTimer.current) clearTimeout(retryTimer.current);
    };
  }, [runId]);

  return { state, error, isConnected };
}
