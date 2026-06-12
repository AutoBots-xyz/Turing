// src/types/graph.ts
// Matches python-engine/schemas/graph.py

export type NodeType = 'controllable' | 'mediator' | 'bottleneck' | 'outcome' | 'chemistry';

export interface CausalNode {
  id: string;
  label: string;
  type: NodeType;
  value: number;
  beta: number;
}

export interface CausalEdge {
  source: string;
  target: string;
  curvature: number;
  weight: number;
  label: string;
  crossDomain?: boolean;
}

export interface CausalGraph {
  nodes: CausalNode[];
  edges: CausalEdge[];
  overall_graph_confidence?: number;
  urgent_nodes?: { node_id: string; urgency_score: number; label: string }[];
  is_fitted?: boolean;
  routing?: string;
}
