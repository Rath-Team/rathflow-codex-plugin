# RathFlow Codex Plugin

让 Codex 通过本地 `rathflow` CLI 使用 RathFlow 的项目、会话、记忆、沙箱和账单功能。

本插件是 **skill-only plugin**，包含操作和初始化两个 Skill：

- 不包含 RathFlow CLI；
- 不启动 RathFlow Gateway；
- 不包含 MCP Server；
- 初始化 Skill 可指导 Codex 检查 CLI、设置远程地址、引导登录和选择项目；操作 Skill 指导它调用本地 `rathflow` 命令。

## 前置条件

- 已安装 Codex；
- 已安装 Python 3.10 或更高版本；
- 已有 RathFlow 账号；
- 可以访问 RathFlow Gateway。

## 安装 Plugin

仓库更新推送到 GitHub 后，从 Marketplace 安装：

```bash
codex plugin marketplace add Rath-Team/rathflow-codex-plugin
codex plugin add rathflow-codex-plugin@rathflow-marketplace
```

重新启动 Codex，输入：

```text
帮我从零配置 RathFlow。先检查 CLI 是否已安装、连接的是哪个 Gateway；
需要安装软件或更改现有配置时先征得我的同意，不要在聊天里询问密码。
```

Codex 会使用 `rathflow-setup` Skill 逐步引导；登录密码需要由你在自己的终端交互输入，不能交给 Codex。

## CLI 安装现状

**当前 `rathflow-cli` 尚未发布到 PyPI。**公开仓库只包含插件指令，不能为没有 CLI 获取渠道的新用户自动安装 CLI。正式发布后，CLI 可以用以下命令安装：

```bash
pip install rathflow-cli
```

或者：

```bash
uv tool install rathflow-cli
```

目前有权访问 RathFlow 源码的开发者可以用本地源码安装独立命令：

```bash
uv tool install /path/to/RathFlow-v3/cli/python
```

如果已在虚拟环境中安装 CLI，也可以激活该环境后启动 Codex。确认命令可被 Codex 找到：

```bash
rathflow --help
```

## 手动配置（可选）

不使用初始化 Skill 时，可以手动将 CLI 指向 RathFlow Gateway（写入 CLI 本地配置）：

```bash
rathflow config set base_url https://rathflow.lynwe.com
```

如果设置了 `RATHFLOW_BASE_URL` 环境变量，它会覆盖配置文件里的地址。登录你自己的 RathFlow 账号：

```bash
rathflow auth login -e your-email@example.com
rathflow whoami
rathflow project list
rathflow project use <project_id>
```

密码会在终端交互提示，不要把密码或令牌粘贴到聊天、README 或代码仓库中。

如果使用的是自部署 Gateway，只需把 `RATHFLOW_BASE_URL` 换成自己的服务地址。

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
├── .agents/plugins/marketplace.json
└── plugins/rathflow-codex-plugin/
    ├── .codex-plugin/plugin.json
    └── skills/
        ├── rathflow-cli/SKILL.md
        └── rathflow-setup/SKILL.md
```

`marketplace.json` 只负责登记插件；`plugin.json` 和 `SKILL.md` 才是插件本身。当前仓库已经采用这种单仓库结构。

## 本地开发和验证

验证插件结构：

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/rathflow-codex-plugin
```

更改 `SKILL.md` 或 `plugin.json` 后，重新安装插件并启动新的 Codex 会话进行测试。
