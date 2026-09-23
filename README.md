# RathFlow Codex Plugin

[English](README.en.md) | 中文

让 Codex 通过本地 `rathflow` CLI 使用 RathFlow 的项目、会话、记忆、沙箱和账单功能。

本插件是 **skill-only plugin**，包含操作和初始化两个 Skill：

- 不包含 RathFlow CLI；
- 不启动 RathFlow Gateway；
- 不包含 MCP Server；
- 初始化 Skill 可指导 Codex 检查 CLI、设置远程地址、引导登录和选择项目；操作 Skill 指导它调用本地 `rathflow` 命令。

## 前置条件

- 已安装 Codex；
- 已安装 `rathflow` CLI 且在 `PATH` 上（`rathflow --help` 可运行）；插件不会替你寻找源码或本地部署 CLI；
- 已有 RathFlow 账号；
- 可以访问 RathFlow Gateway。

## 安装 Plugin

仓库更新推送到 GitHub 后，从 Marketplace 安装：

```bash
codex plugin marketplace add Rath-Team/rathflow-codex-plugin
codex plugin add rathflow-codex-plugin@rathflow-marketplace
```

如果克隆 Marketplace 时提示需要身份认证（仓库私有或未登录 GitHub），改用 SSH 源：

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

`rathflow-setup` Skill 现在是一份可执行的排查流程，Codex 会自己完成下列步骤，而不是一上来就让你手工配置或反复追问：

- **检查 CLI**：只看 `rathflow` 命令本身是否可用（`command -v rathflow` / `rathflow --help`）。**不会**在磁盘上找 RathFlow 源码、checkout 或虚拟环境。
- **缺 CLI 时提示你安装**：给出 `uv tool install rathflow-cli`（或 `pip install rathflow-cli`）让你在自己的终端执行。CLI 是作为产品分发的，Codex 不会克隆仓库、不会从本地源码安装，也不会尝试自己起服务。
- **判定配置**：`config show` / `config list`，并说明 `flag > 环境变量 > profile > 默认` 的优先级，以及 `RATHFLOW_CONFIG_DIR` 把配置文件放到了哪里。
- **选 Gateway 并探活**：用 `curl -s -o /dev/null -w '%{http_code}' <gateway>/api/v1/sessions`，`401` 才代表网关 API 真的在；`200 text/html` 只是前端页面，不能当作可用依据。
- **告诉你登录命令**：给出带上配置文件目录的一条 `rathflow auth login -e <email>`，由你在自己的终端输入密码。
- **选项目并只读验证**：`project list` / `project use` / `session list`，最后汇报拿到什么状态、还缺什么。

## CLI 安装现状

**当前 `rathflow-cli` 尚未发布到 PyPI。**公开仓库只包含插件指令，不能为没有 CLI 获取渠道的新用户自动安装 CLI。正式发布后，CLI 可以用以下命令安装：

```bash
pip install rathflow-cli
```

或者：

```bash
uv tool install rathflow-cli
```

开发者在自己机器上从源码安装 CLI 属于开发流程，不属于插件/Codex 的配置流程——插件不会、也不应该这么做。源码安装方式仅作参考：

```bash
uv tool install /path/to/RathFlow-v3/cli/python
```

如果已在虚拟环境中安装 CLI，也可以激活该环境后启动 Codex。确认命令可被 Codex 找到：

```bash
rathflow --help
```

CLI 必须已安装且在 `PATH` 上（`rathflow --help` 能跑通）。插件只把它当已发布的产品使用：Codex 不会去寻找源码、不会从本地仓库安装，也不会替你启动 Gateway。如果命令不可用，它会停下来告诉你怎么安装。

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

如果设置了 `RATHFLOW_BASE_URL` 环境变量，它会覆盖配置文件里的地址。登录你自己的 RathFlow 账号：

```bash
rathflow auth login -e your-email@example.com
rathflow whoami
rathflow project list
rathflow project use <project_id>
```

密码会在终端交互提示，不要把密码或令牌粘贴到聊天、README 或代码仓库中。

如果使用的是自部署 Gateway，只需把 `RATHFLOW_BASE_URL` 换成自己的服务地址。

## MCP（实验）

插件带一个实验性 MCP server：`.mcp.json` 注册 `rathflow`，由 `mcp/server.py`（仅标准库）直接调 Gateway REST，提供只读工具 `rathflow_session_list`、`rathflow_memory_list`，**不需要 CLI**。

- 鉴权沿用 CLI 的配置：`RATHFLOW_CONFIG_DIR`（默认 `~/.config/rathflow`）下的 `config.json`，或 `RATHFLOW_TOKEN` / `RATHFLOW_BASE_URL` / `RATHFLOW_PROJECT`，优先级与 CLI 一致。
- 未登录时工具返回「先 `rathflow auth login`」，不静默失败、不打印令牌。
- MCP server 只在**新会话**加载；`codex mcp list` 可确认注册状态。
- 目前是 spike：工具面很窄，写操作、流式接口（memory search 等）都未接入。正式形态建议由 Gateway 直接托管 MCP（`type: http` + OAuth/API key），插件只保留注册与授权指引。

本地验证：

```bash
cd plugins/rathflow-codex-plugin
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | RATHFLOW_CONFIG_DIR=~/.config/rathflow python3 mcp/server.py
```

注意：现有的 `rathflow-cli` Skill 仍指引 Codex 使用 CLI，与 MCP 面并存；如果 MCP 成为主路径，两个 Skill 需要相应收敛。

## 从零体验（现有开发环境）

你当前已经在本机安装过本地测试版插件和 CLI。想**重新体验安装**而不删除已有 RathFlow 登录，可以在新终端执行下面的步骤（先把更新推送到 GitHub，或把第一条命令的仓库名换为本地仓库绝对路径）：

```bash
# 已有同名本地 Marketplace 时，先移除旧插件及入口（可选）
codex plugin remove rathflow-codex-plugin@rathflow-marketplace
codex plugin marketplace remove rathflow-marketplace
# 若以前装过 rathflow-local-test，也先移除对应旧插件：
codex plugin remove rathflow-codex-plugin@rathflow-local-test

# 从 GitHub 重新添加并安装；本地未推送时使用 ~/my_workspace/rathflow-codex-plugin
codex plugin marketplace add Rath-Team/rathflow-codex-plugin
codex plugin add rathflow-codex-plugin@rathflow-marketplace
codex plugin list

# 在此终端模拟首次配置，不触碰已有的 RathFlow CLI 配置
unset RATHFLOW_BASE_URL RATHFLOW_PROJECT RATHFLOW_TOKEN
export RATHFLOW_CONFIG_DIR="$(mktemp -d)"
echo "$RATHFLOW_CONFIG_DIR"  # 登录时另一终端也要使用这个目录
codex
```

上面的移除命令仅针对已安装过旧插件的开发环境；首次安装时跳过。若 CLI 在虚拟环境内，请在启动 `codex` 前激活该环境。

在新 Codex 会话里发送「帮我从零配置 RathFlow」。交互登录时另开一个终端，先 `export RATHFLOW_CONFIG_DIR=<上一步创建的临时目录>`，再执行 Codex 提示的登录命令；两个终端必须使用相同的配置目录。体验结束关闭终端即可恢复原 CLI 配置（临时目录中的令牌不会自动删除）。

## 测试

可以向 Codex 输入：

```text
请使用 RathFlow CLI 列出我当前项目的最近会话。
只执行查询，不要修改任何数据，也不要直接调用 HTTP API。
```

Codex 应该调用类似下面的命令，而不是直接伪造 HTTP 请求：

```bash
rathflow session list
```

## 常见用法

```text
列出我当前 RathFlow 项目的最近会话。
搜索 RathFlow 记忆中关于“项目配置”的内容。
查看当前 RathFlow 项目的用量。
创建一个 RathFlow 会话并发送这段提示词：……
```

涉及创建、删除、写入、邀请、执行命令等修改操作时，Codex 应先说明操作并获得确认。

## Repository 和 Marketplace

插件本身可以和 Marketplace 放在同一个公开 GitHub 仓库中，不要求单独建仓库。

如果使用单仓库方案，推荐结构是：

```text
rathflow-codex-plugin/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── scripts/check_plugin.py
├── .github/workflows/ci.yml
├── .agents/plugins/marketplace.json
└── plugins/rathflow-codex-plugin/
    ├── .codex-plugin/plugin.json
    ├── .mcp.json
    ├── assets/{icon.png,composer-icon.png}
    ├── mcp/server.py
    └── skills/
        ├── rathflow-cli/SKILL.md
        └── rathflow-setup/SKILL.md
```

`marketplace.json` 只负责登记插件；`plugin.json` 和 `SKILL.md` 才是插件本身。当前仓库已经采用这种单仓库结构。

## 本地开发和验证

仓库自带的结构校验（CI 跑的就是它，零依赖）：

```bash
python3 scripts/check_plugin.py plugins/rathflow-codex-plugin
```

如果本机装了 Codex 的 `plugin-creator` skill，再跑一遍官方校验（更严格、权威）：

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/rathflow-codex-plugin
```

本地迭代用 cachebuster 触发重装，提 PR 前去掉 `+codex.*` 后缀恢复成正式 semver（CI 会对提交里的 cachebuster 给 warning）：

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/update_plugin_cachebuster.py plugins/rathflow-codex-plugin
```

更改 `SKILL.md`、`plugin.json` 或 `.mcp.json` 后，重新安装插件并启动**新的** Codex 会话进行测试（Skill 与 MCP 只在会话启动时加载）。

CI：`.github/workflows/ci.yml` 在 push/PR 时用 Python 3.10 与 3.12 跑上面的结构校验、编译 `mcp/server.py`、并校验三个 JSON 文件语法。更多约定见 `CONTRIBUTING.md`。

## 许可证

本仓库（插件指令与实验性 MCP server）采用 MIT，见 `LICENSE`；不涉及 RathFlow 服务端与 CLI 本体。
