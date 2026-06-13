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

    # --- Fallback (no API key) ---
    raise RuntimeError(
        "Domain-blind query generation failed: ANTHROPIC_API_KEY is missing. "
        "Cannot reliably generate structural queries without a configured LLM."
    )


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

    # --- Fallback (no API key) ---
    # Fixes ERR-B31: Replaced hardcoded test mocks that poisoned the engine
    # with a clear, fail-fast exception. Real graph extraction requires an LLM.
    raise RuntimeError(
        "Generative extraction failed: ANTHROPIC_API_KEY is missing. "
        "Cannot reliably extract causal graphs from text without a configured LLM."
    )


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

    # --- Fallback (no API key) ---
    # Fixes ERR-B32: Replaced the fake semantic overlap calculation 
    # (word set intersections) with a clear exception. 
    raise RuntimeError(
        "Semantic evaluation failed: ANTHROPIC_API_KEY is missing. "
        "Cannot reliably evaluate constraint compatibility or transferability without a configured LLM."
    )


# ---------------------------------------------------------------------------
# Function 4: classify_deployment_status
# Fixes Error B23: Uses LLM to evaluate domain authority instead of hardcoded lists.
# ---------------------------------------------------------------------------
async def classify_deployment_status(url: str, snippet: str) -> str:
    """
    Layer 3 LLM call: Classifies the deployment status of a web search result.
    Evaluates the snippet and URL domain to determine engineering authority.
    """
    prompt = (
        f"Analyze the following search result:\nURL: {url}\nSnippet: {snippet}\n\n"
        "Classify the production deployment evidence into exactly one of these categories:\n"
        "- 'deployed': Major engineering blogs, clear production deployment at scale (e.g., AWS, Netflix, Uber).\n"
        "- 'replicated': Proven across multiple studies or companies.\n"
        "- 'single_study': Authoritative technical publishers or isolated case studies.\n"
        "- 'blog': Personal blogs, tutorials, or unverified claims.\n"
        "- 'unknown': Cannot determine.\n\n"
        "Return ONLY the category name. No explanation."
    )

    client = _get_llm_client()
    if client:
        # Using litellm's acompletion for proper async behavior if available, else completion
        try:
            response = await client.acompletion(
                model="claude-3-5-sonnet-20241022",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10
            )
        except AttributeError:
            response = client.completion(
                model="claude-3-5-sonnet-20241022",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10
            )
        cat = response.choices[0].message.content.strip().lower()
        # Clean up any potential markdown or punctuation
        cat = cat.strip("`'\".,\n")
        valid = {"deployed", "replicated", "single_study", "blog", "unknown"}
        if cat in valid:
            return cat

    # --- Fallback (no API key) ---
    raise RuntimeError(
        "Deployment classification failed: ANTHROPIC_API_KEY is missing. "
        "Cannot safely classify deployment status without a configured LLM."
    )

