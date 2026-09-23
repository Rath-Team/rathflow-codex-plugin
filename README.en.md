# RathFlow Codex Plugin

[中文](README.md) | English

Let Codex use RathFlow — projects, sessions, memory, sandboxes, and billing —
through the locally installed `rathflow` CLI.

This is a **skill-only plugin** with two skills:

- it does not ship the RathFlow CLI;
- it does not start the RathFlow Gateway;
- it does not contain an MCP server beyond the experimental one described below;
- `rathflow-setup` guides Codex through checking the CLI, choosing a Gateway,
  handing you the login command, and selecting a project; `rathflow-cli` guides
  it through day-to-day commands.

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

If the clone asks for credentials (private repo or no GitHub auth), use the SSH
source instead:

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

- **Checks the CLI** with `command -v rathflow` / `rathflow --help` only. It does
  **not** search the filesystem for source, checkouts, or virtualenvs.
- **Stops and hands off** when the CLI is missing, telling you to run
  `uv tool install rathflow-cli` (or `pip install rathflow-cli`) yourself. The CLI
  is distributed as a product, so Codex never clones the repo or builds from a
  local checkout.
- **Reads the effective config** (`config show` / `config list`) and explains the
  precedence: flag > environment (`RATHFLOW_BASE_URL`, `RATHFLOW_PROJECT`,
  `RATHFLOW_TOKEN`) > profile > default `http://127.0.0.1:8080`, plus where
  `RATHFLOW_CONFIG_DIR` puts the file.
- **Proves the Gateway is the API** with
  `curl -s -o /dev/null -w '%{http_code}' <gateway>/api/v1/sessions`: `401` means
  the API is there; `200 text/html` is just the web app and proves nothing.
- **Gives you one login command** (`rathflow auth login -e <email>`) with the right
  config directory, for you to run yourself.
- **Selects the project and verifies read-only** with `project list`,
  `project use`, and `session list`.

## CLI availability

`rathflow-cli` is **not on PyPI yet**, so a brand-new user cannot install it with
`pip` today. Once published:

```bash
pip install rathflow-cli     # or: uv tool install rathflow-cli
```

Installing the CLI from a source checkout is a developer workflow, not part of
the plugin flow — Codex will not do it.

## Manual configuration (optional)

```bash
rathflow config set base_url https://rathflow.lynwe.com
curl -s -o /dev/null -w '%{http_code}\n' https://rathflow.lynwe.com/api/v1/sessions   # expect 401
```

`RATHFLOW_BASE_URL` overrides the saved value if it is set. Then log in:

```bash
rathflow auth login -e your-email@example.com
rathflow whoami
rathflow project list
rathflow project use <project_id>
```

Never paste passwords or tokens into chat, READMEs, or repositories.

## MCP (experimental)

The plugin also registers an experimental MCP server (`.mcp.json` →
`mcp/server.py`, standard library only) that calls the Gateway REST API directly
and exposes two read-only tools, `rathflow_session_list` and
`rathflow_memory_list`. It does not use the CLI.

- Auth reuses the CLI config (`RATHFLOW_CONFIG_DIR`, default `~/.config/rathflow`)
  or `RATHFLOW_TOKEN` / `RATHFLOW_BASE_URL` / `RATHFLOW_PROJECT`, with the same
  precedence as the CLI.
- When unauthenticated the tool returns "run `rathflow auth login`" instead of
  failing silently, and it never prints tokens.
- MCP servers also only load in a **new** session; `codex mcp list` shows whether
  it is registered.
- Scope: read-only, two tools, no streaming, no writes. The production shape is a
  Gateway-hosted remote MCP (`type: http` + OAuth or an MCP API key) with the
  plugin reduced to registration plus auth guidance.

## Common prompts

```text
List the recent sessions in my current RathFlow project.
Search RathFlow memory for "project config".
Show usage for the current RathFlow project.
Create a RathFlow session and send this prompt: …
```

For mutating actions (create, delete, write, invite, execute), Codex states the
operation and asks for confirmation first.

## Repository layout

```text
rathflow-codex-plugin/
├── .agents/plugins/marketplace.json
├── .github/{workflows/ci.yml,dependabot.yml}
├── scripts/check_plugin.py
└── plugins/rathflow-codex-plugin/
    ├── .codex-plugin/plugin.json
    ├── .mcp.json
    ├── assets/{icon.png,composer-icon.png,screenshot.png}
    ├── mcp/server.py
    └── skills/{rathflow-cli,rathflow-setup}/SKILL.md
```

## Development

```bash
python3 scripts/check_plugin.py plugins/rathflow-codex-plugin      # what CI runs
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugins/rathflow-codex-plugin                                    # official validator
```

For local iteration, add a cachebuster token to the version, reinstall, and
start a new session; drop the `+codex.*` suffix before opening a release PR (CI
warns about committed cachebusters). See `CONTRIBUTING.md`.

## License

MIT — see `LICENSE`. This covers the plugin instructions and the experimental MCP
server in this repository, not the RathFlow service or CLI.
