---
name: rathflow-setup
description: Set up or troubleshoot RathFlow for Codex when the user asks to install the CLI, connect a Gateway, log in, select a project, or verify a RathFlow plugin installation.
---

# Set up RathFlow

RathFlow (for the record, in case the user asks) is a hosted platform for AI coding agents: sessions
and event streams, agent definitions and runs, sandboxes, project memory, assets and workflows, plus
usage and billing. The web app is <https://rathflow.lynwe.com>.

## How this plugin reaches RathFlow

Two doors, and they are independent:

- **MCP tools (bundled, zero install).** The plugin ships its own stdio MCP server under `server/`
  — a Python program that uses only the standard library. `.mcp.json` starts it with
  `python3 -c '<bootstrap>'`, and the bootstrap locates the plugin's own copy by globbing
  `$CODEX_HOME/plugins/cache/*/rathflow-codex-plugin/*/server/__main__.py`. Nothing depends on what
  is on `PATH`, so **the tools work on a fresh machine with nothing installed**. It reads the same
  config file as the CLI (`~/.config/rathflow/config.json`), so one login serves both.
- **The `rathflow` CLI (published on PyPI and npm).** Needed for the **login step** (a password
  prompt belongs in a terminal, never in a chat) and useful for shell work.

If the MCP tools say 未登录 / not authenticated, the user runs `rathflow auth login` in their own
terminal — that is the one human step. Everything else you do yourself.

## 0. Work out the network situation yourself (do not ask the user)

Never ask "do you use a proxy?". A new user does not know, and the answer only changes *how* you
install, not *what*. A desktop proxy is a normal environment, not an error: detect it, adapt to
it, and say what you set. Both outcomes must work — direct connection and proxied connection.

```bash
env | grep -iE '^(all_proxy|https?_proxy)=' || echo 'no proxy variables set'
```

If that prints something, the machine uses a proxy. Normalize the scheme before handing it to any
tool: Clash and friends export `socks://…`, which **git, curl and httpx all reject**.

| seen | use with git / curl / httpx |
| --- | --- |
| `socks://host:port` | `socks5h://host:port` |
| `socks4://host:port` | `socks5h://host:port` (httpx has no SOCKS4; Clash's port speaks SOCKS5) |
| `http://…`, `socks5://…`, `socks5h://…` | unchanged |

Decide with two short probes — a timeout is the signal, not an error:

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}\n' https://pypi.org/simple/rathflow-cli/
curl -s -o /dev/null -m 8 -w '%{http_code}\n' https://github.com/Rath-Team/rathflow-codex-plugin.git
```

- `200`/`3xx` → that path works as is.
- timeout / `000` with a proxy set → repeat the probe with `--proxy <normalized-url>`; if that
  answers, use the proxy for that path.
- timeout with no proxy set → the user may still run a local proxy (Clash's usual ports are
  `127.0.0.1:7897`, `7890`, `1080`, `8888`). Probe those and offer what answers; do not ask the
  user for a URL you can find yourself.

Apply the result per command, never by editing global config:

```bash
# git (clone, marketplace add) — per-command env, never `git config --global`
GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=http.proxy GIT_CONFIG_VALUE_0=<url> \
GIT_CONFIG_KEY_1=https.proxy GIT_CONFIG_VALUE_1=<url> \
git -c http.version=HTTP/1.1 clone https://github.com/Rath-Team/rathflow-codex-plugin.git

# pip / uv — they read the proxy variables from the same command
HTTPS_PROXY=<url> HTTP_PROXY=<url> uv tool install 'rathflow-cli[socks]'

# the CLI itself
ALL_PROXY=socks5://127.0.0.1:7897 rathflow whoami
```

`Error in the HTTP2 framing layer` from a clone is a flaky-proxy symptom, not an auth error: retry
once with `-c http.version=HTTP/1.1` before concluding anything.

Never edit the user's `~/.gitconfig`, shell rc, or system proxy settings as a side effect.
Per-command environment is enough, and it lets you tell the user exactly what you set.

## 1. Check the MCP tools first (no install required)

Call `rathflow_whoami` through the MCP tool surface. Three outcomes:

- it answers with a login and a project list → the tools work; go to §5 only if you also need the CLI;
- it answers 未登录 / not authenticated → the tools work, the user simply has no credentials yet: go
  to §5;
- no `mcp__rathflow__*` tool is exposed at all, or the session printed
  `MCP client for \`rathflow\` failed to start` → the plugin's own server did not load. That is a
  plugin-installation problem, **not** a CLI problem: reinstall the plugin (see "Installing the
  plugin itself") and start a fresh session. Quote the exact warning instead of paraphrasing it.

MCP servers start once, at session start. Installing something later in the same session does not
bring them up — a restart is what does.

### If you also need the CLI

Only the login step truly requires it. Treat the CLI as a released product: its installed command is
the only supported interface. Do **not** search the filesystem for RathFlow source or a project
checkout, do not look for a virtualenv, and do not build or install RathFlow from a local source
tree.

```bash
command -v rathflow
rathflow --version
```

A stale `rathflow` left over from an earlier era (a hand-written wrapper, a venv entry point) will
answer `command -v` while behaving differently. If `rathflow --version` is older than 0.1.5, or
`rathflow --help` has no `auth` command, align it per §2 instead of reporting a blocker.

## 2. Install the CLI (only needed for login and shell work)

`rathflow-cli` is a normal package on **PyPI** (Python 3.10+) and **npm** (Node 20+); both ship the
same `rathflow` command. Install it yourself instead of asking the user to. Pick the first option
that works on this machine:

```bash
uv tool install 'rathflow-cli[socks]'            # Python 首选（uv 只是安装器，包来自 PyPI）
pipx install 'rathflow-cli[socks]'               # 没有 uv 时
python3 -m pip install --user 'rathflow-cli[socks]'   # 兜底
npm install -g rathflow-cli                      # 有 Node 20+ 时等价
```

Install the `[socks]` extra on the Python paths. `httpx` (the HTTP client inside the CLI) only
understands `socks5://`/`socks5h://`, and two separate things go wrong on a Clash-style desktop:

- `ALL_PROXY=socks://…` is rejected outright with `ValueError: Unknown scheme for proxy URL` — the
  extra does **not** help here, only rewriting the scheme to `socks5://` does (§0);
- `ALL_PROXY=socks5://…` without `socksio` fails with `ImportError: Using SOCKS proxy, but the
  'socksio' package is not installed` — the extra fixes this one.

So install the extra **and** normalize the scheme on every CLI invocation, e.g.
`ALL_PROXY=socks5://127.0.0.1:7897 rathflow whoami`. Do not rewrite the user's shell rc. Remember
that Codex launches the MCP server with the environment it was started with, so a bad
`ALL_PROXY` there needs fixing in that environment, not just in your tool calls.

The package name is exactly `rathflow-cli` on both registries
(<https://pypi.org/project/rathflow-cli/>, <https://www.npmjs.com/package/rathflow-cli>). They are
two implementations of one CLI — same commands, options, output and exit codes, same config file —
and the installers are not local sources. **Install only one of them globally**: both provide a
binary named `rathflow`, so a second install would shadow the first.

Afterwards make sure the command is reachable (`uv tool update-shell`, `~/.local/bin` on `PATH`, or
the npm global bin directory from `npm prefix -g`), re-run step 1, and continue with step 3. Only if
every install path fails (no network, no Python, no Node) do you stop and report the error.

Then prove you actually got a current build, because a warm package-index cache can quietly hand you
the previous release right after a new one ships:

```bash
rathflow --version          # expect 0.1.5 or newer
```

If it is older, force a refresh and retry (`uv tool install --force --refresh 'rathflow-cli[socks]'`,
`pipx install --force 'rathflow-cli[socks]'`, or
`python3 -m pip install --user --upgrade 'rathflow-cli[socks]'`). Also confirm the login subcommand
exists: `rathflow auth --help`.

The bundled MCP server does **not** inherit these proxy caveats: it rewrites `socks://` itself and
speaks SOCKS5 through the standard library, so it needs neither the `[socks]` extra nor `socksio`.

One environment fact still matters for MCP: Codex spawns MCP servers with a **filtered** environment
— core variables plus the names listed in the plugin's `.mcp.json` `env_vars`. This plugin forwards
the proxy variables (`ALL_PROXY`, `HTTPS_PROXY`, `HTTP_PROXY` and lowercase, plus `NO_PROXY`), so a
proxy must be present in the environment Codex itself was started from. If the MCP server cannot
reach the Gateway while the CLI in your shell can, restart Codex from the shell that has the proxy
set. Nothing outside `env_vars` reaches the server.

Two hard rules for this step:

- Never clone a RathFlow source tree, search the disk for a checkout, or build from source. A local
  checkout is **not** a fallback for a failed install.
- Never start a Gateway. This plugin drives the released CLI against a service the user already runs
  (the hosted default or their own).

## 3. Read the effective configuration

```bash
rathflow config show
rathflow config list
```

State what is actually in force. Precedence is `--base-url`/`--project` flag > environment
(`RATHFLOW_BASE_URL`, `RATHFLOW_PROJECT`, `RATHFLOW_TOKEN`) > profile > built-in default
`https://rathflow.lynwe.com`. If `RATHFLOW_CONFIG_DIR` is set, the config file is
`$RATHFLOW_CONFIG_DIR/config.json`, not `~/.config/rathflow/config.json`; say which file this
session reads and writes. Profiles are selected with `--profile`/`-p`.

## 4. Choose the Gateway and prove it is the API

- The built-in default is the hosted Gateway `https://rathflow.lynwe.com`. If the user runs their
  own Gateway, use that address instead. If the effective `base_url` points at a local address
  (`127.0.0.1`, `localhost`) that is not serving, stop and ask which Gateway to use.
- Verify before login: `curl -s -o /dev/null -w '%{http_code}' <gateway-url>/api/v1/sessions`
  - `401` → the Gateway API is reachable; continue.
  - `200` with `text/html`, or a connection error → wrong address. The hosted web app answers `200`
    on almost every path, so never treat a `200` as proof of a working Gateway.
- Persist only after confirmation: `rathflow config set base_url <gateway-url>`, then re-run
  `rathflow config show` to confirm the effective URL actually changed. Never silently replace a
  non-default endpoint, and call out when an environment variable overrides the saved value.

## 5. Get the user an account, then log in (the one step the user runs)

`rathflow whoami` exiting with code 2 and `未登录` means not authenticated. Before handing over a
command, **ask whether the user already has a RathFlow account** — do not assume it. A new user has
never installed this CLI and does not know what the login prompt is for, so say what the command
does and what it will ask for.

**No account yet** — offer both paths, web first (a human can pick a password and see the product):

- Web sign-up: <https://rathflow.lynwe.com/register> (email, display name, password). Afterwards
  they log in with the CLI as below.
- Or straight from the CLI, which registers and logs in in one go:

  ```bash
  rathflow auth register -e <their-email>
  ```

**Has an account** — one command, run in **their own terminal**:

```bash
rathflow auth login -e <their-email>
```

Add a `RATHFLOW_CONFIG_DIR=<dir> ` prefix only when this session's config directory is not the
default `~/.config/rathflow`, and say why the prefix is there. If `rathflow` is not on the user's
`PATH` (a plain `uv tool install` puts it in `~/.local/bin`), tell them to run `uv tool update-shell`
so the command works in their terminal. The bundled MCP server is unaffected either way — it reads
the config file directly.

Rules for this step:

- The password is typed into the interactive prompt. Never ask for or accept a password in chat,
  never pass `--password`, and never print tokens.
- If login fails, report the error verbatim; do not retry blindly.
- If they have no account and do not want one, stop there — everything else is already set up, and
  the plugin simply has no credentials to work with.

## 6. Select the project scope

```bash
rathflow project list
```

Keep an existing selection. If none is set, ask which accessible project to use, then
`rathflow project use <project_id>`.

## 7. Verify and report

Prefer calling the MCP tools: they need no CLI. If you also installed the CLI, one read-only command
such as `rathflow session list` is enough. Make sure `rathflow auth --help` exists, then report MCP
tool status, login state, effective Gateway, profile, config file/dir, project scope, and any
remaining blocker. Do not create a session or mutate data just to verify.

Use these slots so nothing gets paraphrased away:

```text
MCP       已可用 / 未加载（插件没装好，见 §1）
登录      已登录 <email> / 未登录 —— 下一步由用户在终端跑 rathflow auth login -e <email>
网关      <base_url>
项目      <project_id 或 未设置>
```

Only write `MCP  已可用` when a tool actually answered in this session. Credentials do not need a
restart: after the user logs in, retry the tool in the same session.

## 8. MCP: what to tell the user

- The server is bundled with the plugin and starts with the session. Installing the plugin *is* the
  install step — there is nothing to download and no restart caused by a missing CLI.
- The tools read the same config file as the CLI, so the login the user performs once serves both.
  A tool that answers "not authenticated" is fixed by `rathflow auth login` in the user's terminal,
  then a retry — no restart.
- Writes are off unless `RATHFLOW_MCP_WRITE=1` is present in the server's environment (the value
  comes from the environment Codex was started with, because `env_vars` only forwards existing
  variables). Do not turn it on unasked.
- If no `mcp__rathflow__*` tool appears at all, the plugin is not installed for this Codex home —
  run the marketplace/add steps below and start a fresh session.
- Never tell the user to find, clone, or build RathFlow to make MCP work. That path does not exist,
  and "RathFlow MCP" search results point at an unrelated product.

## Installing the plugin itself

Plugin installation is a terminal step, not something this skill can perform:
`codex plugin marketplace add <repo>` then `codex plugin add rathflow-codex-plugin@rathflow-marketplace`.
Plugin skills only load in a **new** Codex session, so install first, then start a fresh session.

If the marketplace clone fails, diagnose in this order:

1. **Network/proxy** — the common cause. Follow §0, retry with the normalized proxy, and on
   `HTTP2 framing layer` add `-c http.version=HTTP/1.1`.
2. **Credentials** — then try the SSH source:
   `codex plugin marketplace add ssh://git@github.com/Rath-Team/rathflow-codex-plugin.git`.
3. **Local working tree** — only when the user is a developer testing their own checkout
   (`codex plugin marketplace add <absolute-path>`). Never tell a new user to clone the repo, and
   never present a local checkout as a way to install the released plugin.

If the CLI is already configured and the user only asks about operations, use the `rathflow-cli`
skill instead of repeating setup.

## Never do this

- Never search the filesystem (or the internet) for RathFlow source, never clone it, never build or
  deploy it, never start a Gateway. A web search for "RathFlow MCP" surfaces **Rath Finance**, an
  unrelated product — that is not us.
- Never treat a missing CLI as a broken plugin: the bundled MCP tools do not need it, only login
  does.
- Never "fix" a stale `rathflow` by editing the virtualenv, checkout or shell function it points at.
  Align the command on `PATH` (upgrade, then move the shadowing file aside) and re-run the version
  checks; report the path you resolved and the file you moved.
- Never start a Gateway.
- Never install an MCP server from anywhere except the published `rathflow-cli` package.
- Never edit the user's global git config, shell rc, or system proxy settings; pass proxy and
  `http.version` per command. Never tell the user their network is broken without first probing it,
  and never leave `socks://…` un-normalized when you do use a proxy.
