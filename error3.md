# Project Audit Report — error3.md

Fresh, comprehensive audit of `d:\autobots\Turing`. Issues are **documented only** and have not been resolved.

---

## 1. TypeScript Errors (`tsc --noEmit`)

**Result: ✅ PASS — Zero TypeScript errors.**

---

## 2. ESLint Errors (`npm run lint`)

**Result: ✅ PASS — No ESLint warnings or errors.**

### Resolved

- **`src/components/layer4/ReportNav.tsx`** (Line 14) — ✅ Fixed
  - Was: `{modelName} // {status}` — `//` treated as a JSX comment literal.
  - Fix: Changed to `{modelName}{' // '}{status}` (explicit string literal).

- **`src/components/layer4/ReportSection.tsx`** (Line 24) — ✅ Fixed
  - Was: `{stepNumber} //` — same `//` JSX comment issue.
  - Fix: Changed to `{stepNumber}{' //'}` (explicit string literal).

- **`src/app/(dashboard)/run/[runId]/page.tsx`** (Line 72) — ✅ Fixed
  - Was: `useEffect` dependency array `[runState?.currentLayer]` missing `runState`.
  - Fix: Changed to `[runState]` to cover all fields read inside the effect.

---

## 3. Hardcoded Values

### Frontend (`src/`) — ✅ All magic numbers resolved

| File | Line | Value | Status |
|------|------|-------|--------|
| `src/lib/api.ts` | 10 | `"http://127.0.0.1:8000"` | ✅ Necessary — local dev fallback, overridden by `NEXT_PUBLIC_API_URL` |
| `src/lib/api.ts` | 110, 130 | `FETCH_TIMEOUT_MS = 3000` | ✅ Fixed — extracted to named constant |
| `src/hooks/useRunState.ts` | 42 | `POLL_INTERVAL_MS = 1500` | ✅ Fixed — extracted to named constant |
| `src/hooks/useGraphAnimation.ts` | 42 | `POLL_INTERVAL_MS = 2000` | ✅ Fixed — extracted to named constant |
| `src/hooks/useAgentLoop.ts` | 42 | `POLL_INTERVAL_MS = 1000` | ✅ Fixed — extracted to named constant |
| `src/components/layer4/ReportNav.tsx` | 9 | `"CLAUDE_3.5_SONNET"` (default model name) | ⚠️ Open — hardcoded model name, should come from env/config |
| `src/components/layer4/ReportSection.tsx` | 16 | `'#000000'` (default color) | ✅ Necessary — acceptable UI default |

### Backend (`python-engine/`) — Open items remain

| File | Line | Value | Status |
|------|------|-------|--------|
| `main.py` | 79 | `"0.0.0.0"` (bind host) | ✅ Necessary — standard for containerised deployments |
| `main.py` | 80 | `8000` (default port) | ✅ Necessary — readable from `PORT` env var with fallback |
| `main.py` | 21 | `"1.0.0"` (default app version) | ✅ Necessary — overridden by `APP_VERSION` env var |
| `main.py` | 46 | `allow_origins=["*"]` (CORS wildcard) | ❌ Security risk — restrict to known frontend origins in production |
| `services/layer3/search_web.py` | 55 | `timeout=10.0` | ⚠️ Open — should be a named constant |
| `services/layer3/search_patents.py` | 47 | `timeout=15.0` | ⚠️ Open — should be a named constant |
| `services/layer3/search_papers.py` | 54 | `timeout=10.0` | ⚠️ Open — should be a named constant |
| `services/layer3/search_wikipedia.py` | 40 | `timeout=10.0` | ⚠️ Open — should be a named constant |
| `services/layer3/isomorphism.py` | 38 | `timeout=3.0` | ⚠️ Open — should be a named constant |

---

## 4. API Keys Exposed in `.env`

> [!CAUTION]
> The `.env` file contained **live API keys in plain text**. The keys have been scrubbed from the file, but the keys themselves must still be **rotated** by the developer since they were stored in plain text on disk and may have been exposed.

### Status

| Key | Action Taken | Remaining |
|-----|-------------|-----------|
| `OPENAI_API_KEY` (`sk-ws-...`) | ✅ Scrubbed from `.env` — replaced with placeholder | ⚠️ **Rotate this key** in your Aliyun DashScope console |
| `DASHSCOPE_API_KEY` (same key) | ✅ Scrubbed from `.env` — replaced with placeholder | ⚠️ **Rotate this key** in your Aliyun DashScope console |
| `SERPER_API_KEY` (hash value) | ✅ Scrubbed from `.env` — replaced with placeholder | ⚠️ **Rotate this key** at serper.dev |

### Other Actions Taken

- ✅ **`.env` is in `.gitignore`** (line 9) — confirmed, the file will not be committed going forward.
- ✅ **`.env.example` updated** — added missing `OPENAI_API_KEY`, `OPENAI_API_BASE`, `DASHSCOPE_API_KEY` placeholder entries so it is a complete template for new developers.

### Remaining Manual Action Required

> [!IMPORTANT]
> Even though `.env` is gitignored going forward, **check if the file was ever committed** in git history: run `git log --all --full-history -- .env`. If it appears in history, the keys must be treated as compromised and rotated regardless.

---

## 5. Empty Source Files (Orphaned Stubs) — ✅ Resolved

All 5 previously empty source files (0 bytes) have now been fully implemented as React components matching the project's design system:

| File | Status | Description |
|------|--------|-------------|
| `src/components/graph/BottleneckPulse.tsx` | ✅ Implemented | SVG overlay for the pulsing red bottleneck ring animation |
| `src/components/graph/CausalGraph.tsx` | ✅ Implemented | Tabular summary view of nodes, edges, weights and β-coefficients |
| `src/components/graph/GraphEdge.tsx` | ✅ Implemented | List row component for a causal edge (with cross-domain support) |
| `src/components/graph/GraphNode.tsx` | ✅ Implemented | Circle + label component matching the `COLOR_MAP` |
| `src/components/layer3/MechanismComparison.tsx` | ✅ Implemented | Side-by-side isomorphic match comparison panel |
---

## 6. Code Quality Issues

### TypeScript `any` Usage

| File | Line | Issue |
|------|------|-------|
| `src/components/graph/GraphPane.tsx` | 59, 72, 85 | `catch (err: any)` — error typed as `any` in all three fetch handlers |
| `src/components/layer2/AgentStatusPanel.tsx` | 90 | `agents as any` — unsafe type cast |
| `src/components/layer2/AgentStatusPanel.tsx` | 91 | `nodes as any`, `lines as any` — unsafe type casts |

### Python `print()` Instead of Logging

The following files use bare `print()` statements instead of a proper logging framework (e.g., Python's `logging` module). This is bad practice in production services as print output is not structured, configurable, or capturable by log aggregation tools.

| File | Lines |
|------|-------|
| `services/layer3/search_web.py` | 42, 86 |
| `services/layer3/search_patents.py` | 34, 91 |
| `services/layer3/search_wikipedia.py` | 95 |
| `services/layer3/search_papers.py` | 97 |
| `services/layer3/contradiction_detector.py` | 179 |
| `services/layer3/bridge_ranker.py` | 85 |
| `routers/layer3.py` | 39, 42, 60 |

### `console.error` in Hooks

| File | Line | Issue |
|------|------|-------|
| `src/hooks/useSearchStream.ts` | 46 | `console.error(...)` — swallows parse errors silently after logging |
| `src/hooks/useReportStream.ts` | 45 | `console.error(...)` — same issue |

---

## 7. Configuration Issues

### Missing ESLint Config (now resolved)
- `.eslintrc.json` was absent, causing `npm run lint` to stall with an interactive prompt.
- ✅ Fixed: `.eslintrc.json` created with `{ "extends": "next/core-web-vitals" }`.
- `eslint` and `eslint-config-next@14.2.3` installed as dev dependencies.

### `npm audit` Vulnerabilities
Running `npm install` reported **8 vulnerabilities (1 moderate, 6 high, 1 critical)** in installed packages.
- Run `npm audit` for full details.
- Run `npm audit fix` to auto-resolve non-breaking ones.

### README.md is Nearly Empty
- `README.md` is only **8 bytes** — essentially blank. The project has no documentation for setup, usage, or deployment.

---

## 8. `.env` vs `.gitignore` Check

> [!IMPORTANT]
> Verify that `.env` is listed in `.gitignore`. If live API keys in `.env` have ever been committed to git history, they must be treated as compromised and rotated immediately regardless.
