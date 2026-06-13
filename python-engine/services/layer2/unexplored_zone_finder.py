import warnings
from schemas.layer2 import ZoneFinderInput, ZoneFinderOutput, UnexploredZone, SearchSpace, GaussianPrediction
from services.layer2.do_calculus import DoCalculusSimulator


class UnexploredZoneFinder:
    """
    Checks original data against simulated space to find mathematically
    uncertain but highly promising unexplored zones.
    """

    def __init__(self):
        self.simulator = DoCalculusSimulator()

    def find_zones(self, payload: ZoneFinderInput) -> ZoneFinderOutput:
        unexplored_zones = []

        # ── Step 1: Determine Source Nodes and Sink Node ────────────────────
        in_degrees = {node: 0 for node in payload.nodes}
        out_degrees = {node: 0 for node in payload.nodes}

        for edge in payload.edges:
            if edge.source in out_degrees:
                out_degrees[edge.source] += 1
            if edge.target in in_degrees:
                in_degrees[edge.target] += 1

        source_nodes = [
            node for node in payload.nodes
            if in_degrees[node] == 0 and out_degrees[node] > 0
        ]

        if not source_nodes:
            raise ValueError(
                "UnexploredZoneFinder: no source nodes found in the graph "
                "(nodes with no incoming edges and at least one outgoing edge)."
            )

        # Resolve sink node dynamically
        if payload.sink_node:
            sink_node = payload.sink_node
            if sink_node not in payload.nodes:
                raise ValueError(
                    f"UnexploredZoneFinder: specified sink_node '{sink_node}' "
                    "is not in the nodes list."
                )
        else:
            sink_candidates = [
                n for n in payload.nodes
                if out_degrees[n] == 0 and in_degrees[n] > 0
            ]
            if sink_candidates:
                sink_node = sink_candidates[-1]
            else:
                sink_node = payload.nodes[-1]
                warnings.warn(
                    f"UnexploredZoneFinder: could not auto-detect sink node. "
                    f"Falling back to last node: '{sink_node}'.",
                    UserWarning,
                    stacklevel=2,
                )

        # ── Step 2: Extract historically tested ranges for each source node ──
        tested_ranges = {
            node: {"min": float('inf'), "max": -float('inf')}
            for node in source_nodes
        }

        # Find best past run for hold-steady logic later
        best_past = {}
        if payload.historical_data:
            if not any(sink_node in entry for entry in payload.historical_data):
                warnings.warn(
                    f"UnexploredZoneFinder: None of the historical entries contain the sink_node key '{sink_node}'. "
                    "Hold-steady logic will fall back to domain center values.",
                    UserWarning,
                    stacklevel=2,
                )
            best_run = max(
                payload.historical_data,
                key=lambda x: x.get(sink_node, 0)
            )
            best_past = best_run.get("values", {})

        for data_point in payload.historical_data:
            values = data_point.get("values", {})
            for node in source_nodes:
                val = values.get(node)
                if val is not None:
                    tested_ranges[node]["min"] = min(tested_ranges[node]["min"], val)
                    tested_ranges[node]["max"] = max(tested_ranges[node]["max"], val)

        # ── Step 3: Compare tested ranges against domain config boundaries ────
        for node in source_nodes:
            space = payload.domain_config.get(node)
            if not space:
                warnings.warn(
                    f"UnexploredZoneFinder: node '{node}' has no SearchSpace in "
                    "domain_config. Skipping zone detection for this parameter.",
                    UserWarning,
                    stacklevel=2,
                )
                continue

            tested_min = tested_ranges[node]["min"]
            tested_max = tested_ranges[node]["max"]

            # If no data for this node at all, entire space is unexplored
            if tested_min == float('inf'):
                unexplored_gaps = [(space.min, space.max)]
            else:
                unexplored_gaps = []
                space_width = space.max - space.min
                gap_size_required = space_width * payload.gap_threshold

                # Check bottom gap
                if tested_min - space.min > gap_size_required:
                    unexplored_gaps.append((space.min, tested_min))
                # Check top gap
                if space.max - tested_max > gap_size_required:
                    unexplored_gaps.append((tested_max, space.max))

            # ── Step 4: Simulate midpoint of unexplored gaps ──────────────────
            for gap_min, gap_max in unexplored_gaps:
                midpoint = (gap_min + gap_max) / 2

                # Setup simulation holding others steady at their historically best
                # values (not domain center), mirroring heatmap.py logic
                interventions = {node: midpoint}
                for other_node in source_nodes:
                    if other_node != node:
                        other_space = payload.domain_config.get(other_node)
                        if not other_space:
                            raise ValueError(
                                f"UnexploredZoneFinder: source node '{other_node}' is missing from domain_config. "
                                "Cannot determine hold-steady baseline."
                            )
                        if other_node in best_past:
                            steady_val = best_past[other_node]
                        else:
                            # Fixes ERR-B41: Prevent statistically meaningless middle-of-domain fallbacks
                            raise ValueError(
                                f"Cannot establish a steady-state baseline for '{other_node}'. It is missing from "
                                "historical data, and blindly picking the domain midpoint is statistically invalid."
                            )
                        interventions[other_node] = steady_val

                sim_res = self.simulator.simulate(
                    payload.nodes, payload.edges, interventions
                )
                
                # Fixes ERR-B42: Remove fake Gaussian prediction injection
                pred = sim_res.predictions.get(sink_node)
                if not pred:
                    continue

                num_experiments = len(payload.historical_data)

                msg = (
                    f"You have never tested {node} between {round(gap_min, 1)} and {round(gap_max, 1)}. "
                    f"Simulation predicts {sink_node} may reach {round(pred.mean, 1)} "
                    f"but uncertainty is high ± {round(pred.std_dev, 1)} — "
                    f"only {num_experiments} experiment(s) globally."
                )

                unexplored_zones.append(UnexploredZone(
                    parameter_name=node,
                    range_min=round(gap_min, 2),
                    range_max=round(gap_max, 2),
                    predicted_yield=round(pred.mean, 2),
                    uncertainty=round(pred.std_dev, 2),
                    message=msg
                ))

        return ZoneFinderOutput(unexplored_zones=unexplored_zones)
