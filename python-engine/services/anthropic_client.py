import os
import json
import asyncio
from typing import Optional, Tuple
from schemas.graph import CausalGraph, Node, Edge

# ---------------------------------------------------------------------------
# LLM Client Helper
# ---------------------------------------------------------------------------
def _get_llm_client():
    """
    Returns the configured LLM client via LiteLLM.
    Falls back to a mock if the API key is not configured.
    """
    try:
        import litellm
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set")
        return litellm
    except (ImportError, EnvironmentError):
        return None  # Signals mock fallback

# ---------------------------------------------------------------------------
# Function 1: generate_domain_blind_query
# Fixes Error 1: Now builds a real structured prompt and calls Claude.
# ---------------------------------------------------------------------------
def generate_domain_blind_query(node: Node, graph: CausalGraph) -> str:
    """
    Calls Claude (via LiteLLM) to convert a domain-specific node into a
    domain-blind structural query that can search any industry.
    """
    incoming = [e for e in graph.edges if e.target == node.id]
    outgoing = [e for e in graph.edges if e.source == node.id]

    prompt = (
        f"You are a cross-domain systems engineer. "
        f"A node named '{node.label}' (confidence: {node.confidence}%) exists in a causal graph.\n"
        f"It receives {len(incoming)} incoming causal edges and produces {len(outgoing)} outgoing causal edges.\n"
        f"Describe the underlying structural mechanism in one sentence using ONLY physics/math terms. "
        f"Remove all domain-specific language (biology, chemistry, software, etc.). "
        f"Example output: 'A high-variance input causes catastrophic bottleneck constriction leading to systemic output failure.'\n"
        f"Output ONLY the one-sentence description."
    )

    client = _get_llm_client()
    if client:
        response = client.completion(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        return response.choices[0].message.content.strip()

    # --- Mock fallback (only used if ANTHROPIC_API_KEY is not set) ---
    num_inputs = len(incoming)
    num_outputs = len(outgoing)
    if num_inputs >= 2 and num_outputs == 1:
        return f"{num_inputs} high-variance inputs converge on a single shared bottleneck causing systemic output failure"
    elif num_inputs == 0:
        return f"an unconstrained source node produces {num_outputs} diverging causal outputs"
    else:
        return f"a node with {num_inputs} inputs and {num_outputs} outputs mediates causal flow with {node.confidence:.0f}% confidence"


# ---------------------------------------------------------------------------
# Function 2: extract_causal_graph_from_text
# Fixes Error 2: Now sends text to Claude and parses JSON into a CausalGraph.
# ---------------------------------------------------------------------------
async def extract_causal_graph_from_text(text: str) -> CausalGraph:
    """
    Step 12 LLM call: Extracts a mini causal graph from a text summary.
    As per 'different.md' rules:
    - Nodes must be nouns.
    - Edges must be verbs (e.g., INHIBITS, ACTIVATES).
    - Confidence is scored based on the strength of the language.
    """
    prompt = (
        "You are a causal graph extractor. Read the following scientific text and extract all causal relationships.\n\n"
        f"TEXT:\n{text}\n\n"
        "Return a JSON object with this exact structure:\n"
        "{\n"
        '  "nodes": [{"id": "n1", "label": "<noun>", "confidence": <0-100>}],\n'
        '  "edges": [{"source": "n1", "target": "n2", "relation": "<VERB>", "confidence": <0-100>}]\n'
        "}\n\n"
        "Rules:\n"
        "- Nodes MUST be nouns (entities, substances, components).\n"
        "- Edge 'relation' MUST be a single uppercase verb (e.g., INHIBITS, ACTIVATES, CAUSES, PREVENTS).\n"
        "- Edge confidence: 'inhibits' → 90, 'may inhibit' → 40, 'sometimes affects' → 20.\n"
        "- Output ONLY valid JSON. No explanation."
    )

    client = _get_llm_client()
    if client:
        response = client.completion(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        nodes = [Node(id=n["id"], label=n["label"], confidence=n["confidence"]) for n in data["nodes"]]
        edges = [Edge(source=e["source"], target=e["target"], relation=e["relation"], confidence=e["confidence"]) for e in data["edges"]]
        return CausalGraph(nodes=nodes, edges=edges)

    # --- Mock fallback (only used if ANTHROPIC_API_KEY is not set) ---
    await asyncio.sleep(0.1)
    text_lower = text.lower()

    if "bypass" in text_lower and "valve" in text_lower:
        nodes = [
            Node(id="n1", label="Input Pressure",   confidence=95.0),
            Node(id="n2", label="Bottleneck",        confidence=95.0),
            Node(id="n3", label="Bypass Valve",      confidence=95.0),
            Node(id="n4", label="System Failure",    confidence=95.0),
        ]
        edges = [
            Edge(source="n1", target="n2", relation="OVERLOADS",  confidence=95.0),
            Edge(source="n3", target="n2", relation="RELIEVES",   confidence=95.0),
            Edge(source="n3", target="n4", relation="PREVENTS",   confidence=90.0),
        ]
    elif "inhibit" in text_lower or "activat" in text_lower:
        nodes = [
            Node(id="n1", label="Compound X",  confidence=88.0),
            Node(id="n2", label="Protein Y",   confidence=88.0),
            Node(id="n3", label="Pathway Z",   confidence=75.0),
        ]
        edges = [
            Edge(source="n1", target="n2", relation="INHIBITS",  confidence=90.0),
            Edge(source="n2", target="n3", relation="ACTIVATES", confidence=75.0),
        ]
    else:
        nodes = [
            Node(id="n_a", label="Primary Factor",   confidence=70.0),
            Node(id="n_b", label="Secondary Effect", confidence=65.0),
        ]
        edges = [
            Edge(source="n_a", target="n_b", relation="CAUSES", confidence=60.0),
        ]

    return CausalGraph(nodes=nodes, edges=edges)


# ---------------------------------------------------------------------------
# Function 3: evaluate_compatibility_and_transferability
# Fixes Error 3: Now sends real context to Claude instead of keyword matching.
# ---------------------------------------------------------------------------
async def evaluate_compatibility_and_transferability(
    domain_context: str, candidate_mechanism: str
) -> Tuple[float, float]:
    """
    Step 14 LLM call: Evaluates constraint compatibility and solution
    transferability by asking Claude to reason about both domains.
    Returns two floats between 0.0 and 1.0.
    """
    prompt = (
        "You are a cross-domain systems engineer.\n\n"
        f"TARGET PROBLEM (domain-blind):\n{domain_context}\n\n"
        f"CANDIDATE SOLUTION MECHANISM:\n{candidate_mechanism}\n\n"
        "Score the following on a scale of 0.0 to 1.0:\n"
        "1. constraint_compatibility: How well do the physical/mathematical constraints of the candidate mechanism align with the target problem?\n"
        "2. solution_transferability: How directly could the candidate's solution approach be applied to the target problem without major re-engineering?\n\n"
        'Return ONLY a JSON object: {"constraint_compatibility": <float>, "solution_transferability": <float>}. No explanation.'
    )

    client = _get_llm_client()
    if client:
        response = client.completion(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        compatibility = float(data["constraint_compatibility"])
        transferability = float(data["solution_transferability"])
        return min(1.0, max(0.0, compatibility)), min(1.0, max(0.0, transferability))

    # --- Mock fallback (only used if ANTHROPIC_API_KEY is not set) ---
    await asyncio.sleep(0.1)

    # Score based on semantic overlap between the domain context and candidate
    context_words = set(domain_context.lower().split())
    candidate_words = set(candidate_mechanism.lower().split())
    overlap_ratio = len(context_words & candidate_words) / max(len(context_words), 1)

    # Structural keywords that signal transferability
    structural_signals = {"bottleneck", "bypass", "flow", "pressure", "load", "failure", "collapse", "converge", "diverge"}
    structural_overlap = len(structural_signals & candidate_words) / len(structural_signals)

    compatibility = min(1.0, 0.5 + overlap_ratio * 0.3 + structural_overlap * 0.2)
    transferability = min(1.0, 0.4 + structural_overlap * 0.4 + overlap_ratio * 0.2)

    return round(compatibility, 2), round(transferability, 2)
