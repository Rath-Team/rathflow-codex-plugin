"""错误信封。形状与 CLI 一致：{"error": {"code","message","details"}}。

本文件零依赖，随插件分发；不 import 任何第三方包。
"""

from __future__ import annotations


class ApiError(Exception):
    """一次失败的 API 调用（信封已解出，或传输层失败）。"""

    def __init__(self, status: int, code: str, message: str, details=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = list(details or [])

    def __str__(self) -> str:
        if self.code and self.code not in ("UNKNOWN", ""):
            return f"{self.message} [{self.code}]"
        return self.message


class UsageError(Exception):
    """本地用法错误（未登录、缺 project、参数不合法）。"""


def from_response(status: int, payload) -> ApiError:
    """从响应体解出信封；形状不符时退回通用文案（不外泄内部细节）。"""
    body = payload if isinstance(payload, dict) else {}
    err = body.get("error")
    if not isinstance(err, dict):
        return ApiError(status, "UNKNOWN", f"请求失败（HTTP {status}）")
    return ApiError(
        status,
        str(err.get("code") or "UNKNOWN"),
        str(err.get("message") or f"请求失败（HTTP {status}）"),
        err.get("details"),
    )
