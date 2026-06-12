"use client";

import React from 'react';
import { useRunState } from '@/hooks/useRunState';

export const LayerProgress: React.FC = () => {
  const { runState } = useRunState('nexus-active-run');
  // Default to 1 if no state is present
  const currentLayer = runState?.currentLayer || 1;

  const layers = [
    { id: 1, label: 'L1 CAUSAL DISCOVERY' },
    { id: 2, label: 'L2 ADVERSARIAL SWARM' },
    { id: 3, label: 'L3 CROSS-DOMAIN SEARCH' },
    { id: 4, label: 'L4 CONTEXT PACKAGING' },
  ];

  return (
    <div className="flex items-center gap-4 font-mono text-[10px] font-bold text-gray-400 transition-all duration-500">
      {layers.map((layer, index) => {
        const isActive = layer.id === currentLayer;
        const isPast = layer.id < currentLayer;

        return (
          <React.Fragment key={layer.id}>
            <div className={`flex items-center gap-2 transition-colors duration-500 ${isActive ? 'text-black scale-105' : isPast ? 'text-gray-600' : 'text-gray-400'}`}>
              <div 
                className={`w-2 h-2 rounded-full transition-colors duration-500 ${
                  isActive ? 'bg-orange-500 animate-pulse shadow-[0_0_8px_rgba(249,115,22,0.8)]' 
                  : isPast ? 'bg-black' 
                  : 'bg-gray-300'
                }`}
              />
              <span>{layer.label}</span>
            </div>
            
            {index < layers.length - 1 && (
              <div className={`w-8 border-t-2 transition-all duration-500 ${isPast ? 'border-solid border-black' : 'border-dashed border-gray-300'}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
