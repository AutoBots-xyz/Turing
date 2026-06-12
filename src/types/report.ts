// src/types/report.ts
// Matches python-engine/schemas/report.py

export interface ReportSection {
  title: string;
  content: string;
  confidenceScore: number;
}

export interface Layer4Report {
  id: string;
  runId: string;
  mechanismExplanation: string;
  experimentResults: string;
  bridgeSummary: string;
  warnings: string[];
  recommendedActions: string[];
  isComplete: boolean;
}
