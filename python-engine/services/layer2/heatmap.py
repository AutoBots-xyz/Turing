import warnings
from typing import List
from schemas.layer2 import HeatmapInput, HeatmapOutput, HeatmapPoint, SearchSpace, GaussianPrediction
from services.layer2.do_calculus import DoCalculusSimulator
from services.layer2.cliff_detector import CliffDetector


def linspace(start: float, stop: float, num: int) -> List[float]:
    """Return `num` evenly spaced values from start to stop (inclusive)."""
    if num <= 1:
        return [start]
    step = (stop - start) / (num - 1)
    return [start + step * i for i in range(num)]


class HeatmapGenerator:
    """
    Generates a full 2D heatmap of the parameter space using the GP simulator.
    If there are >2 source nodes, picks the first two for axes and holds the
    rest steady at their historically best values (hold-steady logic).
    """

    def __init__(self):
        self.simulator = DoCalculusSimulator()

    def generate(self, payload: HeatmapInput) -> HeatmapOutput:
        """
        Generate the heatmap grid.

        Raises:
            ValueError: if no source nodes found, or required domain_config keys missing.
        """
        # ── Step 1: Determine source nodes from graph topology ──────────────
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
                "HeatmapGenerator: no source nodes found in the graph "
                "(nodes with no incoming edges and at least one outgoing edge). "
                "Check that edges are correctly directed."
            )

        # ── Step 2: Select X and Y axes ──────────────────────────────────────
        x_label = source_nodes[0]
        y_label = source_nodes[1] if len(source_nodes) > 1 else source_nodes[0]
        single_axis = (x_label == y_label)

        # Validate domain_config has entries for axis nodes
        for label in set([x_label, y_label]):
            if label not in payload.domain_config:
                raise ValueError(
                    f"HeatmapGenerator: source node '{label}' is not in domain_config. "
                    "Every source node used as an axis must have explicit SearchSpace bounds."
                )

        x_space = payload.domain_config[x_label]
        y_space = payload.domain_config[y_label]

        # ── Step 3: Resolve sink node ─────────────────────────────────────────
        if payload.sink_node:
            sink_node_name = payload.sink_node
            if sink_node_name not in payload.nodes:
                raise ValueError(
                    f"HeatmapGenerator: specified sink_node '{sink_node_name}' "
                    "is not in the nodes list."
                )
        else:
            # Auto-detect: node with no outgoing edges
            sink_candidates = [
                n for n in payload.nodes
                if out_degrees[n] == 0 and in_degrees[n] > 0
            ]
            if sink_candidates:
                sink_node_name = sink_candidates[-1]
            else:
                sink_node_name = payload.nodes[-1]
                warnings.warn(
                    f"HeatmapGenerator: could not auto-detect sink node. "
                    f"Falling back to last node: '{sink_node_name}'.",
                    UserWarning,
                    stacklevel=2,
                )

        # ── Step 4: Hold-steady values for extra source nodes ─────────────────
        steady_values = {}
        if len(source_nodes) > 2:
            best_past = {}
            if payload.historical_data:
                if not any(sink_node_name in entry for entry in payload.historical_data):
                    warnings.warn(
                        f"HeatmapGenerator: None of the historical entries contain the sink_node key '{sink_node_name}'. "
                        "Hold-steady logic will fall back to domain center values.",
                        UserWarning,
                        stacklevel=2,
                    )
                else:
                    best_run = max(
                        payload.historical_data,
                        key=lambda x: x.get(sink_node_name, 0)
                    )
                    best_past = best_run.get("values", {})

            for node in source_nodes[2:]:
                if node not in payload.domain_config:
                    raise ValueError(
                        f"HeatmapGenerator: extra source node '{node}' is not in domain_config. "
                        "All source nodes must have SearchSpace bounds for hold-steady logic."
                    )
                space = payload.domain_config[node]
                steady_values[node] = best_past.get(node, (space.min + space.max) / 2)

        # ── Step 5: Generate grid ─────────────────────────────────────────────
        x_steps = linspace(x_space.min, x_space.max, payload.resolution)
        y_steps = linspace(y_space.min, y_space.max, payload.resolution)
        data_points = []

        for x_val in x_steps:
            y_iter = [x_val] if single_axis else y_steps
            for y_val in y_iter:
                interventions = {x_label: float(x_val)}
                if not single_axis:
                    interventions[y_label] = float(y_val)
                interventions.update(steady_values)

                sim_res = self.simulator.simulate(payload.nodes, payload.edges, interventions)
                pred = sim_res.predictions.get(
                    sink_node_name,
                    GaussianPrediction(mean=0.0, std_dev=1.0)
                )

                data_points.append(HeatmapPoint(
                    x_val=round(float(x_val), 2),
                    y_val=round(float(y_val if not single_axis else x_val), 2),
                    z_val=round(pred.mean, 2),
                    is_cliff=False
                ))

        # ── Step 6: Relative cliff detection ─────────────────────────────────
        CliffDetector.detect_cliffs(data_points, payload.cliff_sigma)

        return HeatmapOutput(
            x_label=x_label,
            y_label=y_label,
            is_1d=single_axis,
            data=data_points,
        )
