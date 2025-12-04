"""
Key optimizations:
- Uses repo planner.call_ollama (chat endpoint, faster)
- Uses repo json_validator for JSON parsing
- Uses repo config.py for model/endpoint settings
- Imports tools for execution
"""

import json
import time
from typing import Dict, Any, List, Optional
import numpy as np
import sys
from pathlib import Path

from .state import GraphState, PlannerState, create_initial_state, update_state_with_result, add_to_conversation, create_context_summary
from .prompts import SYSTEM_PROMPT, CLARIFICATION_PROMPT, FOLLOWUP_PROMPT, TOOL_DESCRIPTIONS

from . import planner

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
try:
    from tools import (
        detect_objects,
        crop_image,
        apply_filter,
        resize_image,
        create_parallax,
        super_resolution,
        inpaint_region,
        change_theme,
    )
    from tools.seg import segment_single_bbox
except Exception:
    # Fallback if not available
    detect_objects = None
    crop_image = None
    apply_filter = None
    resize_image = None
    create_parallax = None
    super_resolution = None
    inpaint_region = None
    change_theme = None
    segment_single_bbox = None


def _make_planner_state_from_graph(state: GraphState):
    """Create a PlannerState from GraphState conversation_history."""
    ps = PlannerState()
    for msg in state.get("conversation_history", []):
        if isinstance(msg, dict) and msg.get("role") and msg.get("content"):
            ps.messages.append({"role": msg.get("role"), "content": msg.get("content")})
    return ps


def plan_node(state: GraphState) -> GraphState:
    """
    Planning node: Analyze user query and create execution plan using repo planner.

    Args:
        state: Current graph state

    Returns:
        Updated state with plan
    """
    print(f"[PLAN] Planning for query: {state['query']}")

    # Get current image information
    image_info = ""
    if state.get("current_image") is not None:
        img = state["current_image"]
        h, w = img.shape[:2]
        image_info = f"Current image dimensions: {w}x{h} (width x height)"

    # Build context-aware prompt
    context_summary = create_context_summary(state)

    # Check if this is a follow-up query
    is_followup = len(state["conversation_history"]) > 1

    if is_followup:
        # Build followup prompt with context
        edit_history = "\n".join([
            f"- {step.get('description', step.get('tool', 'unknown'))}"
            for step in state.get("plan", [])
            if step.get("status") == "completed"
        ])

        detected_objects = ", ".join([
            f"{det.get('label', 'object')} (conf: {det.get('confidence', 0):.2f})"
            for det in state.get("cached_detections", [])[:5]
        ])

        segmented_objects = ", ".join(state.get("cached_segmentations", {}).keys())

        user_prompt = FOLLOWUP_PROMPT.format(
            edit_history=edit_history or "None",
            conversation_context=context_summary,
            detected_objects=detected_objects or "None",
            segmented_objects=segmented_objects or "None",
            query=state["query"]
        )
        # Add image info to followup
        if image_info:
            user_prompt = f"{image_info}\n\n{user_prompt}"
    else:
        # First query - use base system prompt
        user_prompt = f"User query: {state['query']}"
        # Add image info
        if image_info:
            user_prompt = f"{image_info}\n\n{user_prompt}"

    # Call repo planner (uses chat endpoint, lower latency)
    planner_state = _make_planner_state_from_graph(state)
    try:
        parsed_plan = planner.call_ollama(planner_state, user_prompt)
    except Exception as e:
        print(f"[PLAN] Planner error: {e}")
        parsed_plan = {
            "analysis": f"Error calling LLM: {str(e)}",
            "plan": [],
            "explain": "Failed to generate plan due to LLM error",
            "requires_confirmation": True,
            "confidence": 0.0,
            "error": str(e)
        }

    # Ensure required fields
    if not isinstance(parsed_plan, dict):
        parsed_plan = {}
    parsed_plan.setdefault("plan", [])
    parsed_plan.setdefault("analysis", "")
    parsed_plan.setdefault("explain", "")
    parsed_plan.setdefault("confidence", 0.5)
    parsed_plan.setdefault("requires_confirmation", False)

    # Update state
    new_state = state.copy()
    new_state["plan"] = parsed_plan.get("plan", [])
    new_state["analysis"] = parsed_plan.get("analysis", "")
    new_state["explain"] = parsed_plan.get("explain", "")
    new_state["confidence"] = parsed_plan.get("confidence", 0.0)
    new_state["requires_confirmation"] = parsed_plan.get("requires_confirmation", False)
    new_state["status"] = "planning_complete"

    # Add LLM response to conversation
    new_state = add_to_conversation(new_state, "assistant", parsed_plan.get("explain", ""))

    # Add plan steps with status
    for step in new_state["plan"]:
        if "status" not in step:
            step["status"] = "pending"

    print(f"[PLAN] Generated {len(new_state['plan'])} steps, confidence: {new_state['confidence']:.2f}")

    return new_state


def execute_tool(tool_name: str, image: np.ndarray, params: Dict[str, Any], state: GraphState) -> Dict[str, Any]:
    """
    Execute a single tool from tools.

    Args:
        tool_name: Name of the tool
        image: Input image
        params: Tool parameters
        state: Current state (for cached data)

    Returns:
        Tool execution result
    """
    print(f"[EXEC] Executing tool: {tool_name} with params: {params}")

    try:
        if tool_name == "detect":
            if detect_objects is None:
                return {"error": "detect_objects not available"}
            conf_threshold = params.get("conf_threshold", 0.5)
            result = detect_objects(image, conf_threshold=conf_threshold)
            return result

        elif tool_name == "seg":
            if segment_single_bbox is None:
                return {"error": "segment_single_bbox not available"}
            
            # Get bbox from cached detections
            label = params.get("label", "")
            cached_dets = state.get("cached_detections", [])

            if not cached_dets:
                return {"error": "No detections cached. Run detect first."}

            # If label is missing, try to infer it
            if not label:
                print("[EXEC] Label missing in seg params, attempting to infer...")
                query_lower = state.get("query", "").lower()
                
                # 1. Check if any detection label is in the query
                for det in cached_dets:
                    if det["label"].lower() in query_lower:
                        label = det["label"]
                        print(f"[EXEC] Inferred label from query: {label}")
                        break
                
                # 2. If still no label, and only one detection, use it
                if not label and len(cached_dets) == 1:
                    label = cached_dets[0]["label"]
                    print(f"[EXEC] Inferred label from single detection: {label}")
                
                # 3. If still no label, check for "person" as default (common case)
                if not label:
                    person_dets = [d for d in cached_dets if d["label"].lower() == "person"]
                    if person_dets:
                        label = "person"
                        print(f"[EXEC] Defaulting to label: person")

            if not label:
                return {"error": "Could not determine object to segment. Please specify object name."}

            # Find matching detection
            matching_dets = [d for d in cached_dets if d["label"].lower() == label.lower()]

            if not matching_dets:
                return {"error": f"No {label} found in detections"}

            # Use first matching detection
            bbox = matching_dets[0]["bbox"]
            result = segment_single_bbox(image, bbox, label)
            return result

        elif tool_name == "crop":
            if crop_image is None:
                return {"error": "crop_image not available"}
            bbox = params.get("bbox")
            aspect_ratio = params.get("aspect_ratio")
            result = crop_image(image, bbox=bbox, aspect_ratio=aspect_ratio)
            return result

        elif tool_name == "resize":
            if resize_image is None:
                return {"error": "resize_image not available"}
            width = params.get("width")
            height = params.get("height")
            scale = params.get("scale")
            maintain_aspect = params.get("maintain_aspect", True)
            result = resize_image(image, width=width, height=height, scale=scale, maintain_aspect=maintain_aspect)
            return result

        elif tool_name == "filter":
            if apply_filter is None:
                return {"error": "apply_filter not available"}
            filter_type = params.get("filter_type", "grayscale")
            intensity = params.get("intensity", 1.0)
            result = apply_filter(image, filter_type, intensity)
            return result

        elif tool_name == "sr":
            if super_resolution is None:
                return {"error": "super_resolution not available"}
            scale = params.get("scale", 2)
            result = super_resolution(image, scale=scale)
            return result

        elif tool_name == "inpaint":
            if inpaint_region is None:
                return {"error": "inpaint_region not available"}
            # Get mask from cached segmentations
            cached_segs = state.get("cached_segmentations", {})
            if not cached_segs:
                return {"error": "No segmentation mask cached. Run seg first."}

            # Use first available mask
            mask = list(cached_segs.values())[0]["mask"]

            # Check if we need to recover original image from history
            # This happens if the previous step was 'seg' which overwrites the image
            if state.get("results") and state["results"][-1]["tool"] == "seg":
                if state.get("image_history"):
                    print("[EXEC] Recovering image from history for inpainting")
                    image = state["image_history"][-1]

            result = inpaint_region(image, mask)
            return result

        elif tool_name == "parallax":
            if create_parallax is None:
                return {"error": "create_parallax not available"}
            mask = params.get("mask")
            depth_scale = params.get("depth_scale", 20.0)
            output_format = params.get("output_format", "html")
            result = create_parallax(image, mask=mask, depth_scale=depth_scale, output_format=output_format)
            return result

        elif tool_name == "theme_changer":
            if change_theme is None:
                return {"error": "change_theme not available"}
            time_of_day = params.get("time_of_day", 50)
            weather_class = params.get("weather_class")
            blending_mode = params.get("blending_mode", "Alpha")
            fg_intensity = params.get("fg_intensity", 0.8)
            result = change_theme(
                image,
                time_of_day=time_of_day,
            )
            return result

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    except Exception as e:
        print(f"[EXEC] Tool error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def executor_node(state: GraphState) -> GraphState:
    """
    Executor node: Execute the plan steps sequentially.

    Args:
        state: Current graph state

    Returns:
        Updated state after execution
    """
    print(f"[EXECUTOR] Starting execution of {len(state['plan'])} steps")

    new_state = state.copy()
    new_state["status"] = "executing"

    current_image = new_state["current_image"]

    for i, step in enumerate(new_state["plan"]):
        if step.get("status") != "pending":
            continue

        tool_name = step.get("tool", "")
        params = step.get("params", {})

        print(f"[EXECUTOR] Step {i+1}/{len(new_state['plan'])}: {tool_name}")

        # Update step status
        step["status"] = "running"

        # Execute tool
        start_time = time.time()
        result = execute_tool(tool_name, current_image, params, new_state)
        execution_time = time.time() - start_time

        # Check for errors
        if "error" in result:
            step["status"] = "failed"
            step["error"] = result["error"]
            new_state["status"] = "error"
            new_state["error"] = result["error"]
            print(f"[EXECUTOR] Step failed: {result['error']}")
            break

        # Update state with result
        new_state = update_state_with_result(new_state, result, tool_name)

        # Update current image for next step
        if new_state["current_image"] is not None:
            current_image = new_state["current_image"]

        # Mark step as complete
        step["status"] = "completed"

        # Record result
        if not new_state["results"]:
            new_state["results"] = []
        new_state["results"].append({
            "tool": tool_name,
            "success": True,
            "execution_time": execution_time,
            "result": result
        })

        # Add to pipeline_nodes for session-wide visualization
        if "pipeline_nodes" not in new_state:
            new_state["pipeline_nodes"] = []

        # Create a lightweight result summary for the node
        node_result = {k: v for k, v in result.items() if k not in ['image', 'mask', 'filtered_image', 'cropped_image', 'resized_image', 'upscaled_image', 'inpainted_image', 'transformed_image']}

        new_state["pipeline_nodes"].append({
            "id": f"step_{len(new_state['pipeline_nodes'])+1}",
            "tool": tool_name,
            "status": "completed",
            "result": node_result,
            "timestamp": time.time()
        })

        print(f"[EXECUTOR] Step {i+1} completed in {execution_time:.2f}s")

    # Check if all steps completed
    all_completed = all(step.get("status") == "completed" for step in new_state["plan"])

    if all_completed:
        new_state["status"] = "completed"
        print(f"[EXECUTOR] All steps completed successfully")
    elif new_state["status"] != "error":
        new_state["status"] = "partial"

    return new_state


def should_clarify(state: GraphState) -> str:
    """
    Routing function: Determine if clarification is needed.

    Args:
        state: Current state

    Returns:
        "clarify" if clarification needed, "execute" otherwise
    """
    if state.get("requires_confirmation") or state.get("needs_clarification"):
        return "clarify"
    return "execute"


def clarification_node(state: GraphState) -> GraphState:
    """
    Clarification node: Ask user for clarification using repo planner.

    Args:
        state: Current state

    Returns:
        Updated state with clarification request
    """
    print(f"[CLARIFY] Asking for clarification")

    new_state = state.copy()
    new_state["status"] = "clarifying"
    new_state["needs_clarification"] = True

    # Generate clarification question if not already set
    if not new_state.get("clarification_question"):
        context_summary = create_context_summary(new_state)

        prompt = CLARIFICATION_PROMPT.format(
            conversation_context=context_summary,
            query=new_state["query"]
        )

        planner_state = _make_planner_state_from_graph(new_state)
        try:
            parsed = planner.call_ollama(planner_state, prompt)
            if isinstance(parsed, dict):
                new_state["clarification_question"] = parsed.get(
                    "clarification_question",
                    "Could you please provide more details about what you'd like to do?"
                )
            else:
                new_state["clarification_question"] = "Could you please clarify what you'd like to do with the image?"
        except Exception:
            new_state["clarification_question"] = "Could you please clarify what you'd like to do with the image?"

    return new_state


def create_graph():
    """
    Create a simple graph-like object

    Returns an object with invoke(state) method that runs plan -> [clarify|executor].
    """
    class _SimpleGraph:
        def invoke(self, state: GraphState) -> GraphState:
            # Run planner
            s = plan_node(state)

            # Check if clarification needed
            if should_clarify(s) == "clarify":
                return clarification_node(s)

            # Otherwise execute
            return executor_node(s)

    return _SimpleGraph()


def run_agent(query: str, image: np.ndarray, session_id: Optional[str] = None, existing_state: Optional[GraphState] = None) -> Dict[str, Any]:
    """
    Run the conversational agent on a query.

    This is the main entry point for the orchestrator.

    Args:
        query: User query/command
        image: Input image
        session_id: Optional session ID for continuity
        existing_state: Optional existing state to continue from

    Returns:
        Dict with result_image, status, state, etc.
    """
    # Create or update state
    if existing_state:
        state = existing_state.copy()
        state["query"] = query
        state = add_to_conversation(state, "user", query)
    else:
        state = create_initial_state(image, query, session_id)

    # Create and run graph
    graph = create_graph()

    try:
        # Run the graph
        final_state = graph.invoke(state)

        # Extract result
        result = {
            "result_image": final_state.get("current_image"),
            "status": final_state.get("status", "unknown"),
            "confidence": final_state.get("confidence", 0.0),
            "explain": final_state.get("explain", ""),
            "state": final_state,
            "html_output": final_state.get("html_output"),
        }

        return result

    except Exception as e:
        print(f"[AGENT] Error: {e}")
        import traceback
        traceback.print_exc()

        return {
            "result_image": None,
            "status": "error",
            "confidence": 0.0,
            "explain": f"Error: {str(e)}",
            "state": state,
            "html_output": None,
        }


def route_query(query: str) -> Dict[str, Any]:
    """
    Quick query routing without full execution (for analysis).

    Args:
        query: User query

    Returns:
        Routing information
    """
    # Simple keyword-based routing for quick analysis
    query_lower = query.lower()

    detected_intent = "unknown"
    suggested_tools = []
    workflow_type = "step_by_step"

    # One-tap workflows
    if any(kw in query_lower for kw in ["parallax", "3d", "depth", "live photo"]):
        detected_intent = "parallax_effect"
        suggested_tools = ["parallax"]
        workflow_type = "one_tap"
    elif any(kw in query_lower for kw in ["night", "day", "evening", "weather", "sunset", "sunrise"]):
        detected_intent = "theme_change"
        suggested_tools = ["theme_changer"]
        workflow_type = "one_tap"

    # Multi-step workflows
    elif any(kw in query_lower for kw in ["remove", "erase", "delete"]):
        detected_intent = "object_removal"
        suggested_tools = ["detect", "seg", "inpaint"]
    elif any(kw in query_lower for kw in ["black and white", "grayscale", "vintage", "filter"]):
        detected_intent = "filter_application"
        suggested_tools = ["filter"]
    elif any(kw in query_lower for kw in ["crop", "trim", "square"]):
        detected_intent = "crop"
        suggested_tools = ["crop"]
    elif any(kw in query_lower for kw in ["resize", "scale", "smaller", "larger"]):
        detected_intent = "resize"
        suggested_tools = ["resize"]
    elif any(kw in query_lower for kw in ["enhance", "upscale", "quality"]):
        detected_intent = "super_resolution"
        suggested_tools = ["sr"]
    elif any(kw in query_lower for kw in ["detect", "find", "locate"]):
        detected_intent = "detection"
        suggested_tools = ["detect"]
    elif any(kw in query_lower for kw in ["segment", "mask", "isolate"]):
        detected_intent = "segmentation"
        suggested_tools = ["detect", "seg"]

    return {
        "detected_intent": detected_intent,
        "suggested_tools": suggested_tools,
        "workflow_type": workflow_type,
        "confidence": 0.8 if detected_intent != "unknown" else 0.3,
        "parameters": {}
    }


__all__ = [
    "create_graph",
    "run_agent",
    "route_query",
    "create_initial_state",
    "GraphState",
    "SYSTEM_PROMPT",
]
