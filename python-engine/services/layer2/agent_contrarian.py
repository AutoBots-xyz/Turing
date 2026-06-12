import random
import warnings
from typing import Dict, Optional
from schemas.layer2 import SearchSpace, AgentProposal


class AgentContrarian:
    """
    Contrarian Agent.
    Challenges assumptions by picking the boundary that is OPPOSITE to what
    the Explorer would choose — ensuring every round covers a unique boundary
    and no simulation round is wasted on a duplicate proposal.

    Fixes applied:
    - Optional seed for reproducibility (pass seed=42 for deterministic runs)
    - Anti-duplication: always picks the boundary the Explorer did NOT choose,
      ensuring Contrarian and Explorer always test different corners
    - Empty base_point emits UserWarning instead of silently returning {}
    - Missing domain_config key emits UserWarning with fallback to raw value
    - Dynamic justification: reports each node's chosen boundary and why
    """

    def propose(
        self,
        base_point: Dict[str, float],
        domain_config: Dict[str, SearchSpace],
        seed: Optional[int] = None,
    ) -> AgentProposal:
        """
        Propose boundary values that directly challenge the current base point.

        Args:
            base_point:    {node_name: current_best_value} from BayesianOptimizer
            domain_config: {node_name: SearchSpace(min, max)}
            seed:          Optional random seed for reproducibility (default: None)

        Returns:
            AgentProposal with boundary values opposite to what Explorer would pick.
        """
        if seed is not None:
            random.seed(seed)

        if not base_point:
            warnings.warn(
                "AgentContrarian: base_point is empty — no variables to challenge. "
                "Returning empty proposal.",
                UserWarning,
                stacklevel=2,
            )
            return AgentProposal(
                agent_name="Contrarian",
                proposed_values={},
                justification="No variables to challenge (empty base_point).",
            )

        proposed = {}
        challenge_details = []

        for node, val in base_point.items():
            space = domain_config.get(node)

            if space is None:
                warnings.warn(
                    f"AgentContrarian: node '{node}' has no SearchSpace in domain_config. "
                    "Falling back to raw base_point value — no boundary challenge applied.",
                    UserWarning,
                    stacklevel=2,
                )
                proposed[node] = val
                challenge_details.append(f"{node}={val} (no space — not challenged)")
                continue

            dist_to_min = abs(val - space.min)
            dist_to_max = abs(val - space.max)

            # Anti-duplication: Explorer always picks the FARTHER boundary.
            # Contrarian always picks the OPPOSITE (closer) boundary to guarantee
            # that no two agents test the same corner in the same round.
            # Tie-break: Explorer goes to min, so Contrarian goes to max.
            if dist_to_min > dist_to_max:
                # Explorer would pick min — Contrarian picks max
                chosen = space.max
                challenge_details.append(
                    f"{node}={val}->MAX({space.max}) [opposite of Explorer's MIN]"
                )
            elif dist_to_max > dist_to_min:
                # Explorer would pick max — Contrarian picks min
                chosen = space.min
                challenge_details.append(
                    f"{node}={val}->MIN({space.min}) [opposite of Explorer's MAX]"
                )
            else:
                # Exact center tie: Explorer goes to min, Contrarian goes to max
                chosen = space.max
                challenge_details.append(
                    f"{node}={val}->MAX({space.max}) [center tie -> opposite of Explorer's MIN]"
                )

            proposed[node] = chosen

        justification = (
            "Contrarian challenged Explorer's assumptions by testing the opposite boundaries. "
            "Challenges: " + "; ".join(challenge_details) + "."
        )

        return AgentProposal(
            agent_name="Contrarian",
            proposed_values=proposed,
            justification=justification,
        )
