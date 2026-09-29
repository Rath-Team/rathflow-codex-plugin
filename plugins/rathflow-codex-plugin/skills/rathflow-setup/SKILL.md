---
name: rathflow-setup
description: Set up or troubleshoot RathFlow for Codex when the user asks to install the CLI, connect a Gateway, log in, select a project, or verify a RathFlow plugin installation.
---

# Set up RathFlow

RathFlow (for the record, in case the user asks) is a hosted platform for AI coding agents: sessions
and event streams, agent definitions and runs, sandboxes, project memory, assets and workflows, plus
usage and billing. The web app is <https://rathflow.lynwe.com>; the plugin reaches it through the
`rathflow` CLI.

Drive the user to a working `rathflow` CLI connection, and do every step yourself that does not
need a human. The only step that truly needs the user is the password prompt. The plugin ships
instructions only: it does not bundle the CLI, does not bundle an MCP server, and does not start a
Gateway. The MCP server this plugin registers is `rathflow mcp serve` — a subcommand of the
published CLI.

## 1. Check whether the CLI is installed

```bash
command -v rathflow
rathflow --help
rathflow mcp serve --help    # 工具面走 MCP 时必须有；缺它说明 CLI 太旧
```

Treat the CLI as a released product: its installed command is the only supported interface. Do
**not** search the filesystem for RathFlow source or a project checkout, do not look for a
virtualenv, and do not build or install RathFlow from a local source tree.

## 2. If the CLI is missing, install it from a public registry and continue

`rathflow-cli` is a normal package on **PyPI** (Python 3.10+) and **npm** (Node 20+); both ship the
same `rathflow` command, so installing it is part of doing the setup — do it yourself instead of
asking the user to. Pick the first option that works on this machine:

```bash
uv tool install rathflow-cli                  # Python 首选（uv 只是安装器，包来自 PyPI）
pipx install rathflow-cli                     # 没有 uv 时
python3 -m pip install --user rathflow-cli    # 兜底
npm install -g rathflow-cli                   # 有 Node 20+ 时等价
```

The package name is exactly `rathflow-cli` on both registries
(<https://pypi.org/project/rathflow-cli/>, <https://www.npmjs.com/package/rathflow-cli>). They are
two implementations of one CLI — same commands, options, output and exit codes, same config file —
and the installers are not local sources. **Install only one of them globally**: both provide a
binary named `rathflow`, so a second install would shadow the first.

Afterwards make sure the command is reachable (`uv tool update-shell`, `~/.local/bin` on `PATH`, or
the npm global bin directory from `npm prefix -g`), re-run step 1, and continue with step 3. Only if
every install path fails (no network, no Python, no Node) do you stop and report the error.

MCP needs `rathflow-cli >= 0.1.4` **and** currently only ships in the Python package. If the user
wants the MCP tools (rather than just the skills) and `mcp serve --help` fails, install the Python
package even if the npm CLI is already present, and mention that the two must not both be first on
`PATH`.

Two hard rules for this step:

- Never clone a RathFlow source tree, search the disk for a checkout, or build from source. A local
  checkout is **not** a fallback for a failed install.
- Never start a Gateway. This plugin drives the released CLI against a service the user already runs
  (the hosted default or their own).

## 3. Read the effective configuration

```bash
rathflow config show
rathflow config list
```

State what is actually in force. Precedence is `--base-url`/`--project` flag > environment
(`RATHFLOW_BASE_URL`, `RATHFLOW_PROJECT`, `RATHFLOW_TOKEN`) > profile > built-in default
`https://rathflow.lynwe.com`. If `RATHFLOW_CONFIG_DIR` is set, the config file is
`$RATHFLOW_CONFIG_DIR/config.json`, not `~/.config/rathflow/config.json`; say which file this
session reads and writes. Profiles are selected with `--profile`/`-p`.

## 4. Choose the Gateway and prove it is the API

- The built-in default is the hosted Gateway `https://rathflow.lynwe.com`. If the user runs their
  own Gateway, use that address instead. If the effective `base_url` points at a local address
  (`127.0.0.1`, `localhost`) that is not serving, stop and ask which Gateway to use.
- Verify before login: `curl -s -o /dev/null -w '%{http_code}' <gateway-url>/api/v1/sessions`
  - `401` → the Gateway API is reachable; continue.
  - `200` with `text/html`, or a connection error → wrong address. The hosted web app answers `200`
    on almost every path, so never treat a `200` as proof of a working Gateway.
- Persist only after confirmation: `rathflow config set base_url <gateway-url>`, then re-run
  `rathflow config show` to confirm the effective URL actually changed. Never silently replace a
  non-default endpoint, and call out when an environment variable overrides the saved value.

## 5. Get the user an account, then log in (the one step the user runs)

`rathflow whoami` exiting with code 2 and `未登录` means not authenticated. Before handing over a
command, **ask whether the user already has a RathFlow account** — do not assume it. A new user has
never installed this CLI and does not know what the login prompt is for, so say what the command
does and what it will ask for.

**No account yet** — offer both paths, web first (a human can pick a password and see the product):

- Web sign-up: <https://rathflow.lynwe.com/register> (email, display name, password). Afterwards
  they log in with the CLI as below.
- Or straight from the CLI, which registers and logs in in one go:

  ```bash
  rathflow auth register -e <their-email>
  ```

**Has an account** — one command, run in **their own terminal**:

```bash
rathflow auth login -e <their-email>
```

Add a `RATHFLOW_CONFIG_DIR=<dir> ` prefix only when this session's config directory is not the
default `~/.config/rathflow`, and say why the prefix is there. Likewise, if `rathflow` is not on the
user's `PATH` (a plain `uv tool install` puts it in `~/.local/bin`), tell them to run
`uv tool update-shell` so the command works in their terminal **and** in the Codex session that will
launch the MCP server.

Rules for this step:

- The password is typed into the interactive prompt. Never ask for or accept a password in chat,
  never pass `--password`, and never print tokens.
- If login fails, report the error verbatim; do not retry blindly.
- If they have no account and do not want one, stop there — everything else is already set up, and
  the plugin simply has no credentials to work with.

## 6. Select the project scope

```bash
rathflow project list
```

Keep an existing selection. If none is set, ask which accessible project to use, then
`rathflow project use <project_id>`.

## 7. Verify and report

Run one read-only command such as `rathflow session list`, then report: CLI availability, effective
Gateway, profile, config file/dir, login state, project scope, MCP status, and any remaining blocker.
Do not create a session or mutate data just to verify.

**Registered is not the same as working.** MCP servers are spawned once, at session start, so if you
installed or upgraded the CLI during this session the running session's server already failed to
start (its `exec` of `rathflow` happened before the binary existed). Never report MCP as ready in
that case. Use these exact slots so nothing gets paraphrased away:

```text
MCP       需要重启 Codex 才会生效 —— 本次会话启动时 rathflow 还不存在
下一步    1) 重启 Codex  2) 让工具出现  3) 再跑一次验证
```

Only write `MCP  已可用` when the tools were already live in this session.

## 8. MCP: what to tell the user

The plugin's `.mcp.json` registers `rathflow mcp serve`, and Codex only loads MCP servers at session
start. So:

- the tools appear in a **new** session. If the CLI was installed or upgraded in this session, the
  server in the running session already failed to start: restart Codex, then `codex mcp list` and a
  first tool call are the real proof;
- do not report MCP as working on the strength of the registration alone, and do not paper over a
  startup failure — quote it;
- writes are off unless `RATHFLOW_MCP_WRITE=1` is set in the server's environment — do not turn it
  on unasked;
- `codex mcp list` shows whether the server is registered. If it is not listed, the plugin is not
  installed for this Codex home; run the marketplace/add steps below.

When an MCP tool call fails with "not authenticated", the fix is the same as the CLI's: the user runs
`rathflow auth login` in their own terminal, then the tool can be retried in the same session.

## Installing the plugin itself

Plugin installation is a terminal step, not something this skill can perform:
`codex plugin marketplace add <repo>` then `codex plugin add rathflow-codex-plugin@rathflow-marketplace`.
Plugin skills only load in a **new** Codex session, so install first, then start a fresh session.
If the marketplace clone fails because the repo needs credentials, use the SSH source:
`codex plugin marketplace add ssh://git@github.com/Rath-Team/rathflow-codex-plugin.git`.

If the CLI is already configured and the user only asks about operations, use the `rathflow-cli`
skill instead of repeating setup.

## Never do this

- Never search the filesystem for a RathFlow checkout, and never build or run RathFlow from source.
- Never start a Gateway.
- Never install an MCP server from anywhere except the published `rathflow-cli` package.
