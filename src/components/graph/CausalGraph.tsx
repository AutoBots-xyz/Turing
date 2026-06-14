import React from 'react';
import { CausalNode, CausalEdge, type CausalGraph as CausalGraphType } from '../../types/graph';

export interface CausalGraphProps {
  /** The causal graph data to display. If null, shows a loading state. */
  graph: CausalGraphType | null;
  /** Optional highlight node IDs (e.g. bottleneck nodes). */
  highlightIds?: string[];
}

// ─── NodeRow ──────────────────────────────────────────────────────────────────
const TYPE_COLORS: Record<string, string> = {
  controllable: '#FF6B35',
  mediator:     '#004E89',
  bottleneck:   '#C5283D',
  outcome:      '#1A936F',
  chemistry:    '#7B2D8E',
};

const NodeRow: React.FC<{ node: CausalNode; highlighted: boolean }> = ({ node, highlighted }) => {
  const color = TYPE_COLORS[node.type] ?? '#999';
  return (
    <div
      className={`flex items-center gap-3 py-2 px-3 border-b border-gray-100 last:border-0 transition-colors ${
        highlighted ? 'bg-red-50' : 'hover:bg-gray-50'
      }`}
    >
      <span
        className="w-2 h-2 rounded-full shrink-0"
        style={{ backgroundColor: color }}
      />
      <span className="font-sans text-[13px] font-semibold text-black flex-1 truncate">
        {node.label}
      </span>
      <span
        className="font-mono text-[10px] font-bold uppercase tracking-wider shrink-0"
        style={{ color }}
      >
        {node.type}
      </span>
      <span className="font-mono text-[11px] text-gray-400 shrink-0 w-14 text-right">
        β {(node.beta ?? 0).toFixed(3)}
      </span>
    </div>
  );
};

// ─── EdgeRow ──────────────────────────────────────────────────────────────────
const EdgeRow: React.FC<{ edge: CausalEdge; nodeMap: Map<string, string> }> = ({ edge, nodeMap }) => {
  const isCross = !!edge.crossDomain;
  return (
    <div className={`flex items-center gap-2 py-1.5 px-3 border-b border-gray-100 last:border-0 text-[11px] font-mono ${isCross ? 'bg-purple-50' : ''}`}>
      <span className="font-semibold text-black truncate max-w-[110px]">
        {nodeMap.get(String(edge.source)) ?? String(edge.source)}
      </span>
      <span className="text-gray-400">
        {isCross ? '⇢' : '→'}
      </span>
      <span className="font-semibold text-black truncate max-w-[110px]">
        {nodeMap.get(String(edge.target)) ?? String(edge.target)}
      </span>
      <span className="ml-auto text-gray-400 shrink-0">
        w={Math.abs(edge.weight ?? 0).toFixed(2)}
      </span>
      {isCross && (
        <span className="text-[#7B2D8E] font-bold shrink-0">✦</span>
      )}
    </div>
  );
};

// ─── CausalGraph ─────────────────────────────────────────────────────────────
/**
 * CausalGraph — a compact tabular view of a CausalGraph data object.
 * Complements the interactive D3GraphEngine with a readable summary panel
 * that lists all nodes and edges with their properties.
 */
export const CausalGraph: React.FC<CausalGraphProps> = ({ graph, highlightIds = [] }) => {
  if (!graph) {
    return (
      <div className="flex items-center justify-center w-full h-full font-mono text-xs text-gray-400 tracking-widest uppercase">
        Awaiting causal graph data...
      </div>
    );
  }

  const nodeMap = new Map<string, string>(graph.nodes.map(n => [n.id, n.label]));
  const highlightSet = new Set(highlightIds);

  return (
    <div className="w-full flex flex-col gap-4 font-sans">
      {/* Summary bar */}
      <div className="flex items-center gap-4 px-1 font-mono text-[10px] text-gray-500 uppercase tracking-widest">
        <span>{graph.nodes.length} nodes</span>
        <span className="text-gray-300">|</span>
        <span>{graph.edges.length} edges</span>
        {graph.overall_graph_confidence !== undefined && (
          <>
            <span className="text-gray-300">|</span>
            <span>confidence {(graph.overall_graph_confidence * 100).toFixed(1)}%</span>
          </>
        )}
        {graph.is_fitted && (
          <>
            <span className="text-gray-300">|</span>
            <span className="text-green-600">● fitted</span>
          </>
        )}
      </div>

      {/* Nodes table */}
      <div className="border-2 border-black">
        <div className="bg-black text-white font-mono text-[10px] font-bold tracking-widest px-3 py-2 uppercase">
          Nodes
        </div>
        <div className="divide-y divide-gray-100">
          {graph.nodes.length === 0 ? (
            <div className="px-3 py-4 text-xs text-gray-400 font-mono">No nodes.</div>
          ) : (
            graph.nodes.map(n => (
              <NodeRow key={n.id} node={n} highlighted={highlightSet.has(n.id)} />
            ))
          )}
        </div>
      </div>

      {/* Edges table */}
      <div className="border-2 border-black">
        <div className="bg-black text-white font-mono text-[10px] font-bold tracking-widest px-3 py-2 uppercase">
          Edges
        </div>
        <div className="divide-y divide-gray-100">
          {graph.edges.length === 0 ? (
            <div className="px-3 py-4 text-xs text-gray-400 font-mono">No edges.</div>
          ) : (
            graph.edges.map((e, i) => (
              <EdgeRow key={i} edge={e} nodeMap={nodeMap} />
            ))
          )}
        </div>
      </div>
    </div>
  );
};
