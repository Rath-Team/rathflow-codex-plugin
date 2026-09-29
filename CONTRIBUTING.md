# Contributing

## Layout

```text
.agents/plugins/marketplace.json          # marketplace registration
.github/workflows/ci.yml                  # structure check + JSON validation
.github/dependabot.yml                    # keeps SHA-pinned Actions fresh
SECURITY.md                               # vulnerability disclosure policy
requirements-lock.txt                     # explicit "no third-party deps"
plugins/rathflow-codex-plugin/
├── .codex-plugin/plugin.json             # plugin manifest
├── .codexignore                          # files Codex should not read/bundle
├── .mcp.json                             # registers `rathflow mcp serve`
├── assets/                               # logo and composer icon
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

## Zero-knowledge dry run

`scripts/naive-install.sh` builds a throwaway "brand-new user" environment -- clean
`HOME`/`CODEX_HOME`, no `rathflow` anywhere on `PATH`, no `RATHFLOW_*` variables, no
account -- installs the plugin, and optionally drives a Codex turn through it:

```bash
scripts/naive-install.sh                       # prepare, print how to enter
scripts/naive-install.sh --run                 # prepare, then open a session
scripts/naive-install.sh --local . --prompt "我想试试 RathFlow" --assert
scripts/naive-install.sh --proxy socks5h://127.0.0.1:7897   # force a proxy
scripts/naive-install.sh --proxy auto                        # probe local proxy ports
scripts/naive-install.sh --no-proxy                          # force a direct connection
```

`--local` points the marketplace at a working tree, so skill changes can be checked
before they are pushed. `--assert` fails the run when the agent went looking for
source or never told the user how to get an account. The environment is a temp
directory: delete it and nothing is left behind.

By default the run carries over whatever `*_PROXY` the machine already exports, because
that is what a real user has. `socks://` is normalized to `socks5h://` (git and httpx
reject the short form), a failed clone is retried once with `http.version=HTTP/1.1`, and
the effective proxy is printed in the `2.5/4` health check plus pinned into `env.sh`.

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
- Pin GitHub Actions to commit SHAs (Dependabot proposes updates); never use
  `write-all` permissions or unpinned actions.
- Keep `requirements-lock.txt` accurate: today the plugin is instructions plus
  manifests, with no third-party dependencies. The MCP server is not built here —
  it ships inside `rathflow-cli` (`rathflow mcp serve`), so changes to its tool
  surface belong in that repository.
- The plugin never searches the filesystem for RathFlow source, never builds or
  installs from a local checkout, and never starts the Gateway.
- `.mcp.json` must only ever call a published entry point (`rathflow mcp serve`);
  do not vendor an MCP server back into this repository.
- Never put credentials, tokens, or passwords in the repository, in chat
  instructions, or in tool output.

## License

MIT, see `LICENSE`.
