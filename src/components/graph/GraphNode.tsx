import React from 'react';
import { CausalNode, NodeType } from '../../types/graph';

const COLOR_MAP: Record<NodeType, string> = {
  controllable: '#FF6B35',
  mediator:     '#004E89',
  bottleneck:   '#C5283D',
  outcome:      '#1A936F',
  chemistry:    '#7B2D8E',
};

export interface GraphNodeProps {
  node: CausalNode;
  /** Pixel radius of the node circle. Defaults to 10; bottleneck defaults to 13. */
  radius?: number;
  /** Whether to show the node's label beside the circle. */
  showLabel?: boolean;
  /** Whether this node is currently selected / highlighted. */
  selected?: boolean;
  onClick?: (node: CausalNode) => void;
}

export const GraphNode: React.FC<GraphNodeProps> = ({
  node,
  radius,
  showLabel = true,
  selected = false,
  onClick,
}) => {
  const r = radius ?? (node.type === 'bottleneck' ? 13 : 10);
  const color = COLOR_MAP[node.type] ?? '#999';

  return (
    <div
      className="flex items-center gap-2 cursor-pointer select-none"
      onClick={() => onClick?.(node)}
    >
      {/* Circle indicator */}
      <svg width={r * 2 + 4} height={r * 2 + 4} className="shrink-0">
        <circle
          cx={r + 2}
          cy={r + 2}
          r={r}
          fill={color}
          stroke={selected ? '#E91E63' : '#fff'}
          strokeWidth={selected ? 3 : 2}
          style={{ transition: 'stroke 0.2s ease, stroke-width 0.2s ease' }}
        />
      </svg>

      {showLabel && (
        <span
          className="font-sans text-[11px] font-semibold text-black truncate"
          style={{ maxWidth: 160 }}
        >
          {node.label}
        </span>
      )}
    </div>
  );
};
