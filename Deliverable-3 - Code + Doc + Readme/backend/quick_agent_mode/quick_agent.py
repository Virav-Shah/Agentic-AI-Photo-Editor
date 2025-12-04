"""
Quick Instant Agent using Gemma3:1b
Fast JSON-based tool execution for single-step operations
"""

import json
import re
from typing import Dict, Any
import requests

class QuickAgentGemma:
    """
    Quick instant agent using Gemma3:1b for fast JSON parsing.
    Executes single-step operations instantly.
    """

    def __init__(self, model_endpoint: str = "http://localhost:11434/api/chat"):
        """
        Initialize Gemma quick agent.

        Args:
            model_endpoint: Ollama API endpoint (default: localhost:11434/api/chat)
        """
        self.model_endpoint = model_endpoint
        self.model_name = "gemma3:1b" 

    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Parse user query using Gemma to extract tool and parameters.

        Args:
            query: User's natural language command

        Returns:
            Dictionary with tool name and parameters
        """
        system_prompt = """You are a fast AI assistant for an image editor.
Extract the tool and parameters from the user command. Return ONLY valid JSON.

Available tools:
- parallax: Create 3D parallax effect. Params: depth_scale (20-50), output_format ("html" or "frames")
- super_resolution: Upscale image. Params: scale (2, 4, or 8)
- filter: Apply filter. Params: type ("grayscale", "sepia", "blur", "sharpen", "edge_detect"), intensity (0.0-2.0)
- theme_changer: Change day/night. Params: time_of_day (0-100, 0=day, 100=night)
- crop: Crop image. Params: aspect_ratio ("1:1", "16:9", "4:3")
- resize: Resize image. Params: scale (0.1-4.0) or width/height

Examples:
1. User: "Make it grayscale"
   JSON: {"tool": "filter", "params": {"type": "grayscale", "intensity": 1.0}}

2. User: "Upscale this 4x"
   JSON: {"tool": "super_resolution", "params": {"scale": 4}}

3. User: "Turn this into a night scene"
   JSON: {"tool": "theme_changer", "params": {"time_of_day": 100}}

4. User: "Create a 3D effect with depth 30"
   JSON: {"tool": "parallax", "params": {"depth_scale": 30, "output_format": "html"}}

5. User: "Crop to square"
   JSON: {"tool": "crop", "params": {"aspect_ratio": "1:1"}}

Return ONLY valid JSON."""

        try:
            # Call Ollama API with Gemma
            response = requests.post(
                self.model_endpoint,
                json={
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 128,  # Limit generation for speed
                        "keep_alive": "10m"   # Keep model loaded
                    }
                },
                timeout=10  # Slightly increased timeout, but keep_alive makes it fast
            )

            if response.status_code == 200:
                result = response.json()
                response_msg = result.get("message", {})
                response_text = response_msg.get("content", "{}")

                # Try to extract JSON from response
                try:
                    intent = json.loads(response_text)
                    return self._validate_intent(intent)
                except json.JSONDecodeError:
                    # Fallback to regex extraction
                    return self._fallback_parse(query)
            else:
                return self._fallback_parse(query)

        except Exception as e:
            return self._fallback_parse(query)

    def _validate_intent(self, intent: Dict) -> Dict:
        """Validate and normalize parsed intent."""
        tool = intent.get("tool", "unknown")
        params = intent.get("params", {})

        # Normalize tool names
        tool_aliases = {
            "parallax": ["parallax", "3d", "depth", "live photo"],
            "super_resolution": ["upscale", "sr", "super resolution", "enhance"],
            "filter": ["filter", "effect", "style"],
            "theme_changer": ["theme", "day", "night", "time"],
            "crop": ["crop", "trim"],
            "resize": ["resize", "scale", "size"]
        }

        # Find matching tool
        normalized_tool = tool
        for main_tool, aliases in tool_aliases.items():
            if tool.lower() in aliases:
                normalized_tool = main_tool
                break

        return {"tool": normalized_tool, "params": params}

    def _fallback_parse(self, query: str) -> Dict:
        """
        Fallback keyword-based parsing when LLM fails.
        Simple but reliable for common commands.
        """
        query_lower = query.lower()

        # Parallax / 3D
        if any(word in query_lower for word in ["parallax", "3d", "depth", "live photo"]):
            return {
                "tool": "parallax",
                "params": {"depth_scale": 40, "output_format": "html"}
            }

        # Super Resolution
        if any(word in query_lower for word in ["upscale", "sr", "super resolution", "enhance", "higher resolution"]):
            scale = 4
            if "2x" in query_lower or "double" in query_lower:
                scale = 2
            elif "8x" in query_lower:
                scale = 8
            return {
                "tool": "super_resolution",
                "params": {"scale": scale}
            }

        # Filters
        filter_keywords = {
            "grayscale": ["grayscale", "gray", "black and white", "bw"],
            "sepia": ["sepia", "vintage", "old photo"],
            "blur": ["blur", "soft", "smooth"],
            "sharpen": ["sharpen", "sharp", "crisp"],
            "edge_detect": ["edge", "outline", "contour"]
        }

        for filter_type, keywords in filter_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return {
                    "tool": "filter",
                    "params": {"type": filter_type, "intensity": 1.0}
                }

        # Theme changer (day/night)
        if any(word in query_lower for word in ["day", "night", "evening", "sunset", "sunrise", "theme"]):
            time_val = 0  # Default day
            if "night" in query_lower:
                time_val = 100
            elif "evening" in query_lower or "sunset" in query_lower:
                time_val = 50
            return {
                "tool": "theme_changer",
                "params": {"time_of_day": time_val, "blending_mode": "Alpha"}
            }

        # Crop
        if "crop" in query_lower or "trim" in query_lower:
            aspect = None
            if "square" in query_lower or "1:1" in query_lower:
                aspect = "1:1"
            elif "16:9" in query_lower or "widescreen" in query_lower:
                aspect = "16:9"
            elif "4:3" in query_lower:
                aspect = "4:3"

            return {
                "tool": "crop",
                "params": {"aspect_ratio": aspect} if aspect else {}
            }

        # Resize
        if "resize" in query_lower or "scale" in query_lower:
            scale = 1.0
            # Try to extract scale value
            scale_match = re.search(r'(\d+\.?\d*)x', query_lower)
            if scale_match:
                scale = float(scale_match.group(1))

            return {
                "tool": "resize",
                "params": {"scale": scale}
            }

        # Default: unknown
        return {"tool": "unknown", "params": {}}

    def get_tool_description(self, tool: str) -> str:
        """Get user-friendly description of what will be executed."""
        descriptions = {
            "parallax": "Create 3D parallax effect",
            "super_resolution": "Upscale image with AI",
            "filter": "Apply image filter",
            "theme_changer": "Change day/night theme",
            "crop": "Crop image",
            "resize": "Resize image",
            "unknown": "Unknown command"
        }
        return descriptions.get(tool, "Execute command")


# Test function
def test_quick_agent():
    """Test quick agent parsing"""
    agent = QuickAgentGemma()

    test_queries = [
        "apply parallax effect",
        "upscale this image 4x",
        "make it grayscale",
        "change to night mode",
        "crop to square"
    ]
    for query in test_queries:
        intent = agent.parse_query(query)
        desc = agent.get_tool_description(intent["tool"])

if __name__ == "__main__":
    test_quick_agent()