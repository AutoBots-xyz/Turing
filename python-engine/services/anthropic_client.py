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
    Supports Anthropic, OpenAI, NVIDIA NIM, and Groq.
    Falls back to None if no API key is configured.
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
        
        # Inject keys into litellm explicitly so it routes to the right provider
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
        return None  # Signals safe fallback

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
    if not client:
        raise EnvironmentError("API Key is required to generate domain-blind queries.")

    # Set NVIDIA NIM API key for litellm if available
    if os.getenv("NVIDIA_NIM_API_KEY"):
        client.api_key = os.getenv("NVIDIA_NIM_API_KEY")
    response = client.completion(
        model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4o"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
    )
    return response.choices[0].message.content.strip()


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
    if not client:
        # ERR-B31 fix: Do not poison the extraction step with fabricated demo data.
        raise EnvironmentError("API Key is required to extract causal graphs.")

    response = client.completion(
        model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4o"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
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
    if not client:
        # ERR-B32 fix: Do not simulate semantic transferability with naive word intersection.
        raise EnvironmentError("API Key is required to evaluate transferability.")

    response = client.completion(
        model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4o"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60,
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


# ---------------------------------------------------------------------------
# Function 4: evaluate_deployment_status
# Fixes ERR-B23: Classifies domain authority dynamically using LLM
# ---------------------------------------------------------------------------
async def evaluate_deployment_status(url: str, snippet: str) -> str:
    """
    Evaluates whether a search result represents a deployed production system,
    a single study / academic paper, or just a blog/tutorial.
    """
    prompt = (
        f"You are evaluating the engineering deployment status of a search result.\n"
        f"URL: {url}\n"
        f"Snippet: {snippet}\n\n"
        "Classify the deployment status into exactly one of these three categories:\n"
        "1. 'deployed' (Indicates a technology used in a real production system, often a major tech company case study or whitepaper)\n"
        "2. 'single_study' (Indicates a formal academic paper, authoritative single experiment, or official documentation)\n"
        "3. 'blog' (Indicates a tutorial, opinion piece, generic tech blog, or unverified source)\n\n"
        "Return ONLY the category name in lowercase. No explanation."
    )

    client = _get_llm_client()
    if not client:
        raise EnvironmentError("API Key is required to evaluate deployment status.")

    try:
        response = await asyncio.to_thread(
            client.completion,
            model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20
        )
        raw = response.choices[0].message.content.strip().lower()
        if "deployed" in raw: return "deployed"
        if "single_study" in raw: return "single_study"
        return "blog"
    except Exception as e:
        raise EnvironmentError(f"Failed to evaluate deployment status: {e}")
