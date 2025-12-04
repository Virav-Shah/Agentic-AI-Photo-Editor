"""
Prompts adapter: re-export the system prompt and tool descriptions from
the local copy in optimise package.
"""

try:
    from .system_prompt import TOOL_DESCRIPTIONS, SYSTEM_PROMPT, FEW_SHOT_EXAMPLES
except ImportError:
    SYSTEM_PROMPT = ""
    TOOL_DESCRIPTIONS = ""
    FEW_SHOT_EXAMPLES = []

CLARIFICATION_PROMPT = """The user's request needs clarification.

Previous conversation:
{conversation_context}

Current query: "{query}"

What additional information do you need? Generate a specific, helpful question to ask the user.

Output format:
{
    "clarification_question": "Your specific question here",
    "reason": "Why you need this information"
}
"""

FOLLOWUP_PROMPT = """This is a follow-up query in an ongoing editing session.

Previous edits:
{edit_history}

Conversation history:
{conversation_context}

Cached state:
- Detected objects: {detected_objects}
- Segmented objects: {segmented_objects}

Current query: "{query}"

The user is building on previous work. Consider:
1. What can be reused from cache?
2. Is this modifying previous results or adding new effects?
3. Are there implicit references to previous objects/actions?

Create an optimized plan that leverages cached results when possible.
"""

__all__ = [
        "TOOL_DESCRIPTIONS",
        "SYSTEM_PROMPT",
        "FEW_SHOT_EXAMPLES",
        "CLARIFICATION_PROMPT",
        "FOLLOWUP_PROMPT",
]
