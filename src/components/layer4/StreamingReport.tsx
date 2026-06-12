"use client";

import React from 'react';
import { useReportStream } from '@/hooks/useReportStream';
import { MechanismSection } from './MechanismSection';
import { BridgesSection } from './BridgesSection';
import { ExperimentSection } from './ExperimentSection';
import { WarningsSection } from './WarningsSection';

export const StreamingReport: React.FC = () => {
  const runId = 'turing-active-run';
  const { report, isLoading } = useReportStream(runId);

  // If report is null, we are totally waiting for the stream to begin
  const isGlobalStreaming = report ? !report.isComplete : true;

  // Determine which section is currently "active" in the stream based on population
  const hasMech = report?.mechanismExplanation && report.mechanismExplanation.length > 0;
  const hasBridge = report?.bridgeSummary && report.bridgeSummary.length > 0;
  const hasExp = report?.experimentResults && report.experimentResults.length > 0;

  const isMechStreaming = isGlobalStreaming && !hasBridge;
  const isBridgeStreaming = isGlobalStreaming && hasMech && !hasExp;
  const isExpStreaming = isGlobalStreaming && hasBridge;

  return (
    <div className="w-full flex-1 flex flex-col items-center">
      <div className="w-full flex flex-col gap-2">
        <MechanismSection 
          content={report?.mechanismExplanation || ''} 
          isStreaming={isMechStreaming} 
        />
        
        <BridgesSection 
          content={report?.bridgeSummary || ''} 
          isStreaming={isBridgeStreaming} 
        />

        <ExperimentSection 
          content={report?.experimentResults || ''} 
          isStreaming={isExpStreaming} 
        />

        <WarningsSection warnings={report?.warnings} />
      </div>
    </div>
  );
};
