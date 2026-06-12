import React from 'react';
import { AgentEntry } from '@/types/layer2';

export const ExperimentHistoryTable: React.FC<{ entries: AgentEntry[] }> = ({ entries }) => {
  return (
    <>
      <div className="absolute left-0 top-0 w-[280px] h-full min-h-screen bg-white/90 backdrop-blur-md border-r border-[#E5E5E5] z-10">
        <div className="sticky top-20 left-6 mt-20 ml-6 font-mono text-[10px] text-gray-400 tracking-widest font-bold">
          [ ADVERSARIAL STREAM ]
        </div>
      </div>
      {entries.map(entry => (
        <AgentTimelineItem key={entry.id} {...entry} />
      ))}
    </>
  );
};

const AgentTimelineItem: React.FC<AgentEntry> = ({ type, agentId, y, content }) => {
  const colorMap = {
    explorer: 'text-[#1A936F]',
    exploiter: 'text-[#004E89]',
    contrarian: 'text-[#C5283D]',
  };

  return (
    <div 
      className="absolute left-6 w-[240px] z-20 flex flex-col animate-fade-in"
      style={{ top: y }}
    >
      <div className="flex items-center gap-2 mb-1">
        <div className={`w-2 h-2 rounded-full ${colorMap[type].replace('text-', 'bg-')}`} />
        <span className={`font-mono text-[10px] font-bold ${colorMap[type]}`}>
          {agentId} [{type.toUpperCase()}]
        </span>
      </div>
      <div className="text-[12px] text-gray-700 leading-snug border-l-2 border-gray-200 pl-3 ml-1 mt-1 font-sans">
        {content}
      </div>
    </div>
  );
};
