"""
services/layer1/ontology_builder.py — Text Path Ontology Builder

Fixes Error 5 (Batch 4): This file was completely empty.
Calls Claude (via LiteLLM) to extract an initial causal graph from a
document text. This is the Text Path equivalent of the PC Algorithm.
Falls back to a keyword-based heuristic when no API key is available.
"""
import json
import os

from schemas.graph import CausalGraph, Node, Edge


def _get_llm_client():
    """Returns LiteLLM if ANTHROPIC_API_KEY is set, else None."""
    try:
        import litellm
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise EnvironmentError("No key")
        return litellm
    except (ImportError, EnvironmentError):
        return None


async def build_ontology_from_text(content: dict) -> CausalGraph:
    """
    Text Path: Extracts a causal graph from document text using Claude.

    The LLM identifies:
    - Nodes: nouns representing entities, variables, or components
    - Edges: directed causal verbs (CAUSES, INHIBITS, ACTIVATES, REQUIRES, etc.)
    - Confidence: scored from 0-100 based on linguistic certainty

    Parameters
    ----------
    content : dict
        Parsed text content from universal_parser._parse_text().
        Must contain a "content" key with the full document text.

    Returns
    -------
    CausalGraph
        The extracted causal graph with nodes and directed edges.
    """
    text = content.get("content", "")
    if not text.strip():
        return CausalGraph(nodes=[], edges=[])

    # Truncate to avoid excessive token usage
    text_excerpt = text[:4000]

    prompt = (
        "You are a causal graph extractor specialised in scientific and technical documents.\n\n"
        f"TEXT:\n{text_excerpt}\n\n"
        "Extract all causal relationships from the text and return them as a JSON object:\n"
        "{\n"
        '  "nodes": [{"id": "n1", "label": "<noun entity>", "confidence": <0-100>}],\n'
        '  "edges": [{"source": "n1", "target": "n2", "relation": "<UPPERCASE_VERB>", "confidence": <0-100>}]\n'
        "}\n\n"
        "Rules:\n"
        "- Nodes MUST be nouns (entities, variables, components, substances).\n"
        "- Edge 'relation' MUST be a single uppercase causal verb "
        "(e.g., CAUSES, INHIBITS, ACTIVATES, REQUIRES, ENABLES, PREVENTS, AMPLIFIES).\n"
        "- Confidence for edges: 'causes' → 90, 'may cause' → 50, 'correlates with' → 30.\n"
        "- Assign unique, short IDs (n1, n2, ...) to each node.\n"
        "- Output ONLY valid JSON. No explanation, no markdown."
    )

    client = _get_llm_client()
    if client:
        response = client.completion(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        nodes = [Node(id=n["id"], label=n["label"], confidence=n["confidence"]) for n in data["nodes"]]
        edges = [
            Edge(source=e["source"], target=e["target"], relation=e["relation"], confidence=e["confidence"])
            for e in data["edges"]
        ]
        return CausalGraph(nodes=nodes, edges=edges)

    # -----------------------------------------------------------------------
    # Heuristic fallback — no LLM available
    # -----------------------------------------------------------------------
    return _keyword_graph(text_excerpt)


def _keyword_graph(text: str) -> CausalGraph:
    """
    Builds a simple heuristic graph from causal keyword pairs in the text.
    This is NOT a substitute for real LLM extraction — it is only a
    non-crashing fallback for local development without an API key.
    """
    import re

    # Simple causal pattern: "X causes Y", "X leads to Y", "X results in Y"
    causal_patterns = [
        (r"(\w[\w\s]{1,30})\s+causes\s+([\w\s]{1,30})", "CAUSES"),
        (r"(\w[\w\s]{1,30})\s+leads to\s+([\w\s]{1,30})", "CAUSES"),
        (r"(\w[\w\s]{1,30})\s+results in\s+([\w\s]{1,30})", "CAUSES"),
        (r"(\w[\w\s]{1,30})\s+inhibits\s+([\w\s]{1,30})", "INHIBITS"),
        (r"(\w[\w\s]{1,30})\s+activates\s+([\w\s]{1,30})", "ACTIVATES"),
        (r"(\w[\w\s]{1,30})\s+prevents\s+([\w\s]{1,30})", "PREVENTS"),
        (r"(\w[\w\s]{1,30})\s+increases\s+([\w\s]{1,30})", "INCREASES"),
        (r"(\w[\w\s]{1,30})\s+decreases\s+([\w\s]{1,30})", "DECREASES"),
    ]

    node_map: dict[str, str] = {}  # label → id
    nodes = []
    edges = []
    node_counter = 1

    def get_or_create_node(label: str) -> str:
        label = label.strip().title()
        if label not in node_map:
            nid = f"n{node_counter}"
            nonlocal node_counter
            node_map[label] = nid
            nodes.append(Node(id=nid, label=label, confidence=50.0))
            node_counter += 1
        return node_map[label]

    for pattern, relation in causal_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            src_label = match.group(1).strip()
            tgt_label = match.group(2).strip()
            if len(src_label) < 2 or len(tgt_label) < 2:
                continue
            src_id = get_or_create_node(src_label)
            tgt_id = get_or_create_node(tgt_label)
            edges.append(Edge(source=src_id, target=tgt_id, relation=relation, confidence=55.0))

    return CausalGraph(nodes=nodes, edges=edges)
