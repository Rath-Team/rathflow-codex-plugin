"""MCP 工具面：把 REST 端点收敛成任务型工具。

规则（与 CLI 的 `rathflow mcp serve` 同源）：

- 不做 111 个工具。具名工具只覆盖最常用的读路径，其余走 `rathflow_api_call` 逃生舱。
- 写操作默认关闭；关着的时候写工具连 `tools/list` 都不出现。
- 未登录时唯一的正确动作是**让用户去登录**：不要去找源码、不要本地部署、不要换网关。
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Callable

import endpoints
import runtime
from errors import ApiError, UsageError

WRITE_ENV = "RATHFLOW_MCP_WRITE"

AUTH_HINT = (
    "RathFlow 还没有可用的登录凭据。请让用户在他自己的终端里执行：\n"
    "  rathflow auth login -e <登录邮箱>\n"
    "（或在 MCP 服务端环境变量里提供 RATHFLOW_TOKEN）。完成后重试本工具。\n"
    "RathFlow CLI 是已发布的包，装一次就有：`uv tool install rathflow-cli` "
    "或 `npm install -g rathflow-cli`。不要克隆源码、不要本地部署、不要自己起 Gateway。"
)

WRITE_HINT = (
    f"写操作当前未启用（{WRITE_ENV} 未开），这是刻意的默认值。"
    f"确需写权限时，让用户把 MCP 服务端环境变量 {WRITE_ENV}=1 打开，再重开会话。"
)


class ToolError(Exception):
    """工具执行失败 → CallToolResult.isError=true（不是 JSON-RPC error）。"""


@dataclass
class ToolResult:
    text: str
    data: Any = None
    is_error: bool = False


@dataclass(frozen=True)
class Tool:
    name: str
    title: str
    description: str
    input_schema: dict
    run: Callable[[ToolContext, dict], ToolResult]
    write: bool = False

    def annotations(self) -> dict:
        return {
            "title": self.title,
            "readOnlyHint": not self.write,
            "destructiveHint": False,
            "idempotentHint": not self.write,
            "openWorldHint": True,
        }


def _schema(props: dict, required: list[str] | None = None) -> dict:
    schema: dict = {"type": "object", "properties": props, "additionalProperties": False}
    if required:
        schema["required"] = required
    return schema


def _str(desc: str) -> dict:
    return {"type": "string", "description": desc}


def _int(desc: str) -> dict:
    return {"type": "integer", "description": desc}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _text_of(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, bytes):
        raw = value
    else:
        try:
            raw = base64.b64decode(str(value), validate=True)
        except Exception:
            return str(value)
    return raw.decode("utf-8", "replace")


def write_enabled() -> bool:
    return os.environ.get(WRITE_ENV, "").strip().lower() in ("1", "true", "yes", "on")


class ToolContext:
    def __init__(self, state: runtime.State, *, write_enabled: bool = False):
        self.state = state
        self.write_enabled = write_enabled
        self._client: runtime.ApiClient | None = None

    @property
    def client(self) -> runtime.ApiClient:
        if self._client is None:
            self._client = runtime.ApiClient(self.state)
        return self._client


def _invoke(ctx: ToolContext, thunk: Callable[[], Any]) -> Any:
    """把「未登录 / 401 / 403 / 其它」翻译成对模型有指导性的错误。

    刻意不重试、不改网关地址：凭据问题只有一个正确解法 —— 让用户去配置。
    """
    if not ctx.state.has_token():
        raise ToolError(AUTH_HINT)
    try:
        return thunk()
    except UsageError as exc:
        raise ToolError(f"{exc}\n\n{AUTH_HINT}") from None
    except ApiError as exc:
        if exc.status == 401:
            raise ToolError(f"令牌被服务端拒绝（401）。\n\n{AUTH_HINT}\n\n原始错误：{exc}") from None
        if exc.status == 403:
            raise ToolError(
                f"当前账号或令牌没有这个权限（403）：{exc}\n"
                "这多半是账号角色问题，不是配置问题 —— 不要改代码、不要换网关地址。"
            ) from None
        raise ToolError(f"RathFlow 接口报错：{exc}") from None


def _call(ctx: ToolContext, key: str, **kwargs: Any) -> dict:
    return _invoke(ctx, lambda: ctx.client.call(key, **kwargs))


def _page(args: dict, *, default: int | None = None, extra: dict | None = None) -> dict:
    query = {k: v for k, v in (extra or {}).items() if v not in (None, "")}
    size = args.get("page_size") or default
    if size:
        query["page_size"] = size
    if args.get("page_token"):
        query["page_token"] = args["page_token"]
    return query


# ------------------------------------------------------------------ 工具实现


def _t_whoami(ctx: ToolContext, args: dict) -> ToolResult:
    state = ctx.state
    profile_user = state.profile.get("user") or {}
    if not state.has_token():
        return ToolResult(
            text="尚未登录。\n\n" + AUTH_HINT,
            data={"authenticated": False, "baseUrl": state.base_url, "profile": state.profile_name},
            is_error=True,
        )
    payload = _call(ctx, "tenant.ListProjects", query={"page_size": 50})
    projects = payload.get("projects") or []
    lines = [f"网关地址  {state.base_url}", f"配置档    {state.profile_name}"]
    if profile_user.get("email"):
        lines.append(f"用户      {profile_user['email']}")
    lines.append(f"当前项目  {state.project or '(未设置：让用户跑 rathflow project use <project_id>)'}")
    if projects:
        lines.append("")
        lines.append("可访问项目：")
        lines.extend(f"  {p.get('projectId')}  {p.get('name')}" for p in projects)
    data = {
        "authenticated": True,
        "baseUrl": state.base_url,
        "profile": state.profile_name,
        "user": profile_user,
        "project": state.project,
        "projects": projects,
    }
    return ToolResult(text="\n".join(lines), data=data)


def _t_projects_list(ctx: ToolContext, args: dict) -> ToolResult:
    payload = _call(ctx, "tenant.ListProjects", query=_page(args, default=50))
    data = {"projects": payload.get("projects") or [], "nextPageToken": payload.get("nextPageToken")}
    return ToolResult(text=_json(data), data=data)


def _t_project_use(ctx: ToolContext, args: dict) -> ToolResult:
    project_id = args["project_id"]
    ctx.state.profile["project"] = project_id
    runtime.save_config(ctx.state.data)
    ctx.state.project = project_id
    ctx._client = None
    return ToolResult(
        text=f"当前项目已切到 {project_id}（写进 {runtime.config_path()}）。",
        data={"project": project_id},
    )


def _t_sessions_list(ctx: ToolContext, args: dict) -> ToolResult:
    query = _page(args, default=30, extra={"project_id": args.get("project_id")})
    payload = _call(ctx, "session.ListSessions", query=query)
    data = {"sessions": payload.get("sessions") or [], "nextPageToken": payload.get("nextPageToken")}
    return ToolResult(text=_json(data), data=data)


def _t_session_get(ctx: ToolContext, args: dict) -> ToolResult:
    session_id = args["session_id"]
    session = _call(ctx, "session.GetSession", path_params={"session_id": session_id})
    blocks = _call(
        ctx,
        "session.ListBlocks",
        path_params={"session_id": session_id},
        query={"page_size": int(args.get("block_limit") or 50)},
    )
    data = {"session": session, "blocks": blocks.get("blocks") or []}
    return ToolResult(text=_json(data), data=data)


def _t_memory_list(ctx: ToolContext, args: dict) -> ToolResult:
    query = _page(args, default=100, extra={"prefix": args.get("prefix") or "memories"})
    query["recursive"] = bool(args.get("recursive", True))
    payload = _call(ctx, "memory.List", query=query)
    data = {"entries": payload.get("entries") or [], "nextPageToken": payload.get("nextPageToken")}
    return ToolResult(text=_json(data), data=data)


def _t_memory_read(ctx: ToolContext, args: dict) -> ToolResult:
    payload = _call(ctx, "memory.Read", path_params={"memory_path": args["memory_path"]})
    content = _text_of(payload.get("content"))
    data = {"memoryPath": args["memory_path"], "content": content}
    return ToolResult(text=content if content else _json(payload), data=data)


def _t_sandboxes_list(ctx: ToolContext, args: dict) -> ToolResult:
    payload = _call(ctx, "sandbox.List", query=_page(args, default=50))
    data = {"sandboxes": payload.get("sandboxes") or [], "nextPageToken": payload.get("nextPageToken")}
    return ToolResult(text=_json(data), data=data)


def _t_workflows_list(ctx: ToolContext, args: dict) -> ToolResult:
    payload = _call(ctx, "workflow.ListWorkflows", query=_page(args, default=50))
    data = {"workflows": payload.get("workflows") or [], "nextPageToken": payload.get("nextPageToken")}
    return ToolResult(text=_json(data), data=data)


def _t_usage(ctx: ToolContext, args: dict) -> ToolResult:
    query = {
        "project_id": args.get("project_id") or ctx.state.project,
        "start_time": args.get("start_time"),
        "end_time": args.get("end_time"),
    }
    payload = _call(ctx, "billing.GetUsage", query=query)
    return ToolResult(text=_json(payload), data=payload)


def _t_endpoints(ctx: ToolContext, args: dict) -> ToolResult:
    needle = (args.get("filter") or "").lower()
    rows = []
    for key, (method, path) in sorted(endpoints.ENDPOINTS.items()):
        if needle and needle not in key.lower() and needle not in path.lower():
            continue
        rows.append(
            {
                "key": key,
                "method": method,
                "path": path,
                "write": method != "GET",
                "stream": endpoints.is_streaming(key),
            }
        )
    return ToolResult(text=_json(rows), data={"count": len(rows), "endpoints": rows})


def _t_api_call(ctx: ToolContext, args: dict) -> ToolResult:
    """逃生舱：端点表里没做成具名工具的调用走这里。"""
    key = args.get("key")
    if not key:
        raise ToolError("需要 key。用 rathflow_endpoints 查可用 key。")
    if key not in endpoints.ENDPOINTS:
        raise ToolError(f"未知端点 key {key!r}。用 rathflow_endpoints 列出全部 key。")
    method = endpoints.method_of(key)
    if method != "GET" and not ctx.write_enabled:
        raise ToolError(WRITE_HINT)
    payload = _call(
        ctx,
        key,
        query=args.get("query"),
        body=args.get("body"),
        path_params=args.get("path_params"),
    )
    return ToolResult(text=_json(payload), data=payload)


# ------------------------------------------------------------------ 注册表

PAGE_PROPS = {
    "page_size": _int("返回条数上限"),
    "page_token": _str("翻页游标：把上一页返回的 nextPageToken 原样传回"),
}

_READ_TOOLS: list[Tool] = [
    Tool(
        "rathflow_whoami",
        "RathFlow 登录状态",
        "判断是否已登录、当前网关/项目/账号，并列出可访问项目。先调它。",
        _schema({}),
        lambda ctx, a: _t_whoami(ctx, a),
    ),
    Tool(
        "rathflow_projects_list",
        "列出项目",
        "列出当前账号可访问的 RathFlow 项目。",
        _schema(PAGE_PROPS),
        lambda ctx, a: _t_projects_list(ctx, a),
    ),
    Tool(
        "rathflow_sessions_list",
        "列出会话",
        "列出会话（默认当前项目）。",
        _schema({**PAGE_PROPS, "project_id": _str("可选：显式指定项目 id")}),
        lambda ctx, a: _t_sessions_list(ctx, a),
    ),
    Tool(
        "rathflow_session_get",
        "读取会话",
        "按 session_id 读取会话详情与消息块。",
        _schema(
            {"session_id": _str("会话 id"), "block_limit": _int("最多返回多少个块，默认 50")},
            ["session_id"],
        ),
        lambda ctx, a: _t_session_get(ctx, a),
    ),
    Tool(
        "rathflow_memory_list",
        "列出记忆",
        "列出项目记忆条目（默认前缀 memories/）。",
        _schema(
            {
                "prefix": _str("路径前缀，默认 memories"),
                "recursive": {"type": "boolean", "description": "是否递归，默认 true"},
                **PAGE_PROPS,
            }
        ),
        lambda ctx, a: _t_memory_list(ctx, a),
    ),
    Tool(
        "rathflow_memory_read",
        "读取记忆",
        "按路径读取一条记忆内容。",
        _schema({"memory_path": _str("记忆路径，如 memories/notes/a.md")}, ["memory_path"]),
        lambda ctx, a: _t_memory_read(ctx, a),
    ),
    Tool(
        "rathflow_sandboxes_list",
        "列出沙箱",
        "列出沙箱。",
        _schema(PAGE_PROPS),
        lambda ctx, a: _t_sandboxes_list(ctx, a),
    ),
    Tool(
        "rathflow_workflows_list",
        "列出工作流",
        "列出工作流定义。",
        _schema(PAGE_PROPS),
        lambda ctx, a: _t_workflows_list(ctx, a),
    ),
    Tool(
        "rathflow_usage",
        "查询用量",
        "查询计费/用量（默认当前项目）。",
        _schema(
            {
                "project_id": _str("可选：显式指定项目 id"),
                "start_time": _str("RFC3339 起始时间"),
                "end_time": _str("RFC3339 结束时间"),
            }
        ),
        lambda ctx, a: _t_usage(ctx, a),
    ),
    Tool(
        "rathflow_endpoints",
        "查询 REST 端点表",
        "列出可用的 REST 端点 key（喂给 rathflow_api_call）。",
        _schema({"filter": _str("可选：按关键字过滤 key 或路径")}),
        lambda ctx, a: _t_endpoints(ctx, a),
    ),
]

_WRITE_TOOLS: list[Tool] = [
    Tool(
        "rathflow_project_use",
        "切换当前项目",
        "把默认项目写进本地配置（等价 rathflow project use）。这是本地写入，不是远端修改。",
        _schema({"project_id": _str("项目 id")}, ["project_id"]),
        lambda ctx, a: _t_project_use(ctx, a),
        write=True,
    ),
    Tool(
        "rathflow_api_call",
        "调用任意端点",
        "按端点 key 调用 REST 接口（写操作需要 RATHFLOW_MCP_WRITE=1）。先查 rathflow_endpoints。",
        _schema(
            {
                "key": _str("端点 key，如 tenant.ListProjects"),
                "path_params": {"type": "object", "description": "路径参数", "additionalProperties": True},
                "query": {"type": "object", "description": "查询参数", "additionalProperties": True},
                "body": {"type": "object", "description": "请求体", "additionalProperties": True},
            },
            ["key"],
        ),
        lambda ctx, a: _t_api_call(ctx, a),
        write=True,
    ),
]


def list_tools(ctx: ToolContext) -> list[Tool]:
    # project_use 只改本地配置，把它归在写组里，但始终可见（否则切项目都做不了）。
    tools = list(_READ_TOOLS)
    if ctx.write_enabled:
        return tools + _WRITE_TOOLS
    return tools + [_WRITE_TOOLS[0]]


def call_tool(ctx: ToolContext, name: Any, arguments: Any) -> ToolResult:
    if not isinstance(name, str):
        raise ToolError("tools/call 需要 name")
    args = arguments if isinstance(arguments, dict) else {}
    for tool in list_tools(ctx):
        if tool.name == name:
            if tool.write and tool.name == "rathflow_api_call" and not ctx.write_enabled:
                raise ToolError(WRITE_HINT)
            return tool.run(ctx, args)
    raise ToolError(f"未知工具 {name!r}")
