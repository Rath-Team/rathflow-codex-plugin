# Contributing

## Layout

```text
.agents/plugins/marketplace.json          # marketplace registration
plugins/rathflow-codex-plugin/
├── .codex-plugin/plugin.json             # plugin manifest
├── .mcp.json                             # experimental MCP server registration
├── assets/                               # logo and composer icon
├── mcp/server.py                         # experimental stdio MCP server
└── skills/{rathflow-cli,rathflow-setup}/SKILL.md
scripts/check_plugin.py                   # CI structure check
```

## Validate locally

Always run the repository check; it is what CI runs:

```bash
python3 scripts/check_plugin.py plugins/rathflow-codex-plugin
```

When the Codex `plugin-creator` skill is available, also run the official
validator (it is stricter and authoritative):

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugins/rathflow-codex-plugin
```

## Iterate on a local install

1. Bump the manifest with a cachebuster token:

   ```bash
   python3 ~/.codex/skills/.system/plugin-creator/scripts/update_plugin_cachebuster.py \
     plugins/rathflow-codex-plugin
   ```

2. Reinstall and start a **new** Codex session, because skills and MCP servers
   only load at session start:

   ```bash
   codex plugin add rathflow-codex-plugin@rathflow-marketplace
   ```

3. Before opening a release PR, drop the `+codex.*` suffix so the version is
   plain semver (CI warns when a cachebuster is committed).

## Rules

- Keep skills actionable: concrete commands, expected outputs, and explicit
  "stop and ask the user" conditions.
- The plugin never searches the filesystem for RathFlow source, never builds or
  installs from a local checkout, and never starts the Gateway.
- Never put credentials, tokens, or passwords in the repository, in chat
  instructions, or in tool output.

## License

MIT, see `LICENSE`.
