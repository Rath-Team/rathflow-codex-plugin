---
name: rathflow-setup
description: Set up or troubleshoot RathFlow CLI for Codex when the user asks to install, log in, connect a Gateway, select a project, or verify a new RathFlow plugin installation.
---

# Set up RathFlow

Help the user reach a working `rathflow` CLI connection. The plugin provides instructions only; it does not install the CLI or start a Gateway by itself.

1. Check `command -v rathflow` and `rathflow --help`. If unavailable, explain that the CLI is not yet published on PyPI. Ask the user for access to a trusted RathFlow CLI distribution or an authorized local source checkout before installing anything. With their approval and a local checkout, `uv tool install /path/to/RathFlow-v3/cli/python` installs the standalone Python CLI; alternatively use an existing activated venv. Do not install a similarly named PyPI package without confirming it is the official release.
2. Check `rathflow config show` for the effective Gateway and project. If the Gateway is still the local default (`http://127.0.0.1:8080`) and the user does not run it, ask which remote Gateway to use. If they choose the RathFlow-hosted service, suggest `https://rathflow.lynwe.com`. After their confirmation, persist it with `rathflow config set base_url <gateway-url>`. An existing `RATHFLOW_BASE_URL` environment variable overrides the saved value; explain this if the effective URL does not change. Never silently replace a non-default endpoint.
3. Check `rathflow whoami`. If not authenticated, ask the user to run `rathflow auth login -e <their-email>` in their own terminal so the password prompt stays private. Do not request a password or token in chat, use `--password`, or print credentials. If login fails, report the error rather than repeating attempts.
4. Run `rathflow project list` once authenticated. If a project is already selected, preserve it. Otherwise ask the user which accessible project to use before running `rathflow project use <project_id>`.
5. Verify with a read-only command such as `rathflow session list`. Report which steps succeeded and any remaining blocker; do not create a session or modify data just for verification.

If the user only asks about RathFlow operations and the CLI is already configured, use the `rathflow-cli` skill instead of repeating setup.
