import warnings
from typing import Dict
from schemas.layer2 import SearchSpace, AgentProposal


class AgentExplorer:
    """
    Explorer Agent.
    Takes the Bayesian base point and pushes each variable to the farthest
    boundary of its search space, deliberately seeking the edges of the system
    to find where performance degrades (cliff detection).

    Fixes applied:
    - Empty base_point emits a UserWarning and returns an empty proposal
    - Missing domain_config key emits a UserWarning and falls back to raw value
    - Center tie-breaking (dist_to_min == dist_to_max) now explicitly picks min
      to ensure deterministic, documented behaviour (not silent bias toward max)
    - Justification string is now dynamic and lists each node's actual push direction
    """

    def propose(
        self,
        base_point: Dict[str, float],
        domain_config: Dict[str, SearchSpace],
    ) -> AgentProposal:
        """
        Propose extreme boundary values for every controllable variable.

        Args:
            base_point:    {node_name: current_best_value} from BayesianOptimizer
            domain_config: {node_name: SearchSpace(min, max)}

        Returns:
            AgentProposal with values pushed to the farthest boundary per variable.
        """
        if not base_point:
            warnings.warn(
                "AgentExplorer: base_point is empty — no variables to explore. "
                "Returning empty proposal.",
                UserWarning,
                stacklevel=2,
            )
            return AgentProposal(
                agent_name="Explorer",
                proposed_values={},
                justification="No variables to explore (empty base_point).",
            )

        proposed = {}
        push_details = []

        for node, val in base_point.items():
            space = domain_config.get(node)

            if space is None:
                warnings.warn(
                    f"AgentExplorer: node '{node}' has no SearchSpace in domain_config. "
                    "Falling back to raw base_point value — no boundary push applied.",
                    UserWarning,
                    stacklevel=2,
                )
                proposed[node] = val
                push_details.append(f"{node}={val} (no space — not pushed)")
                continue

            dist_to_min = abs(val - space.min)
            dist_to_max = abs(val - space.max)

            if dist_to_min > dist_to_max:
                # Further from min — push to min (the farther extreme)
                proposed[node] = space.min
                push_details.append(f"{node}={val}->{space.min} (pushed to MIN)")
            elif dist_to_max > dist_to_min:
                # Further from max — push to max (the farther extreme)
                proposed[node] = space.max
                push_details.append(f"{node}={val}->{space.max} (pushed to MAX)")
            else:
                # Exactly at center — documented tie-break: always push to min
                proposed[node] = space.min
                push_details.append(f"{node}={val}->{space.min} (center tie -> pushed to MIN)")

        justification = (
            "Explorer pushed variables to their farthest boundaries to find cliff edges. "
            "Decisions: " + "; ".join(push_details) + "."
        )

        return AgentProposal(
            agent_name="Explorer",
            proposed_values=proposed,
            justification=justification,
        )
