# Frontend & Backend Audit — Error Report

> **Scope:** 5 files from `src/` and 5 files from `python-engine/` read top-to-bottom.  
> **Auditor:** Antigravity  
> **Date:** 2026-06-13  

---

## PART 1: FRONTEND AUDIT

### FILE 1 — `src/app/page.tsx` (Landing Page)

#### ❌ ERR-01: Hardcoded Run ID — No Backend Integration
**Line 15:**
```ts
router.push('/run/turing-active-run');
```
- The form `handleStart` function **ignores** the user's uploaded file and typed prompt entirely.
- It does NOT `POST` the data to the backend to create a real run. It just hard-navigates to a fake static route.
- The `prompt` state variable is captured via `useState` but **never sent anywhere**. It's dead state.
- **Impact:** The "Launch Pipeline" button is cosmetic. Pressing it always goes to the same page regardless of input.

#### ❌ ERR-02: Stub Comment Admitting It's a Demo
**Lines 13–14:**
```ts
// In a real app, this would POST the initial data/prompt to create a run ID
// For this demo, we immediately route to the active pipeline
```
- This comment explicitly admits the form submission is a stub and not production-ready.

#### ⚠️ ERR-03: Hardcoded System Status
**Lines 33–34:**
```tsx
SYSTEM STATUS: <span className="text-green-500">ONLINE</span>
ENGINE: V4_ALPHA
```
- "ONLINE" is hardcoded. It does not reflect actual backend health. If the Python backend is down, this still says ONLINE.
- "V4_ALPHA" is a hardcoded version string with no source of truth.

#### ⚠️ ERR-04: Research Logs Sidebar Is Static
**Lines 99–103:**
```tsx
{/* Dynamically populated from backend in production */}
<div className="text-left opacity-50 p-2 -ml-2">
  <div ...>WAITING FOR INGESTION</div>
  <div ...>No active runs</div>
</div>
```
- The sidebar is supposed to show a dynamic list of past/active runs fetched from the backend.
- Currently it's a static "No active runs" placeholder with a comment admitting it's not wired up.
- There is no `useEffect`, no `fetch`, no state — zero backend integration for the history panel.

---

### FILE 2 — `src/app/(dashboard)/run/[runId]/page.tsx` (Pipeline Dashboard)

#### ❌ ERR-05: Hardcoded Fallback Run ID
**Line 34:**
```ts
const runId = Array.isArray(params.runId) ? params.runId[0] : (params.runId || 'turing-active-run');
```
- If `params.runId` is missing or undefined, the page silently falls back to `'turing-active-run'` instead of showing an error or redirecting.
- This masks bugs — the user might think they're viewing real data when they're viewing stale/nonexistent run data.

#### ⚠️ ERR-06: Tab Auto-Advance Skips "Abstraction" Tab
**Lines 44–57:**
```ts
switch (runState.currentLayer) {
  case 1: setActiveTab('graph'); break;
  case 2: setActiveTab('canvas'); break;
  case 3: setActiveTab('search'); break;
  case 4: setActiveTab('report'); break;
}
```
- Layer 3 auto-advances to the `'search'` tab, but there is also an `'abstraction'` tab (line 83) that renders `<BridgeResultsPanel />`.
- The `'abstraction'` tab is **never auto-selected** by the backend layer progression. The user can only reach it by manually clicking the TopNav.
- This means `BridgeResultsPanel` is effectively hidden during normal pipeline flow.

#### ⚠️ ERR-07: `PipelineRunPageProps` Interface Is Wrong for App Router
**Lines 26–30:**
```ts
interface PipelineRunPageProps {
  params: {
    runId?: string | string[];
  };
}
```
- In Next.js 14 App Router, `params` is a **Promise** in server components. But this is a `"use client"` component that also uses `useParams()` import (line 5) which is **never actually called**.
- The `useParams` import on line 5 is dead code — imported but unused.

---

### FILE 3 — `src/hooks/useRunState.ts`

#### ❌ ERR-08: Hardcoded Backend URL
**Line 16:**
```ts
const response = await fetch(`http://127.0.0.1:8000/runs/${runId}/state`);
```
- The backend URL `http://127.0.0.1:8000` is hardcoded directly into the hook.
- This will break in any deployment (staging, production, Docker, Vercel, etc.) where the backend isn't on localhost.
- Should use an environment variable like `NEXT_PUBLIC_API_URL`.

#### ⚠️ ERR-09: No Loading State
- The hook returns `{ runState, error }` but has no `isLoading` boolean.
- On initial mount, `runState` is `null` and `error` is `null` — the consuming component has no way to distinguish "loading" from "no data exists."

---

### FILE 4 — `src/hooks/useAgentLoop.ts`

#### ❌ ERR-10: Hardcoded Backend URL (Same as ERR-08)
**Line 16:**
```ts
const response = await fetch(`http://127.0.0.1:8000/runs/${runId}/layer2/agents`);
```
- Same hardcoded `http://127.0.0.1:8000` problem. Will break in any non-local deployment.

#### ⚠️ ERR-11: No Loading State (Same Pattern as ERR-09)
- Returns `{ state, error }` with no `isLoading`. Same null ambiguity problem.

---

### FILE 5 — `src/hooks/useGraphAnimation.ts`

#### ❌ ERR-12: Hardcoded Backend URL (Same as ERR-08)
**Line 16:**
```ts
const response = await fetch(`http://127.0.0.1:8000/runs/${runId}/layer1/graph`);
```
- Same hardcoded localhost URL.

#### ⚠️ ERR-13: No Loading State (Same Pattern as ERR-09)
- Returns `{ graph, error }` with no `isLoading`.

---

### BONUS: Issues Found in `useSearchStream.ts` and `useReportStream.ts`

#### ❌ ERR-14: Hardcoded Backend URL in SSE Streams
**useSearchStream.ts line 12:**
```ts
const eventSource = new EventSource(`http://127.0.0.1:8000/runs/${runId}/layer3/search/stream`);
```
**useReportStream.ts line 12:**
```ts
const eventSource = new EventSource(`http://127.0.0.1:8000/runs/${runId}/layer4/report/stream`);
```
- Both SSE hooks hardcode `http://127.0.0.1:8000`. Same deployment-breaking issue as ERR-08/10/12.

#### ⚠️ ERR-15: SSE Error Handling Silently Closes Connection
**useSearchStream.ts lines 30–34, useReportStream.ts lines 29–33:**
```ts
eventSource.onerror = (err) => {
  console.error('...');
  setError(new Error('Connection lost'));
  eventSource.close();
};
```
- On any SSE error (network glitch, backend restart), the connection is permanently closed with no retry logic.
- If the backend momentarily restarts, the user must refresh the entire page to reconnect.
- Production SSE implementations should include exponential backoff reconnection.

---
---

## PART 2: BACKEND (PYTHON ENGINE) AUDIT (Initial 5 files)

### FILE 1 — `python-engine/services/layer1/ambiguity.py`

#### ❌ ERR-B01: Completely Empty Stub File
**Line 1:**
```python
# teammate's file
```
- The file contains zero logic. It is an empty placeholder.
- **Impact:** Any call to `AmbiguityDetector.analyze_graph()` will fail unless it's mocked elsewhere, or if the class exists it's completely missing its implementation.

---

### FILE 2 — `python-engine/services/layer1/confidence.py`

#### ❌ ERR-B02: Completely Empty Stub File
**Line 1:**
```python
# teammate's file
```
- The file contains zero logic. It is an empty placeholder.
- **Impact:** Any call to `ConfidenceChecker.evaluate_graph()` will fail.

---

### FILE 3 — `python-engine/routers/runs.py`

#### ⚠️ ERR-B03: Hardcoded Model Choice (`gpt-4o`)
**Lines 110 & 118:**
```python
graph = LLMGraphBuilder.build_graph(text, "gpt-4o")
# ...
graph = GraphValidator.validate(graph, "gpt-4o")
```
- The model string `"gpt-4o"` is hardcoded directly into the orchestrator.
- **Impact:** The system cannot easily switch to Anthropic, Gemini, or local open-source models without changing the codebase, defeating the purpose of using LiteLLM. It should be an environment variable (e.g. `DEFAULT_LLM_MODEL`).

#### ⚠️ ERR-B04: Ephemeral In-Memory State (`RUNS_STORE`)
**Line 77:**
```python
RUNS_STORE = {}
```
- The background task orchestrator stores all run states in a Python dictionary.
- **Impact:** If the FastAPI server restarts, crashes, or is deployed in a multi-worker environment (like `uvicorn --workers 4`), all active and past runs are instantly lost. It does not use the persistent database for active processing.

#### ⚠️ ERR-B05: Silent Error Swallowing in Background Task
**Lines 135-136:**
```python
except Exception as e:
    print(f"Warning during advanced layer 1 steps: {e}")
```
- If validation, fitting, classification, or ambiguity detection fail, it prints a warning to stdout and marks `layer1Status = "completed"`.
- **Impact:** The frontend will think Layer 1 succeeded even if half the pipeline crashed. The user will see an incomplete graph but no error message.

---

### FILE 4 — `python-engine/services/layer1/fitter.py`

#### ⚠️ ERR-B06: Hardcoded Random State
**Line 84:**
```python
gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=5, normalize_y=True, random_state=42)
```
- The Gaussian Process always uses `random_state=42`.
- **Impact:** While good for reproducibility during testing, it might hide optimization instability in production by forcing the same random seed every time.

#### ⚠️ ERR-B07: Hardcoded Kernel Parameters
**Line 81:**
```python
kernel = 1.0 * RBF(length_scale=1.0) + WhiteKernel(noise_level=1.0)
```
- The GP uses a strictly hardcoded kernel initialization for every relationship, regardless of the data scale or variance.
- **Impact:** While `GaussianProcessRegressor` will optimize these hyperparameters during `.fit()`, starting every single variable pair with the exact same initial bounds might lead to suboptimal local minima for wildly different datasets.

---

### FILE 5 — `python-engine/main.py`

#### ⚠️ ERR-B08: Hardcoded API Version
**Lines 31 & 58:**
```python
version="1.0.0",
# ...
return {"status": "ok", "service": "turing-python-engine", "version": "1.0.0"}
```
- The API version is hardcoded in multiple places.
- **Impact:** When updating versions, developers have to hunt down multiple hardcoded strings. This should be pulled from a single source of truth or an env variable.

---
---

## PART 3: BACKEND AUDIT (ADDITIONAL 5 FILES)

### FILE 6 — `python-engine/services/layer1/file_detector.py`

#### ❌ ERR-B09: Hardcoded Failure Fallback
**Lines 107-109:**
```python
except Exception as e:
    result["path"] = "TEXT"
```
- If analyzing a file crashes entirely, it blindly hardcodes the routing to `"TEXT"` path rather than returning a clear API error. This forces binary/corrupt files through the LLM path.

---

### FILE 7 — `python-engine/services/layer1/extractor.py`

#### ❌ ERR-B10: Blindly Catching and Defaulting to CSV
**Lines 145-147:**
```python
else:
    # Fallback, try reading as CSV
    df = pd.read_csv(io.BytesIO(file_bytes))
```
- If an unsupported file extension is passed, it forces pandas to read it as a CSV. If it's not a CSV, pandas will crash. The `except` block catches it, but the fallback design is poor.

#### ⚠️ ERR-B11: Hardcoded "Low Data" Limit
**Lines 237-239:**
```python
final_len = len(numeric_df)
if final_len < 30:
    warnings.append(f"LOW_DATA_WARNING: Dataset has only {final_len} rows...")
```
- The minimum data limit (`30`) for issuing a warning is entirely hardcoded in the logic, instead of being configurable.

---

### FILE 8 — `python-engine/services/layer1/validator.py`

#### ❌ ERR-B12: Prompt Schema Stub / Hardcoded Examples
**Lines 216-217:**
```python
Schema: [{{"source": "Yield", "target": "Temperature", "reason": "Outcome cannot cause input"}}]
If all are fine, return an empty array [].
```
- The agent prompt uses a highly specific manufacturing example ("Yield" and "Temperature") as the sole structural template. This could severely bias the LLM's understanding of edges if the dataset is completely unrelated (e.g. medical data).

#### ⚠️ ERR-B13: Duplicate Architecture / Hidden Code
**Lines 290+:**
- This file completely duplicates the implementations of `StructuralFitter` and `ConfidenceChecker`.
- **Impact:** The dedicated files (`fitter.py`, `confidence.py`) either contain old stubs or are entirely blank, while the actual runtime code is shoved into the bottom of `validator.py`. This is extremely misleading and breaks the architectural pattern.

---

### FILE 9 — `python-engine/routers/layer1.py`

#### ⚠️ ERR-B14: Hardcoded Model Parameter Again
**Line 194:**
```python
model_name = payload.get("model_name", "gpt-4o") # User specified model
```
- Same as ERR-B03, `gpt-4o` is hardcoded as the fallback string for graph building if the frontend doesn't provide one.

---

### FILE 10 — `python-engine/routers/layer2.py`

#### ❌ ERR-B15: Hardcoded Fake Gaussian Prediction
**Line 153:**
```python
pred = sim_res.predictions.get(sink_node_name, GaussianPrediction(mean=0.0, std_dev=1.0))
```
- If the simulation step fails to yield a prediction for the target node, it silently injects a completely fake `GaussianPrediction` with `mean=0.0` and `std_dev=1.0`.
- **Impact:** The Bayesian optimizer will use this fabricated data to update its beliefs, completely poisoning the simulation process with fake math rather than gracefully handling an edge case.

---
---

## PART 4: BACKEND AUDIT (FINAL 5 FILES - LAYER 2 AGENTS)

### FILE 11 — `python-engine/services/layer2/bayesian_optimizer.py`

#### ❌ ERR-B16: Fake Bayesian Optimization (Admitted Mock)
**Lines 5-7:**
```python
# TODO: REPLACE WITH REAL EI — When Layer 1 GP training is complete, replace
# get_base_point() with a proper Expected Improvement (EI) calculation
```
- The core of the layer 2 AI is totally fake. It uses a naive heuristic to guess points instead of actual mathematical Expected Improvement.
- **Impact:** The entire simulation step isn't performing real Bayesian Optimization.

---

### FILE 12 — `python-engine/services/layer2/do_calculus.py`

#### ❌ ERR-B17: Hardcoded High-Uncertainty Fallback
**Line 134:**
```python
predictions[node] = GaussianPrediction(mean=0.0, std_dev=1.0)
```
- When a node has no predicted parents in the do-calculus chain, it injects a completely fabricated value instead of failing gracefully.

---

### FILE 13 — `python-engine/services/layer2/agent_explorer.py`

#### ⚠️ ERR-B18: Hardcoded Center Fallback
**Line 62:**
```python
val = base_point.get(node, (space.min + space.max) / 2)
```
- If the base point is missing a node, the agent blindly defaults to the exact mathematical center of the bounds, which could be meaningless in non-linear spaces.

---

### FILE 14 — `python-engine/services/layer2/agent_exploiter.py`

#### ⚠️ ERR-B19: Hardcoded Domain Nudge Percentage
**Line 18:**
```python
nudge_pct: float = 0.01,
```
- The exploiter agent always nudges exactly 1% of the total domain space. This hardcoded learning rate might be way too large or way too small depending on the variable scale.

#### ⚠️ ERR-B20: Center Fallback (Same as ERR-B18)
**Line 53:**
```python
proposed[node] = (space.min + space.max) / 2
```
- Same fallback pattern as the explorer agent.

---

### FILE 15 — `python-engine/services/layer2/agent_contrarian.py`

#### ⚠️ ERR-B21: Center Fallback (Same as ERR-B18/20)
**Line 63:**
```python
val = base_point.get(node, (space.min + space.max) / 2)
```
- Same fallback pattern as the other two agents.

---
---

## PART 5: BACKEND AUDIT (LAYER 3 SERVICES & QUALITY CHECK)

### FILE 16 — `python-engine/services/layer3/search_papers.py`

#### ❌ ERR-B22: Hardcoded Mocks for Confidence & Status
**Lines 12-29:**
```python
def _deployment_status_from_citations(citation_count: int) -> str:
    if citation_count >= 500: return "replicated"
    elif citation_count >= 50: return "single_study"
    else: return "single_study"

def _confidence_from_rank(rank: int, total: int) -> float:
    return round(90.0 - (rank / max(total - 1, 1)) * 30.0, 1)
```
- The deployment status logic is hardcoded and actually returns `"single_study"` for *both* the `else` and `elif` blocks, ignoring the "blog" or "unverified" levels. 
- The confidence score is a completely arbitrary formula (`90 - rank/total * 30`) that has no mathematical basis in real ML confidence metrics.
- **Production Grade Quality:** Extremely low. Arbitrary thresholds like this break scalability and reliability.

---

### FILE 17 — `python-engine/services/layer3/search_web.py`

#### ❌ ERR-B23: Hardcoded Domain Authority Lists
**Lines 20-29:**
```python
_DEPLOYED_DOMAINS = frozenset({"aws.amazon.com", "cloud.google.com", "azure.microsoft.com", ...})
_AUTHORITATIVE_DOMAINS = frozenset({"martinfowler.com", "infoq.com", "acm.org", "ieee.org", ...})
```
- The system determines the entire "deployment status" of a search result by checking against a hardcoded list of exactly 17 domains. Any other domain automatically gets flagged as a "blog". 
- **Production Grade Quality:** Poor. This requires a developer to manually add new domains forever. It should use an ML classification approach or an external domain authority API.

---

### FILE 18 — `python-engine/services/layer3/bridge_ranker.py`

#### ❌ ERR-B24: Magic Numbers for Evidence Strength
**Lines 30-63:**
- The file is full of arbitrary hardcoded "magic numbers" (`score = 0.70`, `score += 0.25`, `score += 0.05`). There is no statistical basis for these weights.

#### ❌ ERR-B25: Silent LLM Failure Swallowing
**Lines 112-114:**
```python
if isinstance(llm_result, Exception):
    compatibility, transferability = 0.5, 0.5
```
- If the LLM fails to rank the bridges (due to a timeout, API error, or token limit), the code silently sets the scores to `0.5` instead of failing. 
- **Production Grade Quality:** Unacceptable. Silent data poisoning is worse than a hard crash, as the user will see "successful" results that are actually completely random.

---

### FILE 19 — `python-engine/services/layer3/isomorphism.py`

#### ❌ ERR-B26: Completely Empty Placeholder File
**Line 1:**
- The file `isomorphism.py` is **0 bytes**. It is completely empty. There is absolutely no logic inside it, indicating the entire isomorphism matching layer is either missing or heavily stubbed elsewhere.

---

### FILE 20 — `python-engine/services/layer3/contradiction_detector.py`

#### ⚠️ ERR-B27: Dummy Coroutine Anti-Pattern
**Lines 7-17:**
```python
async def _no_debate():
    return None
```
- The code uses a dummy coroutine just so it can `asyncio.gather` it with actual LLM calls. While it fixes a bug, creating dummy awaitables just to satisfy `gather` rather than filtering the list first is a poor design pattern.

---
---

## PART 6: BACKEND AUDIT (LAYER 4 & AGENT FACTORY)

### FILE 21 — `python-engine/routers/layer3.py`
*(No significant issues found. Basic routing logic.)*

### FILE 22 — `python-engine/routers/layer4.py`
*(No significant issues found. Basic routing logic.)*

### FILE 23 — `python-engine/services/layer4/context_packager.py`
*(No significant issues found. Handles string formatting appropriately.)*

### FILE 24 — `python-engine/services/layer4/report_builder.py`

#### ❌ ERR-B28: Fallback Generates Fake Positive Report
**Lines 136-155:**
```python
problem_statement=(
    f"The target graph exhibits a structural bottleneck pattern that matches "
    f"the mechanism described in '{top_title}'."
)
```
- When no Anthropic API key is available, the system completely abandons generative reporting and falls back to a hardcoded string template that guarantees a positive outcome ("exhibits a structural bottleneck pattern that matches the mechanism"). 
- **Production Grade Quality:** Very poor. The user is presented with what appears to be a bespoke AI-generated analysis but is actually a deterministic mad-libs string replacement.

---

### FILE 25 — `python-engine/services/agent_factory.py`

#### ❌ ERR-B29: Brittle String-Matching "Smart Fallback" (Skeptic)
**Lines 76-80:**
```python
contradiction_pairs = [
    ("inhibit", "activat"), ("increas", "decreas"),
    ("prevent", "caus"), ("widen", "narrow"),
    ("bypass", "block"), ("prevent", "allow"),
]
```
- If the LLM is unavailable, the fallback Skeptic agent uses an extremely naive string-matching heuristic to find contradictions. It blindly checks if the words "inhibit" and "activat" exist in the same source. 
- **Production Grade Quality:** Unacceptable. This is a fragile hack masquerading as natural language understanding.

#### ❌ ERR-B30: Hardcoded Fake Consensus (Synthesizer)
**Lines 135-141:**
```python
consensus = f"Sources disagree on mechanism direction: {conflict_snippet[:120]}"
experiment = (
    f"Design a controlled A/B experiment comparing the mechanism proposed "
    f"by the primary source against the contradicting approach: {conflict_snippet[:80]}..."
)
```
- Similarly, the fallback Synthesizer just hardcodes string slicing to generate a "consensus" and "recommended experiment". 
- This gives the illusion of a 3-agent swarm debate when it is actually just static text generation.

---
---

## PART 7: BACKEND AUDIT (CORE UTILITIES & LAYER 1 COMPONENTS)

### FILE 26 — `python-engine/services/anthropic_client.py`

#### ❌ ERR-B31: Fake Graph Extraction (Hardcoded Test Mock)
**Lines 115-144:**
- If the Anthropic API key is missing, `extract_causal_graph_from_text` falls back to completely fabricated data instead of failing or using a local open-source model.
- It scans the text for words like `"bypass"` or `"valve"` and injects a hardcoded graph involving `Input Pressure`, `Bottleneck`, and `Bypass Valve`.
- If it sees `"inhibit"` or `"activat"`, it injects a fake graph with `Compound X` and `Protein Y`. 
- **Production Grade Quality:** Unacceptable. This poisons the engine with mocked demo data, completely failing silently.

#### ❌ ERR-B32: Fake Semantic Transferability Heuristics
**Lines 192-201:**
- `evaluate_compatibility_and_transferability` mocks its response by literally computing the set intersection of words: `overlap_ratio = len(context_words & candidate_words) / max(len(context_words), 1)`.
- It then calculates compatibility by hardcoding arbitrary weights like `0.5 + overlap_ratio * 0.3 + structural_overlap * 0.2`.
- This is not production AI, this is simple string matching dressed up as "reasoning".

---

### FILE 27 — `python-engine/services/layer1/classifier.py`

#### ❌ ERR-B33: Hardcoded Extension-Based Routing
**Lines 35-39:**
- The `classify_path` function blindly assumes that all PDFs are text, and CSVs are data. It does not parse the internal file headers. This is brittle.

#### ⚠️ ERR-B34: String Manipulating JSON from LLM
**Lines 160-164:**
```python
if content.startswith("```json"):
    content = content[7:-3]
```
- In the hidden node detection pass, it attempts to parse the LLM output by slicing characters off strings rather than using robust JSON extraction tools (like `pydantic` or robust regex). This will break easily if the model's spacing changes.

---

### FILE 28 — `python-engine/services/layer1/gaussian_process.py`

#### ❌ ERR-B35: Admitted Mock for Gaussian Process Engine
**Lines 19-24:**
- The `GPEngine` class docstring explicitly admits: "Mock Gaussian Process Engine... For this architectural demonstration, it simulates mathematical prediction".
- **Production Grade Quality:** The entire Layer 2 simulation math layer is currently simulated math rather than a real Gaussian process, relying on weighted averages and quadrature instead of covariance kernels.

#### ⚠️ ERR-B36: Silently Ignoring Missing ML Libraries
**Lines 150-152:**
- `refine_confidence_with_gp` has a `try/except ImportError` block for `scikit-learn`. If `scikit-learn` is not installed, the system just returns the unrefined graph. No error is raised, no warning is logged.

---

### FILE 29 — `python-engine/services/layer1/ontology_builder.py`

#### ❌ ERR-B37: Heuristic Fallback with Hardcoded Regex
**Lines 87-95:**
- If the LLM call fails, `_keyword_graph` uses simple, hardcoded regexes (like `(\w[\w\s]{1,30})\s+causes\s+([\w\s]{1,30})`) to find causal edges. This is not natural language processing, it's brittle regex matching.

#### ❌ ERR-B38: Fake Ontology Generation
**Lines 214-217:**
- If `_generate_ontology` fails, it falls back to hardcoding `"VARIABLE", "METRIC", "COMPONENT"`. It does not inform the system that ontology extraction failed.

---

### FILE 30 — `python-engine/services/layer1/pc_algorithm.py`

#### ❌ ERR-B39: "Correlation is Causation" Fallback (Anti-Pattern)
**Lines 73-113:**
- If the `causal-learn` library is missing, `run_pc_algorithm` falls back to `_fallback_correlation_graph`.
- This fallback simply calculates the Pearson correlation between columns. If the correlation is `> 0.5`, it draws a causal edge.
- **Production Grade Quality:** Terrible. Correlation is famously not causation. Using Pearson correlation as a fallback for the PC Algorithm (which relies on conditional independence to rule out confounding) completely undermines the scientific integrity of the engine.

---
---

## PART 8: BACKEND AUDIT (ADDITIONAL LAYER 2/3 SERVICES)

### FILE 31 — `python-engine/services/layer2/heatmap.py`

#### ❌ ERR-B40: Hardcoded Fake Gaussian Prediction Injection
**Lines 138-141:**
```python
pred = sim_res.predictions.get(
    sink_node_name,
    GaussianPrediction(mean=0.0, std_dev=1.0)
)
```
- When generating the parameter space heatmap, if the simulation fails to yield a prediction for a given target node, the engine injects a perfectly neutral, completely fabricated Gaussian prediction instead of marking the coordinate as invalid/null.
- **Impact:** This fills the frontend UI heatmap with fake data points, making the user believe the simulation was successful across the entire parameter grid.

---

### FILE 32 — `python-engine/services/layer2/unexplored_zone_finder.py`

#### ❌ ERR-B41: Hardcoded Middle-of-Domain Fallback
**Lines 136-137:**
```python
steady_val = best_past.get(
    other_node,
    (other_space.min + other_space.max) / 2
)
```
- If historical data does not contain a specific node when attempting to find unexplored zones, the engine blindly falls back to the exact middle of the mathematical domain.
- **Production Grade Quality:** Low. Blindly picking the middle of a non-linear search space as a "steady state" is statistically meaningless.

#### ❌ ERR-B42: Duplicate Fake Prediction Injection
**Lines 150-152:**
```python
pred = sim_res.predictions.get(
    sink_node, GaussianPrediction(mean=0.0, std_dev=1.0)
)
```
- Same as ERR-B40, it injects fake data if the simulator returns nothing.

---

### FILE 33 — `python-engine/services/layer3/isomorphism_matcher.py`

#### ⚠️ ERR-B43: Arbitrary Magic Weights for Graph Matching
**Lines 92-97:**
```python
score = (
    max(0.0, min(1.0, degree_seq_score))  * 0.35 +
    max(0.0, min(1.0, out_degree_score))  * 0.25 +
    max(0.0, min(1.0, bottleneck_score))  * 0.25 +
    max(0.0, min(1.0, density_score))     * 0.15
) * 100.0
```
- The core isomorphism algorithm uses completely arbitrary "magic number" weights (0.35, 0.25, 0.15) to calculate structural similarity between causal graphs. 
- **Impact:** There is no statistical/mathematical justification for these weights. They appear to be tuned specifically to pass dummy test cases rather than accurately measure isomorphism.

---

### FILE 34 — `python-engine/services/layer1/universal_parser.py`
*(No critical architecture flaws found. Basic wrapper around pandas and pdfplumber, though error handling is rudimentary.)*

### FILE 35 — `python-engine/services/layer2/cliff_detector.py`
*(No significant issues found. Mathematical detection looks valid.)*

---
---

## PART 9: BACKEND AUDIT (FINAL SEARCH APIS & UTILITIES)

### FILE 36 — `python-engine/services/layer3/search_patents.py`

#### ❌ ERR-B44: Hardcoded Citation Fake Math
**Lines 77-78:**
```python
age = 2025 - int(year)
citation_count = min(500, age * 15)  # Rough proxy for citation accumulation
```
- The system generates a completely fake citation count for patents by multiplying the age of the patent by 15. This is fabricated data presented as authoritative metadata.

#### ❌ ERR-B45: Hardcoded Target Company Deployments
**Lines 69-72:**
```python
is_major_org = any(org in assignee for org in ["boeing", "nasa", "pfizer", "google", "microsoft", "amazon", "ge ", "siemens"])
deployment_status = "deployed" if is_major_org else "single_study"
```
- A patent is only marked as "deployed" if the assignee matches a hardcoded list of exactly 8 major corporations. Any other company or patent automatically defaults to "single_study". 
- **Production Grade Quality:** Extremely low.

---

### FILE 37 — `python-engine/services/layer3/search_wikipedia.py`

#### ❌ ERR-B46: Hardcoded Citation Fake Math (Wikipedia)
**Line 74:**
```python
citation_count = page_info.get("length", 0) // 100
```
- Similar to ERR-B44, it invents a citation count by simply dividing the byte-length of the Wikipedia article by 100.

---

### FILE 38 — `python-engine/services/layer3/relation_extractor.py`

#### ⚠️ ERR-B47: Dummy Data Propagation
- This file simply maps to `extract_causal_graph_from_text` (found in `anthropic_client.py`). Because that underlying function is rigged with hardcoded dummy graphs ("Bottleneck", "Input Pressure"), this extraction step acts as a passthrough for dummy data when API keys are missing.

---

### FILE 39 — `python-engine/database/crud.py`
*(No critical logic flaws found. Standard SQLAlchemy CRUD wrapper.)*

### FILE 40 — `python-engine/database/models.py`
*(No critical logic flaws found. Standard declarative tables.)*

---
---

## PART 10: BACKEND AUDIT (SCHEMAS)

### FILE 41-45 — `python-engine/schemas/` 
*(Files: `graph.py`, `layer2.py`, `layer3.py`, `report.py`, `run.py`)*
- These files are purely Pydantic data class definitions.
- They contain standard default values (e.g., `confidence_threshold=80.0`) but do not contain any hardcoded heuristic logic or mock data generation logic themselves.
- **Production Grade Quality:** Good. The schemas are strongly typed using Pydantic, which is standard for modern FastAPI applications.

---
---

## PART 11: BACKEND AUDIT (TEST FILES)

### FILE 46-49 — `python-engine/test_step*.py`
*(Files: `test_step11.py`, `test_step12.py`, `test_step13.py`, `test_step14.py`)*

#### ❌ ERR-B48: Hardcoded Target Graphs and Legacy Print Runners
- All four test files (`test_step11.py` through `test_step14.py`) use hardcoded query targets: `QUERY_BOTTLENECK`, `QUERY_ISOLATED_NODE`, `QUERY_HIGH_CONF_NODE`. 
- `test_step13.py` and `test_step14.py` hardcode a `TARGET_GRAPH` featuring `"Bottleneck Node"` and `"System Crash"`, manually forcing specific isomorphism match outcomes.
- Each test file includes a legacy `__main__` block with print statements (`print("\n--- RESULTS ---")`), acting as primitive test runners rather than strictly adhering to the pytest framework.

---
> **AUDIT COMPLETE:** Every single file in the `python-engine` directory (including routers, services, schemas, database, and tests) has been parsed and reviewed.


# Frontend Audit — Error Report

> **Scope:** 5 files from `src/` read top-to-bottom.  
> **Auditor:** Antigravity  
> **Date:** 2026-06-13  

---

## FILE 1 — `src/app/page.tsx` (Landing Page)

### ❌ ERR-01: Hardcoded Run ID — No Backend Integration
**Line 15:**
```ts
router.push('/run/turing-active-run');
```
- The form `handleStart` function **ignores** the user's uploaded file and typed prompt entirely.
- It does NOT `POST` the data to the backend to create a real run. It just hard-navigates to a fake static route.
- The `prompt` state variable is captured via `useState` but **never sent anywhere**. It's dead state.
- **Impact:** The "Launch Pipeline" button is cosmetic. Pressing it always goes to the same page regardless of input.

### ❌ ERR-02: Stub Comment Admitting It's a Demo
**Lines 13–14:**
```ts
// In a real app, this would POST the initial data/prompt to create a run ID
// For this demo, we immediately route to the active pipeline
```
- This comment explicitly admits the form submission is a stub and not production-ready.

### ⚠️ ERR-03: Hardcoded System Status
**Lines 33–34:**
```tsx
SYSTEM STATUS: <span className="text-green-500">ONLINE</span>
ENGINE: V4_ALPHA
```
- "ONLINE" is hardcoded. It does not reflect actual backend health. If the Python backend is down, this still says ONLINE.
- "V4_ALPHA" is a hardcoded version string with no source of truth.

### ⚠️ ERR-04: Research Logs Sidebar Is Static
**Lines 99–103:**
```tsx
{/* Dynamically populated from backend in production */}
<div className="text-left opacity-50 p-2 -ml-2">
  <div ...>WAITING FOR INGESTION</div>
  <div ...>No active runs</div>
</div>
```
- The sidebar is supposed to show a dynamic list of past/active runs fetched from the backend.
- Currently it's a static "No active runs" placeholder with a comment admitting it's not wired up.
- There is no `useEffect`, no `fetch`, no state — zero backend integration for the history panel.

---

## FILE 2 — `src/app/(dashboard)/run/[runId]/page.tsx` (Pipeline Dashboard)

### ❌ ERR-05: Hardcoded Fallback Run ID
**Line 34:**
```ts
const runId = Array.isArray(params.runId) ? params.runId[0] : (params.runId || 'turing-active-run');
```
- If `params.runId` is missing or undefined, the page silently falls back to `'turing-active-run'` instead of showing an error or redirecting.
- This masks bugs — the user might think they're viewing real data when they're viewing stale/nonexistent run data.

### ⚠️ ERR-06: Tab Auto-Advance Skips "Abstraction" Tab
**Lines 44–57:**
```ts
switch (runState.currentLayer) {
  case 1: setActiveTab('graph'); break;
  case 2: setActiveTab('canvas'); break;
  case 3: setActiveTab('search'); break;
  case 4: setActiveTab('report'); break;
}
```
- Layer 3 auto-advances to the `'search'` tab, but there is also an `'abstraction'` tab (line 83) that renders `<BridgeResultsPanel />`.
- The `'abstraction'` tab is **never auto-selected** by the backend layer progression. The user can only reach it by manually clicking the TopNav.
- This means `BridgeResultsPanel` is effectively hidden during normal pipeline flow.

### ⚠️ ERR-07: `PipelineRunPageProps` Interface Is Wrong for App Router
**Lines 26–30:**
```ts
interface PipelineRunPageProps {
  params: {
    runId?: string | string[];
  };
}
```
- In Next.js 14 App Router, `params` is a **Promise** in server components. But this is a `"use client"` component that also uses `useParams()` import (line 5) which is **never actually called**.
- The `useParams` import on line 5 is dead code — imported but unused.

---

## FILE 3 — `src/hooks/useRunState.ts`

### ❌ ERR-08: Hardcoded Backend URL
**Line 16:**
```ts
const response = await fetch(`http://127.0.0.1:8000/runs/${runId}/state`);
```
- The backend URL `http://127.0.0.1:8000` is hardcoded directly into the hook.
- This will break in any deployment (staging, production, Docker, Vercel, etc.) where the backend isn't on localhost.
- Should use an environment variable like `NEXT_PUBLIC_API_URL`.

### ⚠️ ERR-09: No Loading State
- The hook returns `{ runState, error }` but has no `isLoading` boolean.
- On initial mount, `runState` is `null` and `error` is `null` — the consuming component has no way to distinguish "loading" from "no data exists."

---

## FILE 4 — `src/hooks/useAgentLoop.ts`

### ❌ ERR-10: Hardcoded Backend URL (Same as ERR-08)
**Line 16:**
```ts
const response = await fetch(`http://127.0.0.1:8000/runs/${runId}/layer2/agents`);
```
- Same hardcoded `http://127.0.0.1:8000` problem. Will break in any non-local deployment.

### ⚠️ ERR-11: No Loading State (Same Pattern as ERR-09)
- Returns `{ state, error }` with no `isLoading`. Same null ambiguity problem.

---

## FILE 5 — `src/hooks/useGraphAnimation.ts`

### ❌ ERR-12: Hardcoded Backend URL (Same as ERR-08)
**Line 16:**
```ts
const response = await fetch(`http://127.0.0.1:8000/runs/${runId}/layer1/graph`);
```
- Same hardcoded localhost URL.

### ⚠️ ERR-13: No Loading State (Same Pattern as ERR-09)
- Returns `{ graph, error }` with no `isLoading`.

---

## BONUS: Issues Found in `useSearchStream.ts` and `useReportStream.ts` (Read During Audit)

### ❌ ERR-14: Hardcoded Backend URL in SSE Streams
**useSearchStream.ts line 12:**
```ts
const eventSource = new EventSource(`http://127.0.0.1:8000/runs/${runId}/layer3/search/stream`);
```
**useReportStream.ts line 12:**
```ts
const eventSource = new EventSource(`http://127.0.0.1:8000/runs/${runId}/layer4/report/stream`);
```
- Both SSE hooks hardcode `http://127.0.0.1:8000`. Same deployment-breaking issue as ERR-08/10/12.

### ⚠️ ERR-15: SSE Error Handling Silently Closes Connection
**useSearchStream.ts lines 30–34, useReportStream.ts lines 29–33:**
```ts
eventSource.onerror = (err) => {
  console.error('...');
  setError(new Error('Connection lost'));
  eventSource.close();
};
```
- On any SSE error (network glitch, backend restart), the connection is permanently closed with no retry logic.
- If the backend momentarily restarts, the user must refresh the entire page to reconnect.
- Production SSE implementations should include exponential backoff reconnection.

---

## Summary Table

| ID | Severity | File | Issue |
|----|----------|------|-------|
| ERR-01 | ❌ Critical | `page.tsx` | Form submit is a stub — ignores file + prompt, hardcodes route |
| ERR-02 | ❌ Critical | `page.tsx` | Stub comment explicitly says "For this demo" |
| ERR-03 | ⚠️ Warning | `page.tsx` | "ONLINE" status is hardcoded, not from backend health check |
| ERR-04 | ⚠️ Warning | `page.tsx` | Research Logs sidebar is static placeholder, no backend fetch |
| ERR-05 | ❌ Critical | `[runId]/page.tsx` | Silent fallback to `'turing-active-run'` masks missing params |
| ERR-06 | ⚠️ Warning | `[runId]/page.tsx` | Auto-advance skips "abstraction" tab — BridgeResults hidden |
| ERR-07 | ⚠️ Warning | `[runId]/page.tsx` | Dead `useParams` import + wrong props interface for App Router |
| ERR-08 | ❌ Critical | `useRunState.ts` | Hardcoded `http://127.0.0.1:8000` — breaks in any deployment |
| ERR-09 | ⚠️ Warning | `useRunState.ts` | No `isLoading` state — null ambiguity on mount |
| ERR-10 | ❌ Critical | `useAgentLoop.ts` | Hardcoded `http://127.0.0.1:8000` |
| ERR-11 | ⚠️ Warning | `useAgentLoop.ts` | No `isLoading` state |
| ERR-12 | ❌ Critical | `useGraphAnimation.ts` | Hardcoded `http://127.0.0.1:8000` |
| ERR-13 | ⚠️ Warning | `useGraphAnimation.ts` | No `isLoading` state |
| ERR-14 | ❌ Critical | `useSearchStream.ts` + `useReportStream.ts` | Hardcoded `http://127.0.0.1:8000` in SSE connections |
| ERR-15 | ⚠️ Warning | `useSearchStream.ts` + `useReportStream.ts` | No SSE reconnection logic — permanent disconnect on error |

---

## Verdict

**8 Critical issues (❌)** — These will cause failures in production or are functionally broken stubs.  
**7 Warnings (⚠️)** — These are missing best practices that will cause UX problems or deployment friction.

The single biggest systemic issue is **ERR-08/10/12/14**: the backend URL `http://127.0.0.1:8000` is copy-pasted into every single hook. This should be extracted into a single `NEXT_PUBLIC_API_URL` environment variable used everywhere.

The second biggest issue is **ERR-01**: the landing page form is entirely fake — it collects input but throws it away and navigates to a hardcoded route.

