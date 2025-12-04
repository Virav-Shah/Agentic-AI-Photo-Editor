import requests
import json
import time
from typing import Dict, Any
import sys
from pathlib import Path

# Add root directory to path for importing root modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .state import PlannerState
from .system_prompt import SYSTEM_PROMPT
from .config import MODEL_NAME, OLLAMA_URL, KEEP_ALIVE, CTX_SIZE, PREDICT_LEN, TEMPERATURE
from .json_validator import validate_and_fix_json

def call_ollama(state: PlannerState, user_text: str) -> Dict[str, Any]:
    start_time = time.perf_counter()
    
    if state.turn == 0:
        state.messages.append({"role": "system", "content": SYSTEM_PROMPT})
    
    state.messages.append({"role": "user", "content": user_text})
    
    payload = {
        "model": MODEL_NAME,
        "messages": state.messages,
        "stream": False,
        "options": {
            "keep_alive": KEEP_ALIVE,
            "temperature": TEMPERATURE,
            "num_ctx": CTX_SIZE,
            "num_predict": PREDICT_LEN
        }
    }
    
    
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        
        latency = time.perf_counter() - start_time
        state.last_latency = latency
        if state.turn == 0:
            state.cold_start_latency = latency
            
        assistant_msg = result.get("message", {})
        content = assistant_msg.get("content", "")
        
        state.messages.append(assistant_msg)
        state.turn += 1
        
        parsed_json = validate_and_fix_json(content)
        return parsed_json
        
    except Exception as e:
        return {"error": str(e)}
