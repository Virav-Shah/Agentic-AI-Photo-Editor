import json
import re

def validate_and_fix_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Simple heuristic to find JSON block
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}
