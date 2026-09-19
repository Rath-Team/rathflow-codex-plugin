---
name: rathflow-cli
description: Use RathFlow through the installed rathflow CLI when the user asks to inspect or operate RathFlow projects, sessions, sandboxes, memory, or billing.
---

# RathFlow CLI

Use the local `rathflow` command as the interface to RathFlow. The CLI is an HTTP client; it does not start the RathFlow Gateway.

## Preconditions

- Confirm that `rathflow` is installed with `rathflow --help`.
- Confirm the configured endpoint and project with `rathflow config show`.
- If installation, Gateway configuration, login, or project selection is missing, follow the `rathflow-setup` skill before attempting operations.
- If authentication is missing, ask the user to run `rathflow auth login -e <email>` or provide an already configured token.
- Do not print, echo, or include access tokens in responses.
- The default endpoint is local. Use `RATHFLOW_BASE_URL` or the CLI configuration when the Gateway is remote.

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
