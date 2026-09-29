"""配置与 API 客户端（标准库实现，语义对齐 CLI）。

配置来源与 CLI 完全同一份文件 `~/.config/rathflow/config.json`，环境变量优先级也一致
（env > profile > 默认）。这样「CLI 登录过」和「MCP 能用」说的是同一件事：
用户只要登录一次，两边都认。
"""

from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path
from urllib.parse import urlencode

import endpoints
from errors import ApiError, UsageError, from_response
from transport import TransportError, normalize_proxy_env, request

DEFAULT_BASE_URL = "https://rathflow.lynwe.com"

ENV_BASE_URL = "RATHFLOW_BASE_URL"
ENV_PROJECT = "RATHFLOW_PROJECT"
ENV_TOKEN = "RATHFLOW_TOKEN"
ENV_CONFIG_DIR = "RATHFLOW_CONFIG_DIR"

# 到期前多久就主动刷新（秒），与 CLI 一致。
REFRESH_MARGIN = 60

_TIMEOUT = 120.0
# 流式端点用的有界读取：够拿到一屏结果，又不会被长流挂死。
_STREAM_MAX_BYTES = 2 * 1024 * 1024


def config_dir() -> Path:
    return Path(os.environ.get(ENV_CONFIG_DIR) or (Path.home() / ".config" / "rathflow"))


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {"current": "default", "profiles": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # 文件坏了不是致命错误：当作未登录处理，让用户重新登录即可。
        return {"current": "default", "profiles": {}}
    if not isinstance(data, dict):
        return {"current": "default", "profiles": {}}
    data.setdefault("current", "default")
    data.setdefault("profiles", {})
    return data


def save_config(data: dict) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return path


class State:
    """一次进程内的配置视图（合并 flag/env/profile/默认）。"""

    def __init__(self, *, base_url: str | None = None, project: str | None = None):
        self.data = load_config()
        self.profile_name = self.data.get("current") or "default"
        profile = self.profile
        self.token_override = os.environ.get(ENV_TOKEN) or None
        self.base_url = (
            base_url
            or os.environ.get(ENV_BASE_URL)
            or profile.get("base_url")
            or DEFAULT_BASE_URL
        )
        self.project = project or os.environ.get(ENV_PROJECT) or profile.get("project")

    @property
    def profile(self) -> dict:
        profiles = self.data.setdefault("profiles", {})
        return profiles.setdefault(self.profile_name, {})

    def has_token(self) -> bool:
        return bool(self.token_override or self.profile.get("access_token"))

    def remember_tokens(self, payload: dict) -> None:
        """令牌轮换后落盘（refresh 会换掉 refresh token，不存回下次就登不上）。"""
        profile = self.profile
        access = payload.get("accessToken") or payload.get("access_token")
        refresh = payload.get("refreshToken") or payload.get("refresh_token")
        if access:
            profile["access_token"] = access
        if refresh:
            profile["refresh_token"] = refresh
        ttl = payload.get("expiresInSeconds", payload.get("expires_in_seconds"))
        try:
            seconds = int(ttl) if ttl is not None else 0
        except (TypeError, ValueError):
            seconds = 0
        if seconds > 0:
            profile["expires_at"] = time.time() + seconds - REFRESH_MARGIN
        elif access:
            profile["expires_at"] = time.time() + 15 * 60 - REFRESH_MARGIN
        save_config(self.data)


class ApiClient:
    """带令牌发请求；401 时用 refresh token 换一次并重放。"""

    def __init__(self, state: State):
        self.state = state
        normalize_proxy_env()
        self._token = state.token_override or state.profile.get("access_token")
        self._refresh = state.profile.get("refresh_token")
        try:
            self._expires_at = float(state.profile.get("expires_at") or 0)
        except (TypeError, ValueError):
            self._expires_at = 0.0

    # ------------------------------------------------------------ 令牌

    def _headers(self, auth: bool = True) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if auth and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self.state.project:
            headers["X-RathFlow-Project"] = self.state.project
        return headers

    def _absorb(self, payload: dict) -> None:
        access = payload.get("accessToken") or payload.get("access_token")
        refresh = payload.get("refreshToken") or payload.get("refresh_token")
        if access:
            self._token = access
        if refresh:
            self._refresh = refresh
        self.state.remember_tokens(payload)

    def refresh_token(self) -> bool:
        if not self._refresh:
            return False
        try:
            payload = self._raw(
                "POST",
                endpoints.render_path("auth.Refresh", {}),
                body={"refreshToken": self._refresh},
                auth=False,
            )
        except ApiError:
            return False
        self._absorb(payload)
        return True

    def ensure_token(self) -> None:
        if not self._token:
            raise UsageError("未登录")
        if self._refresh and self._expires_at and time.time() >= self._expires_at:
            self.refresh_token()

    # ------------------------------------------------------------ 请求

    def call(
        self,
        key: str | None = None,
        *,
        method: str | None = None,
        path: str | None = None,
        query: dict | None = None,
        body: dict | None = None,
        path_params: dict | None = None,
        auth: bool = True,
    ) -> dict:
        if key:
            method = endpoints.method_of(key)
            path = endpoints.render_path(key, path_params or {})
        elif not (method and path):
            raise UsageError("需要端点 key，或显式 method/path")
        assert method and path
        streaming = bool(key) and endpoints.is_streaming(key)
        return self._raw(method, path, query=query, body=body, auth=auth, streaming=streaming)

    def _raw(
        self,
        method: str,
        path: str,
        *,
        query: dict | None = None,
        body: dict | None = None,
        auth: bool = True,
        streaming: bool = False,
    ) -> dict:
        if auth:
            self.ensure_token()
        url = self.state.base_url.rstrip("/") + path
        if query:
            cleaned = {k: v for k, v in query.items() if v is not None}
            if cleaned:
                url += ("&" if "?" in url else "?") + urlencode(cleaned)
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        method = method.upper()
        max_bytes = _STREAM_MAX_BYTES if streaming else None

        for attempt in (0, 1):
            try:
                response = request(
                    method,
                    url,
                    headers=self._headers(auth),
                    body=payload,
                    timeout=_TIMEOUT,
                    max_bytes=max_bytes,
                )
            except TransportError as exc:
                raise ApiError(0, "UNAVAILABLE", f"无法连接 {self.state.base_url}：{exc}") from None
            if response.status == 401 and auth and attempt == 0 and self.refresh_token():
                continue
            data = response.json()
            if response.status >= 400:
                raise from_response(response.status, data)
            if streaming:
                return _collect_stream(response)
            return data
        raise ApiError(0, "UNAVAILABLE", "请求重试后仍未成功")  # pragma: no cover


def _collect_stream(response) -> dict:
    """把流式正文按行解成帧（与 CLI `stream()` 的读取纪律一致）。"""
    frames: list = []
    for line in response.text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            frame = json.loads(line)
        except ValueError:
            raise ApiError(response.status, "UNKNOWN", "流中断：收到非 JSON 帧") from None
        if not isinstance(frame, dict):
            raise ApiError(response.status, "UNKNOWN", "流中断：帧不是对象")
        if set(frame) == {"result"}:
            frames.append(frame["result"])
        elif set(frame) == {"error"}:
            raise from_response(response.status, frame)
        else:
            raise ApiError(
                response.status,
                "UNKNOWN",
                f"流帧含未知键 {sorted(frame)}（前后端契约漂移，拒绝该帧）",
            )
    return {"frames": frames}


def mask(secret: str | None) -> str:
    if not secret:
        return "(未设置)"
    return secret[:8] + "…" if len(secret) > 8 else "…"
