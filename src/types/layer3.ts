// src/types/layer3.ts
// Matches python-engine/schemas/layer3.py

export interface SearchSource {
  src: string;
  title: string;
  match: number;
}

export interface BridgeResult {
  sourceDomain: string;
  targetDomain: string;
  isomorphismScore: number;
  description: string;
  title: string;
  evidenceTier: string;
}

export interface Layer3State {
  status: string;
  query: string;
  streamSources: SearchSource[];
  topBridges: BridgeResult[];
  isLocked: boolean;
}
