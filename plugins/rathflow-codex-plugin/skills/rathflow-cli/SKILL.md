---
name: rathflow-cli
description: Use RathFlow through the installed rathflow CLI when the user asks to inspect or operate RathFlow projects, sessions, sandboxes, memory, or billing.
---

# RathFlow CLI

Use the local `rathflow` command as the interface to RathFlow. The CLI is an HTTP client; it does not start the RathFlow Gateway.

## Preconditions

- Confirm that `rathflow` is installed and runnable with `rathflow --help`. The CLI is a released
  product: do not search the filesystem for source, a checkout, or a virtualenv, and do not build or
  install from a local source tree. If it is missing, follow the `rathflow-setup` skill.
- Check that the resolved command is current: `rathflow --version` should be 0.1.5 or newer and
  `rathflow mcp --help` should exist. `No such command 'mcp'` means `PATH` resolves to a stale
  install — align it (see the `rathflow-setup` skill) instead of working around it through the old
  virtualenv.
- Confirm the effective endpoint, profile, and project with `rathflow config show`. Precedence is
  `--base-url`/`--project` flag > `RATHFLOW_BASE_URL`/`RATHFLOW_PROJECT`/`RATHFLOW_TOKEN` > profile >
  built-in default `https://rathflow.lynwe.com`. `RATHFLOW_CONFIG_DIR` moves the config file away from
  `~/.config/rathflow/`.
- If installation, Gateway configuration, login, or project selection is missing, follow the
  `rathflow-setup` skill before attempting operations.
- If authentication is missing (`rathflow whoami` exits 2 with `未登录`), ask the user to run
  `rathflow auth login -e <email>` in their own terminal.
- If the CLI dies with `ValueError: Unknown scheme for proxy URL`, the environment exports a
  `socks://…` proxy that httpx cannot parse — normalize it for this command
  (`ALL_PROXY=socks5://127.0.0.1:7897 rathflow …`) instead of hunting for source; see
  `rathflow-setup` §0. `ImportError: … 'socksio' …` means the `[socks]` extra is missing.
- Do not print, echo, or include access tokens in responses.

## Command Selection

- Identity and access: `rathflow whoami`, `rathflow org list`, `rathflow project list`.
- Project scope: `rathflow project use <project_id>`.
- Sessions and agents: `rathflow session list`, `rathflow session create`, `rathflow agent prompt`.
- Sandboxes: `rathflow sandbox list`, `rathflow sandbox create`, `rathflow sandbox exec`.
- Memory: `rathflow memory list`, `rathflow memory search`, `rathflow memory write`.
- Billing visibility: `rathflow billing subscription`, `rathflow billing usage`, `rathflow billing invoices`.

Use `--json` when output will be inspected or summarized programmatically. Prefer the CLI's named commands over the low-level `rathflow api` escape hatch unless no named command exists.

## Safety

- Read-only commands may run directly when they match the user's request.
- Before creating, deleting, terminating, sharing, inviting, writing, or executing anything, state the intended operation and obtain confirmation if the user did not explicitly request that mutation.
- Preserve the user's project scope. Do not switch projects without an explicit project ID or user instruction.
- Report the CLI error and its likely remedy when a command fails; do not silently retry destructive operations.

## Output

Summarize the command result in natural language. For large or structured responses, use `--json` and extract only the fields relevant to the user's request. Do not claim success unless the command exits successfully.
