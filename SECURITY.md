# Security Policy

## Scope

This repository contains Codex plugin instructions (skills) and manifests. It
does not contain the RathFlow service, the RathFlow CLI, an MCP server
implementation, or any credentials.

The MCP server the plugin registers is `rathflow mcp serve`, which ships inside
the `rathflow-cli` package installed from PyPI / npm. Report vulnerabilities in
it against <https://github.com/Rath-Team/rathflow-cli>, not here.

## Reporting a vulnerability

Please report suspected vulnerabilities privately through GitHub Security
Advisories:

<https://github.com/Rath-Team/rathflow-codex-plugin/security/advisories/new>

Do not open a public issue for security reports. Include what you observed, how
to reproduce it, and the affected version (`plugin.json` `version` field).
We aim to acknowledge reports within 3 business days.

## What this plugin never does

- It never asks for a password or token in chat, and never prints credentials.
- It never searches the filesystem for RathFlow source, and never builds or
  installs from a local checkout.
- It never starts the RathFlow Gateway.
- It does not ship secrets: authentication comes from your own CLI config file
  (`RATHFLOW_CONFIG_DIR`, default `~/.config/rathflow/config.json`) or from
  environment variables.

## Hardening notes for users

- Log in with `rathflow auth login -e <email>` in your own terminal, so the
  password prompt stays private.
- The CLI writes its config with `0600` permissions because it contains tokens.
- The MCP server starts read-only: writes are unavailable unless you opt in by
  setting `RATHFLOW_MCP_WRITE=1` in its environment. Leave it unset unless you
  want the agent to be able to create sessions, write memory or run sandbox
  commands.
- The MCP server runs under the same credentials as the CLI and refreshes the
  token in place, so it inherits the config file's `0600` protection. Keep the
  config directory private (`RATHFLOW_CONFIG_DIR`).
