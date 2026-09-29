# RathFlow Codex Plugin

[English](README.en.md) | 中文

让 Codex 通过插件自带的 MCP server（或本地 `rathflow` CLI）使用 RathFlow 的项目、会话、记忆、沙箱和账单功能。

本插件自带 MCP server：

- MCP server 随插件分发（`server/` 目录，纯 Python 标准库，零第三方依赖），**不需要先装任何东西**；
- 不包含、也不启动 RathFlow Gateway；
- 包含两个 Skill：`rathflow-setup`（初始化与排查）和 `rathflow-cli`（日常操作）；
- `rathflow` CLI（PyPI / npm 单独分发）只在**登录**和命令行操作时需要 —— 插件不会替你找源码或本地部署。

## 前置条件

- 已安装 Codex；
- 已安装本插件（见下一节）——MCP 工具即刻可用，不需要其他安装；
- 需要一个 RathFlow 账号，或先到 <https://rathflow.lynwe.com/register> 注册；
- 首次使用要登录：安装 `rathflow` CLI 后在终端跑一次 `rathflow auth login -e <邮箱>`（或在 server 环境里提供 `RATHFLOW_TOKEN`）；MCP 与 CLI 读同一份配置；
- 可以访问 RathFlow Gateway。

## 安装 Plugin

```bash
codex plugin marketplace add Rath-Team/rathflow-codex-plugin
codex plugin add rathflow-codex-plugin@rathflow-marketplace
```

如果克隆 Marketplace 时提示需要身份认证，改用 SSH 源：

```bash
codex plugin marketplace add ssh://git@github.com/Rath-Team/rathflow-codex-plugin.git
codex plugin add rathflow-codex-plugin@rathflow-marketplace
```

插件安装是**终端里的步骤**：插件的 Skill 只会随新会话加载，同一条会话里刚装完插件，Codex 还看不到它。所以先安装，**再开一个新的 Codex 会话**，输入：

```text
帮我从零配置 RathFlow。先检查 CLI 是否已安装、连接的是哪个 Gateway；
需要安装软件或更改现有配置时先征得我的同意，不要在聊天里询问密码。
```

Codex 会使用 `rathflow-setup` Skill 逐步引导；登录密码需要由你在自己的终端交互输入，不能交给 Codex。

## Codex 能自己做到哪一步

`rathflow-setup` Skill 是一份可执行的排查流程，Codex 会自己完成下列步骤，而不是一上来就让你手工配置或反复追问：

- **检查 CLI**：只看 `rathflow` 命令本身是否可用（`command -v rathflow` / `rathflow --help`）。**不会**在磁盘上找 RathFlow 源码、checkout 或虚拟环境。
- **缺 CLI 时自己装**：从公开 registry 装 `rathflow-cli`（`uv tool install` → `pipx` → `pip install --user` → `npm install -g` 依次尝试）。安装器本身不是本地源码，包来自 PyPI/npm。只有所有装法都失败（比如没网络）才会停下来报错。
- **判定配置**：`config show` / `config list`，并说明 `flag > 环境变量 > profile > 默认` 的优先级，以及 `RATHFLOW_CONFIG_DIR` 把配置文件放到了哪里。
- **选 Gateway 并探活**：用 `curl -s -o /dev/null -w '%{http_code}' <gateway>/api/v1/sessions`，`401` 才代表网关 API 真的在；`200 text/html` 只是前端页面，不能当作可用依据。
- **告诉你登录命令**：给出带上配置文件目录的一条 `rathflow auth login -e <email>`，由你在自己的终端输入密码。
- **选项目并只读验证**：`project list` / `project use` / `session list`，最后汇报拿到什么状态、还缺什么。

## CLI 安装现状

**`rathflow-cli` 已发布到 PyPI 和 npm**（[pypi.org/project/rathflow-cli](https://pypi.org/project/rathflow-cli/)、[npmjs.com/package/rathflow-cli](https://www.npmjs.com/package/rathflow-cli)）：插件的 MCP 工具不需要它，但**登录**需要。Codex 会在需要时自己装；想手动装的话，任选一种：

```bash
uv tool install 'rathflow-cli[socks]'         # 有 uv 时首选（Python 3.10+）
pipx install 'rathflow-cli[socks]'            # 没有 uv
python3 -m pip install --user 'rathflow-cli[socks]'   # 兜底
npm install -g rathflow-cli                   # 等价的 Node 实现（Node 20+）
```

两个包是同一个 CLI 的两套实现：命令、选项、输出、退出码和配置文件都一致。**只全局装一个**——两边都提供名为 `rathflow` 的命令，装两个会互相覆盖。

Python 版建议带 `[socks]` extra：很多桌面代理（Clash 等）会导出 `ALL_PROXY=socks://…`，`httpx` 需要 `socksio` 才能走 SOCKS；CLI ≥ 0.1.5 会把 `socks://` 自动改写成 `socks5h://`，不用你手工改环境变量。**代理要设在启动 Codex 的那个 shell 里**，MCP server 只继承插件转发的那几个代理变量（见「MCP」一节）。

装完确认命令可见（`~/.local/bin` 需在 `PATH` 上，或执行一次 `uv tool update-shell`；npm 全局 bin 目录见 `npm prefix -g`）：

```bash
rathflow --help
```

从源码安装 CLI 属于开发流程，不属于插件的配置流程——Codex 不会克隆仓库、也不会拿本地 checkout 兜底；装不上就报错停下。

CLI 的默认网关是托管的 `https://rathflow.lynwe.com`；自建网关用 `--base-url` 或 `RATHFLOW_BASE_URL` 覆盖。

## 手动配置（可选）

不使用初始化 Skill 时，可以手动将 CLI 指向 RathFlow Gateway（写入 CLI 本地配置）：

```bash
rathflow config set base_url https://rathflow.lynwe.com
```

改完先确认真的是网关地址，而不是被前端页面顶包：

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://rathflow.lynwe.com/api/v1/sessions   # 期望 401
```

`401`（JSON `unauthorized`）说明网关 API 可达；如果拿到 `200 text/html`，说明这个地址其实指向 Web 前端，不是 Gateway。

然后登录你自己的 RathFlow 账号：

```bash
rathflow auth login -e your-email@example.com
rathflow whoami
rathflow project list
rathflow project use <project_id>
```

密码会在终端交互提示。**不要把密码或令牌粘贴到聊天、README 或代码仓库中。** 如果设置了 `RATHFLOW_BASE_URL`，它会覆盖配置文件里的地址。

## 常见用法

```text
列出我当前 RathFlow 项目的最近会话。
搜索 RathFlow 记忆中关于"项目配置"的内容。
查看当前 RathFlow 项目的用量。
创建一个 RathFlow 会话并发送这段提示词：……
```

Codex 应该调用 `rathflow session list` 这类 CLI 命令，而不是绕过 CLI 直接伪造 HTTP 请求。涉及创建、删除、写入、邀请、执行命令等修改操作时，它会先说明操作并获得你的确认。

## MCP

插件自带一个 stdio MCP server（`server/`，Python 标准库实现）。`.mcp.json` 用
`python3 -c '<引导脚本>'` 启动它，引导脚本按
`$CODEX_HOME/plugins/cache/*/rathflow-codex-plugin/*/server/__main__.py` 定位插件自己那份实现
—— 不依赖 `PATH` 上有没有 `rathflow`，新机器装完插件就能用。

- 默认提供 10 个只读工具（身份、项目、会话、记忆、沙箱、工作流、用量、端点发现）；
- 另有一个 `rathflow_project_use`（只改本地配置）始终可见；在 server 环境里设
  `RATHFLOW_MCP_WRITE=1` 会再放开 `rathflow_api_call` 的写端点，默认关闭；
- 具名工具没覆盖的端点，用 `rathflow_endpoints` 查 key，再走 `rathflow_api_call`；
- 鉴权与 CLI 同一份配置（`~/.config/rathflow/config.json`，可用 `RATHFLOW_CONFIG_DIR` 改）。
  先用 CLI 登录一次，token 过期时 server 自己续期；
- 代理：server 自己支持 `http` / `socks5h` 代理，并会把 `socks://`、`socks4://` 规范成
  `socks5h://`，不需要 `[socks]` extra、也不需要 `socksio`。但 Codex 启动 MCP server 时会**过滤
  环境变量**（核心变量 + 插件 `.mcp.json` 里 `env_vars` 列出的名字），所以代理变量必须存在于启动
  Codex 的那个 shell 里；
- 只在**新会话**加载。`codex mcp list` 可确认注册状态；未登录时工具会返回明确提示，引导用户去
  `rathflow auth login`，而不是去找源码或本地部署。

## 已知限制

- 启动命令是 `python3`，因此需要机器上有 Python 3.9+（Codex 官方插件脚手架同样假定 python3 存在）。
  Windows 上如果只有 `py`，把 `.mcp.json` 里的 `command` 改成 `py`。
- 插件内 server 与 CLI 的工具面同源，但**不是同一份代码**：CLI 改动端点后，插件侧需要同步。
## 许可证

本仓库（插件指令与自带的 MCP server）采用 MIT，见 `LICENSE`；不涉及 RathFlow 服务端与 CLI 本体。
