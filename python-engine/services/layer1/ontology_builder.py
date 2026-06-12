"""
FILE: python-engine/services/layer1/ontology_builder.py
PURPOSE: Implements the Dual-Stage LLM Extraction (Stage A: Ontology, Stage B: Extraction) for the Text Path.
"""
import json
import logging
import networkx as nx
from litellm import completion

logger = logging.getLogger(__name__)

class LLMGraphBuilder:
    """
    Step 3 (TEXT PATH): Converts raw text into a causal graph using LiteLLM.
    Supports user-specified models (e.g., 'gpt-4o', 'ollama/llama3').
    """

    @staticmethod
    def build_graph(text: str, model_name: str) -> dict:
        """
        Executes Stage A (Ontology) and Stage B (Extraction).
        Returns a networkx compatible JSON dictionary.
        """
        if not text.strip():
            raise ValueError("Cannot build graph from empty text.")

        # Stage A: Generate Ontology Schema
        ontology = LLMGraphBuilder._generate_ontology(text, model_name)
        
        # Stage B: Chunk and Extract
        raw_edges = LLMGraphBuilder._extract_causal_edges(text, ontology, model_name)
        
        # Build NetworkX graph
        nx_graph = nx.DiGraph()
        
        for edge in raw_edges:
            source = edge.get("source", "").strip().upper()
            target = edge.get("target", "").strip().upper()
            relation = edge.get("relation", "CAUSES").strip().upper()
            confidence_str = edge.get("confidence", "POSSIBLY")
            
            if not source or not target:
                continue
                
            # Translate language confidence to numerical weight
            conf_map = {"DEFINITELY": 0.9, "LIKELY": 0.7, "MAYBE": 0.4, "POSSIBLY": 0.2}
            weight = conf_map.get(confidence_str.upper(), 0.5)
            
            # Add Nodes
            if not nx_graph.has_node(source):
                nx_graph.add_node(source, id=source, label=source, type="entity")
            if not nx_graph.has_node(target):
                nx_graph.add_node(target, id=target, label=target, type="entity")
                
            # Add Edge
            nx_graph.add_edge(
                source, 
                target, 
                type=relation,
                confidence=weight,
                weight=weight if relation != "INHIBITS" else -weight
            )

        return LLMGraphBuilder._serialize_nx(nx_graph)

    @staticmethod
    def _generate_ontology(text: str, model_name: str) -> dict:
        """
        Stage A: Asks the LLM to read the document and determine the top entity types
        and relationship types.
        """
        logger.info(f"Running Stage A: Ontology Generation with model {model_name}")
        
        prompt = f"""
        You are an expert causal ontologist. Read the following text snippet and identify:
        1. The top 8 causal entity types (e.g., ENZYME, PATHWAY, TEMPERATURE, METRIC)
        2. The primary relationship types (e.g., INHIBITS, ACTIVATES, CAUSES)
        
        TEXT SNIPPET (First 2000 chars):
        {text[:2000]}
        
        Respond ONLY with a valid JSON object matching this schema:
        {{"entity_types": ["TYPE1", "TYPE2"], "relation_types": ["REL1", "REL2"]}}
        """
        
        try:
            response = completion(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"Ontology generation failed: {e}")
            # Fallback ontology
            return {
                "entity_types": ["VARIABLE", "METRIC", "COMPONENT"],
                "relation_types": ["CAUSES", "INHIBITS", "ACTIVATES", "CORRELATES_WITH"]
            }

    @staticmethod
    def _extract_causal_edges(text: str, ontology: dict, model_name: str) -> list:
        """
        Stage B: Chunks the text (larger paragraphs) and extracts specific cause-effect edges.
        """
        logger.info(f"Running Stage B: Causal Extraction with model {model_name}")
        
        # Chunking strategy: 500 characters, no overlap per spec
        chunk_size = 500
        chunks = []
        
        if len(text) <= chunk_size:
            chunks.append(text)
        else:
            i = 0
            while i < len(text):
                chunks.append(text[i:i + chunk_size])
                i += chunk_size
                
        all_edges = []
        
        for idx, chunk in enumerate(chunks):
            logger.debug(f"Processing chunk {idx+1}/{len(chunks)}")
            
            prompt = f"""
            Extract causal relationships from the text based on this ontology:
            Entities: {ontology['entity_types']}
            Relations: {ontology['relation_types']}
            
            TEXT:
            {chunk}
            
            Respond ONLY with a JSON array of objects matching this schema:
            [{{"source": "Entity A", "target": "Entity B", "relation": "INHIBITS", "confidence": "DEFINITELY"}}]
            Note: Confidence should be language-based (e.g., "DEFINITELY", "LIKELY", "MAYBE", "POSSIBLY").
            """
            
            try:
                response = completion(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    # Not enforcing strict json_object here as we want a JSON array, 
                    # but we can instruct the LLM tightly.
                )
                content = response.choices[0].message.content.strip()
                
                # Strip markdown blocks if present
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]
                    
                edges = json.loads(content)
                if isinstance(edges, list):
                    all_edges.extend(edges)
            except Exception as e:
                logger.error(f"Extraction failed on chunk {idx}: {e}")
                
        return all_edges

    @staticmethod
    def _serialize_nx(graph: nx.DiGraph) -> dict:
        nodes = [{"id": n, **d} for n, d in graph.nodes(data=True)]
        edges = [{"source": u, "target": v, **d} for u, v, d in graph.edges(data=True)]
        return {"nodes": nodes, "edges": edges}
