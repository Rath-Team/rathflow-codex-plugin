# RathFlow Codex Plugin

[中文](README.md) | English

Let Codex use RathFlow — projects, sessions, memory, sandboxes, and billing —
through the locally installed `rathflow` CLI.

This is a **skill-only plugin**:

- it does not ship or install the RathFlow CLI (the CLI is distributed on PyPI);
- it does not start the RathFlow Gateway;
- it contains exactly two skills: `rathflow-setup` (setup and troubleshooting)
  and `rathflow-cli` (day-to-day operations);
- it also registers one experimental read-only MCP server, described below.

## Requirements

- Codex installed;
- the `rathflow` CLI installed and on `PATH` (`rathflow --help` works). The
  plugin will not look for source or install the CLI for you;
- a RathFlow account;
- network access to your RathFlow Gateway.

## Install

```bash
codex plugin marketplace add Rath-Team/rathflow-codex-plugin
codex plugin add rathflow-codex-plugin@rathflow-marketplace
```

If the clone asks for credentials, use the SSH source instead:

```bash
codex plugin marketplace add ssh://git@github.com/Rath-Team/rathflow-codex-plugin.git
codex plugin add rathflow-codex-plugin@rathflow-marketplace
```

Plugin installation happens in the terminal: skills load with the **next**
session. Install first, then start a new Codex session and type:

```text
Help me set up RathFlow. Check whether the CLI is installed and which Gateway it
points at; ask before installing software or changing existing config, and never
ask me for a password in chat.
```

The password prompt is yours to run in your own terminal — Codex never asks for
or accepts credentials in chat.

## What Codex does itself

`rathflow-setup` is an executable checklist, so Codex does the work instead of
handing you a manual configuration guide or asking the same question twice:

- **Checks the CLI** with `command -v rathflow` / `rathflow --help` only. It does
  **not** search the filesystem for source, checkouts, or virtualenvs.
- **Installs it when missing**: `rathflow-cli` is a normal PyPI package, so Codex
  runs `uv tool install rathflow-cli` (falling back to `pipx` or
  `pip install --user`) itself. `uv`/`pipx` are only installers — the wheel comes
  from PyPI, not a local source tree. It stops only if every install path fails.
- **Reads the effective config** (`config show` / `config list`) and explains the
  precedence: flag > environment (`RATHFLOW_BASE_URL`, `RATHFLOW_PROJECT`,
  `RATHFLOW_TOKEN`) > profile > default `https://rathflow.lynwe.com`, plus where
  `RATHFLOW_CONFIG_DIR` puts the file.
- **Proves the Gateway is the API** with
  `curl -s -o /dev/null -w '%{http_code}' <gateway>/api/v1/sessions`: `401` means
  the API is there; `200 text/html` is just the web app and proves nothing.
- **Gives you one login command** (`rathflow auth login -e <email>`) with the right
  config directory, for you to run yourself.
- **Selects the project and verifies read-only** with `project list`,
  `project use`, and `session list`.

## CLI availability

`rathflow-cli` is **published on PyPI** ([pypi.org/project/rathflow-cli](https://pypi.org/project/rathflow-cli/),
currently `0.1.0`):

```bash
uv tool install rathflow-cli                  # preferred when uv exists
pipx install rathflow-cli                     # otherwise
python3 -m pip install --user rathflow-cli    # fallback
```

You normally don't have to do this by hand: Codex installs the CLI when it is
missing. All three installers fetch the same wheel from PyPI. Installing from a
source checkout is a developer workflow, not part of the plugin flow — Codex
never clones the repo or falls back to a local checkout; if the install fails it
reports the error and stops. The CLI's built-in Gateway default is the hosted
`https://rathflow.lynwe.com`.

## Manual configuration (optional)

```bash
rathflow config set base_url https://rathflow.lynwe.com
curl -s -o /dev/null -w '%{http_code}\n' https://rathflow.lynwe.com/api/v1/sessions   # expect 401
```

A `401` (JSON `unauthorized`) means the Gateway API is reachable; `200 text/html`
means the address is the web app, not the Gateway. Then log in:

```bash
rathflow auth login -e your-email@example.com
rathflow whoami
rathflow project list
rathflow project use <project_id>
```

The password prompt runs in your terminal. Never paste passwords or tokens into
chat, READMEs, or repositories. `RATHFLOW_BASE_URL` overrides the saved value if
it is set.

## Common prompts

```text
List the recent sessions in my current RathFlow project.
Search RathFlow memory for "project config".
Show usage for the current RathFlow project.
Create a RathFlow session and send this prompt: …
```

Codex should run CLI commands such as `rathflow session list` rather than
hand-rolling HTTP requests. For mutating actions (create, delete, write, invite,
execute), it states the operation and asks for confirmation first.

## MCP (experimental)

The plugin registers an experimental MCP server (`.mcp.json` → `mcp/server.py`,
standard library only) that calls the Gateway REST API directly and exposes two
read-only tools, `rathflow_session_list` and `rathflow_memory_list`. It does not
use the CLI; auth reuses the CLI config and environment variables, returning
"run `rathflow auth login`" when unauthenticated. It loads in a **new** session
only, and `codex mcp list` shows whether it is registered.

Known limits: it starts via `python3`, which Windows usually does not provide
(only `python` / `py`), so `.mcp.json` needs adjusting there — the skills are
unaffected. The tool surface is deliberately narrow (read-only, no streaming, no
writes); the production shape is a Gateway-hosted remote MCP.

## License

MIT — see `LICENSE`. This covers the plugin instructions and the experimental MCP
server in this repository, not the RathFlow service or CLI.
