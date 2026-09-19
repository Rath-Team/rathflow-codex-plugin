# RathFlow Codex Plugin

Minimal Codex plugin for using RathFlow through the local `rathflow` CLI.

This plugin is skill-only. It does not include an MCP server and does not start a RathFlow Gateway. The user must install the CLI separately and configure it to reach a local or remote Gateway.

## Repository Layout

```text
.codex-plugin/plugin.json  Plugin manifest
skills/rathflow-cli/       CLI usage instructions loaded by Codex
```

## Local Development

From the RathFlow repository, install the Python CLI in editable mode:

```bash
uv pip install -e ./cli/python
```

Verify the CLI and configure the Gateway:

```bash
rathflow --help
export RATHFLOW_BASE_URL=http://127.0.0.1:8080
rathflow auth login -e me@example.com
rathflow whoami
```

The Node implementation is an alternative and exposes the same `rathflow` command:

```bash
npm install -g ./cli/node
```

## Validate

Run the Codex plugin validator:

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

## Install for Codex Testing

The plugin must be exposed through a configured marketplace snapshot before `codex plugin add` can install it. For a repository marketplace, create a marketplace entry whose source path points to this plugin, add that marketplace with `codex plugin marketplace add <path>`, and then install `rathflow-codex-plugin` from the marketplace.

After installation, start a new Codex session and ask:

```text
请列出我当前 RathFlow 项目的最近会话。
```

Codex should use the local `rathflow` command rather than pretending that it has direct access to the RathFlow service.
