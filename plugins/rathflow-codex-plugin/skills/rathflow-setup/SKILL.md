---
name: rathflow-setup
description: Set up or troubleshoot RathFlow for Codex when the user asks to install the CLI, connect a Gateway, log in, select a project, or verify a RathFlow plugin installation.
---

# Set up RathFlow

Drive the user to a working `rathflow` CLI connection, and do every step yourself that does not
need a human. The only step that truly needs the user is the password prompt. The plugin ships
instructions only; it does not install the CLI or start a Gateway.

## 1. Check whether the CLI is installed

```bash
command -v rathflow
rathflow --help
```

Treat the CLI as a released product: its installed command is the only supported interface. Do
**not** search the filesystem for RathFlow source or a project checkout, do not look for a
virtualenv, and do not build or install RathFlow from a local source tree.

## 2. If the CLI is missing, stop and ask the user to install it

Report that `rathflow` is not on `PATH` and hand the user a single install action to run in their
own terminal:

```bash
uv tool install rathflow-cli     # or: pip install rathflow-cli
```

The CLI is not published on PyPI yet, so this may fail for now; in that case tell the user to obtain
it from the official RathFlow distribution channel. Never install a similarly named third-party
package, never clone or build RathFlow's source, and never start a Gateway. Once the CLI is
installed, re-run this skill from step 1.

## 3. Read the effective configuration

```bash
rathflow config show
rathflow config list
```

State what is actually in force. Precedence is `--base-url`/`--project` flag > environment
(`RATHFLOW_BASE_URL`, `RATHFLOW_PROJECT`, `RATHFLOW_TOKEN`) > profile > built-in default
`http://127.0.0.1:8080`. If `RATHFLOW_CONFIG_DIR` is set, the config file is
`$RATHFLOW_CONFIG_DIR/config.json`, not `~/.config/rathflow/config.json`; say which file this
session reads and writes. Profiles are selected with `--profile`/`-p`.

## 4. Choose the Gateway and prove it is the API

- If the effective `base_url` is still the local default and the user does not run a local Gateway,
  ask which Gateway to use; suggest the hosted `https://rathflow.lynwe.com`.
- Verify before login: `curl -s -o /dev/null -w '%{http_code}' <gateway-url>/api/v1/sessions`
  - `401` → the Gateway API is reachable; continue.
  - `200` with `text/html`, or a connection error → wrong address. The hosted web app answers `200`
    on almost every path, so never treat a `200` as proof of a working Gateway.
- Persist only after confirmation: `rathflow config set base_url <gateway-url>`, then re-run
  `rathflow config show` to confirm the effective URL actually changed. Never silently replace a
  non-default endpoint, and call out when an environment variable overrides the saved value.

## 5. Log in (the one step the user runs)

`rathflow whoami` exiting with code 2 and `未登录` means not authenticated. Give the user exactly one
command to run in their own terminal, in the same config directory this session uses:

```bash
RATHFLOW_CONFIG_DIR=<dir> rathflow auth login -e <their-email>
```

Never ask for or accept a password in chat, never pass `--password`, and never print tokens. If
login fails, report the error; do not retry blindly.

## 6. Select the project scope

```bash
rathflow project list
```

Keep an existing selection. If none is set, ask which accessible project to use, then
`rathflow project use <project_id>`.

## 7. Verify and report

Run one read-only command such as `rathflow session list`, then report: CLI availability, effective
Gateway, profile, config file/dir, login state, project scope, and any remaining blocker. Do not
create a session or mutate data just to verify.

## Installing the plugin itself

Plugin installation is a terminal step, not something this skill can perform:
`codex plugin marketplace add <repo>` then `codex plugin add rathflow-codex-plugin@rathflow-marketplace`.
Plugin skills only load in a **new** Codex session, so install first, then start a fresh session.
If the marketplace clone fails because the repo needs credentials, use the SSH source:
`codex plugin marketplace add ssh://git@github.com/Rath-Team/rathflow-codex-plugin.git`.

If the CLI is already configured and the user only asks about operations, use the `rathflow-cli`
skill instead of repeating setup.
