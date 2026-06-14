import asyncio
import json
import os
from typing import List, Tuple
from schemas.layer3 import SearchResult, DebateTranscript, ContradictionDetails


def _get_llm_client():
    """Returns LiteLLM client if API key is set, else None for mock fallback."""
    try:
        import litellm
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise EnvironmentError("No key")
        return litellm
    except (ImportError, EnvironmentError):
        return None


class AgentFactory:
    """
    Dynamically spawns specialized agents to debate and analyse search results.
    Uses real LLM calls via LiteLLM. Falls back to a smart heuristic when no
    API key is configured.
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
        Fixes Error 5: Replaces the `'Alternative' in r.title` string-match hack
        with a real LLM call that reasons over the actual content of all sources.

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
            # ERR-B29 fix: Do not perform naive string-matching masquerading as AI.
            raise EnvironmentError("ANTHROPIC_API_KEY is required to run the Skeptic agent.")

        response = client.completion(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()

    @staticmethod
    async def run_synthesizer(
        results: List[SearchResult],
        proposer_arg: str,
        skeptic_arg: str
    ) -> ContradictionDetails:
        """
        Fixes Error 6: Replaces the hardcoded experiment string with a real LLM call
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
                # ERR-B30 fix: Do not perform hardcoded string slicing to fake a consensus.
                raise EnvironmentError("ANTHROPIC_API_KEY is required to run the Synthesizer agent.")

            response = client.completion(
                model="claude-3-5-sonnet-20241022",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
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
