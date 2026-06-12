import { useState, useEffect } from 'react';
import { Layer4Report } from '../types/report';

export function useReportStream(runId: string) {
  const [report, setReport] = useState<Layer4Report | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!runId) return;

    // Establish Server-Sent Events (SSE) connection for live LLM streaming
    const eventSource = new EventSource(`http://127.0.0.1:8000/runs/${runId}/layer4/report/stream`);

    eventSource.onmessage = (event) => {
      try {
        const data: Layer4Report = JSON.parse(event.data);
        setReport(data);
        setError(null);

        // If the backend generative AI signals completion, gracefully close the pipeline
        if (data.isComplete) {
          eventSource.close();
        }
      } catch (err) {
        console.error('Failed to parse Layer 4 report stream chunk:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('Layer 4 EventSource error:', err);
      setError(new Error('Connection to Layer 4 reporting stream lost'));
      eventSource.close();
    };

    // Cleanup: strictly close connection to prevent memory leaks if user navigates away
    return () => {
      eventSource.close();
    };
  }, [runId]);

  return { report, error };
}
