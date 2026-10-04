"""Master template plugin for Hermes Agent.

Demonstrates:
- Lifecycle hooks (on_session_start, on_session_end, pre_tool_call, post_tool_call)
- Slash commands (ctx.register_command)
- Custom tools (ctx.register_tool)
- Thread-safe lazy initialization via plugins.plugin_utils
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from plugins.plugin_utils import SingletonSlot
from . import plugin_logic as logic

logger = logging.getLogger(__name__)

# Thread-safe lazy singleton client slot (if your plugin connects to a DB/API)
_client_slot: SingletonSlot[Any] = SingletonSlot()


# ------------------------------------------------------------------------------
# 1. Lifecycle Hooks
# ------------------------------------------------------------------------------
def _on_session_start(session_id: str, **kwargs) -> None:
    """Invoked when a new Hermes session starts."""
    logger.info("[template-plugin] Session started: %s", session_id)


def _on_session_end(session_id: str, **kwargs) -> None:
    """Invoked when a Hermes session ends."""
    logger.info("[template-plugin] Session ended: %s", session_id)


def _on_pre_tool_call(tool_name: str, args: Dict[str, Any], task_id: Optional[str] = None, **kwargs) -> None:
    """Invoked immediately before any tool call executes."""
    # Example: Audit or log tool usage
    logger.debug("[template-plugin] Pre-call tool: %s with args: %s", tool_name, args)


def _on_post_tool_call(tool_name: str, args: Dict[str, Any], result: str, task_id: Optional[str] = None, **kwargs) -> None:
    """Invoked immediately after a tool call completes."""
    # Example: Track created files or monitor performance
    logger.debug("[template-plugin] Post-call tool: %s", tool_name)


# ------------------------------------------------------------------------------
# 2. Slash Command Handler (/template-cmd)
# ------------------------------------------------------------------------------
def _handle_slash_command(raw_args: str) -> Optional[str]:
    """Handler for the /template-cmd slash command in chat or CLI."""
    argv = raw_args.strip().split()
    if not argv or argv[0] in {"help", "-h", "--help"}:
        return (
            "📖 /template-cmd Usage:\n"
            "  /template-cmd status      — Check plugin status\n"
            "  /template-cmd echo <text> — Echo back the text"
        )

    subcmd = argv[0].lower()
    if subcmd == "status":
        return "🟢 template-plugin is active and healthy!"
    elif subcmd == "echo":
        text = " ".join(argv[1:]) if len(argv) > 1 else "(empty)"
        return f"✨ template-plugin echoed: {text}"
    else:
        return f"❓ Unknown subcommand '{subcmd}'. Run `/template-cmd help` for usage."


# ------------------------------------------------------------------------------
# 3. Plugin Registration Entry Point
# ------------------------------------------------------------------------------
def register(ctx) -> None:
    """Main registration function called once by Hermes plugin loader.
    
    Args:
        ctx: Plugin registration context providing:
             - ctx.register_hook(hook_name, callback)
             - ctx.register_command(name, handler, description)
             - ctx.register_tool(name, toolset, schema, handler, check_fn, emoji)
    """
    # 1. Register lifecycle hooks
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("on_session_end", _on_session_end)
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_hook("post_tool_call", _on_post_tool_call)

    # 2. Register slash command (/template-cmd)
    ctx.register_command(
        name="template-cmd",
        handler=_handle_slash_command,
        description="Master template plugin slash command."
    )

    # 3. Register custom tool
    ctx.register_tool(
        name="template_plugin_action",
        toolset="template",
        schema=logic.TEMPLATE_ACTION_SCHEMA,
        handler=logic.handle_template_action,
        check_fn=logic.check_template_available,
        emoji="🧩"
    )
