# RathFlow Codex Plugin

[English](README.en.md) | 中文

让 Codex 通过本地 `rathflow` CLI 使用 RathFlow 的项目、会话、记忆、沙箱和账单功能。

本插件是 **skill-only plugin**：

- 不包含、也不安装 RathFlow CLI —— CLI 由 PyPI 单独分发；
- 不启动 RathFlow Gateway；
- 只包含两个 Skill：`rathflow-setup`（初始化与排查）和 `rathflow-cli`（日常操作）；
- 另附一个实验性只读 MCP server，见文末。

## 前置条件

- 已安装 Codex；
- 已安装 `rathflow` CLI 且在 `PATH` 上（`rathflow --help` 可运行）；插件不会替你寻找源码或本地部署 CLI；
- 已有 RathFlow 账号；
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
- **缺 CLI 时自己装**：直接从 PyPI 装 `rathflow-cli`（`uv tool install` → `pipx` → `pip install --user` 依次尝试）。`uv`/`pipx` 只是安装器，包同样来自 PyPI，不是本地源码。只有所有装法都失败（比如没网络）才会停下来报错。
- **判定配置**：`config show` / `config list`，并说明 `flag > 环境变量 > profile > 默认` 的优先级，以及 `RATHFLOW_CONFIG_DIR` 把配置文件放到了哪里。
- **选 Gateway 并探活**：用 `curl -s -o /dev/null -w '%{http_code}' <gateway>/api/v1/sessions`，`401` 才代表网关 API 真的在；`200 text/html` 只是前端页面，不能当作可用依据。
- **告诉你登录命令**：给出带上配置文件目录的一条 `rathflow auth login -e <email>`，由你在自己的终端输入密码。
- **选项目并只读验证**：`project list` / `project use` / `session list`，最后汇报拿到什么状态、还缺什么。

## CLI 安装现状

**`rathflow-cli` 已发布到 PyPI**（[pypi.org/project/rathflow-cli](https://pypi.org/project/rathflow-cli/)）：正常情况你不用手动做什么，Codex 会在缺 CLI 时自己装。想手动装的话，下面三种等价，都从 PyPI 下载同一个包：

```bash
uv tool install rathflow-cli                  # 有 uv 时首选
pipx install rathflow-cli                     # 没有 uv
python3 -m pip install --user rathflow-cli     # 兜底
```

装完确认命令可见（`~/.local/bin` 需在 `PATH` 上，或执行一次 `uv tool update-shell`）：

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

## MCP（实验）

插件注册了一个实验性 MCP server（`.mcp.json` → `mcp/server.py`，仅标准库），直接调 Gateway REST，提供两个只读工具 `rathflow_session_list` 和 `rathflow_memory_list`，不使用 CLI。鉴权沿用 CLI 的配置与环境变量，未登录时返回"先 `rathflow auth login`"。它同样只在**新会话**加载，`codex mcp list` 可确认注册状态。

已知限制：启动命令写的是 `python3`，Windows 上通常没有这个名字（只有 `python` / `py`），需要自行调整 `.mcp.json`，Skill 部分不受影响。工具面也很窄（只读、无流式、无写操作），正式形态建议由 Gateway 直接托管远程 MCP。

## 许可证

本仓库（插件指令与实验性 MCP server）采用 MIT，见 `LICENSE`；不涉及 RathFlow 服务端与 CLI 本体。
