import React from 'react';
import { BridgeResult } from '../../types/layer3';

export interface MechanismComparisonProps {
  /** The source bridge result (from the user's domain). */
  source: BridgeResult | null;
  /** The cross-domain bridge found by Layer 3 isomorphism search. */
  match: BridgeResult | null;
  /** Whether the comparison is still being streamed/loaded. */
  isLoading?: boolean;
}

// ─── MechanismCard ───────────────────────────────────────────────────────────
const MechanismCard: React.FC<{
  label: string;
  bridge: BridgeResult | null;
  accentColor: string;
}> = ({ label, bridge, accentColor }) => (
  <div className="flex-1 border-2 border-black bg-white p-5 flex flex-col gap-3">
    <div
      className="font-mono text-[10px] font-bold uppercase tracking-[0.2em]"
      style={{ color: accentColor }}
    >
      {label}
    </div>

    {bridge ? (
      <>
        <h3 className="font-sans text-base font-bold text-black leading-snug">
          {bridge.title}
        </h3>

        <div className="flex gap-2 items-center font-mono text-[10px] font-bold text-gray-500 uppercase">
          <span
            className="px-1.5 py-0.5 border font-bold"
            style={{ borderColor: accentColor, color: accentColor }}
          >
            {bridge.sourceDomain}
          </span>
          <span>→</span>
          <span
            className="px-1.5 py-0.5 border font-bold"
            style={{ borderColor: accentColor, color: accentColor }}
          >
            {bridge.targetDomain}
          </span>
        </div>

        <p className="font-sans text-[13px] text-gray-700 leading-relaxed border-l-2 pl-3" style={{ borderColor: accentColor }}>
          {bridge.description}
        </p>

        <div className="flex gap-3 mt-auto pt-2 border-t border-gray-100">
          <div className="font-mono text-[10px] text-gray-500">
            TIER: <span className="font-bold text-black">{bridge.evidenceTier}</span>
          </div>
          <div className="font-mono text-[10px] text-gray-500">
            SCORE:{' '}
            <span className="font-bold text-black">
              {(bridge.isomorphismScore * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </>
    ) : (
      <div className="flex-1 flex items-center justify-center font-mono text-xs text-gray-400 uppercase tracking-widest">
        Awaiting data...
      </div>
    )}
  </div>
);

// ─── IsomorphismBadge ────────────────────────────────────────────────────────
const IsomorphismBadge: React.FC<{ score: number | null }> = ({ score }) => (
  <div className="flex flex-col items-center justify-center gap-2 px-4 shrink-0">
    <div className="w-px flex-1 bg-gray-300" />
    <div className="flex flex-col items-center gap-1">
      <div className="font-mono text-[9px] text-gray-400 uppercase tracking-wider text-center">
        ISO
        <br />
        MATCH
      </div>
      {score !== null ? (
        <div
          className="font-mono text-base font-bold"
          style={{ color: score > 0.7 ? '#1A936F' : score > 0.4 ? '#FF6B35' : '#C5283D' }}
        >
          {(score * 100).toFixed(0)}%
        </div>
      ) : (
        <div className="w-2 h-2 rounded-full bg-gray-300 animate-pulse" />
      )}
    </div>
    <div className="w-px flex-1 bg-gray-300" />
  </div>
);

// ─── MechanismComparison ─────────────────────────────────────────────────────
/**
 * MechanismComparison — side-by-side view of the source problem mechanism
 * and the cross-domain analogical match discovered by the Layer 3 isomorphism engine.
 */
export const MechanismComparison: React.FC<MechanismComparisonProps> = ({
  source,
  match,
  isLoading = false,
}) => {
  const isoScore = source && match ? match.isomorphismScore : null;

  if (isLoading) {
    return (
      <div className="w-full flex items-center justify-center gap-3 py-10 font-mono text-xs text-gray-400 uppercase tracking-widest">
        <div className="w-2 h-2 rounded-full bg-gray-300 animate-ping" />
        Searching for structural isomorphisms...
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col gap-3">
      {/* Header */}
      <div className="font-mono text-[10px] font-bold text-gray-500 uppercase tracking-[0.2em]">
        Mechanism Comparison — Cross-Domain Isomorphism
      </div>

      {/* Cards */}
      <div className="flex items-stretch gap-0 w-full min-h-[220px]">
        <MechanismCard
          label="Source Mechanism"
          bridge={source}
          accentColor="#004E89"
        />
        <IsomorphismBadge score={isoScore} />
        <MechanismCard
          label="Analogical Match"
          bridge={match}
          accentColor="#7B2D8E"
        />
      </div>

      {/* Footer note */}
      {source && match && (
        <div className="font-mono text-[9px] text-gray-400 uppercase tracking-wider text-right">
          Similarity computed via structural graph edit distance · Layer 3 Engine
        </div>
      )}
    </div>
  );
};
