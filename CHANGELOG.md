# Changelog

## Unreleased

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
