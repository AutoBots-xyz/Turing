import asyncio
from typing import List
from schemas.layer3 import SearchResult, DebateTranscript, ContradictionDetails

class AgentFactory:
    """
    Dynamically spawns specialized agents to debate and analyze search results.
    """
    
    @staticmethod
    async def run_proposer(results: List[SearchResult]) -> str:
        """
        The Proposer asserts a unified theory based on the highest-confidence source.
        """
        await asyncio.sleep(0.5)  # Simulate LLM latency
        top_result = max(results, key=lambda x: x.confidence)
        return f"Hypothesis based on [{top_result.source.value}]: {top_result.summary}"

    @staticmethod
    async def run_skeptic(results: List[SearchResult], proposer_argument: str) -> str:
        """
        The Skeptic actively scans lower-confidence sources to find direct contradictions to the Proposer.
        """
        await asyncio.sleep(0.5)  # Simulate LLM latency
        
        # Check if there are conflicting terms in the mock data
        conflicts = [r for r in results if "Alternative" in r.title or "conflicting" in r.summary.lower()]
        
        if conflicts:
            conflict = conflicts[0]
            return f"REJECTED. Data contradiction found in [{conflict.source.value}]: {conflict.summary}"
        return "ACCEPTED. No direct contradictions found in other sources."

    @staticmethod
    async def run_synthesizer(results: List[SearchResult], proposer_arg: str, skeptic_arg: str) -> ContradictionDetails:
        """
        The Synthesizer reviews the debate, decides if a true contradiction exists, and formulates an experiment.
        """
        await asyncio.sleep(0.5)  # Simulate LLM latency
        
        conflict_detected = "REJECTED" in skeptic_arg
        
        transcript = DebateTranscript(
            proposer_argument=proposer_arg,
            skeptic_rebuttal=skeptic_arg,
            synthesizer_consensus="Conflict confirmed between sources." if conflict_detected else "All sources align structurally."
        )
        
        return ContradictionDetails(
            conflict_detected=conflict_detected,
            nature_of_conflict="Conflicting structural resolutions proposed by different sources." if conflict_detected else "None",
            debate_log=transcript,
            recommended_experiment="Perform dynamic stress test varying input pressure to measure bottleneck capacity." if conflict_detected else "Proceed with standard implementation."
        )

    @classmethod
    async def conduct_adversarial_debate(cls, results: List[SearchResult]) -> ContradictionDetails:
        """
        Orchestrates the 3-Agent Swarm (Proposer -> Skeptic -> Synthesizer).
        """
        proposer_arg = await cls.run_proposer(results)
        skeptic_arg = await cls.run_skeptic(results, proposer_arg)
        details = await cls.run_synthesizer(results, proposer_arg, skeptic_arg)
        return details
