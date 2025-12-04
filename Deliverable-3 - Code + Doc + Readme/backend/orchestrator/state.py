"""
State management for the optimised orchestrator.
"""

from typing import TypedDict, List, Dict, Any, Optional
from dataclasses import dataclass, field
import uuid
from datetime import datetime
import copy


class GraphState(TypedDict):
    """State schema for the conversational image editing graph."""

    # Session management
    session_id: str
    timestamp: str

    # Image data
    current_image: Optional[Any]
    original_image: Optional[Any]
    image_history: List[Any]

    # Query and intent
    query: str
    user_intent: str

    # Conversation context
    conversation_history: List[Dict[str, str]]
    previous_queries: List[str]
    context_summary: str

    # Execution plan
    plan: List[Dict[str, Any]]
    current_step: int
    explain: str
    analysis: str

    # Execution state
    status: str
    results: List[Dict[str, Any]]
    intermediate_images: List[Any]
    intermediate_thumbnails: List[Any]
    pipeline_nodes: List[Dict[str, Any]]

    # Cached results (for multi-turn optimization)
    cached_detections: List[Dict[str, Any]]
    cached_segmentations: Dict[str, Any]
    cached_metadata: Dict[str, Any]

    # User interaction
    requires_confirmation: bool
    needs_clarification: bool
    clarification_question: str
    user_feedback: Optional[str]

    # Confidence and error handling
    confidence: float
    error: Optional[str]

    # Branching and undo
    edit_branches: Dict[str, Any]
    active_branch: str
    can_undo: bool
    can_redo: bool

    # Metadata
    metadata: Dict[str, Any]
    overlays: Dict[str, Any]

    # Output
    media_type: str
    html_output: Optional[str]


def create_initial_state(image: Any, query: str, session_id: Optional[str] = None) -> GraphState:
    if session_id is None:
        session_id = str(uuid.uuid4())

    return GraphState(
        session_id=session_id,
        timestamp=datetime.now().isoformat(),
        current_image=copy.deepcopy(image) if image is not None else None,
        original_image=copy.deepcopy(image) if image is not None else None,
        image_history=[],
        query=query,
        user_intent="",
        conversation_history=[{"role": "user", "content": query, "timestamp": datetime.now().isoformat()}],
        previous_queries=[],
        context_summary="",
        plan=[],
        current_step=0,
        explain="",
        analysis="",
        status="idle",
        results=[],
        intermediate_images=[],
        intermediate_thumbnails=[],
        pipeline_nodes=[],
        cached_detections=[],
        cached_segmentations={},
        cached_metadata={},
        requires_confirmation=False,
        needs_clarification=False,
        clarification_question="",
        user_feedback=None,
        confidence=0.0,
        error=None,
        edit_branches={},
        active_branch="main",
        can_undo=False,
        can_redo=False,
        metadata={},
        overlays={},
        media_type="image",
        html_output=None,
    )


def create_session_state(image: Any) -> GraphState:
    return create_initial_state(image, "")


def update_state_with_result(state: GraphState, result: Dict[str, Any], tool_name: str) -> GraphState:
    new_state = copy.deepcopy(state)

    # Save current image to history for undo
    if new_state.get("current_image") is not None:
        if not new_state.get("image_history"):
            new_state["image_history"] = []
        new_state["image_history"].append(copy.deepcopy(new_state["current_image"]))
        new_state["can_undo"] = True

    # Find the image key using same priority as original
    image_key = f"{tool_name}_image" if f"{tool_name}_image" in result else \
                "filtered_image" if "filtered_image" in result else \
                "cropped_image" if "cropped_image" in result else \
                "resized_image" if "resized_image" in result else \
                "upscaled_image" if "upscaled_image" in result else \
                "inpainted_image" if "inpainted_image" in result else \
                "transformed_image" if "transformed_image" in result else \
                "transformed_image" if "transformed_image" in result else \
                "masked_image" if "masked_image" in result else \
                None

    if image_key and image_key in result:
        new_state["current_image"] = result[image_key]


        # Add to intermediate images
        if not new_state.get("intermediate_images"):
            new_state["intermediate_images"] = []
        new_state["intermediate_images"].append(copy.deepcopy(result[image_key]))
    else:
        pass

    # Cache detection results
    if tool_name == "detect" and "detections" in result:
        new_state["cached_detections"] = result["detections"]
        if "annotated_image" in result:
            if not new_state.get("overlays"):
                new_state["overlays"] = {}
            new_state["overlays"]["detection"] = result["annotated_image"]

    # Cache segmentation results
    if tool_name == "seg" and "mask" in result:
        label = result.get("label", "object")
        if not new_state.get("cached_segmentations"):
            new_state["cached_segmentations"] = {}
        new_state["cached_segmentations"][label] = {
            "mask": result["mask"],
            "coverage": result.get("coverage", 0),
        }

    # Store HTML output for parallax
    if tool_name == "parallax" and "html" in result:
        new_state["html_output"] = result["html"]
        new_state["media_type"] = "html"

    return new_state


def undo_last_edit(state: GraphState) -> GraphState:
    new_state = copy.deepcopy(state)
    if new_state.get("image_history") and len(new_state.get("image_history")) > 0:
        new_state["current_image"] = new_state["image_history"].pop()
        if new_state.get("intermediate_images") and len(new_state.get("intermediate_images")) > 0:
            new_state["intermediate_images"].pop()
        new_state["can_undo"] = len(new_state.get("image_history")) > 0
        new_state["can_redo"] = True
    return new_state


def add_to_conversation(state: GraphState, role: str, content: str) -> GraphState:
    new_state = copy.deepcopy(state)
    if not new_state.get("conversation_history"):
        new_state["conversation_history"] = []
    new_state["conversation_history"].append({"role": role, "content": content, "timestamp": datetime.now().isoformat()})
    return new_state


def create_context_summary(state: GraphState, max_messages: int = 5) -> str:
    if not state.get("conversation_history"):
        return ""
    recent = state["conversation_history"][-max_messages:]
    parts = []
    for msg in recent:
        role = msg.get("role")
        content = msg.get("content")
        parts.append(f"{role.capitalize()}: {content}")
    return "\n".join(parts)

__all__ = [
    "GraphState",
    "create_initial_state",
    "create_session_state",
    "update_state_with_result",
    "create_context_summary",
    "PlannerState",
]


@dataclass
class PlannerState:
    messages: List[Dict] = field(default_factory=list)
    last_latency: float = 0.0
    cold_start_latency: float = 0.0
    turn: int = 0
