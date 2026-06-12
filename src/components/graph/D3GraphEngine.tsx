"use client";

import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { GraphLegend } from './GraphLegend';
import { CrossDomainBridge } from './CrossDomainBridge';
import { GraphControls } from './GraphControls';
import { CausalGraph, CausalNode, CausalEdge, NodeType } from '../../types/graph';
import { BridgeResult } from '../../types/layer3';

// ─────────────────── Types ────────────────────────────────────────────────────
// D3 requires mutable coordinate properties for its simulation
interface SimulationNode extends CausalNode, d3.SimulationNodeDatum {
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

interface SimulationLink extends d3.SimulationLinkDatum<SimulationNode> {
  curvature: number;
  crossDomain?: boolean;
  weight: number;
  label: string;
}

export type PipelineStep = 'idle' | 'simulated' | 'bottleneck' | 'crossdomain';

export interface D3GraphEngineProps {
  graph?: CausalGraph | null;
  bridge?: BridgeResult | null;
  step?: PipelineStep;
  insightVisible?: boolean;
  onRunDiscovery?: () => void;
  onIdentifyBottleneck?: () => void;
  onSearchCrossDomain?: () => void;
}

// ─────────────────── Color Map ─────────────────────────────────────────────────
const COLOR_MAP: Record<NodeType, string> = {
  controllable: '#FF6B35',
  mediator:     '#004E89',
  bottleneck:   '#C5283D',
  outcome:      '#1A936F',
  chemistry:    '#7B2D8E',
};

// ─────────────────── Component ────────────────────────────────────────────────
export const D3GraphEngine: React.FC<D3GraphEngineProps> = ({
  graph,
  bridge,
  step = 'idle',
  insightVisible = false,
  onRunDiscovery,
  onIdentifyBottleneck,
  onSearchCrossDomain,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const simRef = useRef<d3.Simulation<SimulationNode, SimulationLink> | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const [tooltip, setTooltip] = useState<{ x: number; y: number; node: SimulationNode } | null>(null);

  // 1. Rebuild the entire graph topology when the 'graph' data prop changes
  const buildGraph = useCallback(() => {
    if (!svgRef.current) return;
    if (!graph || !graph.nodes || !graph.edges) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth || 900;
    const height = svgRef.current.clientHeight || 600;

    // Zoom Container
    const g = svg.append('g').attr('class', 'graph-container');
    
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => g.attr('transform', event.transform));
      
    svg.call(zoom);

    // Arrow Markers Definition
    const defs = svg.append('defs');
    [
      { id: 'arrow-normal',  fill: '#C0C0C0' },
      { id: 'arrow-dashed',  fill: '#7B2D8E' },
      { id: 'arrow-active',  fill: '#3498db' },
      { id: 'arrow-danger',  fill: '#C5283D' }
    ].forEach(({ id, fill }) => {
      defs.append('marker')
        .attr('id', id)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', fill);
    });

    // Deep copy data for D3 mutation to prevent polluting React props
    const nodes: SimulationNode[] = graph.nodes.map(n => ({ ...n }));
    
    // Resolve edge references from string IDs to actual node objects
    const links: SimulationLink[] = graph.edges.map(e => ({
      ...e,
      source: nodes.find(n => n.id === e.source) || e.source,
      target: nodes.find(n => n.id === e.target) || e.target,
    })) as SimulationLink[];

    // Force Simulation Setup
    const simulation = d3.forceSimulation<SimulationNode>(nodes)
      .force('link', d3.forceLink<SimulationNode, SimulationLink>(links).id(d => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide(50));

    simRef.current = simulation;

    // Render Edges
    const linkGroup = g.append('g').attr('class', 'links');
    const linkEl = linkGroup.selectAll<SVGPathElement, SimulationLink>('path.link')
      .data(links)
      .enter()
      .append('path')
      .attr('class', d => `link ${d.crossDomain ? 'cross-domain' : ''}`)
      .attr('data-source', d => (d.source as SimulationNode).type)
      .attr('data-target', d => (d.target as SimulationNode).type)
      .attr('stroke', d => d.crossDomain ? '#7B2D8E' : '#C0C0C0')
      .attr('stroke-width', 1.5)
      .attr('stroke-dasharray', d => d.crossDomain ? '5,5' : null)
      .attr('marker-end', d => `url(#${d.crossDomain ? 'arrow-dashed' : 'arrow-normal'})`)
      .attr('fill', 'none')
      .style('transition', 'stroke-opacity 0.2s ease, stroke 0.2s ease, stroke-width 0.2s ease')
      .on('click', (event, d) => {
        linkEl.attr('stroke', l => (l === d ? '#3498db' : (l.crossDomain ? '#7B2D8E' : '#C0C0C0')))
              .attr('stroke-width', l => (l === d ? 3 : 1.5))
              .attr('marker-end', l => l === d ? 'url(#arrow-active)' : `url(#${l.crossDomain ? 'arrow-dashed' : 'arrow-normal'})`);
      });

    // Render Edge Labels
    const edgeLabelGroup = g.append('g').attr('class', 'edge-labels');
    const edgeLabelBg = edgeLabelGroup.selectAll<SVGRectElement, SimulationLink>('rect')
      .data(links).enter().append('rect')
      .attr('fill', 'rgba(255,255,255,0.95)')
      .attr('rx', 0).attr('ry', 0)
      .attr('cursor', 'pointer');

    const edgeLabelText = edgeLabelGroup.selectAll<SVGTextElement, SimulationLink>('text')
      .data(links).enter().append('text')
      .attr('font-size', 9)
      .attr('fill', '#666')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('cursor', 'pointer')
      .attr('font-family', "'Space Grotesk', sans-serif")
      .attr('font-weight', 600)
      .text(d => d.label);

    // Render Nodes
    const nodeGroup = g.append('g').attr('class', 'nodes');
    const nodeEl = nodeGroup.selectAll<SVGGElement, SimulationNode>('g.node')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', d => `node node-${d.type}`)
      .call(
        d3.drag<SVGGElement, SimulationNode>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x; d.fy = d.y;
          })
          .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null; d.fy = null;
          })
      )
      .on('mouseover', (event, d) => {
        d3.select(event.currentTarget).select('circle')
          .attr('stroke', '#333')
          .attr('stroke-width', 3);
        setTooltip({ x: event.clientX, y: event.clientY, node: d });
      })
      .on('mousemove', (event) => {
        setTooltip(prev => prev ? { ...prev, x: event.clientX, y: event.clientY } : null);
      })
      .on('mouseout', (event, d) => {
        d3.select(event.currentTarget).select('circle')
          .attr('stroke', '#fff')
          .attr('stroke-width', 2.5);
        setTooltip(null);
      })
      .on('click', (event, d) => {
        nodeEl.select('circle')
          .attr('stroke', '#fff')
          .attr('stroke-width', 2.5);
        d3.select(event.currentTarget).select('circle')
          .attr('stroke', '#E91E63')
          .attr('stroke-width', 4);
      });

    nodeEl.append('circle')
      .attr('r', d => d.type === 'bottleneck' ? 13 : 10)
      .attr('fill', d => COLOR_MAP[d.type] || '#999')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2.5)
      .style('cursor', 'pointer')
      .style('transition', 'r 0.2s ease, fill 0.2s ease, stroke-width 0.2s ease, stroke 0.2s ease');

    nodeEl.append('text')
      .attr('dx', 14)
      .attr('dy', 4)
      .attr('font-family', "'Space Grotesk', sans-serif")
      .attr('font-size', 11)
      .attr('fill', '#000000')
      .attr('font-weight', 600)
      .attr('pointer-events', 'none')
      .attr('user-select', 'none')
      .text(d => d.label);

    // Bezier Path Calculator
    function linkPath(d: SimulationLink): string {
      const s = d.source as SimulationNode;
      const t = d.target as SimulationNode;
      const dx = (t.x ?? 0) - (s.x ?? 0);
      const dy = (t.y ?? 0) - (s.y ?? 0);
      const mid = { x: ((s.x ?? 0) + (t.x ?? 0)) / 2, y: ((s.y ?? 0) + (t.y ?? 0)) / 2 };
      const len = Math.sqrt(dx * dx + dy * dy) || 1;
      const curveOffset = len * (d.curvature ?? 0.3);
      const cx = mid.x - (dy / len) * curveOffset;
      const cy = mid.y + (dx / len) * curveOffset;
      return `M${s.x ?? 0},${s.y ?? 0} Q${cx},${cy} ${t.x ?? 0},${t.y ?? 0}`;
    }

    // Tick handler for physical simulation step
    simulation.on('tick', () => {
      linkEl.attr('d', d => linkPath(d));

      edgeLabelBg.each(function(d) {
        const s = d.source as SimulationNode;
        const t = d.target as SimulationNode;
        const mx = ((s.x ?? 0) + (t.x ?? 0)) / 2;
        const my = ((s.y ?? 0) + (t.y ?? 0)) / 2;
        d3.select(this)
          .attr('x', mx - 20).attr('y', my - 8)
          .attr('width', 40).attr('height', 16);
      });
      
      edgeLabelText
        .attr('x', d => (((d.source as SimulationNode).x ?? 0) + ((d.target as SimulationNode).x ?? 0)) / 2)
        .attr('y', d => (((d.source as SimulationNode).y ?? 0) + ((d.target as SimulationNode).y ?? 0)) / 2);

      nodeEl.attr('transform', d => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

  }, [graph]);

  // Boot the graph simulation when data changes
  useEffect(() => {
    buildGraph();
    return () => {
      if (simRef.current) {
        simRef.current.stop();
      }
    };
  }, [buildGraph]);

  // 2. Handle 'step' prop changes imperatively (animations, highlights) without rebuilding the DOM
  useEffect(() => {
    if (!svgRef.current) return;
    
    // Reset all animations
    d3.selectAll<SVGGElement, SimulationNode>('g.node-bottleneck').classed('pulsing', false);
    const links = d3.selectAll<SVGPathElement, SimulationLink>('path.link');
    links.classed('animated', false);
    
    if (step === 'simulated') {
      simRef.current?.alpha(1).restart();
      links
        .classed('animated', true)
        .attr('stroke', '#3498db')
        .attr('stroke-dasharray', '4,4')
        .attr('marker-end', 'url(#arrow-active)');
    } 
    else if (step === 'bottleneck' || step === 'crossdomain') {
      // Highlight bottlenecks and cross-domain links
      d3.selectAll<SVGGElement, SimulationNode>('g.node-bottleneck').classed('pulsing', true);
      links
        .attr('stroke', function() {
          const src = d3.select(this).attr('data-source');
          const tgt = d3.select(this).attr('data-target');
          const cross = d3.select(this).classed('cross-domain');
          if (src === 'bottleneck' || tgt === 'bottleneck') return '#C5283D';
          return cross ? '#7B2D8E' : '#C0C0C0';
        })
        .attr('stroke-width', function() {
          const src = d3.select(this).attr('data-source');
          const tgt = d3.select(this).attr('data-target');
          return (src === 'bottleneck' || tgt === 'bottleneck') ? 3 : 1.5;
        })
        .attr('stroke-dasharray', function() {
          return d3.select(this).classed('cross-domain') ? '5,5' : null;
        })
        .attr('marker-end', function() {
          const src = d3.select(this).attr('data-source');
          const tgt = d3.select(this).attr('data-target');
          const cross = d3.select(this).classed('cross-domain');
          if (src === 'bottleneck' || tgt === 'bottleneck') return 'url(#arrow-danger)';
          return cross ? 'url(#arrow-dashed)' : 'url(#arrow-normal)';
        });
    }
    else {
      // Idle / Reset State
      links
        .attr('stroke', function() { return d3.select(this).classed('cross-domain') ? '#7B2D8E' : '#C0C0C0'; })
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', function() { return d3.select(this).classed('cross-domain') ? '5,5' : null; })
        .attr('marker-end', function() { return d3.select(this).classed('cross-domain') ? 'url(#arrow-dashed)' : 'url(#arrow-normal)'; });
    }
  }, [step]);

  // Calculate unique node types present in the current graph
  const uniqueTypes = React.useMemo(() => {
    if (!graph || !graph.nodes) return [];
    return Array.from(new Set(graph.nodes.map(n => n.type)));
  }, [graph]);

  // ── Render ─────────────────────────────────────────────────────────────────
  
  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-[#F5F5F5] tab-pane-bg font-mono text-sm text-gray-400 font-bold tracking-widest">
        AWAITING LAYER 1 CAUSAL GRAPH DATA...
      </div>
    );
  }

  return (
    <>
      <style>{`
        .link.animated {
          stroke-dasharray: 4, 4;
          animation: flow 0.8s linear infinite;
          stroke: #3498db !important;
        }
        @keyframes flow { to { stroke-dashoffset: -8; } }

        @keyframes pulse-subtle {
          0%   { r: 13; opacity: 1; stroke-width: 2.5px; }
          50%  { r: 17; opacity: 0.9; stroke-width: 4px; stroke: rgba(197, 40, 61, 0.5); }
          100% { r: 13; opacity: 1; stroke-width: 2.5px; }
        }
        .node-bottleneck.pulsing circle {
          animation: pulse-subtle 1.5s infinite ease-in-out;
        }
      `}</style>

      {/* SVG Canvas */}
      <svg
        ref={svgRef}
        className="absolute inset-0 w-full h-full"
        style={{ zIndex: 1 }}
      />

      {/* Dynamic Hover Tooltip */}
      {tooltip && (
        <div
          ref={tooltipRef}
          className="absolute bg-white border border-[#E5E5E5] p-4 pointer-events-none z-20 text-[12px] text-black shadow-[4px_4px_0px_rgba(0,0,0,0.05)] min-w-[220px]"
          style={{
            left: tooltip.x + 15,
            top:  tooltip.y + 15,
            opacity: 1,
            transition: 'opacity 0.15s ease',
            position: 'fixed',
          }}
        >
          <h3
            className="text-[14px] font-bold mb-2.5 pb-2 font-sans"
            style={{ borderBottom: `2px solid ${COLOR_MAP[tooltip.node.type] || '#999'}` }}
          >
            {tooltip.node.label}
          </h3>
          <div className="flex justify-between my-1.5 leading-relaxed">
            <span className="text-[#666666] font-semibold">Value</span>
            <span className="text-black font-mono">{tooltip.node.value.toFixed(2)}</span>
          </div>
          <div className="flex justify-between my-1.5 leading-relaxed">
            <span className="text-[#666666] font-semibold">β Coefficient</span>
            <span className="text-black font-mono">{tooltip.node.beta.toFixed(3)}</span>
          </div>
          <div className="flex justify-between my-1.5 leading-relaxed">
            <span className="text-[#666666] font-semibold">Type</span>
            <span className="text-black font-mono uppercase">{tooltip.node.type}</span>
          </div>
        </div>
      )}

      <GraphControls 
        step={step}
        onRunDiscovery={onRunDiscovery}
        onIdentifyBottleneck={onIdentifyBottleneck}
        onSearchCrossDomain={onSearchCrossDomain}
      />

      <CrossDomainBridge insightVisible={insightVisible} bridge={bridge} />
      <GraphLegend types={uniqueTypes} colorMap={COLOR_MAP} />
    </>
  );
};
