---
name: rathflow-setup
description: Set up or troubleshoot RathFlow for Codex when the user asks to install the CLI, connect a Gateway, log in, select a project, or verify a RathFlow plugin installation.
---

# Set up RathFlow

RathFlow (for the record, in case the user asks) is a hosted platform for AI coding agents: sessions
and event streams, agent definitions and runs, sandboxes, project memory, assets and workflows, plus
usage and billing. The web app is <https://rathflow.lynwe.com>; the plugin reaches it through the
`rathflow` CLI.

Drive the user to a working `rathflow` CLI connection, and do every step yourself that does not
need a human. The only step that truly needs the user is the password prompt. The plugin ships
instructions only: it does not bundle the CLI, does not bundle an MCP server, and does not start a
Gateway. The MCP server this plugin registers is `rathflow mcp serve` — a subcommand of the
published CLI.

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

## 1. Check whether the CLI is installed

```bash
command -v rathflow
rathflow --help
rathflow mcp serve --help    # 工具面走 MCP 时必须有；缺它说明 CLI 太旧
```

Treat the CLI as a released product: its installed command is the only supported interface. Do
**not** search the filesystem for RathFlow source or a project checkout, do not look for a
virtualenv, and do not build or install RathFlow from a local source tree.

## 2. If the CLI is missing, install it from a public registry and continue

`rathflow-cli` is a normal package on **PyPI** (Python 3.10+) and **npm** (Node 20+); both ship the
same `rathflow` command, so installing it is part of doing the setup — do it yourself instead of
asking the user to. Pick the first option that works on this machine:

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
rathflow mcp serve --help   # the MCP subcommand must exist
```

If the version is older than that (or `mcp serve` is missing), force a refresh and retry:
`uv tool install --force --refresh 'rathflow-cli[socks]'`, `pipx install --force 'rathflow-cli[socks]'`,
or `python3 -m pip install --user --upgrade 'rathflow-cli[socks]'`.

MCP needs `rathflow-cli >= 0.1.4` (`>= 0.1.5` on a machine whose `ALL_PROXY` uses `socks://…`, since
0.1.5 normalizes that scheme itself) **and** currently only ships in the Python package. If the user
wants the MCP tools (rather than just the skills) and `mcp serve --help` fails, install the Python
package even if the npm CLI is already present, and mention that the two must not both be first on
`PATH`.

One more thing to know before you blame the CLI: Codex spawns MCP servers with a **filtered**
environment — core variables plus the names in the plugin's `.mcp.json` `env_vars`. This plugin
forwards the proxy variables there (`ALL_PROXY`, `HTTPS_PROXY`, `HTTP_PROXY` and lowercase, plus
`NO_PROXY`), so a proxy has to be present in the environment Codex itself was started from. If the
MCP server cannot reach the Gateway while the CLI in your shell can, that difference is the reason:
restart Codex from the shell that has the proxy set. Nothing outside `env_vars` reaches the server.

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
default `~/.config/rathflow`, and say why the prefix is there. Likewise, if `rathflow` is not on the
user's `PATH` (a plain `uv tool install` puts it in `~/.local/bin`), tell them to run
`uv tool update-shell` so the command works in their terminal **and** in the Codex session that will
launch the MCP server.

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

Run one read-only command such as `rathflow session list`, then report: CLI availability, effective
Gateway, profile, config file/dir, login state, project scope, MCP status, and any remaining blocker.
Do not create a session or mutate data just to verify.

**Registered is not the same as working.** MCP servers are spawned once, at session start, so if you
installed or upgraded the CLI during this session the running session's server already failed to
start (its `exec` of `rathflow` happened before the binary existed). Never report MCP as ready in
that case. Use these exact slots so nothing gets paraphrased away:

```text
MCP       需要重启 Codex 才会生效 —— 本次会话启动时 rathflow 还不存在
下一步    1) 重启 Codex  2) 让工具出现  3) 再跑一次验证
```

Only write `MCP  已可用` when the tools were already live in this session.

## 8. MCP: what to tell the user

The plugin's `.mcp.json` registers `rathflow mcp serve`, and Codex only loads MCP servers at session
start. So:

- the tools appear in a **new** session. If the CLI was installed or upgraded in this session, the
  server in the running session already failed to start: restart Codex, then `codex mcp list` and a
  first tool call are the real proof;
- do not report MCP as working on the strength of the registration alone, and do not paper over a
  startup failure — quote it;
- writes are off unless `RATHFLOW_MCP_WRITE=1` is set in the server's environment — do not turn it
  on unasked;
- `codex mcp list` shows whether the server is registered. If it is not listed, the plugin is not
  installed for this Codex home; run the marketplace/add steps below.

When an MCP tool call fails with "not authenticated", the fix is the same as the CLI's: the user runs
`rathflow auth login` in their own terminal, then the tool can be retried in the same session.

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

- Never search the filesystem for a RathFlow checkout, and never build or run RathFlow from source.
- Never start a Gateway.
- Never install an MCP server from anywhere except the published `rathflow-cli` package.
- Never edit the user's global git config, shell rc, or system proxy settings; pass proxy and
  `http.version` per command. Never tell the user their network is broken without first probing it,
  and never leave `socks://…` un-normalized when you do use a proxy.
