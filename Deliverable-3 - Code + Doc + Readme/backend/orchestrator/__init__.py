"""
Optimised orchestrator package that mirrors the original
`orchestrator` layout but uses the repository's low-latency
`planner.call_ollama` for planning.

This module re-exports the same public API as the original orchestrator
so it can be used as a drop-in replacement.
"""

import sys
from pathlib import Path
# Add parent directory to path for root modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from .graph import create_graph, run_agent, route_query
from .state import create_initial_state, create_session_state, undo_last_edit, GraphState
from .prompts import SYSTEM_PROMPT
from .visualization import get_graph_visualization, get_pipeline_mermaid

__all__ = [
    "create_graph",
    "run_agent",
    "route_query",
    "create_initial_state",
    "create_session_state",
    "undo_last_edit",
    "GraphState",
    "SYSTEM_PROMPT",
    "get_graph_visualization",
    "get_pipeline_mermaid",
]
