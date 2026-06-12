import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useRunState } from '@/hooks/useRunState';
import { useGraphAnimation } from '@/hooks/useGraphAnimation';
import { useSearchStream } from '@/hooks/useSearchStream';
import { PipelineStep } from './D3GraphEngine';

// D3GraphEngine touches SVG/DOM APIs — must be client-only
const D3GraphEngine = dynamic(
  () => import('./D3GraphEngine').then(mod => mod.D3GraphEngine),
  { ssr: false }
);

export const GraphPane: React.FC = () => {
  // In a real app, runId would be dynamic (e.g., from URL or Context)
  // For the active production pipeline, we use a single active run namespace
  const runId = 'nexus-active-run'; 
  const API_BASE = 'http://127.0.0.1:8000';
  
  const { runState } = useRunState(runId);
  const { graph } = useGraphAnimation(runId);
  const { state: layer3State } = useSearchStream(runId);

  const topBridge = layer3State?.topBridges?.[0] || null;

  const [step, setStep] = useState<PipelineStep>('idle');
  const [insightVisible, setInsightVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Map the backend RunState strictly to the D3 Animation Sequence
  useEffect(() => {
    if (!runState) return;

    if (runState.currentLayer >= 3) {
      setStep('crossdomain');
      setInsightVisible(true);
    } else if (runState.currentLayer === 2) {
      setStep('bottleneck');
      setInsightVisible(false);
    } else if (runState.layer1Status === 'completed') {
      setStep('simulated');
      setInsightVisible(false);
    } else {
      setStep('idle');
      setInsightVisible(false);
    }
  }, [runState]);

  // Robust network calls for orchestrating the AI pipeline
  const handleRunDiscovery = async () => {
    try {
      setError(null);
      const res = await fetch(`${API_BASE}/runs/${runId}/layer1`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!res.ok) throw new Error(`Layer 1 API failed: ${res.statusText}`);
    } catch (err: any) {
      setError(err.message || "Network error triggering Layer 1 Causal Discovery");
    }
  };

  const handleIdentifyBottleneck = async () => {
    try {
      setError(null);
      const res = await fetch(`${API_BASE}/runs/${runId}/layer2`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!res.ok) throw new Error(`Layer 2 API failed: ${res.statusText}`);
    } catch (err: any) {
      setError(err.message || "Network error triggering Layer 2 Bottleneck Resolution");
    }
  };

  const handleSearchCrossDomain = async () => {
    try {
      setError(null);
      const res = await fetch(`${API_BASE}/runs/${runId}/layer3`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!res.ok) throw new Error(`Layer 3 API failed: ${res.statusText}`);
    } catch (err: any) {
      setError(err.message || "Network error triggering Layer 3 Isomorphism Search");
    }
  };

  return (
    // position:relative + overflow:hidden so absolute children stay inside
    <div className="relative w-full h-full bg-[#F5F5F5] tab-pane-bg overflow-hidden flex-1">
      {error && (
        <div className="absolute top-5 left-1/2 -translate-x-1/2 z-50 bg-red-500 text-white px-4 py-2 text-sm font-mono font-bold shadow-[4px_4px_0px_rgba(0,0,0,0.2)] border-2 border-black">
          SYSTEM ERROR: {error}
        </div>
      )}
      
      <D3GraphEngine 
        graph={graph}
        bridge={topBridge}
        step={step}
        insightVisible={insightVisible}
        onRunDiscovery={handleRunDiscovery}
        onIdentifyBottleneck={handleIdentifyBottleneck}
        onSearchCrossDomain={handleSearchCrossDomain}
      />
    </div>
  );
};
