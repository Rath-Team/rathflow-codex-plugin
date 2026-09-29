#!/usr/bin/env python3
"""Protocol self-check for the plugin's bundled MCP server.

Runs the server the same way `.mcp.json` does (as a real subprocess over a pipe)
and asserts the JSON-RPC / MCP contract:

  * one JSON object per line on stdout, nothing else on stdout;
  * initialize negotiates a protocol version and advertises tools;
  * notifications get no response;
  * tools/list and tools/call return the documented shapes;
  * bad JSON gets a -32700 parse error with id null;
  * unknown methods get -32601;
  * a non-"2.0" envelope gets -32600.

Usage: python3 scripts/check_mcp_server.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parent.parent / "plugins" / "rathflow-codex-plugin" / "server" / "__main__.py"


class Checks:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def ok(self, condition: bool, label: str) -> None:
        print(("  ok   " if condition else "  FAIL ") + label)
        if not condition:
            self.failures.append(label)


def main() -> int:
    checks = Checks()
    if not SERVER.is_file():
        print(f"server not found: {SERVER}")
        return 1

    proc = subprocess.Popen(
        [sys.executable, str(SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    assert proc.stdin and proc.stdout

    def send(payload: str) -> None:
        proc.stdin.write(payload + "\n")
        proc.stdin.flush()

    def read() -> dict:
        line = proc.stdout.readline()
        if not line:
            raise AssertionError("server closed stdout unexpectedly")
        return json.loads(line)

    send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}))
    init = read()
    checks.ok(init.get("id") == 1, "initialize: id echoed")
    result = init.get("result", {})
    checks.ok(result.get("protocolVersion") == "2025-06-18", "initialize: protocol version echoed back")
    checks.ok(result.get("capabilities", {}).get("tools") is not None, "initialize: advertises tools")
    checks.ok(result.get("serverInfo", {}).get("name") == "rathflow", "initialize: serverInfo.name")

    send(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}))
    send(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}))
    listing = read()
    tools = listing.get("result", {}).get("tools", [])
    checks.ok(listing.get("id") == 2, "tools/list: notification produced no response")
    checks.ok(len(tools) >= 10, f"tools/list: {len(tools)} tools")
    names = {t["name"] for t in tools}
    checks.ok("rathflow_whoami" in names, "tools/list: whoami present")
    checks.ok("rathflow_api_call" not in names, "tools/list: write escape hatch hidden by default")
    checks.ok(all("inputSchema" in t and "title" in t for t in tools), "tools/list: every tool has schema+title")

    send(json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "rathflow_whoami", "arguments": {}}}))
    call = read()
    content = call.get("result", {}).get("content", [])
    checks.ok(call.get("id") == 3, "tools/call: id echoed")
    checks.ok(bool(content) and content[0].get("type") == "text", "tools/call: text content block")

    send(json.dumps({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "nope", "arguments": {}}}))
    unknown_tool = read()
    checks.ok(unknown_tool.get("result", {}).get("isError") is True, "tools/call: unknown tool is an isError result")

    send(json.dumps({"jsonrpc": "2.0", "id": 5, "method": "ping"}))
    checks.ok(read().get("result") == {}, "ping: empty result")

    send(json.dumps({"jsonrpc": "2.0", "id": 6, "method": "no/such/method"}))
    checks.ok(read().get("error", {}).get("code") == -32601, "unknown method: -32601")

    send("{not json")
    parse_error = read()
    checks.ok(parse_error.get("error", {}).get("code") == -32700, "bad JSON: -32700")
    checks.ok(parse_error.get("id") is None, "bad JSON: id is null")

    send(json.dumps({"jsonrpc": "1.0", "id": 7, "method": "ping"}))
    checks.ok(read().get("error", {}).get("code") == -32600, "bad version: -32600")

    proc.stdin.close()
    proc.wait(timeout=10)
    checks.ok(proc.returncode == 0, "clean EOF exit status 0")

    print()
    if checks.failures:
        print(f"{len(checks.failures)} check(s) failed")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
