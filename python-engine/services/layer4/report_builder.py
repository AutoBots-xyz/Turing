"""
services/layer4/report_builder.py — Final Report Generator

Generates a 5-section FinalReport matching the README specification:
  Section 1 — THE MECHANISM    (cause chain + confidence badges)
  Section 2 — THE EXPERIMENT   (exact next experiment to run)
  Section 3 — WHO SOLVED THIS  (top 3 cross-domain bridge analogies)
  Section 4 — WARNINGS         (contradictions + low data flags)
  Section 5 — NEXT 3 ACTIONS   (ranked, specific, actionable)
"""
import json
import os

from schemas.report import FinalReport
from schemas.layer3 import Step14Response, RankedBridge
from services.layer4.context_packager import pack_bridges_into_context


def _get_llm_client():
    """Returns LiteLLM client if any supported API KEY is set, else None.
    
    Supported providers: Anthropic, OpenAI, NVIDIA NIM, Groq.
    LiteLLM routes automatically based on the model string in DEFAULT_LLM_MODEL.
    """
    try:
        import litellm
        supported_keys = [
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "NVIDIA_API_KEY",
            "NVIDIA_NIM_API_KEY",
            "GROQ_API_KEY",
        ]
        found = {k: os.getenv(k) for k in supported_keys if os.getenv(k)}
        if not found:
            raise EnvironmentError("No supported LLM API KEY found in environment")
        
        # Pass keys into litellm explicitly so it can route correctly
        for key_name, key_val in found.items():
            if key_name == "GROQ_API_KEY":
                litellm.groq_key = key_val
            elif key_name == "ANTHROPIC_API_KEY":
                litellm.anthropic_key = key_val
            elif key_name == "OPENAI_API_KEY":
                litellm.openai_key = key_val
            elif key_name in ("NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY"):
                litellm.api_key = key_val
        
        return litellm
    except (ImportError, EnvironmentError):
        return None


def _build_fallback_report(run_id: str, bridges: list, contradiction_warnings: list, confidence_disclaimer: str) -> FinalReport:
    """
    Deterministic fallback when no LLM is available.
    Produces a readable report from raw bridge data without AI generation.
    """
    if not bridges:
        return FinalReport(
            run_id=run_id,
            the_mechanism=(
                "No cross-domain bridges were found above the minimum score threshold. "
                "The causal graph was built successfully but no matching mechanisms "
                "were identified in the search corpus. "
                "❌ Low confidence — recommend broadening the search query."
            ),
            the_experiment=(
                "Configure an LLM API KEY (ANTHROPIC_API_KEY, OPENAI_API_KEY, or NVIDIA_API_KEY) "
                "to receive AI-generated experiment recommendations. "
                "In the meantime, revisit the input graph and ensure low-confidence nodes "
                "are correctly identified before rerunning."
            ),
            who_solved_this="No bridges found above the minimum isomorphism threshold.",
            warnings_and_conflicts=contradiction_warnings,
            next_3_actions=[
                "Configure an LLM API KEY to enable AI-generated recommendations.",
                "Review the causal graph for disconnected or low-confidence nodes.",
                "Broaden the search query domain and rerun Layer 3."
            ],
            top_bridges=[],
            confidence_disclaimer="Pipeline completed with 0 valid bridges. Confidence: N/A."
        )

    # Build readable mechanism from bridge data
    top = bridges[0]
    mechanism_lines = [
        f"The pipeline identified {len(bridges)} cross-domain bridge(s) for the bottleneck mechanism.",
        "",
        f"Primary mechanism candidate: {top.match.mechanism.source_result.title}",
        f"Underlying mechanism: {top.match.mechanism.source_result.underlying_mechanism}",
        "",
        "⚠️ Medium confidence — LLM API unavailable for full synthesis.",
        "Configure an API KEY for complete plain-English mechanism analysis."
    ]

    who_solved_lines = []
    evidence_labels = {0: "BRIDGE 1 — Strongest", 1: "BRIDGE 2 — Strong", 2: "BRIDGE 3 — Moderate"}
    for idx, bridge in enumerate(bridges[:3]):
        src = bridge.match.mechanism.source_result
        score_pct = int(bridge.match.isomorphism_score * 100)
        evidence = "HIGH" if bridge.scores.final_score > 0.8 else ("MEDIUM" if bridge.scores.final_score > 0.5 else "LOW")
        who_solved_lines.append(
            f"{evidence_labels.get(idx, f'BRIDGE {idx+1}')}\n"
            f"Source: {src.title}\n"
            f"Match: {score_pct}% structural match\n"
            f"Evidence: {evidence}\n"
            f"Mechanism: {src.underlying_mechanism}\n"
        )

    return FinalReport(
        run_id=run_id,
        the_mechanism="\n".join(mechanism_lines),
        the_experiment=(
            "LLM API KEY not configured — AI experiment recommendations unavailable. "
            "Based on the bridge data, the highest-priority experiment is to validate the "
            f"'{bridges[0].match.mechanism.source_result.title}' mechanism in your domain context."
        ),
        who_solved_this="\n\n".join(who_solved_lines),
        warnings_and_conflicts=contradiction_warnings,
        next_3_actions=[
            f"Validate the top bridge: {bridges[0].match.mechanism.source_result.title}",
            "Configure an LLM API KEY for full AI-synthesized experiment design.",
            "Review contradiction warnings (if any) before trusting bridge solutions."
        ],
        top_bridges=bridges,
        confidence_disclaimer=confidence_disclaimer
    )


async def build_report(run_id: str, step14_response: Step14Response) -> FinalReport:
    """
    Layer 4 Final Step: Generates the 5-section human-readable FinalReport.

    Strategy:
    1. Collect contradiction warnings from all bridge metadata.
    2. Build a rich context block from the Top 3 bridges.
    3. Call the LLM with an explicit, numbered prompt matching the README's 5-section spec.
       The prompt forces all output to be flat strings — never nested dicts.
    4. Parse the JSON response safely, with per-field fallbacks if the LLM misbehaves.
    5. Fall back to deterministic template if LLM is unavailable.
    """
    bridges = step14_response.top_bridges

    # ── Collect contradiction warnings (always, regardless of LLM) ──────────
    contradiction_warnings = []
    for bridge in bridges:
        analysis = bridge.match.mechanism.source_result.contradiction_analysis
        if analysis and analysis.conflict_detected:
            contradiction_warnings.append(
                f"⚡ CONTRADICTION in '{bridge.match.mechanism.source_result.title}': "
                f"{analysis.nature_of_conflict}"
            )

    # ── Compute confidence disclaimer ────────────────────────────────────────
    if bridges:
        avg_score = sum(b.scores.final_score for b in bridges) / len(bridges)
        confidence_disclaimer = (
            f"Based on {len(bridges)} cross-domain bridge(s) with average validity score "
            f"{avg_score:.0%}. AI-generated — validate with domain experts before implementation."
        )
    else:
        confidence_disclaimer = "No bridges found. Confidence: N/A."

    if contradiction_warnings:
        confidence_disclaimer += (
            f" ⚡ {len(contradiction_warnings)} contradiction(s) detected — see Section 4."
        )

    # ── LLM unavailable → graceful fallback ─────────────────────────────────
    client = _get_llm_client()
    if not client:
        return _build_fallback_report(run_id, bridges, contradiction_warnings, confidence_disclaimer)

    # ── Build rich context for the LLM ──────────────────────────────────────
    if bridges:
        context = pack_bridges_into_context(
            bridges=bridges,
            user_query=bridges[0].match.mechanism.source_result.merged_summary[:300]
        )
    else:
        context = "No cross-domain bridges were found."

    # ── Bridge detail block for Section 3 ───────────────────────────────────
    bridge_detail_lines = []
    for idx, bridge in enumerate(bridges[:3], 1):
        src = bridge.match.mechanism.source_result
        score_pct = int(bridge.match.isomorphism_score * 100)
        evidence = "HIGHEST (production-deployed)" if bridge.scores.final_score > 0.9 else (
            "HIGH (replicated studies)" if bridge.scores.final_score > 0.75 else
            "MEDIUM (well-established)" if bridge.scores.final_score > 0.5 else "LOW"
        )
        bridge_detail_lines.append(
            f"BRIDGE {idx}: {src.title}\n"
            f"  Field: {src.sources[0].value if src.sources else 'Unknown'}\n"
            f"  Match: {score_pct}% structural isomorphism\n"
            f"  Evidence: {evidence}\n"
            f"  Mechanism: {src.underlying_mechanism}\n"
            f"  Summary: {src.merged_summary[:300]}"
        )
    bridge_details = "\n\n".join(bridge_detail_lines) if bridge_detail_lines else "No bridges available."

    # ── Craft the prompt ─────────────────────────────────────────────────────
    prompt = f"""You are a cross-domain systems analyst writing a final research report for a scientist.
You must be honest about uncertainty. Never mention algorithm names (no 'Bayesian', 'PC Algorithm', 'isomorphism').
Write as if talking to a smart researcher, not a computer scientist. Use domain vocabulary.

CONTEXT — CROSS-DOMAIN BRIDGES FOUND:
{context}

BRIDGE DETAILS:
{bridge_details}

CONTRADICTIONS DETECTED: {contradiction_warnings if contradiction_warnings else 'None'}

Write the report as a JSON object with EXACTLY these 5 keys. Every value MUST be a plain string or array of strings — NEVER a nested object or dict.

{{
  "the_mechanism": "SECTION 1 — THE MECHANISM\\n\\nPlain English explanation of what is actually causing what. Include inline confidence markers: ✅ High confidence / ⚠️ Medium confidence / ❌ Low confidence / ⚡ Contradicted — whenever stating a causal relationship. Minimum 3 paragraphs. Be specific about the bottleneck structure.",

  "the_experiment": "SECTION 2 — THE EXPERIMENT\\n\\nThe single most important next experiment the researcher should run. Include: what exactly to test, what values or conditions to use, what outcome to measure, why this resolves the most ambiguity. Be specific and actionable. One experiment, fully described.",

  "who_solved_this": "SECTION 3 — WHO ALREADY SOLVED THIS\\n\\nFor each of the top bridges, write a vivid analogy explaining how a completely different field solved the exact same structural problem. Format each bridge clearly with its source, field, match percentage, evidence level, and an explanation of how their solution maps to the researcher's domain.",

  "warnings_and_conflicts": ["⚡ CONTRADICTION: [description]", "⚠️ LOW DATA: [description]"],

  "next_3_actions": ["ACTION 1 — [most important specific action]", "ACTION 2 — [if Action 1 confirms, do this]", "ACTION 3 — [parallel track to run simultaneously]"]
}}

Output ONLY valid JSON. No markdown fences. No explanation. Every string value must be a flat string — never nest dicts inside the JSON values."""

    # ── Call the LLM ─────────────────────────────────────────────────────────
    try:
        response = client.completion(
            model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content.strip()
    except Exception as llm_err:
        return _build_fallback_report(run_id, bridges, contradiction_warnings, confidence_disclaimer)

    # ── Parse JSON response with safe per-field extraction ───────────────────
    import re
    # Strip markdown fences if the LLM adds them despite instructions
    fence_match = re.search(r'```(?:json)?\s*(.*?)```', raw, re.DOTALL)
    if fence_match:
        raw = fence_match.group(1).strip()

    # Find the outermost JSON object
    obj_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if obj_match:
        raw = obj_match.group(0)

    try:
        data = json.loads(raw)
    except Exception:
        # Complete parse failure — use raw text as mechanism, fallback rest
        return FinalReport(
            run_id=run_id,
            the_mechanism=raw[:2000],
            the_experiment="See raw output above.",
            who_solved_this="JSON parse error — see raw output.",
            warnings_and_conflicts=contradiction_warnings,
            next_3_actions=["Review raw LLM output.", "Retry with a different model.", "Check API key configuration."],
            top_bridges=bridges,
            confidence_disclaimer=confidence_disclaimer
        )

    def safe_str(val, fallback: str) -> str:
        """Safely coerce a field to str — handles nested dicts from misbehaving LLMs."""
        if isinstance(val, str):
            return val
        if isinstance(val, dict):
            # Flatten dict to readable text
            return "\n".join(f"{k}: {v}" for k, v in val.items())
        if val is None:
            return fallback
        return str(val)

    def safe_list(val, fallback: list) -> list:
        """Safely coerce a field to list[str]."""
        if isinstance(val, list):
            return [safe_str(item, "") for item in val if item]
        if isinstance(val, str):
            return [val]
        return fallback

    return FinalReport(
        run_id=run_id,
        the_mechanism=safe_str(data.get("the_mechanism"), "Mechanism analysis unavailable."),
        the_experiment=safe_str(data.get("the_experiment"), "Experiment design unavailable."),
        who_solved_this=safe_str(data.get("who_solved_this"), "No bridge analogies available."),
        warnings_and_conflicts=safe_list(
            data.get("warnings_and_conflicts"),
            contradiction_warnings  # always include real contradictions even if LLM omits them
        ),
        next_3_actions=safe_list(
            data.get("next_3_actions"),
            ["Review the mechanism section.", "Run the recommended experiment.", "Explore the bridge analogies."]
        ),
        top_bridges=bridges,
        confidence_disclaimer=confidence_disclaimer
    )
