// src/types/layer2.ts
// Matches python-engine/schemas/layer2.py

export interface AgentEntry {
  id: string;
  type: 'explorer' | 'exploiter' | 'contrarian';
  agentId: string;
  y: number;
  content: string;
  delayMs: number;
}

export type HypothesisNodeVariant = 'normal' | 'falsified' | 'confirmed' | 'synthesized';

export interface HypothesisNode {
  id: string;
  variant: HypothesisNodeVariant;
  label: string;
  title: string;
  description: string;
  x: number;
  y: number;
  delayMs?: number;
  mechanism?: string;
}

export type ConnectorLineVariant = 'explorer' | 'contrarian' | 'exploiter' | 'tree';

export interface ConnectorLine {
  id: string;
  variant: ConnectorLineVariant;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  delayMs?: number;
}

export interface Layer2State {
  status: string;
  nodesComputed: number;
  agents: AgentEntry[];
  heatmapNodes: HypothesisNode[];
  heatmapLines: ConnectorLine[];
}
