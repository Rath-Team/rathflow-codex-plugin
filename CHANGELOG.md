# Changelog

## 0.1.8

- Proxy handling is now a first-class part of setup instead of an environment assumption. Codex
  spawns MCP servers with a **filtered** environment (core variables + the plugin's `env_vars`), so
  the `.mcp.json` now forwards `ALL_PROXY` / `HTTP(S)_PROXY` / `NO_PROXY` (both cases). Without
  this a proxied machine's MCP server silently ran with no proxy while the CLI in the same shell
  worked. Missing entries are simply not set, so unproxied machines are unaffected.
  `rathflow-setup` gains a "work out the network yourself" step: detect the machine's proxy,
  normalize `socks://…` (which git, curl and httpx all reject) to `socks5h://…`, probe PyPI and
  GitHub with and without the proxy, and fall back to the usual local Clash ports instead of
  asking the user for a URL. It also corrects a wrong claim: the `[socks]` extra fixes
  `socks5://…` (missing `socksio`), **not** `socks://…` (bad scheme) — that one needs the scheme
  rewritten. `Error in the HTTP2 framing layer` is documented as a retry-with-HTTP/1.1 symptom,
  and the skill is explicit that global git config / shell rc must not be edited as a side effect.
  MCP needs `rathflow-cli >= 0.1.5` for the `socks://` rewrite (0.1.4 needs a hand-normalized
  `ALL_PROXY`).
- `scripts/naive-install.sh` follows the same rules: it inherits the machine's proxy by default,
  adds `--proxy <url|auto>` / `--no-proxy` / `--http1`, normalizes the scheme, retries a failed
  clone once over HTTP/1.1, health-checks PyPI and GitHub before installing, and prints the exact
  proxy alternatives when the marketplace clone keeps failing.

## 0.1.7

- The setup skill now installs `rathflow-cli[socks]` on the Python paths. Without
  the extra, a desktop proxy setup that exports `ALL_PROXY=socks://...` (Clash is
  the common one) makes the very first CLI call die with a bare
  `ValueError: Unknown scheme for proxy URL` -- a traceback that says nothing
  about proxies and invites the agent to go bug-hunting instead.

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
