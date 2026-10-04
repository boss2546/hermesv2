"""Core business logic, schemas, and handlers for template-plugin.

Demonstrates production-ready structure:
1. Tool Schema (OpenAI Function Calling format)
2. Readiness Check Function (API Key / Auth check)
3. Safe execution handler with JSON return
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# 1. Tool JSON Schema
# ------------------------------------------------------------------------------
TEMPLATE_ACTION_SCHEMA: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "template_plugin_action",
        "description": "Execute a sample action provided by the template plugin.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The input message or text to process."
                },
                "mode": {
                    "type": "string",
                    "enum": ["uppercase", "lowercase", "reverse", "echo"],
                    "description": "Transformation mode for the message.",
                    "default": "echo"
                }
            },
            "required": ["message"]
        }
    }
}


# ------------------------------------------------------------------------------
# 2. Check Function (Readiness Gate)
# ------------------------------------------------------------------------------
def check_template_available() -> Tuple[bool, Optional[str]]:
    """Verify prerequisites before the tool can be dispatched.
    
    Returns:
        (True, None) if ready.
        (False, "hint message") if not ready.
    """
    # Example: Check if required auth or environment is present
    return True, None


# ------------------------------------------------------------------------------
# 3. Tool Handler
# ------------------------------------------------------------------------------
def handle_template_action(args: Dict[str, Any], task_id: Optional[str] = None) -> str:
    """Execute the core plugin tool action."""
    message = str(args.get("message", "")).strip()
    mode = str(args.get("mode", "echo")).lower()

    if not message:
        return json.dumps({
            "success": False,
            "error": "The 'message' parameter cannot be empty."
        }, ensure_ascii=False)

    try:
        if mode == "uppercase":
            processed = message.upper()
        elif mode == "lowercase":
            processed = message.lower()
        elif mode == "reverse":
            processed = message[::-1]
        else:
            processed = message

        result = {
            "success": True,
            "original": message,
            "mode": mode,
            "result": processed,
            "task_id": task_id
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    except Exception as exc:
        logger.exception("Failed to execute template_plugin_action: %s", exc)
        return json.dumps({
            "success": False,
            "error": f"Internal execution error: {exc}"
        }, ensure_ascii=False)
