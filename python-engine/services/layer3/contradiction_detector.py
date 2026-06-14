import asyncio
from typing import List
import json
import os
from schemas.layer3 import MergedResult, SearchResult, DebateTranscript, ContradictionDetails


def _get_llm_client():
    """Returns LiteLLM client if API key is set, else None for missing key fallback."""
    try:
        import litellm
        if not any(os.getenv(k) for k in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "NVIDIA_API_KEY"]):
            raise EnvironmentError("No key")
        return litellm
    except (ImportError, EnvironmentError):
        return None


class AgentFactory:
    """
    Dynamically spawns specialized agents to debate and analyse search results.
    Uses real LLM calls via LiteLLM.
    """

    @staticmethod
    async def run_proposer(results: List[SearchResult]) -> str:
        """
        The Proposer asserts a unified theory based on the highest-confidence source.
        """
        top = max(results, key=lambda x: x.confidence)
        return f"Hypothesis based on [{top.source.value}]: {top.summary}"

    @staticmethod
    async def run_skeptic(results: List[SearchResult], proposer_argument: str) -> str:
        """
        Replaces the string-match hack with a real LLM call that reasons over the actual content of all sources.
        Asks Claude to compare all summaries against the proposer's hypothesis
        and identify any genuine directional or mechanistic contradictions.
        """
        summaries_block = "\n".join(
            f"[{r.source.value}] {r.title}: {r.summary}" for r in results
        )

        prompt = (
            "You are an adversarial scientific skeptic in a structured debate.\n\n"
            f"PROPOSER HYPOTHESIS:\n{proposer_argument}\n\n"
            f"ALL AVAILABLE SOURCES:\n{summaries_block}\n\n"
            "Your job: Identify if ANY source contradicts the proposer's hypothesis "
            "on the direction, mechanism, or outcome of the causal relationship described.\n"
            "A contradiction means two sources disagree on HOW the mechanism works "
            "(e.g., one says X inhibits Y, another says X activates Y).\n\n"
            "If a contradiction exists, respond with: "
            "'REJECTED. Data contradiction found in [SOURCE]: <exact quote of the conflicting claim>.'\n"
            "If no contradiction exists, respond with exactly: "
            "'ACCEPTED. No direct contradictions found in other sources.'\n"
            "Output ONLY the single response line above, nothing else."
        )

        client = _get_llm_client()
        if not client:
            raise EnvironmentError("LLM API KEY is required to run the Skeptic agent.")

        response = client.completion(
            model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            api_key=os.getenv("NVIDIA_NIM_API_KEY") or os.getenv("NVIDIA_API_KEY") or None
        )
        return response.choices[0].message.content.strip()

    @staticmethod
    async def run_synthesizer(
        results: List[SearchResult],
        proposer_arg: str,
        skeptic_arg: str
    ) -> ContradictionDetails:
        """
        Replaces the static string with a real LLM call
        that generates a domain-specific experiment tailored to the exact conflict found.
        """
        conflict_detected = skeptic_arg.startswith("REJECTED")

        if conflict_detected:
            prompt = (
                "You are a scientific synthesizer resolving a debate between two agents.\n\n"
                f"PROPOSER:\n{proposer_arg}\n\n"
                f"SKEPTIC:\n{skeptic_arg}\n\n"
                "Tasks:\n"
                "1. Write one sentence describing the nature of the conflict (the 'consensus' field).\n"
                "2. Design one specific, measurable experiment that would empirically resolve "
                "which side is correct. The experiment must be directly relevant to the specific "
                "mechanism under debate — not a generic stress test.\n\n"
                'Return ONLY a JSON object: {"consensus": "<string>", "experiment": "<string>"}. No explanation.'
            )

            client = _get_llm_client()
            if not client:
                raise EnvironmentError("LLM API KEY is required to run the Synthesizer agent.")

            response = client.completion(
                model=os.getenv("DEFAULT_LLM_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                response_format={"type": "json_object"} if "gpt" in os.getenv("DEFAULT_LLM_MODEL", "gpt-4o") or "claude" in os.getenv("DEFAULT_LLM_MODEL", "gpt-4o") else None,
                api_key=os.getenv("NVIDIA_NIM_API_KEY") or os.getenv("NVIDIA_API_KEY") or None
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            consensus = data.get("consensus", "Conflict confirmed between sources.")
            experiment = data.get("experiment", "Design a controlled comparative experiment.")

            nature = skeptic_arg.replace("REJECTED. ", "")
        else:
            consensus = "All sources align structurally — no directional contradictions detected."
            nature = "None"
            experiment = "Proceed with standard implementation."

        transcript = DebateTranscript(
            proposer_argument=proposer_arg,
            skeptic_rebuttal=skeptic_arg,
            synthesizer_consensus=consensus,
        )
        return ContradictionDetails(
            conflict_detected=conflict_detected,
            nature_of_conflict=nature,
            debate_log=transcript,
            recommended_experiment=experiment,
        )

    @classmethod
    async def conduct_adversarial_debate(cls, results: List[SearchResult]) -> ContradictionDetails:
        """
        Orchestrates the 3-Agent Swarm (Proposer -> Skeptic -> Synthesizer).
        Each agent's output feeds into the next — sequential, not parallel.
        """
        proposer_arg = await cls.run_proposer(results)
        skeptic_arg = await cls.run_skeptic(results, proposer_arg)
        details = await cls.run_synthesizer(results, proposer_arg, skeptic_arg)
        return details


async def detect_contradictions(merged_results: List[MergedResult]) -> List[MergedResult]:
    """
    Step 11.5 Contradiction Detector:
    Passes merged findings to the 3-Agent Swarm (Proposer → Skeptic → Synthesizer)
    to debate and identify structural contradictions between sources.

    Fixes L3-2 / ERR-B27: No longer uses a dummy coroutine to satisfy asyncio.gather.
    Properly filters the list to only include multi-source results before gathering.

    Fixes L3-3: MergedResult is a Pydantic v2 BaseModel which is frozen
    (immutable) by default. Direct assignment `merged.contradiction_analysis = x`
    raises `ValidationError: Instance is frozen`. Fixed by using
    `model_copy(update={...})` to produce a new immutable instance.
    """
    debate_tasks = []
    debate_indices = []

    for idx, merged in enumerate(merged_results):
        if len(merged.source_results) > 1:
            debate_tasks.append(AgentFactory.conduct_adversarial_debate(merged.source_results))
            debate_indices.append(idx)

    # return_exceptions=True ensures one failed debate doesn't kill the whole batch
    debates = await asyncio.gather(*debate_tasks, return_exceptions=True) if debate_tasks else []

    # Reconstruct results
    debate_map = dict(zip(debate_indices, debates))
    
    processed_results = []
    for idx, merged in enumerate(merged_results):
        if idx in debate_map:
            debate_result = debate_map[idx]
            if isinstance(debate_result, Exception):
                print(f"[contradiction_detector] Debate error for '{merged.title}': {debate_result}")
                processed_results.append(merged)
            elif debate_result is not None:
                updated = merged.model_copy(update={"contradiction_analysis": debate_result})
                processed_results.append(updated)
            else:
                processed_results.append(merged)
        else:
            processed_results.append(merged)

    return processed_results
