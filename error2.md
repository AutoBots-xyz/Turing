# Project Audit Report

This report contains findings regarding typescript errors, hardcoded values, and empty files found in the project. Issues are only documented and have not been resolved.

## 1. TypeScript Errors (`tsc --noEmit`)

The following type errors were identified in the React frontend:

- **`src/components/graph/GraphPane.tsx`**
  - Line 110: `error TS2367: This comparison appears to be unintentional because the types 'LayerStatus | undefined' and '"failed"' have no overlap.`
  - Line 138: `error TS2367: This comparison appears to be unintentional because the types 'LayerStatus | undefined' and '"processing"' have no overlap.`
  - Line 138: `error TS2367: This comparison appears to be unintentional because the types 'LayerStatus | undefined' and '"pending"' have no overlap.`

- **`src/components/layer4/StreamingReport.tsx`**
  - Line 15: `error TS2339: Property 'isLoading' does not exist on type '{ report: Layer4Report | null; error: Error | null; isConnected: boolean; }'.`
  - Line 39: `error TS2322: Type 'boolean | "" | undefined' is not assignable to type 'boolean | undefined'. Type '""' is not assignable to type 'boolean | undefined'.`
  - Line 44: `error TS2322: Type 'boolean | "" | undefined' is not assignable to type 'boolean | undefined'. Type '""' is not assignable to type 'boolean | undefined'.`

## 2. Linter Errors (`npm run lint`)

- ESLint execution failed. The project seems to be missing a complete ESLint configuration or prompts for interactive setup during `next lint`, which halts automated checks.

## 3. Hardcoded Values

Several hardcoded strings were found. Most of these appear necessary for the project to function correctly, but they are listed here for review:

**Frontend (`src/`):**
- **`src/lib/api.ts`** (Line 10): Fallback API URL: `"http://127.0.0.1:8000"`
- **`src/components/layer3/BridgeResultsPanel.tsx`** (Line 52): SVG Namespace: `"http://www.w3.org/2000/svg"`
- **`src/components/layer2/Heatmap.tsx`** (Line 64): SVG Namespace: `"http://www.w3.org/2000/svg"`

**Backend (`python-engine/`):**
- Numerous hardcoded environment variable keys for API integrations are present across multiple service files (e.g., `report_builder.py`, `search_web.py`, `search_patents.py`, `contradiction_detector.py`, `validator.py`, `ontology_builder.py`, `classifier.py`, `anthropic_client.py`).
  - Example keys: `"ANTHROPIC_API_KEY"`, `"OPENAI_API_KEY"`, `"NVIDIA_API_KEY"`, `"NVIDIA_NIM_API_KEY"`, `"SERPER_API_KEY"`.
  - *Note: These are standard practices for retrieving secrets from environment variables and are necessary for the project.*

## 4. Empty Files

The following **5 source files are completely empty (0 bytes)** and need to be implemented or removed:

- **`src/components/graph/BottleneckPulse.tsx`** — 0 bytes
- **`src/components/graph/CausalGraph.tsx`** — 0 bytes
- **`src/components/graph/GraphEdge.tsx`** — 0 bytes
- **`src/components/graph/GraphNode.tsx`** — 0 bytes
- **`src/components/layer3/MechanismComparison.tsx`** — 0 bytes

> [!WARNING]
> These files are not currently imported anywhere in the codebase, so they don't cause an immediate build failure. However, they are orphaned stubs — likely components that were planned but never implemented. They should either be implemented or deleted to keep the project clean.

- **`python-engine/venv/`**: Numerous 0-byte files (like `__init__.py` and `py.typed`) exist within the Python virtual environment's `site-packages` directory. This is standard Python behavior and does not constitute an error.

## 5. Other Potential Issues

- No `TODO` or `FIXME` comments were found in the source directories.
- No loose `console.log` statements were found in the `src` directory that might indicate leftover debugging code.
