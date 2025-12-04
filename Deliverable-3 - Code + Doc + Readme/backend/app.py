"""
Streamlit UI for AI Photo Editor
"""

import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import cv2
from PIL import Image
import io
import json
import time
import uuid
import asyncio
import threading
import queue
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

try:
    from streamlit_mermaid import mermaid
except Exception:
    def mermaid(diagram: str, height: int = 500, scrolling: bool = True):
        """
        Fallback mermaid renderer using components.html and the mermaid CDN.
        This avoids hard import errors when streamlit_mermaid is not installed.
        """
        html = f"""
        <div class="mermaid">
        {diagram}
        </div>
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>mermaid.initialize({{startOnLoad:true}});</script>
        """
        components.html(html, height=height, scrolling=scrolling)

# Add project to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import (
    run_agent,
    route_query,
    get_graph_visualization,
    get_pipeline_mermaid,
    create_session_state,
    undo_last_edit
)
from tools import (
    detect_objects, segment_object, crop_image, apply_filter,
    resize_image, create_parallax, super_resolution, inpaint_region,
    change_theme, get_available_weather_classes
)
from tools.seg import segment_with_detection, segment_multiple_objects, segment_single_bbox
from tools.filter import get_available_filters
from quick_agent_mode.quick_agent import QuickAgentGemma

# Import tiefling viewer for 3D parallax rendering
from components.tiefling_viewer import tiefling_viewer_v2

import wave
import threading

st.set_page_config(
    page_title="AI Photo Editor",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        max-width: 100%;
    }
    .tool-card {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .status-idle { color: #666; }
    .status-running { color: #ff9800; }
    .status-done { color: #4caf50; }
    .status-error { color: #f44336; }
    .analysis-box {
        background: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 15px;
        margin: 10px 0;
        border-radius: 0 8px 8px 0;
    }
    .plan-step {
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

def load_image(uploaded_file) -> np.ndarray:
    """Load image from uploaded file."""
    image = Image.open(uploaded_file)
    image = np.array(image)
    if len(image.shape) == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
    elif image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    return image

def display_image(image: np.ndarray, caption: str = ""):
    """Display image in Streamlit."""
    if image is None:
        st.warning("No image to display")
        return

    # Convert BGR to RGB for display
    if len(image.shape) == 3 and image.shape[2] == 3:
        display_img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    elif len(image.shape) == 3 and image.shape[2] == 4:
        display_img = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
    else:
        display_img = image

    st.image(display_img, caption=caption, width=display_img.shape[1])

def main():
    st.title("🎨 AI Photo Editor")

    # Initialize session state
    if "image" not in st.session_state:
        st.session_state.image = None
    if "result_image" not in st.session_state:
        st.session_state.result_image = None
    if "pipeline_state" not in st.session_state:
        st.session_state.pipeline_state = None
    if "history" not in st.session_state:
        st.session_state.history = []
    if "html_output" not in st.session_state:
        st.session_state.html_output = None
    
    
    
    # Sidebar
    with st.sidebar:
        st.header("📤 Upload Image")
        uploaded_file = st.file_uploader(
            "Choose an image",
            type=["jpg", "jpeg", "png", "bmp", "webp"]
        )

        if uploaded_file is not None:
            st.session_state.image = load_image(uploaded_file)
            st.success(f"Loaded: {uploaded_file.name}")

        st.divider()

        # Mode selection
        st.header("🔧 Mode")
        mode = st.radio(
            "Select mode",
            ["AI Assistant", "Quick Edits", "Manual Tools", "Pipeline Viewer"],
            index=0
        )

        st.divider()

       
        
        # Quick actions
        st.header("⚡ Quick Actions")
        if st.button("Reset Image"):
            st.session_state.result_image = None
            st.session_state.pipeline_state = None
            st.session_state.html_output = None
            st.rerun()

        # Undo button
        if st.session_state.pipeline_state and st.session_state.pipeline_state.get("image_history"):
            if st.button("↩️ Undo Last Edit"):
                state = undo_last_edit(st.session_state.pipeline_state)
                st.session_state.pipeline_state = state
                if state["current_image"] is not None:
                    st.session_state.result_image = state["current_image"]
                st.rerun()

        if st.session_state.result_image is not None:
            # Download button
            result_rgb = cv2.cvtColor(st.session_state.result_image, cv2.COLOR_BGR2RGB)
            result_pil = Image.fromarray(result_rgb)
            buf = io.BytesIO()
            result_pil.save(buf, format="PNG")
            st.download_button(
                "Download Result",
                buf.getvalue(),
                "edited_photo.png",
                "image/png"
            )

        # Download HTML if available
        if st.session_state.html_output:
            st.download_button(
                "Download Parallax HTML",
                st.session_state.html_output,
                "parallax.html",
                "text/html"
            )
        

    # Main content area
    if st.session_state.image is None:
        st.info("👆 Please upload an image to get started")
        return

    if mode == "AI Assistant":
        render_ai_assistant()
    elif mode == "Quick Edits":
        render_quick_edits()
    elif mode == "Manual Tools":
        render_manual_tools()
    else:
        render_pipeline_viewer()

def render_ai_assistant():
    """Render AI assistant interface"""
    st.header("🤖 AI Assistant")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Original")
        display_image(st.session_state.image)

    with col2:
        st.subheader("Result")
        # Check if we have HTML output (parallax)
        if st.session_state.pipeline_state and st.session_state.pipeline_state.get("media_type") == "html":
            html_content = st.session_state.pipeline_state.get("html_output", "")
            if html_content:
                st.session_state.html_output = html_content
                components.html(html_content, height=500, scrolling=True)
        elif st.session_state.result_image is not None:
            display_image(st.session_state.result_image)
        else:
            st.info("Result will appear here")

    # Query input
    st.divider()
    if "auto_query" not in st.session_state:
        st.session_state.auto_query = ""

    query = st.text_input(
        "What would you like to do?",
        placeholder="e.g., 'Make it grayscale and brighter', 'Create 3D parallax effect'",
        value=st.session_state.auto_query,
        key="query_input"
    )

 
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        run_button = st.button("🚀 Run", type="primary", use_container_width=True)
    with col2:
        # Commit changes button
        if st.button("💾 Commit Changes", use_container_width=True, help="Save current result as new input image"):
            if st.session_state.result_image is not None:
                st.session_state.image = st.session_state.result_image
                st.session_state.pipeline_state = None
                st.session_state.result_image = None
                st.session_state.html_output = None
                st.session_state.history = []  # Clear history for fresh start
                st.success("Changes committed! You can now continue editing.")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("No result to commit")
    with col3:
        # Clear session button
        if st.button("🔄 New Session", use_container_width=True):
            st.session_state.pipeline_state = None
            st.session_state.result_image = None
            st.session_state.html_output = None
            st.rerun()

    # Handle human feedback when LLM asks a clarification question
    if st.session_state.pipeline_state and st.session_state.pipeline_state.get("needs_clarification"):
        st.divider()
        clarification_q = st.session_state.pipeline_state.get("clarification_question", "")
        st.warning(f"🤔 **AI Assistant asks:** {clarification_q}")

       
        # Text input for clarification
        user_response = st.text_input("Or type your response:", key="human_feedback_input",
                                      placeholder="e.g., 'the left one', 'first', 'rightmost person'")
        if st.button("📤 Send Response", type="primary"):
            if user_response:
                with st.spinner("Continuing..."):
                    current_image = st.session_state.result_image if st.session_state.result_image is not None else st.session_state.image
                    result = run_agent(
                        user_response,
                        current_image,
                        existing_state=st.session_state.pipeline_state
                    )
                    state = result["state"]
                    st.session_state.pipeline_state = state
                    if result["result_image"] is not None:
                        st.session_state.result_image = result["result_image"]
                    if result.get("html_output"):
                        st.session_state.html_output = result["html_output"]
                    st.rerun()

    if run_button and query:
        with st.spinner("Processing..."):
            try:
                # Run the new agent with multi-turn support
                current_image = st.session_state.result_image if st.session_state.result_image is not None else st.session_state.image
                existing_state = st.session_state.pipeline_state if st.session_state.pipeline_state else None

                result = run_agent(
                    query,
                    current_image,
                    existing_state=existing_state
                )

                # Extract state from result
                state = result["state"]
                st.session_state.pipeline_state = state

                if result["result_image"] is not None:
                    st.session_state.result_image = result["result_image"]

                # Store HTML output
                if result.get("html_output"):
                    st.session_state.html_output = result["html_output"]

                # Add to history
                st.session_state.history.append({
                    "query": query,
                    "status": result["status"],
                    "explain": result.get("explain", "")
                })

                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")

    # Display pipeline state
    if st.session_state.pipeline_state:
        state = st.session_state.pipeline_state

        st.divider()

        # Session info
        with st.expander("📋 Session Info", expanded=False):
            st.write(f"**Session ID:** {state.get('session_id', 'N/A')}")
            st.write(f"**Status:** {state.get('status', 'unknown')}")
            if state.get("error"):
                st.error(f"**Error:** {state['error']}")

        # Query Routing Info
        routing_info = state.get("metadata", {}).get("routing", {})
        if routing_info:
            with st.expander("🎯 Query Analysis", expanded=True):
                detected_intent = routing_info.get("detected_intent", "unknown")
                confidence = routing_info.get("confidence", 0)
                workflow_type = routing_info.get("workflow_type", "unknown")

                st.markdown(f"""
                    <div style="background-color: #e3f2fd; padding: 10px; border-radius: 6px; margin-bottom: 10px;">
                        <strong>Detected Intent:</strong> {detected_intent}<br>
                        <strong>Confidence:</strong> {confidence:.0%}<br>
                        <strong>Workflow Type:</strong> {workflow_type}
                    </div>
                    """, unsafe_allow_html=True)

                # Show suggested tools
                suggested_tools = routing_info.get("suggested_tools", [])
                if suggested_tools:
                    st.write("**Suggested Tools:**", ", ".join(suggested_tools))

                # Show parameters
                params = routing_info.get("parameters", {})
                if params:
                    st.write("**Parameters:**")
                    st.json(params)

        # Explanation
        with st.expander("🧠 LLM Analysis", expanded=True):
            explain_text = state.get('explain', 'No explanation')
            if explain_text:
                st.markdown(f"""
                    <div class="analysis-box"
                        style="color: black; background-color: #f5f5f5; padding: 10px; border-radius: 6px;">
                        {explain_text}
                    </div>
                    """, unsafe_allow_html=True)

        # Plan
        with st.expander("📋 Execution Plan", expanded=True):
            plan = state.get("plan", [])
            if plan:
                for i, step in enumerate(plan):
                    # Get status icon based on step status
                    step_status = step.get('status', 'pending')
                    if step_status == 'completed':
                        status_icon = "✅"
                        bg_color = "#e8f5e9"  # Light green
                    elif step_status == 'running':
                        status_icon = "🔄"
                        bg_color = "#fff3e0"  # Light orange
                    elif step_status == 'failed':
                        status_icon = "❌"
                        bg_color = "#ffebee"  # Light red
                    else:  # pending
                        status_icon = "⏳"
                        bg_color = "#f5f5f5"  # Light gray

                    st.markdown(f"""
                        <div class="plan-step"
                            style="color: black; background-color: {bg_color}; padding: 8px; border-radius: 6px; margin-bottom: 6px;">
                            {status_icon} <strong>Step {i+1}: {step.get('tool', 'unknown')}</strong><br>
                            {step.get('description', '')}
                        </div>
                        """, unsafe_allow_html=True)

            else:
                st.info("No plan generated")

        # Raw JSON
        with st.expander("📝 Raw JSON Plan"):
            st.json({
                "session_id": state.get("session_id", ""),
                "plan": state.get("plan", []),
                "explain": state.get("explain", ""),
                "status": state.get("status", ""),
                "cached_detections": len(state.get("cached_detections", [])),
                "cached_segmentations": list(state.get("cached_segmentations", {}).keys())
            })

        # Conversation History
        if state.get("conversation_history"):
            with st.expander("💬 Conversation History", expanded=False):
                for entry in state["conversation_history"]:
                    role = entry.get("role", "unknown")
                    content = entry.get("content", "")
                    icon = "👤" if role == "user" else "🤖"
                    st.markdown(f"{icon} **{role.capitalize()}:** {content}")

        # Cached Results (Detection & Segmentation)
        cached_dets = state.get("cached_detections", [])
        cached_segs = state.get("cached_segmentations", {})
        if cached_dets or cached_segs:
            with st.expander("🎯 Detection & Segmentation Results", expanded=True):
                if cached_dets:
                    st.write("**Detected Objects:**")
                    # Group by label
                    label_groups = {}
                    for det in cached_dets:
                        label = det.get('label', 'unknown')
                        if label not in label_groups:
                            label_groups[label] = []
                        label_groups[label].append(det)

                    for label, dets in label_groups.items():
                        st.write(f"**{label}** ({len(dets)} found):")
                        for i, det in enumerate(dets):
                            bbox = det.get('bbox', [0, 0, 0, 0])
                            conf = det.get('confidence', 0)
                            st.write(f"  [{i}] Confidence: {conf:.0%}, BBox: {bbox}")

                if cached_segs:
                    st.write("**Segmented Objects:**")
                    for label in cached_segs.keys():
                        seg = cached_segs[label]
                        st.write(f"- **{label}**: {seg.get('coverage', 0):.1f}% coverage")

        # Results
        if state.get("results"):
            with st.expander("📊 Execution Results"):
                for result in state["results"]:
                    status = "✅" if result["success"] else "❌"
                    st.write(f"{status} **{result['tool']}** ({result['execution_time']:.2f}s)")
                    if result.get("error"):
                        st.error(result["error"])

        # Pipeline Steps with Intermediate Images
        pipeline_nodes = state.get("pipeline_nodes", [])
        if pipeline_nodes:
            with st.expander("🔄 Step-by-Step Pipeline", expanded=True):
                st.write(f"**Total Steps:** {len(pipeline_nodes)}")
                for i, node in enumerate(pipeline_nodes):
                    tool_name = node.get("tool", "unknown")
                    step_id = node.get("id", f"step_{i}")

                    st.markdown(f"---")
                    st.markdown(f"**Step {i+1}: {tool_name}** (ID: {step_id})")

                    # Show thumbnail if available
                    if node.get("thumbnail") is not None:
                        st.image(node["thumbnail"], caption=f"After {tool_name}", width="stretch")

                    # Show result info
                    if node.get("result"):
                        result_info = node["result"]
                        if isinstance(result_info, dict):
                            st.json(result_info)

        # Intermediate Images Gallery
        intermediate_imgs = state.get("intermediate_images", [])
        if intermediate_imgs:
            with st.expander("🖼️ Intermediate Images Gallery", expanded=False):
                cols = st.columns(min(len(intermediate_imgs), 3))
                for i, img in enumerate(intermediate_imgs):
                    with cols[i % 3]:
                        st.image(img, caption=f"Step {i+1}", width="stretch")

        # Overlays
        if state.get("overlays"):
            with st.expander("🎯 Overlays & Visualizations"):
                cols = st.columns(min(len(state["overlays"]), 3))
                for i, (name, overlay) in enumerate(state["overlays"].items()):
                    with cols[i % 3]:
                        display_image(overlay, name)

def render_quick_edits():
    """Render Quick Edits interface with Gemma 3 1B."""
    st.header("⚡ Quick Edits (Gemma 3:1B)")
    st.info("Fast, single-step edits using a lightweight local model.")

    # Initialize Quick Agent
    if "quick_agent" not in st.session_state:
        st.session_state.quick_agent = QuickAgentGemma()

    
    # Text Input
    if "quick_edit_query" not in st.session_state:
        st.session_state.quick_edit_query = ""

    query = st.text_input(
        "Enter command:",
        value=st.session_state.quick_edit_query,
        placeholder="e.g., 'Make it grayscale', 'Upscale 4x', 'Add parallax'",
        key="quick_input"
    )

    if st.button("🚀 Run Quick Edit", type="primary", use_container_width=True):
        if not query:
            st.warning("Please enter a command")
            return
        
        if st.session_state.image is None:
            st.error("Please upload an image first")
            return

        with st.spinner("Gemma is thinking..."):
            # 1. Parse with Gemma
            start_time = time.time()
            intent = st.session_state.quick_agent.parse_query(query)
            parse_time = time.time() - start_time
            
            tool_name = intent["tool"]
            params = intent["params"]
            
            st.success(f"Parsed: **{tool_name}** ({parse_time:.3f}s)")
            st.json(params)

            # 2. Execute Tool
            try:
                result_image = None
                result_html = None
                
                if tool_name == "filter":
                    res = apply_filter(st.session_state.image, params.get("type"), params.get("intensity", 1.0))
                    result_image = res["filtered_image"]
                
                elif tool_name == "super_resolution":
                    res = super_resolution(st.session_state.image, scale=params.get("scale", 4))
                    result_image = res["upscaled_image"]
                
                elif tool_name == "parallax":
                    # Auto-segment person for parallax
                    with st.spinner("Generating parallax..."):
                        res = create_parallax(
                            st.session_state.image,
                            depth_scale=params.get("depth_scale", 20),
                            output_format=params.get("output_format", "html"),
                            export_json=True  # Always export for flexibility
                        )
                        # Store the full result for 3D viewer access
                        st.session_state.parallax_result = res

                        if "html" in res:
                            result_html = res["html"]
                        elif "frames" in res:
                            result_image = res["frames"][0]
                
                elif tool_name == "theme_changer":
                    with st.spinner("Changing theme..."):
                        res = change_theme(
                            st.session_state.image,
                            time_of_day=params.get("time_of_day", 50)
                        )
                        result_image = res["transformed_image"]
                
                elif tool_name == "crop":
                    res = crop_image(st.session_state.image, aspect_ratio=params.get("aspect_ratio"))
                    result_image = res["cropped_image"]
                
                elif tool_name == "resize":
                    res = resize_image(st.session_state.image, scale=params.get("scale", 1.0))
                    result_image = res["resized_image"]
                
                else:
                    st.error(f"Unknown tool: {tool_name}")

                # 3. Show Result
                if result_image is not None:
                    st.session_state.result_image = result_image
                    st.session_state.html_output = None # Clear HTML if image result
                
                if result_html is not None:
                    st.session_state.html_output = result_html
                    st.session_state.pipeline_state = {"media_type": "html", "html_output": result_html} # Hack for display
                
                st.rerun()

            except Exception as e:
                st.error(f"Execution failed: {e}")

    # Display Results
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Original")
        display_image(st.session_state.image)
    
    with col2:
        st.subheader("Result")
        if st.session_state.html_output:
            components.html(st.session_state.html_output, height=500)
        elif st.session_state.result_image is not None:
            display_image(st.session_state.result_image)
        else:
            st.info("Result will appear here")

    # Commit Changes
    if st.session_state.result_image is not None:
        if st.button("💾 Commit Changes", use_container_width=True):
            st.session_state.image = st.session_state.result_image
            st.session_state.result_image = None
            st.session_state.html_output = None
            st.success("Changes saved!")
            st.rerun()

def render_manual_tools():
    """Render manual tool controls."""
    st.header("🔧 Manual Tools")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Input")
        display_image(st.session_state.image)

    # Tool selection
    st.divider()
    tool = st.selectbox(
        "Select Tool",
        ["detect", "seg", "filter", "crop", "resize", "parallax", "sr", "inpaint", "theme_changer"]
    )

    result = None

    if tool == "detect":
        st.subheader("Object Detection (YOLO)")
        conf = st.slider("Confidence Threshold", 0.1, 1.0, 0.5)
        if st.button("Run Detection"):
            with st.spinner("Detecting..."):
                result = detect_objects(st.session_state.image, conf_threshold=conf)
                st.session_state.result_image = result["annotated_image"]

            st.success(f"Found {result['count']} objects")
            for det in result["detections"]:
                st.write(f"- {det['label']}: {det['confidence']:.2f}")

    elif tool == "seg":
        st.subheader("Segmentation (MobileSAM)")

        # Step 1: Detection (run first or use cached)
        if 'cached_detections' not in st.session_state or st.button("🔍 Detect Objects First"):
            with st.spinner("Detecting objects..."):
                det_result = detect_objects(st.session_state.image, conf_threshold=0.5)
                st.session_state.cached_detections = det_result["detections"]
                st.session_state.annotated_detection = det_result["annotated_image"]

        # Step 2: Display detections and selection UI
        if 'cached_detections' in st.session_state and st.session_state.cached_detections:
            detections = st.session_state.cached_detections

            # Show annotated image with detections
            with st.expander("📸 View Detected Objects", expanded=True):
                display_image(st.session_state.annotated_detection, "Detected Objects")

            st.info(f"**Found {len(detections)} objects**")

            # Multi-select mode toggle
            multi_select = st.checkbox("🎯 Segment multiple objects", value=False,
                                       help="Select multiple objects to segment together")

            if multi_select:
                # ===== MULTI-SELECT MODE =====
                st.markdown("**Select objects to segment:**")

                # Create selection UI
                selected_indices = []

                # Group by class for better organization
                class_groups = {}
                for i, det in enumerate(detections):
                    label = det['label']
                    if label not in class_groups:
                        class_groups[label] = []
                    class_groups[label].append((i, det))

                # Display grouped by class
                for class_label in sorted(class_groups.keys()):
                    st.markdown(f"**{class_label.title()}** ({len(class_groups[class_label])} found)")

                    for idx, (i, det) in enumerate(class_groups[class_label]):
                        col1, col2, col3, col4 = st.columns([1, 2, 2, 2])

                        with col1:
                            if st.checkbox("Select", key=f"det_{i}"):
                                selected_indices.append(i)
                        with col2:
                            st.write(f"#{i}")
                        with col3:
                            st.write(f"{det['confidence']:.1%}")
                        with col4:
                            bbox = det['bbox']
                            st.write(f"Size: {bbox[2]-bbox[0]}×{bbox[3]-bbox[1]}")

                # Segment button
                st.divider()
                if st.button("✂️ Segment Selected Objects", type="primary", disabled=len(selected_indices) == 0):
                    if not selected_indices:
                        st.warning("⚠️ Please select at least one object")
                    else:
                        selected_bboxes = [detections[i]['bbox'] for i in selected_indices]
                        selected_labels = [detections[i]['label'] for i in selected_indices]

                        with st.spinner(f"Segmenting {len(selected_indices)} objects..."):
                            result = segment_multiple_objects(
                                st.session_state.image,
                                selected_bboxes,
                                selected_labels
                            )
                            st.session_state.result_image = result["masked_image"]
                            st.session_state.mask = result["combined_mask"]
                            st.session_state.individual_masks = result["individual_masks"]

                        st.success(f"✓ Segmented {result['count']} objects! Total coverage: {result['coverage']:.1f}%")

                        # Show per-object info
                        with st.expander("📊 Per-Object Details"):
                            for i, (label, mask) in enumerate(zip(result['labels'], result['individual_masks'])):
                                coverage = (mask > 0).sum() / mask.size * 100
                                st.write(f"**{label}**: {coverage:.1f}% coverage")

            else:
                # ===== SINGLE-SELECT MODE =====
                # Group by class
                class_groups = {}
                for i, det in enumerate(detections):
                    label = det['label']
                    if label not in class_groups:
                        class_groups[label] = []
                    class_groups[label].append((i, det))

                # Class selection
                selected_class = st.selectbox("🏷️ Select object class:",
                                              sorted(class_groups.keys()),
                                              help="Choose the type of object to segment")

                class_objects = class_groups[selected_class]

                # Index selection if multiple of same class
                if len(class_objects) > 1:
                    st.write(f"Found **{len(class_objects)}** {selected_class}(s):")

                    # Show radio buttons with details
                    selected_idx = st.radio(
                        "Select which one to segment:",
                        range(len(class_objects)),
                        format_func=lambda i: (
                            f"#{class_objects[i][0]} - "
                            f"Confidence: {class_objects[i][1]['confidence']:.1%}, "
                            f"Size: {class_objects[i][1]['size'][0]}×{class_objects[i][1]['size'][1]}px"
                        ),
                        help="Choose the specific object instance"
                    )
                    bbox_index = selected_idx
                else:
                    bbox_index = 0
                    st.info(f"✓ Found 1 {selected_class}")

                # Segment button
                st.divider()
                if st.button("✂️ Segment Object", type="primary"):
                    det_index, detection = class_objects[bbox_index]

                    with st.spinner(f"Segmenting {selected_class}..."):
                        result = segment_single_bbox(
                            st.session_state.image,
                            detection['bbox'],
                            selected_class
                        )
                        st.session_state.result_image = result["masked_image"]
                        st.session_state.mask = result["mask"]

                    st.success(f"✓ Segmented {selected_class} - Coverage: {result['coverage']:.1f}%")

                    # Show bbox info
                    bbox = detection['bbox']
                    st.write(f"**BBox:** [{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}]")

        else:
            st.info("👆 Click 'Detect Objects First' to find objects in the image")

    elif tool == "filter":
        st.subheader("Filters")
        filter_type = st.selectbox("Filter Type", get_available_filters())
        intensity = st.slider("Intensity", 0.0, 2.0, 1.0)
        if st.button("Apply Filter"):
            result = apply_filter(st.session_state.image, filter_type, intensity)
            st.session_state.result_image = result["filtered_image"]

    elif tool == "crop":
        st.subheader("Crop")
        aspect = st.selectbox("Aspect Ratio", ["Custom", "1:1", "4:3", "16:9", "9:16"])
        if aspect == "Custom":
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                x1 = st.number_input("X1", 0, value=0)
            with col_b:
                y1 = st.number_input("Y1", 0, value=0)
            with col_c:
                x2 = st.number_input("X2", 0, value=st.session_state.image.shape[1])
            with col_d:
                y2 = st.number_input("Y2", 0, value=st.session_state.image.shape[0])
            bbox = [x1, y1, x2, y2]
            aspect_ratio = None
        else:
            bbox = None
            aspect_ratio = aspect

        if st.button("Crop"):
            result = crop_image(st.session_state.image, bbox=bbox, aspect_ratio=aspect_ratio)
            st.session_state.result_image = result["cropped_image"]

    elif tool == "resize":
        st.subheader("Resize")
        resize_mode = st.radio("Mode", ["By Dimensions", "By Scale"])
        if resize_mode == "By Dimensions":
            w = st.number_input("Width", 1, 8000, st.session_state.image.shape[1])
            h = st.number_input("Height", 1, 8000, st.session_state.image.shape[0])
            maintain = st.checkbox("Maintain Aspect Ratio", True)
            if st.button("Resize"):
                result = resize_image(st.session_state.image, width=w, height=h, maintain_aspect=maintain)
                st.session_state.result_image = result["resized_image"]
        else:
            scale = st.slider("Scale", 0.1, 4.0, 1.0)
            if st.button("Resize"):
                result = resize_image(st.session_state.image, scale=scale)
                st.session_state.result_image = result["resized_image"]

    elif tool == "parallax":
        st.subheader("3D Parallax Effect")

        st.info("🤖 **Automatic Mode**")

        use_cached = st.checkbox("🔄 Use previously segmented mask (optional)",
                                 value=False,
                                 help="Use mask from previous segmentation instead of automatic detection",
                                 disabled='cached_detections' not in st.session_state)

        selected_mask = None

        if use_cached and 'cached_detections' in st.session_state:
            detections = st.session_state.cached_detections

            # Multi-select or single-select mode
            multi_select = st.checkbox("🎯 Select multiple objects/classes",
                                       help="Combine multiple objects into the foreground layer")

            if multi_select:
                # ===== MULTI-SELECT MODE =====
                st.write("**Select objects to include in the foreground:**")

                # Group by class
                class_groups = {}
                for i, det in enumerate(detections):
                    label = det['label']
                    if label not in class_groups:
                        class_groups[label] = []
                    class_groups[label].append((i, det))

                selected_indices = []

                # Show checkboxes grouped by class
                for class_label in sorted(class_groups.keys()):
                    with st.expander(f"**{class_label}** ({len(class_groups[class_label])} found)", expanded=True):
                        for i, (det_idx, det) in enumerate(class_groups[class_label]):
                            bbox = det['bbox']
                            conf = det['confidence']

                            col1, col2 = st.columns([3, 1])
                            with col1:
                                selected = st.checkbox(
                                    f"{class_label} #{i+1}",
                                    key=f"parallax_multi_{det_idx}",
                                    help=f"Confidence: {conf:.2f}, BBox: {bbox}"
                                )
                            with col2:
                                st.write(f"conf: {conf:.2f}")

                            if selected:
                                selected_indices.append(det_idx)

                if selected_indices:
                    st.info(f"✓ {len(selected_indices)} object(s) selected for parallax foreground")

                    # Segment all selected objects
                    selected_bboxes = [detections[i]['bbox'] for i in selected_indices]
                    selected_labels = [detections[i]['label'] for i in selected_indices]

                    with st.spinner(f"Segmenting {len(selected_indices)} objects..."):
                        seg_result = segment_multiple_objects(
                            st.session_state.image,
                            selected_bboxes,
                            selected_labels
                        )
                        selected_mask = seg_result['combined_mask']
                        selected_label = f"{len(selected_indices)} objects"
                else:
                    st.warning("⚠️ Please select at least one object")
                    selected_label = None

            else:
                # ===== SINGLE-SELECT MODE =====
                # Group by class
                class_groups = {}
                for i, det in enumerate(detections):
                    label = det['label']
                    if label not in class_groups:
                        class_groups[label] = []
                    class_groups[label].append((i, det))

                # Class selection
                selected_class = st.selectbox("🏷️ Select object class:",
                                              sorted(class_groups.keys()),
                                              help="Choose which object to use for parallax")

                class_objects = class_groups[selected_class]

                # Index selection if multiple of same class
                if len(class_objects) > 1:
                    st.write(f"Found **{len(class_objects)}** {selected_class}(s):")
                    selected_idx = st.radio(
                        "Select which one:",
                        range(len(class_objects)),
                        format_func=lambda i: f"{selected_class} #{i+1} (conf: {class_objects[i][1]['confidence']:.2f})",
                        key="parallax_object_select"
                    )
                    _, detection = class_objects[selected_idx]
                else:
                    _, detection = class_objects[0]

                selected_bbox = detection['bbox']
                selected_label = selected_class

                # Segment the selected object for parallax
                with st.spinner(f"Segmenting {selected_label} for parallax..."):
                    seg_result = segment_single_bbox(st.session_state.image, selected_bbox, selected_label)
                    selected_mask = seg_result['mask']

        # Parallax parameters
        depth = st.slider("Depth Scale", 5.0, 50.0, 20.0,
                         help="Higher values create more pronounced 3D effect")
        output = st.selectbox("Output Format", ["3d_viewer"],
                             help="3D Viewer uses Three.js rendering, HTML for basic preview, Frames for animation")

        if st.button("✨ Create Parallax", type="primary"):
            with st.spinner("Creating parallax effect with automatic subject detection..."):
                # Create parallax with optional pre-computed mask
                # Always export all data for 3D viewer compatibility
                actual_format = "html" if output == "3d_viewer" else output
                result = create_parallax(
                    st.session_state.image,
                    mask=selected_mask,
                    depth_scale=depth,
                    output_format=actual_format,
                    export_json=True  # Always export for 3D viewer
                )

            # Show workflow steps
            with st.expander("🔍 View Workflow Steps", expanded=True):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write("**Step 1: BiRefNet Segmentation**")
                    # Convert RGBA to displayable format
                    subject_display = result['subject_layer']
                    if subject_display.shape[2] == 4:
                        # Create checkerboard background for transparency visualization
                        h, w = subject_display.shape[:2]
                        checker = np.indices((h, w)).sum(axis=0) % 2 * 50 + 100
                        checker_bg = np.stack([checker, checker, checker], axis=-1).astype(np.uint8)

                        # Alpha blend subject over checkerboard
                        alpha = subject_display[:, :, 3:4] / 255.0
                        subject_preview = (subject_display[:, :, :3] * alpha +
                                         checker_bg * (1 - alpha)).astype(np.uint8)
                        st.image(cv2.cvtColor(subject_preview, cv2.COLOR_BGR2RGB),
                               caption="Subject with transparency", use_container_width=True)

                    # Show mask from result
                    if 'mask' in result and result['mask'] is not None:
                        st.image(result['mask'], caption="Segmentation mask",
                               use_container_width=True, clamp=True)

                with col2:
                    st.write("**Step 2: MI-GAN Inpainting**")
                    bg_display = cv2.cvtColor(result['background_layer'], cv2.COLOR_BGR2RGB)
                    st.image(bg_display, caption="Inpainted background",
                           use_container_width=True)

                    # Show background depth if available
                    if 'background_depth' in result:
                        st.image(result['background_depth'], caption="Background depth map",
                               use_container_width=True, clamp=True)

                with col3:
                    st.write("**Step 3: Depth Estimation**")
                    # Show foreground depth if available
                    if 'foreground_depth' in result:
                        st.image(result['foreground_depth'], caption="Foreground depth (grounded)",
                               use_container_width=True, clamp=True)

                    st.write("**Parameters**")
                    st.write(f"- Depth Scale: {result['depth_scale']:.1f}")
                    st.write(f"- Model: BiRefNet + Depth-Anything-V2")
                    if 'num_frames' in result:
                        st.write(f"- Frames: {result['num_frames']}")
                        st.write(f"- Motion: {result['motion_type']}")

            # Display final result
            if output == "3d_viewer":
                st.session_state.result_image = None

                st.divider()
                st.subheader("🎮 3D Parallax Viewer")
                st.info("💡 Move your mouse over the image to see the advanced 3D parallax effect with depth-based rendering!")

                # Convert numpy arrays to PIL Images for the viewer
                from PIL import Image as PILImage

                # Subject (RGBA)
                subject_pil = PILImage.fromarray(cv2.cvtColor(result['subject_layer'], cv2.COLOR_BGRA2RGBA))

                # Background (BGR to RGB)
                background_pil = PILImage.fromarray(cv2.cvtColor(result['background_layer'], cv2.COLOR_BGR2RGB))

                # Foreground depth map
                fg_depth_pil = PILImage.fromarray(result['foreground_depth'])

                # Background depth map
                bg_depth_pil = PILImage.fromarray(result['background_depth'])

                # Mask
                mask_pil = PILImage.fromarray(result['mask'])
                # Render with tiefling viewer
                tiefling_viewer_v2(
                    image=subject_pil,
                    depth_map=fg_depth_pil,
                    background=background_pil,
                    background_depth_map=bg_depth_pil,
                    mask=mask_pil,
                    focus=0.75,
                    sensitivity=0.4,
                    foreground_sensitivity=0.05,
                    background_sensitivity=1.0,
                    grounded_mode=True,
                    key="parallax_3d_viewer"
                )

                # Download options
                col1,= st.columns(1)
                with col1:
                    if 'html' in result:
                        st.download_button(
                            "📥 Download HTML (fallback)",
                            result["html"],
                            "parallax.html",
                            "text/html",
                            help="Download basic HTML preview"
                        )
                
    elif tool == "sr":
        st.subheader("Super Resolution (SwinIR)")
        scale = st.selectbox("Scale", [4])
        if st.button("Upscale"):
            result = super_resolution(st.session_state.image, scale=scale)
            st.session_state.result_image = result["upscaled_image"]
            st.info(result["message"])
    elif tool == "inpaint":
        st.subheader("AI Inpainting (MI-GAN)")
        st.info("Draw on the image to mark regions for removal (stylus/mouse supported).")

        # ==== Mask Source ====
        mask_source = st.radio("Mask Source", ["Draw Mask (Recommended)", "Use Segmentation Mask"], horizontal=True)

        # ======================================================================
        # 1) DRAWN MASK (using custom HTML canvas with download workflow)
        # ======================================================================
        if mask_source == "Draw Mask (Recommended)":
            # Convert image BGR → RGB for display
            img_for_canvas = cv2.cvtColor(st.session_state.image, cv2.COLOR_BGR2RGB)
            pil_canvas_img = Image.fromarray(img_for_canvas)
            
            # Convert image to base64 for embedding in HTML
            import base64
            buffered = io.BytesIO()
            pil_canvas_img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            img_width = pil_canvas_img.width
            img_height = pil_canvas_img.height

            brush_size = st.slider("Brush Size", 5, 200, 40)

            st.write("**Step 1:** Draw on the image with your mouse or stylus to mark areas for inpainting.")
            
            # Custom HTML canvas for drawing
            canvas_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ margin: 0; padding: 20px; background: #f0f0f0; font-family: Arial, sans-serif; }}
                    #container {{ 
                        position: relative; 
                        display: inline-block;
                        border: 2px solid #333;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }}
                    #backgroundCanvas, #drawingCanvas {{
                        position: absolute;
                        top: 0;
                        left: 0;
                    }}
                    #backgroundCanvas {{ z-index: 1; }}
                    #drawingCanvas {{ 
                        z-index: 2; 
                        cursor: crosshair;
                    }}
                    .controls {{
                        margin: 10px 0;
                        padding: 10px;
                        background: white;
                        border-radius: 5px;
                    }}
                    button {{
                        padding: 10px 20px;
                        margin: 5px;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 14px;
                        font-weight: bold;
                    }}
                    .btn-primary {{ background: #4CAF50; color: white; }}
                    .btn-secondary {{ background: #2196F3; color: white; }}
                    .btn-danger {{ background: #f44336; color: white; }}
                    button:hover {{ opacity: 0.8; }}
                    button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
                    .info {{ 
                        padding: 10px; 
                        background: #e3f2fd; 
                        border-radius: 4px; 
                        margin: 10px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="controls">
                    <button class="btn-danger" onclick="clearCanvas()">🗑️ Clear</button>
                    <button class="btn-secondary" onclick="toggleView()">👁️ Toggle View</button>
                    <button class="btn-primary" onclick="downloadMask()" id="downloadBtn">⬇️ Download Mask</button>
                    <span style="margin-left: 20px;">Brush: {brush_size}px | Draw white areas to remove</span>
                </div>
                
                <div id="container">
                    <canvas id="backgroundCanvas" width="{img_width}" height="{img_height}"></canvas>
                    <canvas id="drawingCanvas" width="{img_width}" height="{img_height}"></canvas>
                </div>
                
                <div class="info" id="statusInfo">
                    Draw on the image, then click "Download Mask" to save your drawing.
                </div>
                
                <script>
                    const bgCanvas = document.getElementById('backgroundCanvas');
                    const bgCtx = bgCanvas.getContext('2d');
                    const drawCanvas = document.getElementById('drawingCanvas');
                    const drawCtx = drawCanvas.getContext('2d');
                    
                    let isDrawing = false;
                    let showMaskOnly = false;
                    let hasDrawn = false;
                    const brushSize = {brush_size};
                    
                    // Load background image
                    const bgImage = new Image();
                    bgImage.onload = function() {{
                        bgCtx.drawImage(bgImage, 0, 0);
                    }};
                    bgImage.src = 'data:image/png;base64,{img_base64}';
                    
                    // Set up drawing context
                    drawCtx.strokeStyle = 'white';
                    drawCtx.lineWidth = brushSize;
                    drawCtx.lineCap = 'round';
                    drawCtx.lineJoin = 'round';
                    
                    // Mouse/Touch event handlers
                    function startDrawing(e) {{
                        isDrawing = true;
                        hasDrawn = true;
                        const pos = getPosition(e);
                        drawCtx.beginPath();
                        drawCtx.moveTo(pos.x, pos.y);
                    }}
                    
                    function draw(e) {{
                        if (!isDrawing) return;
                        e.preventDefault();
                        
                        const pos = getPosition(e);
                        drawCtx.lineTo(pos.x, pos.y);
                        drawCtx.stroke();
                    }}
                    
                    function stopDrawing() {{
                        if (isDrawing) {{
                            drawCtx.closePath();
                            isDrawing = false;
                        }}
                    }}
                    
                    function getPosition(e) {{
                        const rect = drawCanvas.getBoundingClientRect();
                        const scaleX = drawCanvas.width / rect.width;
                        const scaleY = drawCanvas.height / rect.height;
                        
                        let clientX, clientY;
                        if (e.touches && e.touches.length > 0) {{
                            clientX = e.touches[0].clientX;
                            clientY = e.touches[0].clientY;
                        }} else {{
                            clientX = e.clientX;
                            clientY = e.clientY;
                        }}
                        
                        return {{
                            x: (clientX - rect.left) * scaleX,
                            y: (clientY - rect.top) * scaleY
                        }};
                    }}
                    
                    // Mouse events
                    drawCanvas.addEventListener('mousedown', startDrawing);
                    drawCanvas.addEventListener('mousemove', draw);
                    drawCanvas.addEventListener('mouseup', stopDrawing);
                    drawCanvas.addEventListener('mouseleave', stopDrawing);
                    
                    // Touch events (for stylus)
                    drawCanvas.addEventListener('touchstart', startDrawing, {{ passive: false }});
                    drawCanvas.addEventListener('touchmove', draw, {{ passive: false }});
                    drawCanvas.addEventListener('touchend', stopDrawing);
                    drawCanvas.addEventListener('touchcancel', stopDrawing);
                    
                    function clearCanvas() {{
                        drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
                        hasDrawn = false;
                        document.getElementById('statusInfo').textContent = 'Canvas cleared. Draw again to create a new mask.';
                    }}
                    
                    function toggleView() {{
                        showMaskOnly = !showMaskOnly;
                        bgCanvas.style.display = showMaskOnly ? 'none' : 'block';
                        document.getElementById('statusInfo').textContent = showMaskOnly ? 
                            'Viewing mask only (white = areas to remove)' : 
                            'Viewing image with mask overlay';
                    }}
                    
                    function downloadMask() {{
                        if (!hasDrawn) {{
                            document.getElementById('statusInfo').textContent = '⚠️ Please draw something first!';
                            return;
                        }}
                        
                        // Create mask (black background + white strokes)
                        const tempCanvas = document.createElement('canvas');
                        tempCanvas.width = drawCanvas.width;
                        tempCanvas.height = drawCanvas.height;
                        const tempCtx = tempCanvas.getContext('2d');
                        
                        // Fill with black
                        tempCtx.fillStyle = 'black';
                        tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);
                        
                        // Draw white strokes
                        tempCtx.drawImage(drawCanvas, 0, 0);
                        
                        // Download
                        tempCanvas.toBlob(function(blob) {{
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = 'inpaint_mask.png';
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            URL.revokeObjectURL(url);
                            
                            document.getElementById('statusInfo').innerHTML = 
                                '✅ <strong>Mask downloaded!</strong> Now upload it below to process.';
                        }}, 'image/png');
                    }}
                </script>
            </body>
            </html>
            """
            
            # Display the canvas component
            components.html(canvas_html, height=img_height + 150, scrolling=False)
            
            st.divider()
            st.write("**Step 2:** Upload the downloaded mask file to process inpainting.")
            
            # Upload mask file
            uploaded_mask = st.file_uploader(
                "Upload Mask (PNG file)", 
                type=["png"],
                key="mask_uploader",
                help="Upload the mask file you just downloaded from the canvas above"
            )
            
            mask = None
            if uploaded_mask is not None:
                try:
                    # Load uploaded mask
                    mask_img = Image.open(uploaded_mask)
                    mask = np.array(mask_img.convert('L'))  # Convert to grayscale
                    
                    # Threshold to binary
                    mask = (mask > 127).astype(np.uint8) * 255
                    
                    # Resize if needed
                    if mask.shape[:2] != (img_height, img_width):
                        mask = cv2.resize(mask, (img_width, img_height), interpolation=cv2.INTER_NEAREST)
                    
                    # Show preview
                    st.image(mask, caption="✅ Mask Loaded Successfully", width=min(400, img_width))
                    st.success(f"Mask coverage: {(mask > 0).sum() / mask.size * 100:.1f}% of image")
                    
                except Exception as e:
                    st.error(f"Error loading mask: {e}")

            # Run inpainting
            if st.button("🎨 Run Inpainting", type="primary", disabled=(mask is None)):
                if mask is None or mask.sum() == 0:
                    st.warning("Please upload a valid mask file first.")
                else:
                    with st.spinner("Running MI-GAN inpainting..."):
                        result = inpaint_region(st.session_state.image, mask)
                        st.session_state.result_image = result["inpainted_image"]
                    st.success("✓ Inpainting completed! Check the result in the output panel.")

        # ======================================================================
        # 2) SEGMENTATION MASK
        # ======================================================================
        if mask_source == "Use Segmentation Mask":
            st.info("You must run segmentation first (Manual Tools → seg).")

            if st.button("Inpaint Segmented Region", type="primary"):
                if hasattr(st.session_state, 'mask') and st.session_state.mask is not None:
                    seg_mask = st.session_state.mask

                    # Normalize mask to uint8 0/255
                    if seg_mask.dtype == np.bool_:
                        seg_mask = seg_mask.astype(np.uint8) * 255
                    elif seg_mask.dtype in (np.float32, np.float64):
                        seg_mask = (seg_mask > 0.5).astype(np.uint8) * 255
                    else:
                        seg_mask = (seg_mask > 127).astype(np.uint8) * 255

                    # Resize mask to match original image (safety)
                    if seg_mask.shape[:2] != st.session_state.image.shape[:2]:
                        seg_mask = cv2.resize(seg_mask,
                            (st.session_state.image.shape[1], st.session_state.image.shape[0]),
                            interpolation=cv2.INTER_NEAREST
                        )

                    with st.spinner("Running MI-GAN inpainting..."):
                        result = inpaint_region(st.session_state.image, seg_mask)
                        st.session_state.result_image = result["inpainted_image"]

                    st.success("✓ Inpainting completed!")
                else:
                    st.error("No segmentation mask found. Run segmentation first.")

        
    elif tool == "theme_changer":
        st.subheader("Weather-Aware Day/Night Theme Changer")
        st.info("Automatically detects weather and transforms day/night with weather-specific sky replacement")

        # Preview mode selection
        preview_mode = st.radio(
            "Mode",
            ["Single Transform", "Interactive Timeline Preview"],
            horizontal=True,
            help="Single: Click to transform once | Timeline: Real-time slider preview"
        )

        # Weather detection mode
        col_weather1, col_weather2 = st.columns(2)

        with col_weather1:
            auto_detect = st.checkbox("Auto-detect weather", value=True,
                                      help="Automatically detect weather from image")

        with col_weather2:
            if not auto_detect:
                weather_override = st.selectbox(
                    "Manual weather selection",
                    get_available_weather_classes(),
                    help="Choose weather class manually"
                )
            else:
                weather_override = None

        # Advanced options
        with st.expander("Advanced Options"):
            blending_mode = st.selectbox(
                "Blending Mode",
                ["Alpha", "Poisson", "Laplacian"],
                help="Alpha is fastest, Poisson/Laplacian provide smoother blending"
            )
            fg_intensity = st.slider(
                "Foreground Intensity",
                0.0, 1.0, 0.8,
                help="Controls how much the foreground is tinted"
            )

        if preview_mode == "Interactive Timeline Preview":
            # ===== INTERACTIVE TIMELINE MODE =====
            st.markdown("---")
            st.write("**🌅 Interactive Timeline - Move the slider to see day-to-night transformation in real-time**")

            # Initialize cache for timeline if not exists
            if 'timeline_cache' not in st.session_state:
                st.session_state.timeline_cache = {}

            # Generate cache key
            cache_key = f"{id(st.session_state.image)}_{weather_override}_{blending_mode}_{fg_intensity}"

            # Pre-compute transformation if not cached
            if cache_key not in st.session_state.timeline_cache:
                with st.spinner("Preparing timeline preview..."):
                    try:
                        # Detect weather once
                        result_sample = change_theme(
                            st.session_state.image,
                            time_of_day=50,
                           
                        )
                        detected_weather = result_sample['detected_weather']
                        st.session_state.timeline_cache[cache_key] = {
                            'weather': detected_weather,
                            'assets_count': result_sample['assets_count']
                        }
                    except Exception as e:
                        st.error(f"Failed to prepare timeline: {str(e)}")
                        st.session_state.timeline_cache[cache_key] = None

            if st.session_state.timeline_cache.get(cache_key):
                # Show weather info
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.metric("Detected Weather",
                             st.session_state.timeline_cache[cache_key]['weather'].replace('_', ' ').title())
                with col_info2:
                    st.metric("Sky Assets", st.session_state.timeline_cache[cache_key]['assets_count'])

                # Interactive slider
                time_of_day = st.slider(
                    "🕐 Time of Day Timeline",
                    0, 100, 50,
                    help="Drag to see real-time transformation: 0=Day → 50=Evening → 100=Night",
                    key="timeline_slider"
                )

                # Real-time transformation on slider change
                try:
                    result = change_theme(
                        st.session_state.image,
                        time_of_day=time_of_day,
                       
                    )

                    # Update result image for display
                    st.session_state.result_image = result["transformed_image"]

                    # Store theme result in session state for sky mask display
                    st.session_state.theme_result = result

                    # Show time phase indicator
                    phase = "🌅 Day" if time_of_day < 33 else "🌆 Evening" if time_of_day < 67 else "🌃 Night"
                    st.info(f"Current Phase: **{phase}** (Time: {time_of_day}/100)")

                    # Option to save current frame
                    if st.button("💾 Save Current View"):
                        st.success(f"✓ Current view saved! ({phase} @ {time_of_day})")

                    # Option to view sky mask (persistent checkbox)
                    if st.checkbox("Show sky segmentation mask", key="timeline_show_mask"):
                        st.image(result['sky_mask'], caption="Sky Segmentation Mask", width="stretch")

                except Exception as e:
                    st.error(f"Timeline preview failed: {str(e)}")

        else:
            # ===== SINGLE TRANSFORM MODE =====
            # Time of day slider
            time_of_day = st.slider(
                "Time of Day",
                0, 100, 50,
                help="0=Day, 50=Evening, 100=Night"
            )

            # Process button
            if st.button("Transform Theme", type="primary"):
                with st.spinner("Detecting weather and transforming theme..."):
                    try:
                        result = change_theme(
                            st.session_state.image,
                            time_of_day=time_of_day,
                          
                        )

                        st.session_state.result_image = result["transformed_image"]

                        # Store theme result in session state for persistent display
                        st.session_state.theme_result = result

                        # Show detection results
                        st.success(f"✓ Theme transformation completed!")

                    except Exception as e:
                        st.error(f"Theme transformation failed: {str(e)}")
                        import traceback
                        st.error(traceback.format_exc())

            # Show metrics and mask option if transformation was done
            if 'theme_result' in st.session_state and st.session_state.theme_result:
                result = st.session_state.theme_result

                col_info1, col_info2, col_info3 = st.columns(3)
                with col_info1:
                    st.metric("Detected Weather", result['detected_weather'].replace('_', ' ').title())
                with col_info2:
                    st.metric("Sky Assets Used", result['assets_count'])
                with col_info3:
                    time_val = result.get('time_of_day', time_of_day)
                    st.metric("Time Phase",
                             "Day" if time_val < 33 else "Evening" if time_val < 67 else "Night")

                # Option to view sky mask (persistent checkbox)
                if st.checkbox("Show sky segmentation mask", key="theme_show_mask"):
                    st.image(result['sky_mask'], caption="Sky Segmentation Mask", width="stretch")

    with col2:
        st.subheader("Result")
        if st.session_state.result_image is not None:
            display_image(st.session_state.result_image)
      

def render_pipeline_viewer():
    """Render pipeline graph viewer."""
    st.header("📊 Pipeline Viewer")

    # Always show the graph structure

    # Get Mermaid diagram
    mermaid_diagram = get_graph_visualization()

    # Display using Streamlit's native Mermaid support
    st.markdown("### Graph Structure")
    mermaid(mermaid_diagram)

    st.caption("The Planner creates execution plans, Executor runs tools, and Clarification handles user input when needed.")

    if st.session_state.pipeline_state is None:
        st.info("Run a query in AI Assistant mode to see execution details")
        return

    state = st.session_state.pipeline_state

    st.divider()

    # Session-specific pipeline visualization
    st.subheader("Execution Pipeline")

    # Get pipeline visualization for this session
    pipeline_mermaid = get_pipeline_mermaid(state)
    if pipeline_mermaid and state.get("pipeline_nodes"):
        mermaid(pipeline_mermaid)
    else:
        st.info("No pipeline steps executed yet")

    st.divider()

    # Execution flow from plan
    st.subheader("Execution Flow")

    plan = state.get("plan", [])
    if plan:
        flow_items = ["Query"]
        for step in plan:
            tool_name = step.get("tool", "unknown")
            step_status = step.get("status", "pending")

            if step_status == "completed":
                bg_color = "#c8e6c9"  # Green
            elif step_status == "running":
                bg_color = "#fff9c4"  # Yellow
            elif step_status == "failed":
                bg_color = "#ffcdd2"  # Red
            else:
                bg_color = "#e3f2fd"  # Blue

            flow_items.append(f"<span style='padding: 4px 8px; background: {bg_color}; border-radius: 4px; margin: 2px;'>{tool_name}</span>")

        if state["status"] == "completed":
            flow_items.append("<span style='padding: 4px 8px; background: #c8e6c9; border-radius: 4px; margin: 2px;'>Output</span>")

        flow_html = " → ".join(flow_items)
        st.markdown(f"<div style='overflow-x: auto;'>{flow_html}</div>", unsafe_allow_html=True)
    else:
        st.info("No execution plan available")

    # Execution timeline
    st.subheader("Execution Timeline")
    if state.get("results"):
        for i, result in enumerate(state["results"]):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{result['tool']}**")
            with col2:
                st.write(f"{result['execution_time']:.3f}s")
            with col3:
                if result["success"]:
                    st.write("✅")
                else:
                    st.write("❌")

    # Intermediate images/thumbnails
    thumbnails = state.get("intermediate_thumbnails", [])
    images = state.get("intermediate_images", [])

    if thumbnails or images:
        st.subheader("Intermediate Results")
        # Prefer thumbnails for display, fallback to full images
        display_list = thumbnails if thumbnails else images
        cols = st.columns(min(len(display_list), 4))
        for i, img in enumerate(display_list):
            if img is not None:
                with cols[i % 4]:
                    step_name = plan[i].get("tool", f"Step {i+1}") if i < len(plan) else f"Step {i+1}"
                    display_image(img, step_name)

    # Show HTML output if available
    if state.get("media_type") == "html" and state.get("html_output"):
        st.subheader("Parallax Output")
        components.html(state["html_output"], height=500, scrolling=True)

if __name__ == "__main__":
    main()