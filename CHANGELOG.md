# Changelog

## 0.1.6

- The report slot is now a literal template instead of prose. A rerun still
  produced "CLI 和 MCP 都就绪" for a session whose MCP server had failed to
  spawn, so the skill hands over the exact lines to print and forbids
  `MCP  已可用` unless the tools were live in that session.

## 0.1.5

- `rathflow-setup` no longer lets "MCP registered and enabled" pass for success.
  MCP servers are spawned once per session, so a CLI installed mid-session means
  that session's server already failed to start; the skill now says to report
  that plainly and to restart Codex before expecting the tools.

## 0.1.4

- `rathflow-setup` no longer assumes the user already has an account, and says
  what RathFlow is. A zero-knowledge run showed the agent finding
  `rathflow auth register` only by trawling `rathflow auth --help`; the skill now
  asks the question outright and offers the web sign-up
  (<https://rathflow.lynwe.com/register>) or `rathflow auth register -e <email>`.
- Login instructions are now explicit about the details a first-timer needs:
  which directory the prefix refers to (only when it is not `~/.config/rathflow`)
  and that `uv tool update-shell` is needed so the command also works in the
  Codex session that launches the MCP server.
- Both READMEs gained the sign-up pointer, and the English one no longer
  describes the removed bundled MCP server.

## 0.1.3

- The MCP server now comes from the CLI itself: `.mcp.json` registers
  `rathflow mcp serve` instead of a bundled spike server, and
  `plugins/rathflow-codex-plugin/mcp/server.py` is gone. One implementation, same
  endpoint table, no drift.
- That gives the plugin 14 read tools out of the box (identity, projects,
  sessions, memory, sandboxes, workflows, usage, endpoint discovery, escape
  hatch) instead of the previous two, plus 5 write tools gated behind
  `RATHFLOW_MCP_WRITE=1` (off by default, and the plugin does not set it).
- Requires `rathflow-cli >= 0.1.4` for MCP: `mcp serve` ships in the **Python**
  package only so far — the npm CLI has not been ported. The skills keep working
  with either package.
- `rathflow-setup` now checks `rathflow mcp serve --help` so an outdated CLI is
  caught during setup rather than at first tool call.
- CI no longer compiles a bundled server; it asserts that `.mcp.json` calls the
  published entry point.

## 0.1.2

- The CLI is now published on **npm** as well (`npm install -g rathflow-cli`), so
  `rathflow-setup` offers both registries when the CLI is missing: `uv tool install`
  → `pipx` → `pip install --user` → `npm install -g`. Both installs provide a
  `rathflow` binary, so the skill tells the user to install only one globally.
- Bump the plugin version to `0.1.2` so Codex picks up the updated skill from cache.

## 0.1.1

- `rathflow-setup` now installs the CLI **itself** from PyPI (`uv tool install`
  → `pipx` → `pip install --user`) when `rathflow` is missing, instead of
  telling the user to do it. The anti-source-hunting rule stays: no repo clone,
  no local checkout, no starting a Gateway.
- Bump the plugin version to `0.1.1` so Codex picks up the updated skill from cache.
- Requires `rathflow-cli >= 0.1.2`: `rathflow config show` now reports the real
  environment variables only (`(未设置)` when unset), instead of echoing the
  merged effective value and looking like an env override.

- Rewrite both READMEs for first-time users (232 → 121 lines): drop the
  developer-only sections that `CONTRIBUTING.md` already covers, fix the
  "no MCP server" contradiction, and document the Windows `python3` limitation
  of the experimental MCP server.
- Fix the marketplace display name to `RathFlow Marketplace`.
- `rathflow-cli` is now published on PyPI
  (<https://pypi.org/project/rathflow-cli/>), so `rathflow-setup` no longer tells
  the user the CLI is unavailable; it installs from PyPI and reports a failed
  install instead of falling back to a local checkout.
- Document the CLI's new built-in Gateway default `https://rathflow.lynwe.com`
  (was `http://127.0.0.1:8080`) in the setup skill and both READMEs.
- Add `SECURITY.md` with private vulnerability reporting and plugin hardening notes.
- Pin GitHub Actions to commit SHAs and add `.github/dependabot.yml` to keep them fresh.
- Add `.codexignore` and an explicit `requirements-lock.txt` (no third-party deps).
- Add `README.en.md` (English) with a language switcher in both READMEs.
- Add `assets/screenshot.png` and reference it from `interface.screenshots`.

## 0.1.0

- Skill-only plugin that drives RathFlow through the installed `rathflow` CLI.
- `rathflow-setup` treats the CLI as a released product: it checks the installed
  command, probes the Gateway with `401` on `/api/v1/sessions`, and stops to ask
  the user to install the CLI instead of searching for source or building locally.
- `rathflow-cli` documents command selection, safety rules, and config precedence.
- Single-repository Marketplace (`Rathflow Marketplace`) plus install guidance.
- Experimental stdio MCP server exposing two read-only tools
  (`rathflow_session_list`, `rathflow_memory_list`).
