import { useState, useEffect, useRef } from 'react';
import { Layer4Report } from '../types/report';
import { apiUrl } from '@/lib/api';

const MAX_RETRIES = 5;
const BASE_RETRY_DELAY_MS = 1000; // doubles each attempt (exponential backoff)

export function useReportStream(runId: string) {
  const [report, setReport] = useState<Layer4Report | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const retryCount = useRef(0);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!runId) return;

    let es: EventSource;
    let cancelled = false;

    const connect = () => {
      // Establish Server-Sent Events (SSE) connection for live LLM streaming
      es = new EventSource(apiUrl(`/api/runs/${runId}/layer4/report/stream`));

      es.onopen = () => {
        if (!cancelled) {
          setIsConnected(true);
          setError(null);
          retryCount.current = 0; // reset backoff on successful connection
        }
      };

      es.onmessage = (event) => {
        try {
          const data: Layer4Report = JSON.parse(event.data);
          if (!cancelled) setReport(data);
          setError(null);

          // If the backend generative AI signals completion, gracefully close the pipeline
          if (data.isComplete) {
            es.close();
            if (!cancelled) setIsConnected(false);
          }
        } catch (err) {
          setError(err instanceof Error ? err : new Error('Failed to parse Layer 4 report stream chunk'));
        }
      };

      es.onerror = () => {
        es.close();
        if (cancelled) return;

        setIsConnected(false);

        if (retryCount.current >= MAX_RETRIES) {
          setError(new Error('Connection to Layer 4 reporting stream lost after max retries'));
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

  return { report, error, isConnected, isLoading: !report && isConnected };
}
