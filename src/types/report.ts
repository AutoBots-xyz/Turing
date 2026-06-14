// src/types/report.ts
// Matches python-engine/schemas/report.py — 5-section FinalReport

export interface Layer4Report {
  isComplete: boolean;

  // Section 1 — The Mechanism (plain-English cause chain + confidence badges)
  theMechanism: string;

  // Section 2 — The Experiment (specific next experiment to run)
  theExperiment: string;

  // Section 3 — Who Already Solved This (top 3 bridge analogies)
  whoSolvedThis: string;

  // Section 4 — Warnings & Conflicts (⚡ contradictions, ⚠️ low data)
  warningsAndConflicts: string[];

  // Section 5 — Next 3 Actions (ranked, specific, actionable)
  next3Actions: string[];

  // Metadata
  confidenceDisclaimer: string;
}
