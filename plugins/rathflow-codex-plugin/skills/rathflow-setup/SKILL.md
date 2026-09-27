---
name: rathflow-setup
description: Set up or troubleshoot RathFlow for Codex when the user asks to install the CLI, connect a Gateway, log in, select a project, or verify a RathFlow plugin installation.
---

# Set up RathFlow

Drive the user to a working `rathflow` CLI connection, and do every step yourself that does not
need a human. The only step that truly needs the user is the password prompt. The plugin ships
instructions only; it does not bundle the CLI or start a Gateway.

## 1. Check whether the CLI is installed

```bash
command -v rathflow
rathflow --help
```

Treat the CLI as a released product: its installed command is the only supported interface. Do
**not** search the filesystem for RathFlow source or a project checkout, do not look for a
virtualenv, and do not build or install RathFlow from a local source tree.

## 2. If the CLI is missing, install it from PyPI and continue

`rathflow-cli` is a normal PyPI package, so installing it is part of doing the setup — do it
yourself instead of asking the user to. Pick the first installer that exists on this machine:

```bash
uv tool install rathflow-cli                  # 首选（uv 只是安装器，包同样来自 PyPI）
pipx install rathflow-cli                     # 没有 uv 时
python3 -m pip install --user rathflow-cli    # 兜底
```

The package name is exactly `rathflow-cli` (<https://pypi.org/project/rathflow-cli/>). All three
installers download the same wheel from PyPI; `uv`/`pipx` are not local sources, they just isolate
the tool. Afterwards make sure the command is reachable (`uv tool update-shell`, or `~/.local/bin`
on `PATH`), re-run step 1, and continue with step 3. Only if every install path fails (no network,
no Python) do you stop and report the error.

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
