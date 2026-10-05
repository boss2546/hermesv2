"""Google Workspace plugin tools for Hermes Agent & Maymint Voice Assistant.

Provides seamless access to Gmail, Google Drive, Google Calendar, Sheets, and Docs
through the bundled google_api.py engine with OAuth2 persistence.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

CURRENT_DIR = Path(__file__).resolve().parent
HERMES_AGENT_DIR = CURRENT_DIR.parent.parent
GOOGLE_API_SCRIPT = HERMES_AGENT_DIR / "skills" / "productivity" / "google-workspace" / "scripts" / "google_api.py"

GOOGLE_WORKSPACE_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "google_workspace_gmail",
            "description": "Manage Gmail: search emails, read message content, send emails, reply to threads, and modify labels/trash. Use this whenever the user asks about emails, wants to read new messages, send an email, or delete/organize mail.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search", "get", "send", "reply", "modify"],
                        "description": "The Gmail action to perform."
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query for 'search' action (e.g. 'is:unread', 'from:boss', 'newer_than:7d', 'has:attachment')."
                    },
                    "message_id": {
                        "type": "string",
                        "description": "The Gmail message ID (required for 'get', 'reply', and 'modify')."
                    },
                    "to": {
                        "type": "string",
                        "description": "Recipient email address for 'send'."
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject for 'send'."
                    },
                    "body": {
                        "type": "string",
                        "description": "Email message body for 'send' or 'reply'."
                    },
                    "add_labels": {
                        "type": "string",
                        "description": "Label to add for 'modify' (e.g. 'TRASH', 'STARRED', 'IMPORTANT')."
                    },
                    "remove_labels": {
                        "type": "string",
                        "description": "Label to remove for 'modify' (e.g. 'UNREAD')."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of emails to return (default: 5).",
                        "default": 5
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "google_workspace_drive",
            "description": "Manage Google Drive: search files, get file metadata, upload local files, download files, create folders, share with users, and delete/trash files. Use this whenever the user asks about Drive files, cloud documents, or uploading/downloading files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search", "get", "upload", "download", "create_folder", "share", "delete"],
                        "description": "The Google Drive action to perform."
                    },
                    "query": {
                        "type": "string",
                        "description": "File name or search term for 'search' action."
                    },
                    "file_id": {
                        "type": "string",
                        "description": "The Drive file or folder ID (for 'get', 'download', 'share', 'delete')."
                    },
                    "local_path": {
                        "type": "string",
                        "description": "Local file path on disk to upload from (for 'upload') or save to (for 'download')."
                    },
                    "folder_name": {
                        "type": "string",
                        "description": "Folder name to create (for 'create_folder')."
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address to share with (for 'share')."
                    },
                    "role": {
                        "type": "string",
                        "enum": ["reader", "writer", "commenter"],
                        "description": "Permission role when sharing (default: 'reader').",
                        "default": "reader"
                    },
                    "permanent": {
                        "type": "boolean",
                        "description": "If true, permanently deletes the file instead of moving to trash (for 'delete').",
                        "default": False
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of files to return (default: 10).",
                        "default": 10
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "google_workspace_calendar",
            "description": "Manage Google Calendar: list upcoming events and meetings, create new calendar events, and delete events. Use this whenever the user asks about schedule, meetings, calendar events, or appointments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "create", "delete"],
                        "description": "The Calendar action to perform."
                    },
                    "summary": {
                        "type": "string",
                        "description": "Title or summary of the event (for 'create')."
                    },
                    "start": {
                        "type": "string",
                        "description": "Event start time in ISO 8601 format with timezone (e.g. '2026-10-06T10:00:00+07:00')."
                    },
                    "end": {
                        "type": "string",
                        "description": "Event end time in ISO 8601 format with timezone (e.g. '2026-10-06T11:00:00+07:00')."
                    },
                    "location": {
                        "type": "string",
                        "description": "Event location (optional, for 'create')."
                    },
                    "attendees": {
                        "type": "string",
                        "description": "Comma-separated list of attendee email addresses (optional, for 'create')."
                    },
                    "event_id": {
                        "type": "string",
                        "description": "Calendar event ID to delete (for 'delete')."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "google_workspace_sheets_docs",
            "description": "Manage Google Sheets and Docs: read spreadsheet data, append rows, update cells, create spreadsheets, and read/create/append Google Docs documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "enum": ["sheets", "docs"],
                        "description": "Choose 'sheets' for Google Sheets or 'docs' for Google Docs."
                    },
                    "action": {
                        "type": "string",
                        "enum": ["get", "create", "update", "append"],
                        "description": "The action to perform."
                    },
                    "id": {
                        "type": "string",
                        "description": "Spreadsheet ID or Document ID (for 'get', 'update', 'append')."
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of the new spreadsheet or document (for 'create')."
                    },
                    "range": {
                        "type": "string",
                        "description": "Cell range in Sheets (e.g. 'Sheet1!A1:D10' or 'Sheet1!A:C')."
                    },
                    "values": {
                        "type": "string",
                        "description": "JSON string representing 2D array of rows for Sheets (e.g. '[[\"Name\", \"Score\"], [\"Boss\", 100]]')."
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to append to Google Docs (for Docs 'append' or 'create')."
                    }
                },
                "required": ["service", "action"]
            }
        }
    }
]


def _run_script(args: List[str]) -> Dict[str, Any]:
    """Execute google_api.py CLI wrapper with arguments and return JSON output."""
    if not GOOGLE_API_SCRIPT.exists():
        return {"error": f"google_api.py script not found at {GOOGLE_API_SCRIPT}"}

    cmd = [sys.executable, str(GOOGLE_API_SCRIPT), *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        if proc.returncode != 0:
            return {
                "error": stderr or stdout or f"Command failed with exit code {proc.returncode}",
                "exit_code": proc.returncode
            }

        if not stdout:
            return {"success": True, "message": "Command completed successfully"}

        try:
            parsed = json.loads(stdout)
            return {"success": True, "data": parsed}
        except Exception:
            return {"success": True, "raw_output": stdout}

    except subprocess.TimeoutExpired:
        return {"error": "Google API call timed out after 45 seconds"}
    except Exception as exc:
        return {"error": str(exc)}


def execute_google_workspace_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Unified dispatcher for Google Workspace tools."""
    action = arguments.get("action", "").lower().strip()

    if name == "google_workspace_gmail":
        if action == "search":
            q = arguments.get("query", "is:unread")
            limit = str(arguments.get("max_results", 5))
            return _run_script(["gmail", "search", q, "--max", limit])

        elif action == "get":
            mid = arguments.get("message_id")
            if not mid:
                return {"error": "message_id is required for gmail get"}
            return _run_script(["gmail", "get", mid])

        elif action == "send":
            to = arguments.get("to")
            subj = arguments.get("subject", "No Subject")
            body = arguments.get("body", "")
            if not to:
                return {"error": "'to' email address is required for sending email"}
            return _run_script(["gmail", "send", "--to", to, "--subject", subj, "--body", body])

        elif action == "reply":
            mid = arguments.get("message_id")
            body = arguments.get("body", "")
            if not mid:
                return {"error": "message_id is required for gmail reply"}
            return _run_script(["gmail", "reply", mid, "--body", body])

        elif action == "modify":
            mid = arguments.get("message_id")
            if not mid:
                return {"error": "message_id is required for gmail modify"}
            cmd = ["gmail", "modify", mid]
            if arguments.get("add_labels"):
                cmd.extend(["--add-labels", arguments["add_labels"]])
            if arguments.get("remove_labels"):
                cmd.extend(["--remove-labels", arguments["remove_labels"]])
            return _run_script(cmd)

        return {"error": f"Unknown Gmail action: {action}"}

    elif name == "google_workspace_drive":
        if action == "search":
            q = arguments.get("query", "").strip()
            limit = str(arguments.get("max_results", 10))
            if not q or q == "*":
                # Search all non-trashed files
                return _run_script(["drive", "search", "trashed = false", "--raw-query", "--max", limit])
            return _run_script(["drive", "search", q, "--max", limit])

        elif action == "get":
            fid = arguments.get("file_id")
            if not fid:
                return {"error": "file_id is required for drive get"}
            return _run_script(["drive", "get", fid])

        elif action == "upload":
            path = arguments.get("local_path")
            if not path:
                return {"error": "local_path is required for drive upload"}
            return _run_script(["drive", "upload", path])

        elif action == "download":
            fid = arguments.get("file_id")
            out = arguments.get("local_path")
            if not fid:
                return {"error": "file_id is required for drive download"}
            cmd = ["drive", "download", fid]
            if out:
                cmd.extend(["--output", out])
            return _run_script(cmd)

        elif action == "create_folder":
            name_arg = arguments.get("folder_name", "New Folder")
            return _run_script(["drive", "create-folder", name_arg])

        elif action == "share":
            fid = arguments.get("file_id")
            email = arguments.get("email")
            role = arguments.get("role", "reader")
            if not fid or not email:
                return {"error": "file_id and email are required for drive share"}
            return _run_script(["drive", "share", fid, "--email", email, "--role", role])

        elif action == "delete":
            fid = arguments.get("file_id")
            if not fid:
                return {"error": "file_id is required for drive delete"}
            cmd = ["drive", "delete", fid]
            if arguments.get("permanent"):
                cmd.append("--permanent")
            return _run_script(cmd)

        return {"error": f"Unknown Drive action: {action}"}

    elif name == "google_workspace_calendar":
        if action == "list":
            return _run_script(["calendar", "list"])

        elif action == "create":
            summary = arguments.get("summary", "New Event")
            start = arguments.get("start")
            end = arguments.get("end")
            if not start or not end:
                return {"error": "start and end times in ISO 8601 format are required for calendar create"}
            cmd = ["calendar", "create", "--summary", summary, "--start", start, "--end", end]
            if arguments.get("location"):
                cmd.extend(["--location", arguments["location"]])
            if arguments.get("attendees"):
                cmd.extend(["--attendees", arguments["attendees"]])
            return _run_script(cmd)

        elif action == "delete":
            eid = arguments.get("event_id")
            if not eid:
                return {"error": "event_id is required for calendar delete"}
            return _run_script(["calendar", "delete", eid])

        return {"error": f"Unknown Calendar action: {action}"}

    elif name == "google_workspace_sheets_docs":
        svc = arguments.get("service", "sheets").lower().strip()

        if svc == "sheets":
            if action == "get":
                sid = arguments.get("id")
                rng = arguments.get("range", "Sheet1!A1:Z50")
                if not sid:
                    return {"error": "Spreadsheet 'id' is required for sheets get"}
                return _run_script(["sheets", "get", sid, rng])

            elif action == "create":
                title = arguments.get("title", "New Spreadsheet")
                return _run_script(["sheets", "create", "--title", title])

            elif action == "update":
                sid = arguments.get("id")
                rng = arguments.get("range")
                vals = arguments.get("values", "[]")
                if not sid or not rng:
                    return {"error": "'id' and 'range' are required for sheets update"}
                return _run_script(["sheets", "update", sid, rng, "--values", vals])

            elif action == "append":
                sid = arguments.get("id")
                rng = arguments.get("range", "Sheet1!A:A")
                vals = arguments.get("values", "[]")
                if not sid:
                    return {"error": "Spreadsheet 'id' is required for sheets append"}
                return _run_script(["sheets", "append", sid, rng, "--values", vals])

        elif svc == "docs":
            if action == "get":
                did = arguments.get("id")
                if not did:
                    return {"error": "Document 'id' is required for docs get"}
                return _run_script(["docs", "get", did])

            elif action == "create":
                title = arguments.get("title", "New Document")
                cmd = ["docs", "create", "--title", title]
                if arguments.get("text"):
                    cmd.extend(["--body", arguments["text"]])
                return _run_script(cmd)

            elif action == "append":
                did = arguments.get("id")
                text = arguments.get("text", "")
                if not did or not text:
                    return {"error": "'id' and 'text' are required for docs append"}
                return _run_script(["docs", "append", did, "--text", text])

        return {"error": f"Unknown Sheets/Docs combination: service={svc}, action={action}"}

    return {"error": f"Unknown tool: {name}"}
