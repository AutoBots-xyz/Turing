// src/types/run.ts
// Matches python-engine/schemas/run.py

export type LayerStatus = 'idle' | 'running' | 'completed' | 'error';

export interface RunState {
  runId: string;
  currentLayer: number; // 1 to 4
  layer1Status: LayerStatus;
  layer2Status: LayerStatus;
  layer3Status: LayerStatus;
  layer4Status: LayerStatus;
  layer1Progress?: number;
  progressPercentage: number;
}
