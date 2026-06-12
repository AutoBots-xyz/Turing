# Layer 2 Codebase Audit — Error Report

> Auditor: AI Code Review Agent  
> Audit Date: 2026-06-12  
> Scope: `python-engine/` — Layer 2 files only  
> Method: File-by-file manual review, one file at a time with user approval

---

## File 1: `python-engine/schemas/layer2.py`

**Status: 5 Issues Found**

---

### Issue 1.1 (FIXED)
- **File Path:** `python-engine/schemas/layer2.py`
- **Line Number(s):** 32–34
- **Severity:** Medium
- **Issue Description:** `SearchSpace` has no validation that `min < max`. A caller can create `SearchSpace(min=100.0, max=50.0)` — an inverted domain — and it will silently propagate through the entire pipeline (optimizer, heatmap, zone finder) producing mathematically incorrect results (negative ranges, reversed linspace grids, etc.).
- **Recommended Fix:** Add a Pydantic `@model_validator(mode='after')` that raises `ValueError` if `self.min >= self.max`.

---

### Issue 1.2 (FIXED)
- **File Path:** `python-engine/schemas/layer2.py`
- **Line Number(s):** 81
- **Severity:** Medium
- **Issue Description:** `RoundInput.historical_data` has no `default_factory`. Unlike `HeatmapInput` (line 105) and `ZoneFinderInput` (line 130) which default to `[]`, `RoundInput.historical_data` is a required field with no default — the frontend **must** always send it, even for round 1 when there is zero history. This is inconsistent with the other schemas and will cause a `422 Validation Error` if the field is omitted.
- **Recommended Fix:** Add `default_factory=list` to match the other schemas: `historical_data: List[Dict[str, Any]] = Field(default_factory=list, description="...")`

---

### Issue 1.3 (FIXED)
- **File Path:** `python-engine/schemas/layer2.py`
- **Line Number(s):** 132
- **Severity:** Low
- **Issue Description:** `ZoneFinderInput.gap_threshold` has no boundary validation. Values outside `0.0–1.0` (e.g. `gap_threshold=5.0` or `gap_threshold=-1.0`) are accepted silently and will produce wrong gap detection logic (either everything is a gap, or nothing is).
- **Recommended Fix:** Add `ge=0.0, le=1.0` constraints: `gap_threshold: float = Field(default=0.2, ge=0.0, le=1.0, ...)`

---

### Issue 1.4 (FIXED)
- **File Path:** `python-engine/schemas/layer2.py`
- **Line Number(s):** 108
- **Severity:** Low
- **Issue Description:** `HeatmapInput.cliff_sigma` has no minimum validation. A value of `0.0` or negative would cause every point to be flagged as a cliff (threshold = mean itself, or above mean). While not a crash, it produces nonsensical output.
- **Recommended Fix:** Add `gt=0.0` constraint: `cliff_sigma: float = Field(default=1.5, gt=0.0, ...)`

---

### Issue 1.5 (FIXED)
- **File Path:** `python-engine/schemas/layer2.py`
- **Line Number(s):** 52–54
- **Severity:** Low
- **Issue Description:** `GaussianPrediction.std_dev` has no non-negative constraint. A negative standard deviation is mathematically undefined. While the GP engine currently never produces one, an external caller could construct `GaussianPrediction(mean=50.0, std_dev=-3.0)` which would corrupt downstream ambiguity calculations (`mean / (std_dev + 0.001)` in the router would produce large negative scores).
- **Recommended Fix:** Add `ge=0.0` constraint: `std_dev: float = Field(ge=0.0)`

---

## File 2: `python-engine/services/layer1/gaussian_process.py`

**Status: 5 Issues Found**

---

### Issue 2.1 (DEFERRED - Architectural Redesign)
- **File Path:** `python-engine/services/layer1/gaussian_process.py`
- **Line Number(s):** 5–7
- **Severity:** Critical
- **Issue Description:** The entire file is a **mock/placeholder**. Lines 5–7 contain a `TODO: REPLACE WITH REAL GP` comment that explicitly states this is not production logic. The class uses a simple weighted sum instead of an actual Gaussian Process Regressor. Every prediction in Layer 2 (Do-Calculus, Heatmap, Zone Finder, Agent Loop) relies on this mock, meaning **no real statistical learning is happening anywhere in the application**. The uncertainty propagation is a rough quadrature approximation, not a trained kernel-based GP posterior.
- **Recommended Fix:** Replace with `scikit-learn.GaussianProcessRegressor` or `BoTorch` fitted on the actual uploaded CSV data. The `predict_child` interface signature must be preserved so downstream Layer 2 code needs no changes.

---

### Issue 2.2 (DEFERRED - Architectural Redesign)
- **File Path:** `python-engine/services/layer1/gaussian_process.py`
- **Line Number(s):** 65–68
- **Severity:** Medium
- **Issue Description:** The mean prediction is a **raw weighted sum** (`parent_mean * weight`), which means edge weights directly scale the parent's output. If weights are > 1.0, the mean inflates unboundedly. If weights are negative (valid in causal graphs for inhibitory relationships), the mean can go negative before the floor on line 71 clamps it. This linear aggregation does not account for non-linear causal relationships, interaction effects, or saturation — which are common in real experimental systems.
- **Recommended Fix:** This is inherent to the mock design. When the real GP replaces this class, it must use a proper kernel-based regression. For now, document this limitation prominently and consider capping the output range to the domain bounds rather than just flooring at 0.0.

---

### Issue 2.3 (DEFERRED - Architectural Redesign)
- **File Path:** `python-engine/services/layer1/gaussian_process.py`
- **Line Number(s):** 75
- **Severity:** Medium
- **Issue Description:** Uncertainty compounding treats all parent errors as **independent** (`sqrt(sum(variances))`). In a causal graph, parent nodes are frequently correlated (e.g., temperature affects both membrane thickness and enzyme activity, which are then co-parents of yield). Ignoring covariance terms underestimates true uncertainty, making the system appear more confident than it should be. The `is_cliff` detection in heatmap.py and the ambiguity scoring in the router both rely on `std_dev`, so underestimated uncertainty causes missed cliffs and inflated ambiguity-reduction scores.
- **Recommended Fix:** When replacing with a real GP, use the full covariance matrix for joint predictions. For the mock, add a comment warning that uncertainty is underestimated due to ignored covariance.

---

### Issue 2.4 (DEFERRED - Enhancement)
- **File Path:** `python-engine/services/layer1/gaussian_process.py`
- **Line Number(s):** 71
- **Severity:** Low
- **Issue Description:** The floor `max(0.0, child_mean)` assumes all predicted quantities are non-negative. While true for yield percentages, this assumption may not hold for all use cases (e.g., temperature deltas, pH changes, net charge). If the platform is extended beyond yield optimization, this floor will silently corrupt predictions for variables with valid negative ranges.
- **Recommended Fix:** Make the floor configurable or remove it entirely, letting the SearchSpace bounds in the schema layer handle validity. Add a comment documenting the assumption.

---

### Issue 2.5 (FIXED)
- **File Path:** `python-engine/services/layer1/gaussian_process.py`
- **Line Number(s):** 39–40
- **Severity:** Low
- **Issue Description:** When `parent_predictions` is empty, the method returns `{"mean": 0.0, "std_dev": self.base_noise}`. This is the prediction for source nodes (nodes with no parents). Returning `mean=0.0` is mathematically arbitrary — in reality, a source node's value comes from the intervention dictionary, not from GP prediction. This fallback is only safe because `do_calculus.py` assigns source node values directly from the intervention dict and never calls `predict_child` for them — but if the call order ever changes, this would silently produce `mean=0.0` for every source node.
- **Recommended Fix:** Add a defensive warning: `warnings.warn("predict_child called with no parents — returning base prior. This should only happen for source nodes.")`

---

## File 3: `python-engine/services/layer2/do_calculus.py`

**Status: 6 Issues Found**

---

### Issue 3.1 (FIXED)
- **File Path:** `python-engine/services/layer2/do_calculus.py`
- **Line Number(s):** 76
- **Severity:** Medium
- **Issue Description:** `queue.pop(0)` on a Python `list` is **O(n)** per pop because every element must shift left. In Kahn's algorithm this makes the topological sort **O(V × E)** instead of the optimal **O(V + E)**. For small graphs (5–10 nodes) this is negligible, but if a user uploads a large causal network (100+ nodes), the quadratic time complexity will cause noticeable latency on every simulation call — and this function is invoked once per heatmap grid point (up to `resolution²` times = 10,000 calls at `resolution=100`).
- **Recommended Fix:** Replace `queue = [...]` + `queue.pop(0)` with `from collections import deque` + `queue = deque(...)` + `queue.popleft()` for O(1) dequeue.

---

### Issue 3.2 (FIXED)
- **File Path:** `python-engine/services/layer2/do_calculus.py`
- **Line Number(s):** 78–82
- **Severity:** Medium
- **Issue Description:** The inner loop on lines 78–82 scans **all active edges** for every node popped from the queue to find which edges originate from the current node. This is a full linear scan of all edges on every pop, making it **O(V × E)**. The adjacency list `incoming_edges` was already built (line 66–68), but a corresponding **outgoing** adjacency list was not built — so the code falls back to a brute-force search.
- **Recommended Fix:** Build an outgoing adjacency map alongside `incoming_edges`:
  ```python
  outgoing_edges: Dict[str, List[str]] = {node: [] for node in nodes}
  for edge in active_edges:
      outgoing_edges[edge.source].append(edge.target)
  ```
  Then replace the inner loop with: `for child in outgoing_edges[n]:`.

---

### Issue 3.3 (FIXED)
- **File Path:** `python-engine/services/layer2/do_calculus.py`
- **Line Number(s):** 109
- **Severity:** Medium
- **Issue Description:** `import warnings` is placed **inside the for-loop body** (line 109, inside the `else` branch on line 107). Python's `import` statement is idempotent and cached after first use, so this doesn't cause a performance crash — but it is a code smell. The `warnings` module should be imported at the top of the file alongside the other imports (line 1–3). Placing imports inside loops is generally considered bad practice and can confuse linters and static analysis tools.
- **Recommended Fix:** Move `import warnings` to the top of the file (line 2) and remove line 109.

---

### Issue 3.4 (FIXED)
- **File Path:** `python-engine/services/layer2/do_calculus.py`
- **Line Number(s):** 118–123
- **Severity:** Medium
- **Issue Description:** If a non-intervened node has incoming edges but **all** its parents were excluded by the orphan warning (line 107), then `parent_preds` will be empty, and the `if parent_preds:` guard on line 118 will skip it. This node receives **no prediction at all** — it is silently omitted from `predictions`. Any downstream node depending on it will also lose its parent, cascading into more orphan warnings. The returned `SimulationStepOutput.predictions` will be missing entries, which will cause `KeyError` or fallback-to-default behavior in `heatmap.py` (line 137) and `unexplored_zone_finder.py`.
- **Recommended Fix:** When `parent_preds` is empty after filtering, assign a high-uncertainty default: `predictions[node] = GaussianPrediction(mean=0.0, std_dev=1.0)` and emit a warning explaining that the node's prediction is unreliable.

---

### Issue 3.5 (FIXED)
- **File Path:** `python-engine/services/layer2/do_calculus.py`
- **Line Number(s):** 57–60
- **Severity:** Low
- **Issue Description:** Intervention values have `std_dev=0.0` (line 58), which is correct (we know the exact forced value). However, if an intervention node name is **not** in the `nodes` list, it is silently added to `predictions` but never validated. For example, `interventions={"typo_node": 50.0}` would be accepted, stored, but never used in propagation — giving the caller a false sense that it was applied.
- **Recommended Fix:** Add a guard at the start of `simulate()`: `for node in interventions: if node not in node_set: raise ValueError(f"Intervention node '{node}' is not in the nodes list.")`

---

### Issue 3.6 (DEFERRED - Enhancement)
- **File Path:** `python-engine/services/layer2/do_calculus.py`
- **Line Number(s):** 19–20
- **Severity:** Low
- **Issue Description:** Every call to `DoCalculusSimulator()` creates a new `GPEngine` instance. In `heatmap.py` and the router, a new `DoCalculusSimulator` is created on every API request (not cached). While the current mock GP is stateless, a real GP fitted on training data would need to load model weights each time — making per-request instantiation expensive.
- **Recommended Fix:** For now this is acceptable since the GP is a mock. When replacing with a real GP, the simulator should be a singleton or accept a pre-fitted GP instance via dependency injection.

---

## File 4: `python-engine/services/layer2/bayesian_optimizer.py`

**Status: 6 Issues Found**

---

### Issue 4.1 (DEFERRED - Architectural Redesign)
- **File Path:** `python-engine/services/layer2/bayesian_optimizer.py`
- **Line Number(s):** 5–7
- **Severity:** Critical
- **Issue Description:** The entire file is a **mock/placeholder**. Lines 5–7 contain a `TODO: REPLACE WITH REAL EI` comment explicitly stating this is not real optimization. The "Bayesian Optimizer" does not compute Expected Improvement (EI), does not fit a surrogate model, and does not balance exploration vs. exploitation. It simply returns the historically best known values (exploitation only) or the center of the domain (when there's no history). **There is no actual Bayesian optimization happening anywhere in the agent loop.**
- **Recommended Fix:** Replace with a proper Expected Improvement calculation using BoTorch or a custom implementation: `EI = (predicted_mean - best_known) * Phi(Z) + predicted_std * phi(Z)`. The `get_base_point` signature must be preserved.

---

### Issue 4.2 (FIXED)
- **File Path:** `python-engine/services/layer2/bayesian_optimizer.py`
- **Line Number(s):** 100–126
- **Severity:** Medium
- **Issue Description:** `get_seed_points()` is defined but **never called** anywhere in the codebase. It is dead code. The router's `run_round` endpoint calls `get_base_point()` directly — it never invokes the 5-seed initial sweep. This means the agent loop starts from a single center point on round 1 instead of the 5-point spread documented in `read.MD`. The initial GP surface has only one data point, making all early agent proposals nearly random.
- **Recommended Fix:** The router's `run_round` endpoint (or the frontend hook) should call `get_seed_points()` for the first 5 rounds to build the initial GP surface before switching to `get_base_point()` for subsequent rounds.

---

### Issue 4.3 (FIXED)
- **File Path:** `python-engine/services/layer2/bayesian_optimizer.py`
- **Line Number(s):** 117–124
- **Severity:** Medium
- **Issue Description:** `get_seed_points()` generates all 5 seeds along the **same diagonal** of the parameter space. For multi-variable domains (e.g., `temperature: 60–100` and `compound: 0–1`), point 0 is `{temp=60, compound=0}`, point 2 is `{temp=80, compound=0.5}`, point 4 is `{temp=100, compound=1.0}`. All 5 points lie on a single line from the bottom-left to the top-right corner. The entire left-top and right-bottom quadrants are completely unexplored. A proper space-filling design (Latin Hypercube Sampling or Sobol sequences) would cover the full parameter space much more efficiently.
- **Recommended Fix:** Replace linear interpolation with Latin Hypercube Sampling (LHS) or Sobol sequences for multi-variable coverage. For 2 variables and 5 points, LHS guarantees coverage of all quadrants.

---

### Issue 4.4 (FIXED)
- **File Path:** `python-engine/services/layer2/bayesian_optimizer.py`
- **Line Number(s):** 42
- **Severity:** Low
- **Issue Description:** The docstring on line 42 still says `{'yield': float, 'values': Dict}` — referencing the hardcoded `'yield'` key. While the actual code on line 73 correctly uses the dynamic `sink_node` parameter, the documentation is stale and misleading to developers. A maintainer reading only the docstring would assume the key is always `'yield'`.
- **Recommended Fix:** Update line 42 to: `each with {<sink_node>: float, 'values': Dict}` or `each with {sink_node: float, 'values': Dict}`.

---

### Issue 4.5 (FIXED)
- **File Path:** `python-engine/services/layer2/bayesian_optimizer.py`
- **Line Number(s):** 73
- **Severity:** Low
- **Issue Description:** `max(historical_data, key=lambda x: x.get(sink_node, 0))` defaults to `0` if the `sink_node` key is missing from a history entry. If **all** history entries lack the `sink_node` key (e.g., a schema mismatch between frontend and backend), every entry evaluates to `0`, and `max()` picks the first one arbitrarily. The caller gets a seemingly valid result with no indication that the optimization is meaningless.
- **Recommended Fix:** After computing `best_past`, check if `best_past.get(sink_node)` is `None`. If so, emit a `UserWarning` that no historical entry contained the expected sink node key.

---

### Issue 4.6 (FIXED)
- **File Path:** `python-engine/services/layer2/bayesian_optimizer.py`
- **Line Number(s):** 36
- **Severity:** Low
- **Issue Description:** `sink_node` has a default value of `"yield"` (line 36). While this is now a configurable parameter rather than hardcoded logic, the **default** still assumes the output variable is named `"yield"`. If a caller forgets to pass `sink_node`, the optimizer silently falls back to looking for `"yield"` in the history — which may not exist, triggering the silent `0` fallback in Issue 4.5.
- **Recommended Fix:** Consider making `sink_node` required (no default) to force callers to explicitly specify it, or change the default to `None` and auto-detect from graph topology like `heatmap.py` does.

---

## File 5: `python-engine/services/layer2/agent_explorer.py`

**Status: 4 Issues Found**

---

### Issue 5.1 (DEFERRED - Agent Strategy Redesign)
- **File Path:** `python-engine/services/layer2/agent_explorer.py`
- **Line Number(s):** 69–80
- **Severity:** Medium
- **Issue Description:** The Explorer always proposes **exactly one boundary value** per variable — whichever is farthest from the base point. Across all 30 rounds of the agent loop, the Explorer will keep proposing the **same boundary** for each variable as long as the base point stays on the same side of center. There is no exploration progression or memory — the Explorer never shifts to the opposite boundary after the first one has been tested. This makes it a one-shot agent that wastes 29 rounds repeating the same proposal.
- **Recommended Fix:** Add round-awareness or history tracking: after a boundary has been tested once, switch to the other boundary, then start testing intermediate points. Alternatively, accept a `round_number` parameter and alternate boundaries on odd/even rounds.

---

### Issue 5.2 (FIXED)
- **File Path:** `python-engine/services/layer2/agent_explorer.py`
- **Line Number(s):** 52
- **Severity:** Medium
- **Issue Description:** The Explorer iterates over `base_point.items()` — which only contains variables present in the Bayesian Optimizer's output. If `domain_config` has **more** variables than `base_point` (e.g., the optimizer returned an empty dict due to an earlier warning), the Explorer will never propose values for those variables. It only explores what the optimizer already knows about, defeating its purpose as the "boundary seeker" for the full parameter space.
- **Recommended Fix:** Iterate over `domain_config.items()` instead (or the union of both), using `base_point.get(node, (space.min + space.max) / 2)` as the fallback value when a node isn't in the base point.

---

### Issue 5.3 (FIXED)
- **File Path:** `python-engine/services/layer2/agent_explorer.py`
- **Line Number(s):** 66–67
- **Severity:** Low
- **Issue Description:** `abs(val - space.min)` and `abs(val - space.max)` use `abs()`, which is redundant when the value is guaranteed to be within bounds (clamped by the optimizer on line 79 of `bayesian_optimizer.py`). While not a bug, it masks the assumption that `val` is always within `[space.min, space.max]`. If `val` is outside bounds (e.g., from a history entry with different domain config), the `abs()` hides the out-of-bounds condition rather than catching it.
- **Recommended Fix:** Add a guard before the distance calculation: `if val < space.min or val > space.max: warnings.warn(...)`. The `abs()` calls can remain for safety.

---

### Issue 5.4 (FIXED)
- **File Path:** `python-engine/services/layer2/agent_explorer.py`
- **Line Number(s):** 43–47
- **Severity:** Low
- **Issue Description:** When `base_point` is empty, the Explorer returns `proposed_values={}`. The router on line 90 of `routers/layer2.py` then passes this empty dict to `simulator.simulate()` as interventions — which means **no source nodes are intervened on**, and every node gets a default or propagated prediction. This is technically valid but semantically useless — the simulation result is meaningless because no experiment was proposed. The Explorer's round effectively counts toward the 30-round limit while contributing zero information.
- **Recommended Fix:** The router should skip agents that return empty `proposed_values` instead of simulating them. Alternatively, the Explorer should fall back to domain center points instead of an empty dict.

---

## File 6: `python-engine/services/layer2/agent_exploiter.py`

**Status: 5 Issues Found**

---

### Issue 6.1 (DEFERRED - Agent Strategy Redesign)
- **File Path:** `python-engine/services/layer2/agent_exploiter.py`
- **Line Number(s):** 85–100
- **Severity:** Medium
- **Issue Description:** The nudge direction selection is deterministic and **never changes between rounds**. Given the same `best_val` and `space`, the Exploiter will always nudge in the **same direction** (whichever side has more room). Since the mock GP always returns the same prediction for the same inputs, the best historical value never changes — so the Exploiter proposes the exact same values for all 30 rounds. There is no gradient descent, no adaptive step size, and no alternation. The agent converges after one round and then wastes 29 identical proposals.
- **Recommended Fix:** Implement adaptive nudging: increase `nudge_pct` progressively per round (e.g., `nudge_pct = 0.01 * round_number`), or alternate between up and down nudges on successive rounds. Accept `round_number` as a parameter to enable this.

---

### Issue 6.2 (FIXED)
- **File Path:** `python-engine/services/layer2/agent_exploiter.py`
- **Line Number(s):** 101–104
- **Severity:** Medium
- **Issue Description:** The "both out of bounds" branch on line 101 means the domain width is **smaller than the nudge size in both directions**. This happens when `nudge_size > (space.max - best_val)` AND `nudge_size > (best_val - space.min)` — i.e., the domain is extremely narrow relative to the nudge. In this case the Exploiter gives up and returns `best_val` unchanged. However, the check is actually **impossible** for in-bounds values: if `best_val` is within `[min, max]`, then `up_val <= max` OR `down_val >= min` must be true (since nudge = 1% of width). This branch is dead code for any valid in-bounds `best_val`.
- **Recommended Fix:** Either remove this dead branch with a comment explaining why it's unreachable, or add a guard that explicitly validates `best_val` is within bounds before nudging (to catch the edge case where history values drift outside the current domain config).

---

### Issue 6.3 (FIXED)
- **File Path:** `python-engine/services/layer2/agent_exploiter.py`
- **Line Number(s):** 69
- **Severity:** Medium
- **Issue Description:** Same as Issue 4.5 — `max(historical_data, key=lambda x: x.get(sink_node, 0))` silently defaults to `0` when the sink node key is missing. If all history entries use a different key name (schema mismatch), the Exploiter picks the first entry arbitrarily and refines around meaningless values with no warning.
- **Recommended Fix:** After computing `best_past`, validate `best_past.get(sink_node) is not None`. If it is `None`, emit a `UserWarning` that no historical entry contained the expected sink node.

---

### Issue 6.4 (FIXED)
- **File Path:** `python-engine/services/layer2/agent_exploiter.py`
- **Line Number(s):** 25
- **Severity:** Low
- **Issue Description:** `sink_node` default is `"yield"` — same issue as `bayesian_optimizer.py` (Issue 4.6). The default assumes the output variable is named `"yield"`. If the caller forgets to pass it, the Exploiter silently searches for a non-existent key.
- **Recommended Fix:** Change default to `None` and auto-detect from graph topology, or make it a required parameter with no default.

---

### Issue 6.5 (FIXED)
- **File Path:** `python-engine/services/layer2/agent_exploiter.py`
- **Line Number(s):** 26
- **Severity:** Low
- **Issue Description:** `nudge_pct` has no validation. Negative values (e.g., `nudge_pct=-0.5`) would reverse the nudge direction silently (nudge "up" actually goes down). A value of `0.0` produces zero nudge size, making the Exploiter always return `best_val` unchanged. Values > 1.0 would produce nudges larger than the domain width, causing both directions to go out of bounds and hitting the dead code on line 101.
- **Recommended Fix:** Add a guard: `if not (0.0 < nudge_pct <= 1.0): raise ValueError(...)`

---

## File 7: `python-engine/services/layer2/agent_contrarian.py`

**Status: 5 Issues Found**

---

### Issue 7.1 (FIXED)
- **File Path:** `python-engine/services/layer2/agent_contrarian.py`
- **Line Number(s):** 1, 40–41
- **Severity:** Medium
- **Issue Description:** `import random` is at the top of the file and `random.seed(seed)` is called on line 41, but **`random` is never actually used for any randomized decision**. The original agent used `random.choice([space.min, space.max])` — but the refactored version replaced that with deterministic anti-duplication logic (lines 76–97). The `random` import and the `seed` parameter are now **dead code**. The `random.seed()` call on line 41 is a global side-effect: it resets the random seed for the **entire Python process**, which could silently affect other modules that depend on `random` (e.g., data augmentation, sampling in Layer 3).
- **Recommended Fix:** Remove `import random`, remove the `seed` parameter from the method signature, and remove lines 40–41. The agent is now fully deterministic and does not need randomness.

---

### Issue 7.2 (DEFERRED - Agent Strategy Redesign)
- **File Path:** `python-engine/services/layer2/agent_contrarian.py`
- **Line Number(s):** 76–97
- **Severity:** Medium
- **Issue Description:** The Contrarian always proposes the **exact opposite boundary** from the Explorer — by design. This means the Contrarian and Explorer together always test `{min, max}` for every variable. While this guarantees coverage of both extremes, it also means the Contrarian provides **zero independent value** — its behavior is entirely determined by the Explorer's behavior. It is not actually "contrarian" (challenging assumptions) — it is simply "the other boundary." A truly contrarian agent should challenge the *direction* of the Exploiter's nudge or propose unexpected intermediate values, not just mirror the Explorer.
- **Recommended Fix:** Consider making the Contrarian challenge the *Exploiter's* proposal instead: if the Exploiter nudges temperature up, the Contrarian nudges it down. This would create three genuinely different strategies (explore boundaries, refine peak, challenge refinement) instead of two (explore boundary A, explore boundary B, refine peak).

---

### Issue 7.3 (DEFERRED - Agent Strategy Redesign)
- **File Path:** `python-engine/services/layer2/agent_contrarian.py`
- **Line Number(s):** 80–97
- **Severity:** Medium
- **Issue Description:** Same as Explorer Issue 5.1 — the Contrarian has **no memory or round-awareness**. Given the same `base_point` and `domain_config`, it proposes the exact same boundary values for all 30 rounds. Since the base point rarely shifts (because the mock GP always returns the same predictions), the Contrarian wastes 29 rounds with identical proposals.
- **Recommended Fix:** Add round-awareness or a history parameter. After both boundaries have been tested, start proposing values at 25%, 33%, or other strategic intermediate positions.

---

### Issue 7.4 (FIXED)
- **File Path:** `python-engine/services/layer2/agent_contrarian.py`
- **Line Number(s):** 59
- **Severity:** Low
- **Issue Description:** Same as Explorer Issue 5.2 — the Contrarian iterates over `base_point.items()`, not `domain_config.items()`. If the optimizer returns fewer variables than the domain config contains, the Contrarian will never challenge those missing variables.
- **Recommended Fix:** Iterate over `domain_config.items()` instead, using `base_point.get(node, (space.min + space.max) / 2)` as fallback.

---

### Issue 7.5 (FIXED)
- **File Path:** `python-engine/services/layer2/agent_contrarian.py`
- **Line Number(s):** 50–54
- **Severity:** Low
- **Issue Description:** Same as Explorer Issue 5.4 — empty `base_point` returns `proposed_values={}`, which the router simulates as a zero-intervention experiment. This counts toward the 30-round limit while contributing no useful information.
- **Recommended Fix:** Fall back to domain boundary values instead of returning an empty dict, or have the router skip agents with empty proposals.

---

## File 8: `python-engine/services/layer2/heatmap.py`

**Status: 6 Issues Found**

---

### Issue 8.1 (DEFERRED - Architectural Optimization)
- **File Path:** `python-engine/services/layer2/heatmap.py`
- **Line Number(s):** 129–148
- **Severity:** Critical
- **Issue Description:** The heatmap grid loop calls `self.simulator.simulate()` once per grid point. For a `resolution=10` 2D grid, that is **100 simulation calls**. For `resolution=50`, that is **2,500 calls**. Each call instantiates Kahn's algorithm, builds adjacency lists, and runs forward propagation. There is **no caching, no batching, and no parallelism**. The endpoint is synchronous (despite being `async def` in the router) — it blocks the FastAPI event loop for the entire duration. At `resolution=100`, the heatmap generation produces **10,000 sequential simulation calls**, which will cause the API to hang for seconds or even minutes depending on graph size.
- **Recommended Fix:** Vectorize the simulation by pre-computing the topological sort once and then running only the forward-propagation step per grid point. Alternatively, compute all grid interventions in a batch and parallelize using `asyncio.gather()` or `concurrent.futures.ThreadPoolExecutor`.

---

### Issue 8.2 (DEFERRED - Feature Enhancement)
- **File Path:** `python-engine/services/layer2/heatmap.py`
- **Line Number(s):** 64–65
- **Severity:** Medium
- **Issue Description:** Axis selection always picks `source_nodes[0]` for X and `source_nodes[1]` for Y, based on the **order nodes appear in `payload.nodes`**. This order is arbitrary and depends on how the frontend serialized the node list. Two identical graphs with the same nodes in different order will produce different heatmaps with swapped axes. The user has no control over which variables are used as axes.
- **Recommended Fix:** Add optional `x_axis` and `y_axis` fields to `HeatmapInput` so the frontend can explicitly select axes. Fall back to auto-detection only when these are not provided.

---

### Issue 8.3 (FIXED)
- **File Path:** `python-engine/services/layer2/heatmap.py`
- **Line Number(s):** 154
- **Severity:** Medium
- **Issue Description:** Cliff detection uses **population variance** (`/ len(z_vals)`) instead of **sample variance** (`/ (len(z_vals) - 1)`). For small grids (resolution=2, giving 4 points), this underestimates the true variance by up to 25%, which shifts the cliff threshold upward and causes fewer cliffs to be flagged. At `resolution=2`, only 1 degree of freedom exists — population variance produces an unreliable threshold.
- **Recommended Fix:** Use Bessel's correction: `variance = sum(...) / (len(z_vals) - 1)` for sample variance. Guard against `len(z_vals) == 1` (would cause division by zero).

---

### Issue 8.4 (FIXED)
- **File Path:** `python-engine/services/layer2/heatmap.py`
- **Line Number(s):** 150–158
- **Severity:** Medium
- **Issue Description:** If **all** z-values are identical (e.g., a flat response surface), `std_z = 0.0` and `cliff_threshold = mean_z - 0.0 = mean_z`. The condition `pt.z_val < cliff_threshold` is `pt.z_val < mean_z`, which is **False** for all points (since all equal mean). This is technically correct (no cliffs in a flat surface), but the **reason** is fragile: if even one value differs by floating-point epsilon, some points may be flagged as cliffs. There's no explicit handling of the zero-variance edge case.
- **Recommended Fix:** Add a guard: `if std_z < 1e-9: for pt in data_points: pt.is_cliff = False` — explicitly skip cliff detection when variance is negligible.

---

### Issue 8.5 (FIXED)
- **File Path:** `python-engine/services/layer2/heatmap.py`
- **Line Number(s):** 111
- **Severity:** Low
- **Issue Description:** Same systemic issue as Issues 4.5 and 6.3 — `max(historical_data, key=lambda x: x.get(sink_node_name, 0))` silently defaults to `0` when the sink node key is missing from history entries. The hold-steady logic then uses values from an arbitrarily selected "best" run, which may not actually be the best.
- **Recommended Fix:** Validate that at least one history entry contains `sink_node_name` as a key. If none do, emit a `UserWarning` and fall back to domain center values for hold-steady nodes.

---

### Issue 8.6 (FIXED)
- **File Path:** `python-engine/services/layer2/heatmap.py`
- **Line Number(s):** 2
- **Severity:** Low
- **Issue Description:** `Optional` is imported from `typing` on line 2 but **never used** anywhere in the file. All optional fields are handled by the Pydantic schema layer (`HeatmapInput`), not in the generator class itself. This is unused dead import.
- **Recommended Fix:** Remove `Optional` from the import line: `from typing import List`

---

## File 9: `python-engine/services/layer2/unexplored_zone_finder.py`

**Status: 6 Issues Found**

---

### Issue 9.1 (DEFERRED - Logic Redesign)
- **File Path:** `python-engine/services/layer2/unexplored_zone_finder.py`
- **Line Number(s):** 119–124
- **Severity:** Medium
- **Issue Description:** Gap detection only checks the **bottom** (below tested_min) and **top** (above tested_max) of the tested range. It completely misses **internal gaps** — large untested regions within the tested range. For example, if a user tested `temperature=60` and `temperature=100` but never tested anything between 61–99, the zone finder reports zero gaps because `tested_min=60` and `tested_max=100` cover the entire domain. The 39-unit gap in the middle is invisible. This is a significant blind spot for sparse experimental data.
- **Recommended Fix:** Implement internal gap detection: sort all tested values for each node, compute intervals between consecutive tested points, and flag any interval wider than `gap_size_required` as an unexplored zone.

---

### Issue 9.2 (DEFERRED - Feature Enhancement)
- **File Path:** `python-engine/services/layer2/unexplored_zone_finder.py`
- **Line Number(s):** 127–128
- **Severity:** Medium
- **Issue Description:** The zone finder only simulates the **midpoint** of each gap. A single midpoint prediction gives no information about the shape of the response surface within the gap — it could be a peak, a valley, or a cliff, and a single point cannot distinguish between them. The user-facing message on line 158 says "simulation predicts yield may reach X%" — but this is the prediction at one arbitrary point, not a representative summary of the entire gap.
- **Recommended Fix:** Simulate 3–5 points within each gap (e.g., 25%, 50%, 75%) and report the range of predictions (min–max) and average uncertainty. This gives the user a much more informative picture of what the gap might contain.

---

### Issue 9.3 (FIXED)
- **File Path:** `python-engine/services/layer2/unexplored_zone_finder.py`
- **Line Number(s):** 156–161
- **Severity:** Medium
- **Issue Description:** The user-facing message hardcodes the `%` symbol (line 158: `{round(pred.mean, 1)}%`). This assumes the sink node is a percentage-based quantity (like yield). If the sink node is `reaction_rate` (measured in mol/s) or `temperature_delta` (measured in °C), the message says "reaction_rate may reach 45.3%" — which is misleading. The `%` symbol should be configurable or omitted.
- **Recommended Fix:** Remove the `%` symbols from the message template, or add a `unit` field to the schema so the frontend can format units appropriately.

---

### Issue 9.4 (FIXED)
- **File Path:** `python-engine/services/layer2/unexplored_zone_finder.py`
- **Line Number(s):** 141–142
- **Severity:** Medium
- **Issue Description:** When a source node has no domain config AND no best historical value, the fallback is `best_past.get(other_node, 0.0)` — a hardcoded `0.0`. For variables like temperature (range 60–100), using `0.0` as the hold-steady value is far outside the domain and will produce wildly incorrect simulation results. This fallback path is reached when: (1) domain_config is missing for a non-axis source node AND (2) there's no history. Both conditions can occur simultaneously on the first run.
- **Recommended Fix:** This branch should either raise a `ValueError` (since we can't produce a meaningful simulation without knowing the domain) or emit a prominent warning. Using `0.0` as a default is dangerous.

---

### Issue 9.5 (FIXED)
- **File Path:** `python-engine/services/layer2/unexplored_zone_finder.py`
- **Line Number(s):** 84
- **Severity:** Low
- **Issue Description:** Same systemic issue as Issues 4.5, 6.3, and 8.5 — `max(historical_data, key=lambda x: x.get(sink_node, 0))` silently defaults to `0` when the sink node key is missing. This affects both the hold-steady values and the "best past" baseline.
- **Recommended Fix:** Validate that at least one history entry contains the `sink_node` key. Emit a warning if none do.

---

### Issue 9.6 (DEFERRED - DRY Refactor)
- **File Path:** `python-engine/services/layer2/unexplored_zone_finder.py`
- **Line Number(s):** 28–41
- **Severity:** Low
- **Issue Description:** The source-node detection logic (lines 28–41) and sink-node auto-detection logic (lines 49–71) are **duplicated** across `heatmap.py` (lines 41–54, 79–102) and `routers/layer2.py` (lines 83–91). All three files independently compute in-degrees, out-degrees, and classify nodes. This is a DRY violation — if the node classification logic changes (e.g., adding support for bidirectional edges), it must be updated in three places.
- **Recommended Fix:** Extract the topology analysis into a shared utility function (e.g., `services/layer2/graph_utils.py`) with methods like `get_source_nodes(nodes, edges)`, `get_sink_nodes(nodes, edges)`, and `auto_detect_sink(nodes, edges)`. All three files should call this utility instead of reimplementing the logic.

---

## File 10: `python-engine/services/layer2/cliff_detector.py`

**Status: 2 Issues Found**

---

### Issue 10.1 (FIXED)
- **File Path:** `python-engine/services/layer2/cliff_detector.py`
- **Line Number(s):** 1
- **Severity:** Critical
- **Issue Description:** The file is **completely empty** (0 bytes, 1 blank line). It is listed in the mandatory folder structure (`rules/folder-structure.md`, line 57) as a required Layer 2 file, indicating it was planned as a dedicated cliff detection module. Currently, cliff detection logic is inlined inside `heatmap.py` (lines 150–158) using a simple z-score threshold. This file was never implemented. It is an **unfinished placeholder** committed to the repository.
- **Recommended Fix:** Either (A) implement the dedicated `CliffDetector` class that encapsulates the cliff detection logic currently inlined in `heatmap.py`, making it reusable and configurable — or (B) if cliff detection is intentionally kept inside `heatmap.py`, remove `cliff_detector.py` from the folder structure rules and delete the empty file to avoid confusion.

---

### Issue 10.2 (FIXED)
- **File Path:** `python-engine/services/layer2/cliff_detector.py`
- **Line Number(s):** N/A
- **Severity:** Medium
- **Issue Description:** The file is **not imported anywhere** in the codebase (confirmed via grep search). No router, service, or test references it. It is completely disconnected from the application flow. Its presence in the repository creates a false impression that cliff detection is a standalone, tested module — when in reality it is non-existent and the actual cliff logic lives in `heatmap.py` with no separation of concerns.
- **Recommended Fix:** If implementing: extract the cliff detection from `heatmap.py` lines 150–158 into a `CliffDetector` class with configurable threshold, gradient-based detection (not just z-score), and per-point cliff severity scoring. If removing: delete the file and update `folder-structure.md`.

---

## File 11: `python-engine/routers/layer2.py`

**Status: 3 Issues Found**

---

### Issue 11.1 (FIXED)
- **File Path:** `python-engine/routers/layer2.py`
- **Line Number(s):** 145–148, 150-158
- **Severity:** Critical
- **Issue Description:** `generate_heatmap` and `find_unexplored_zones` are defined as `async def` endpoints, but they call purely synchronous, CPU-heavy blocking functions (`generator.generate()` and `finder.find_zones()`). In FastAPI, an `async def` endpoint runs on the main event loop. If it blocks for CPU-bound work (like 10,000 simulations in the heatmap), the **entire API server hangs**. No other concurrent requests can be processed.
- **Recommended Fix:** Change the endpoint definitions to standard synchronous functions (remove `async`): `def generate_heatmap(...)`. FastAPI will automatically run them in a separate threadpool, keeping the main event loop responsive.

---

### Issue 11.2 (FIXED)
- **File Path:** `python-engine/routers/layer2.py`
- **Line Number(s):** 101–106
- **Severity:** Medium
- **Issue Description:** `simulate_proposal` is declared as an `async def`, but it calls a synchronous blocking function `simulator.simulate()` without using an executor. Calling `await asyncio.gather(*sim_tasks)` on these functions does **not** make them run in parallel — it runs them sequentially on the main thread and blocks the event loop. This gives the illusion of concurrency while actually degrading performance.
- **Recommended Fix:** Use `asyncio.to_thread` to run the CPU-bound simulation in a background thread:
  ```python
  async def simulate_proposal(prop):
      res = await asyncio.to_thread(simulator.simulate, payload.nodes, payload.edges, prop.proposed_values)
      return prop, res
  ```

---

### Issue 11.3 (FIXED)
- **File Path:** `python-engine/routers/layer2.py`
- **Line Number(s):** 86–91
- **Severity:** Low
- **Issue Description:** The auto-detect sink logic in the router only checks `out_degrees.get(n, 0) == 0`. It does **not** check if the node has incoming edges (`in_degrees > 0`), unlike the identical logic in `heatmap.py` and `unexplored_zone_finder.py`. If a user uploads a graph with an isolated, disconnected node, the router will select it as a sink node candidate, which is semantically incorrect (an outcome must be caused by something).
- **Recommended Fix:** Match the logic from the other files: `if out_degrees.get(n, 0) == 0 and in_degrees.get(n, 0) > 0:`. Better yet, apply the fix from Issue 9.6 and extract this to a shared utility to prevent logic drift.
