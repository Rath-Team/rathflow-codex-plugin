# RathFlow Codex Plugin

让 Codex 通过本地 `rathflow` CLI 使用 RathFlow 的项目、会话、记忆、沙箱和账单功能。

本插件是 **skill-only plugin**：

- 不包含 RathFlow CLI；
- 不启动 RathFlow Gateway；
- 不包含 MCP Server；
- 只负责告诉 Codex 什么时候以及如何调用本地 `rathflow` 命令。

## 前置条件

- 已安装 Codex；
- 已安装 Python 3.10 或更高版本；
- 已有 RathFlow 账号；
- 可以访问 RathFlow Gateway。

## 安装 CLI

CLI 发布到 PyPI 后，推荐使用：

```bash
pip install rathflow-cli
```

或者：

```bash
uv tool install rathflow-cli
```

当前 CLI 尚未发布到 PyPI。开发测试时，可以从 RathFlow 源码安装：

```bash
uv pip install -e /path/to/RathFlow-v3/cli/python
```

确认安装成功：

```bash
rathflow --help
```

## 配置远程 RathFlow

将 CLI 指向 RathFlow Gateway：

```bash
export RATHFLOW_BASE_URL=https://rathflow.lynwe.com
```

登录你自己的 RathFlow 账号：

```bash
rathflow auth login -e your-email@example.com
rathflow whoami
rathflow project list
rathflow project use <project_id>
```

令牌保存在本机 CLI 配置中。不要把令牌粘贴到聊天、README 或代码仓库中。

如果使用的是自部署 Gateway，只需把 `RATHFLOW_BASE_URL` 换成自己的服务地址。

## 安装 Plugin

公开发布时，插件会通过 Marketplace 安装。典型流程是：

```bash
codex plugin marketplace add https://github.com/<owner>/rathflow-codex-plugin.git
codex plugin add rathflow-codex-plugin@rathflow-marketplace
```

安装后请重新启动 Codex。

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
    └── skills/rathflow-cli/SKILL.md
```

`marketplace.json` 只负责登记插件；`plugin.json` 和 `SKILL.md` 才是插件本身。当前仓库已经采用这种单仓库结构。

## 本地开发和验证

验证插件结构：

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/rathflow-codex-plugin
```

更改 `SKILL.md` 或 `plugin.json` 后，重新安装插件并启动新的 Codex 会话进行测试。
