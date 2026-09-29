# RathFlow Codex Plugin

[中文](README.md) | English

Let Codex use RathFlow — projects, sessions, memory, sandboxes, and billing —
through the MCP server bundled with this plugin, or through the local `rathflow` CLI.

This plugin bundles its own MCP server:

- the server ships with the plugin (`server/`, Python standard library only, zero
  third-party dependencies), so **nothing has to be installed first**;
- it does not ship, install, or start the RathFlow Gateway;
- it contains exactly two skills: `rathflow-setup` (setup and troubleshooting)
  and `rathflow-cli` (day-to-day operations);
- the `rathflow` CLI (distributed separately on PyPI / npm) is needed only for
  **logging in** and for shell work. The plugin will not look for source or
  deploy anything locally.

## Requirements

- Codex installed;
- this plugin installed (next section) — the MCP tools then work immediately;
- a RathFlow account, or sign up first at <https://rathflow.lynwe.com/register>;
- to authenticate: install the `rathflow` CLI and run `rathflow auth login -e
  <email>` once in a terminal (or provide `RATHFLOW_TOKEN` to the server). MCP and
  the CLI read the same config file;
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
- **Installs it when missing**: `rathflow-cli` is a normal package on PyPI and on
  npm, so Codex runs `uv tool install 'rathflow-cli[socks]'` (falling back to
  `pipx`, `pip install --user`, then `npm install -g`) itself. The installers only
  fetch from a registry — never a local source tree. It stops only if every path
  fails.
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

`rathflow-cli` is **published on PyPI and npm**
([pypi.org/project/rathflow-cli](https://pypi.org/project/rathflow-cli/),
[npmjs.com/package/rathflow-cli](https://www.npmjs.com/package/rathflow-cli)):

```bash
uv tool install 'rathflow-cli[socks]'         # preferred when uv exists (Python 3.10+)
pipx install 'rathflow-cli[socks]'            # otherwise
python3 -m pip install --user 'rathflow-cli[socks]'   # fallback
npm install -g rathflow-cli                   # equivalent Node implementation (Node 20+)
```

Prefer the `[socks]` extra on the Python paths: many desktop proxies (Clash and
friends) export `ALL_PROXY=socks://…`, and `httpx` needs `socksio` to speak SOCKS.
CLI ≥ 0.1.5 rewrites `socks://` to `socks5h://` on its own, so you do not have to
edit environment variables by hand. The proxy has to be set in the shell that
started Codex, because the MCP server only inherits the proxy variables the plugin
forwards (see "MCP" below).

You normally don't have to do this by hand: Codex installs the CLI when it is
missing. The two packages are implementations of one CLI — same commands, options,
output, exit codes and config file — so **install only one globally**; both provide
a `rathflow` command and would shadow each other. Installing from a source checkout
is a developer workflow, not part of the plugin flow — Codex never clones the repo or
falls back to a local checkout; if the install fails it reports the error and stops.
The CLI's built-in Gateway default is the hosted `https://rathflow.lynwe.com`.

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

## MCP

The plugin bundles a stdio MCP server (`server/`, Python standard library only).
`.mcp.json` starts it with `python3 -c '<bootstrap>'`, and the bootstrap locates
the plugin's own copy via
`$CODEX_HOME/plugins/cache/*/rathflow-codex-plugin/*/server/__main__.py` — nothing
depends on `rathflow` being on `PATH`, so a fresh install works on the first
session.

- 10 read tools out of the box (identity, projects, sessions, memory, sandboxes,
  workflows, usage, endpoint discovery);
- `rathflow_project_use` (local config only) is always visible; setting
  `RATHFLOW_MCP_WRITE=1` in the server's environment additionally unlocks the write
  endpoints reachable through `rathflow_api_call`, off by default;
- endpoints without a named tool are reachable through `rathflow_endpoints` +
  `rathflow_api_call`;
- auth is the same config file as the CLI (`~/.config/rathflow/config.json`,
  relocatable with `RATHFLOW_CONFIG_DIR`). Log in once with the CLI; the server
  refreshes the token itself;
- proxies: the server speaks `http` and `socks5h` itself and normalizes
  `socks://` / `socks4://` to `socks5h://`, so it needs neither the `[socks]` extra
  nor `socksio`. Codex still spawns MCP servers with a **filtered** environment
  (core variables plus the names in the plugin's `.mcp.json` `env_vars`), so the
  proxy must be present in the environment Codex was started from;
- it loads in a **new** session only, and `codex mcp list` shows whether it is
  registered. When not authenticated, the tools return a clear instruction to run
  `rathflow auth login` — never a hunt for source or a local deployment.

## Known limits

- The launch command is `python3`, so the machine needs Python 3.9+ (Codex's own
  plugin scaffolding scripts make the same assumption). On Windows, if only `py`
  exists, change `command` in `.mcp.json` to `py`.
- The bundled server and the CLI share the same tool surface but are **not the same
  code**: endpoint changes in the CLI have to be mirrored here.

## License

MIT — see `LICENSE`. This covers the plugin instructions and the bundled MCP
server in this repository, not the RathFlow service or CLI.
