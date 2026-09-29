"""MCP 服务端：stdio 上的 JSON-RPC 读写循环与方法分发。

纪律：**stdout 只跑协议**，任何诊断都走 stderr —— 混一行日志进去，客户端就解析失败。
"""

from __future__ import annotations

import sys
from typing import IO

import tools
from protocol import (
    INTERNAL_ERROR,
    INVALID_REQUEST,
    JSONRPC_VERSION,
    METHOD_NOT_FOUND,
    RpcError,
    negotiate_version,
    read_message,
    write_message,
)

SERVER_NAME = "rathflow"
SERVER_VERSION = "0.1.12"

# 会话开始时带给模型的说明。「未登录就让用户去配置，不要找源码/本地部署」这条
# 写死在这里，是因为它是模型最容易走偏的一步。
INSTRUCTIONS = (
    "RathFlow 的能力（项目、会话、记忆、沙箱、用量、工作流）通过本 MCP server 暴露，"
    "凭据从 ~/.config/rathflow/config.json 读取（与 rathflow CLI 同一份）。\n"
    "1. 先调 rathflow_whoami 判断是否已登录。未登录时让用户在**他自己的终端**运行 "
    "`rathflow auth login -e <登录邮箱>`，然后重试。\n"
    "2. 不要去找 RathFlow 源码、不要本地构建或部署、不要自己启动 Gateway。"
    "缺 CLI 时用 `uv tool install rathflow-cli` 或 `npm install -g rathflow-cli`。\n"
    "3. 默认作用域是 `rathflow project use <project_id>` 选定的项目；"
    "要操作别的项目就显式传 project_id。\n"
    "4. 写操作默认关闭。具名工具没覆盖的端点用 rathflow_endpoints 查 key，"
    "再走 rathflow_api_call。"
)


def log(*parts: object) -> None:
    print("[rathflow-mcp]", *parts, file=sys.stderr, flush=True)


def _utf8(stream: IO[str]) -> IO[str]:
    """强制 UTF-8：Windows 默认代码页会把中文 JSON 编成 GBK，客户端解不开。"""
    try:
        stream.reconfigure(encoding="utf-8", newline="\n")  # type: ignore[attr-defined]
    except (AttributeError, ValueError, OSError):
        pass
    return stream


def serve(*, stdin: IO[str] | None = None, stdout: IO[str] | None = None) -> int:
    import runtime

    enabled = tools.write_enabled()
    ctx = tools.ToolContext(runtime.State(), write_enabled=enabled)
    if not enabled:
        log(f"写操作未启用（设 {tools.WRITE_ENV}=1 打开）")
    if not ctx.state.has_token():
        log("尚未登录：工具会提示用户跑 rathflow auth login")
    return _loop(ctx, _utf8(stdin or sys.stdin), _utf8(stdout or sys.stdout))


def _loop(ctx: tools.ToolContext, stdin: IO[str], stdout: IO[str]) -> int:
    while True:
        try:
            message = read_message(stdin)
        except RpcError as exc:
            write_message(stdout, _error_response(None, exc))
            continue
        if message is None:
            log("stdin 关闭，结束")
            return 0
        try:
            response = _dispatch(ctx, message)
        except Exception as exc:  # 兜底：循环不能因为一条消息就安静退出
            log(f"分发异常：{exc!r}")
            response = _error_response(message.get("id"), RpcError(INTERNAL_ERROR, f"内部错误：{exc}"))
        if response is not None:
            write_message(stdout, response)


def _dispatch(ctx: tools.ToolContext, message: dict) -> dict | None:
    msg_id = message.get("id")
    is_notification = "id" not in message
    method = message.get("method")
    params = message.get("params") or {}
    try:
        if message.get("jsonrpc") != JSONRPC_VERSION:
            raise RpcError(INVALID_REQUEST, 'jsonrpc 必须是 "2.0"')
        if not isinstance(method, str):
            raise RpcError(INVALID_REQUEST, "缺少 method")
        if not isinstance(params, dict):
            raise RpcError(INVALID_REQUEST, "params 必须是 JSON 对象")
        result = _handle(ctx, method, params)
    except RpcError as exc:
        return None if is_notification else _error_response(msg_id, exc)
    if is_notification:
        return None
    return {"jsonrpc": JSONRPC_VERSION, "id": msg_id, "result": result}


def _error_response(msg_id: object, exc: RpcError) -> dict:
    return {"jsonrpc": JSONRPC_VERSION, "id": msg_id, "error": exc.to_error()}


def _handle(ctx: tools.ToolContext, method: str, params: dict) -> dict:
    if method == "initialize":
        return _initialize(params)
    if method.startswith("notifications/"):
        return {}
    if method == "ping":
        return {}
    if method == "tools/list":
        return _tools_list(ctx)
    if method == "tools/call":
        return _tools_call(ctx, params)
    if method == "resources/list":
        return {"resources": []}
    if method == "prompts/list":
        return {"prompts": []}
    raise RpcError(METHOD_NOT_FOUND, f"未实现的方法：{method}")


def _initialize(params: dict) -> dict:
    return {
        "protocolVersion": negotiate_version(params.get("protocolVersion")),
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {"name": SERVER_NAME, "title": "RathFlow", "version": SERVER_VERSION},
        "instructions": INSTRUCTIONS,
    }


def _tools_list(ctx: tools.ToolContext) -> dict:
    return {
        "tools": [
            {
                "name": tool.name,
                "title": tool.title,
                "description": tool.description,
                "inputSchema": tool.input_schema,
                "annotations": tool.annotations(),
            }
            for tool in tools.list_tools(ctx)
        ]
    }


def _tools_call(ctx: tools.ToolContext, params: dict) -> dict:
    try:
        result = tools.call_tool(ctx, params.get("name"), params.get("arguments"))
    except tools.ToolError as exc:
        text = str(exc)
        log(f"工具 {params.get('name')} 失败：{text.splitlines()[0]}")
        return {"content": [{"type": "text", "text": text}], "isError": True}
    if result.is_error:
        log(f"工具 {params.get('name')} 失败：{result.text.splitlines()[0]}")
    payload: dict = {
        "content": [{"type": "text", "text": result.text}],
        "isError": result.is_error,
    }
    if result.data is not None:
        payload["structuredContent"] = (
            result.data if isinstance(result.data, dict) else {"result": result.data}
        )
    return payload


def main() -> int:
    try:
        return serve()
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
