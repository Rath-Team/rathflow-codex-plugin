#!/usr/bin/env python3
"""Minimal RathFlow MCP server (stdio).

Spike: exposes a few read-only RathFlow tools to Codex without the CLI, by calling
the same Gateway REST API. Standard library only; JSON-RPC 2.0 with newline-delimited
messages on stdin/stdout. Diagnostics go to stderr so stdout stays protocol-clean.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "rathflow"
SERVER_VERSION = "0.1.0-spike"
DEFAULT_BASE_URL = "http://127.0.0.1:8080"
REQUEST_TIMEOUT = 60


def log(*parts: object) -> None:
    print("[rathflow-mcp]", *parts, file=sys.stderr, flush=True)


# --------------------------------------------------------------------- config


def config_dir() -> str:
    return os.environ.get("RATHFLOW_CONFIG_DIR") or os.path.join(
        os.path.expanduser("~"), ".config", "rathflow"
    )


def load_profile() -> dict:
    """Read the active profile from the CLI's config file; never log its contents."""
    path = os.path.join(config_dir(), "config.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    profiles = data.get("profiles") or {}
    return profiles.get(data.get("current") or "default") or {}


def resolve() -> tuple[str, str | None, str | None]:
    """Same precedence as the CLI: env > profile > built-in default."""
    profile = load_profile()
    base_url = os.environ.get("RATHFLOW_BASE_URL") or profile.get("base_url") or DEFAULT_BASE_URL
    project = os.environ.get("RATHFLOW_PROJECT") or profile.get("project")
    token = os.environ.get("RATHFLOW_TOKEN") or profile.get("access_token")
    return base_url.rstrip("/"), project or None, token or None


def api(method: str, path: str, *, query: dict | None = None, body: dict | None = None) -> dict:
    base_url, project, token = resolve()
    if not token:
        raise RuntimeError(
            "RathFlow is not authenticated. Run `rathflow auth login -e <email>` in your "
            "terminal, then start a new Codex session."
        )
    url = base_url + path
    if query:
        filtered = {key: value for key, value in query.items() if value not in (None, "")}
        if filtered:
            url += "?" + urllib.parse.urlencode(filtered)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/json")
    request.add_header("Authorization", f"Bearer {token}")
    if project:
        request.add_header("X-RathFlow-Project", project)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"RathFlow API {exc.code} on {path}: {detail}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach {base_url}: {exc.reason}") from None
    return json.loads(raw) if raw else {}


# ---------------------------------------------------------------------- tools


def tool_session_list(args: dict) -> str:
    size = args.get("page_size") or 20
    payload = api(
        "GET",
        "/api/v1/sessions",
        query={"page_size": size, "status": args.get("status")},
    )
    sessions = payload.get("sessions") or []
    if not sessions:
        return "No sessions in the current project."
    lines = [f"{len(sessions)} session(s) in the current project:"]
    for item in sessions:
        lines.append(
            "- {sid}  {status}  {title}  ({created})".format(
                sid=item.get("sessionId", "?"),
                status=item.get("status", "?"),
                title=item.get("title") or "(untitled)",
                created=item.get("createdAt", "?"),
            )
        )
    return "\n".join(lines)


def tool_memory_list(args: dict) -> str:
    prefix = args.get("prefix") or "memories"
    payload = api(
        "GET",
        "/api/v1/memories",
        query={
            "prefix": prefix,
            "recursive": "true" if args.get("recursive") else None,
            "page_size": args.get("page_size") or 50,
        },
    )
    entries = payload.get("entries") or []
    if not entries:
        return f"No memory entries under prefix {prefix!r}."
    lines = [f"{len(entries)} memory entr(ies) under {prefix!r}:"]
    for item in entries:
        lines.append(f"- {item.get('memoryPath', '?')}  ({item.get('sizeBytes', '?')} bytes)")
    return "\n".join(lines)


TOOLS = [
    {
        "name": "rathflow_session_list",
        "description": "List sessions in the current RathFlow project. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_size": {"type": "integer", "description": "Max sessions to return."},
                "status": {"type": "string", "description": "Optional status filter."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "rathflow_memory_list",
        "description": "List RathFlow memory entries under a path prefix. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prefix": {"type": "string", "description": "Path prefix, e.g. 'memories'."},
                "recursive": {"type": "boolean", "description": "Walk subdirectories."},
                "page_size": {"type": "integer", "description": "Max entries to return."},
            },
            "additionalProperties": False,
        },
    },
]

HANDLERS = {
    "rathflow_session_list": tool_session_list,
    "rathflow_memory_list": tool_memory_list,
}


# ------------------------------------------------------------------- protocol


def result(msg_id: object, payload: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": payload}


def error(msg_id: object, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def handle(message: dict) -> dict | None:
    method = message.get("method")
    msg_id = message.get("id")
    if method == "initialize":
        return result(
            msg_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "ping":
        return result(msg_id, {})
    if method == "tools/list":
        return result(msg_id, {"tools": TOOLS})
    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        handler = HANDLERS.get(name)
        if handler is None:
            return result(
                msg_id,
                {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True},
            )
        try:
            text = handler(args)
        except Exception as exc:  # surfaced to the model, not crashed
            return result(
                msg_id, {"content": [{"type": "text", "text": str(exc)}], "isError": True}
            )
        return result(msg_id, {"content": [{"type": "text", "text": text}], "isError": False})
    if msg_id is None:
        return None
    return error(msg_id, -32601, f"Method not found: {method}")


def main() -> int:
    log(f"ready ({SERVER_NAME} {SERVER_VERSION})")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            log("dropping non-JSON line")
            continue
        response = handle(message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
