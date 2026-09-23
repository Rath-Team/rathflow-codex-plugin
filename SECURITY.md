# Security Policy

## Scope

This repository contains Codex plugin instructions (skills), manifests, and an
experimental MCP server that talks to the RathFlow Gateway. It does not contain
the RathFlow service, the RathFlow CLI, or any credentials.

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
- Treat the MCP server as read-only tooling: it exposes two read-only tools and
  takes no write actions.
