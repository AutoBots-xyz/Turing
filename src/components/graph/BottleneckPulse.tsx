"use client";

import React, { useEffect, useRef } from 'react';
import { CausalNode } from '../../types/graph';

export interface BottleneckPulseProps {
  /** The bottleneck node to animate around. */
  node: CausalNode;
  /** Canvas-space coordinates of the node centre, e.g. from D3 simulation. */
  x: number;
  y: number;
  /** Whether the pulse animation is currently active. */
  active?: boolean;
  /** Base radius of the pulse ring. Defaults to 18. */
  radius?: number;
}

/**
 * BottleneckPulse — an SVG overlay ring that pulses red around a bottleneck node.
 * Rendered as an absolutely positioned SVG layer sitting above the D3 canvas.
 * Drop inside a `position: relative` container that matches your SVG viewport.
 */
export const BottleneckPulse: React.FC<BottleneckPulseProps> = ({
  node,
  x,
  y,
  active = true,
  radius = 18,
}) => {
  const circleRef = useRef<SVGCircleElement>(null);

  // Drive the keyframe animation imperatively so it can be started/stopped
  useEffect(() => {
    const el = circleRef.current;
    if (!el) return;

    if (active) {
      el.style.animation = 'bottleneck-pulse 1.4s ease-in-out infinite';
    } else {
      el.style.animation = 'none';
      el.style.opacity = '0';
    }
  }, [active]);

  if (!active) return null;

  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ zIndex: 2 }}
      aria-hidden
    >
      <style>{`
        @keyframes bottleneck-pulse {
          0%   { r: ${radius}px; opacity: 0.8; stroke-width: 3; }
          60%  { r: ${radius + 12}px; opacity: 0.25; stroke-width: 1; }
          100% { r: ${radius + 20}px; opacity: 0; stroke-width: 0.5; }
        }
      `}</style>

      {/* Static inner ring — stays fixed to mark the node */}
      <circle
        cx={x}
        cy={y}
        r={radius - 2}
        fill="none"
        stroke="#C5283D"
        strokeWidth={2}
        opacity={0.6}
      />

      {/* Expanding pulse ring */}
      <circle
        ref={circleRef}
        cx={x}
        cy={y}
        r={radius}
        fill="none"
        stroke="#C5283D"
        strokeWidth={3}
      />

      {/* Node label badge */}
      <text
        x={x}
        y={y - radius - 6}
        textAnchor="middle"
        fontFamily="'Space Grotesk', monospace"
        fontSize={9}
        fontWeight={700}
        fill="#C5283D"
        letterSpacing={1}
      >
        BOTTLENECK: {node.label.toUpperCase()}
      </text>
    </svg>
  );
};
