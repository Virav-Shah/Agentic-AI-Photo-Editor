"""
AI Thinking - what does ai do in editing - steps it took
Lightweight visualization utilities that produce Mermaid strings from
the simplified PlannerState / results returned by the lightweight
orchestrator.
"""
from typing import Optional, Dict, Any
from .state import GraphState


def get_graph_visualization() -> str:
    return """
graph TD
    Start([User Query]) --> Planner[Planning Node\nLLM Analysis]
    Planner --> Decision{Needs\nClarification?}
    Decision -->|Yes| Clarify[Clarification Node\nAsk User]
    Decision -->|No| Executor[Executor Node\nRun Tools]
    Clarify --> Wait([Wait for User])
    Executor --> Result([Output Image])
"""


def get_pipeline_mermaid(result: Dict[str, Any]) -> Optional[str]:
    """Build a small pipeline mermaid from a result returned by `run_agent`.

    Expects `result["plan"]` to be a list of steps where each step may have
    a `tool` key.
    """
    plan = result.get("plan") or []
    if not plan:
        return None

    lines = ["graph LR", "    Start([Input])"]
    for i, step in enumerate(plan):
        tool = step.get("tool", f"step_{i+1}") if isinstance(step, dict) else f"step_{i+1}"
        node_id = f"S{i+1}"
        label = f"{i+1}. {tool}"
        lines.append(f"    {node_id}[{label}]")
        if i == 0:
            lines.append(f"    Start --> {node_id}")
        else:
            prev = f"S{i}"
            lines.append(f"    {prev} --> {node_id}")

    last = f"S{len(plan)}"
    lines.append(f"    {last} --> End([Output])")
    return "\n".join(lines)


__all__ = ["get_graph_visualization", "get_pipeline_mermaid"]
