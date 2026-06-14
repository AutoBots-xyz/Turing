import React from 'react';
import { CausalEdge } from '../../types/graph';

export interface GraphEdgeProps {
  edge: CausalEdge;
  /** Source node label, shown on the left side. */
  sourceLabel: string;
  /** Target node label, shown on the right side. */
  targetLabel: string;
  /** Whether this edge is currently highlighted/selected. */
  active?: boolean;
  onClick?: (edge: CausalEdge) => void;
}

export const GraphEdge: React.FC<GraphEdgeProps> = ({
  edge,
  sourceLabel,
  targetLabel,
  active = false,
  onClick,
}) => {
  const isCross = !!edge.crossDomain;
  const color = active ? '#3498db' : isCross ? '#7B2D8E' : '#C0C0C0';

  return (
    <div
      className="flex items-center gap-2 cursor-pointer group select-none py-1"
      onClick={() => onClick?.(edge)}
    >
      {/* Source */}
      <span
        className="font-mono text-[10px] font-bold text-black bg-gray-100 border border-gray-300 px-1.5 py-0.5 shrink-0 truncate"
        style={{ maxWidth: 100 }}
      >
        {sourceLabel}
      </span>

      {/* Arrow line */}
      <div className="flex-1 flex items-center gap-0.5 min-w-[40px]">
        <div
          className="flex-1 h-px"
          style={{
            background: isCross
              ? `repeating-linear-gradient(90deg, ${color} 0, ${color} 4px, transparent 4px, transparent 8px)`
              : color,
            transition: 'background 0.2s ease',
          }}
        />
        {/* Arrowhead */}
        <svg width={8} height={10} viewBox="0 0 8 10" className="shrink-0">
          <path d="M0,0 L8,5 L0,10 Z" fill={color} style={{ transition: 'fill 0.2s ease' }} />
        </svg>
      </div>

      {/* Target */}
      <span
        className="font-mono text-[10px] font-bold text-black bg-gray-100 border border-gray-300 px-1.5 py-0.5 shrink-0 truncate"
        style={{ maxWidth: 100 }}
      >
        {targetLabel}
      </span>

      {/* Weight badge */}
      {edge.label && (
        <span
          className="font-mono text-[9px] font-bold px-1 py-0.5 border shrink-0"
          style={{ color, borderColor: color, opacity: 0.8 }}
        >
          {edge.label}
        </span>
      )}

      {isCross && (
        <span className="font-mono text-[9px] font-bold text-[#7B2D8E] shrink-0">
          ✦
        </span>
      )}
    </div>
  );
};
