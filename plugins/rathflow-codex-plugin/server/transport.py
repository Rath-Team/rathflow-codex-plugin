"""HTTP 传输层：只用 Python 标准库（无 httpx、无 requests、无 PySocks）。

为什么自己写：插件的 MCP server 必须零第三方依赖才能在任何新机器上启动。
代价是要自己处理三件 httpx 免费给的事：

1. **SOCKS 代理**：标准库完全没有。这里实现 SOCKS5 CONNECT（含 socks5h 的
   代理端域名解析语义），够覆盖 Clash / V2Ray 这类本地代理。
2. **代理变量规范化**：`socks://` 与 `socks4://` 都不是标准 scheme，但现实里
   很常见；统一改写成 `socks5h://`（与 CLI 的 httpx 路径同名同义）。
3. **手写请求/响应**：因为要往 `socket` 上插代理，不能直接用 http.client 的连接池。

纪律：不打印任何东西到 stdout（stdout 是 MCP 协议通道），诊断一律交给调用方。
"""

from __future__ import annotations

import gzip
import os
import socket
import ssl
import struct
from urllib.parse import urlparse

# 代理相关环境变量；顺序即优先级（同 scheme 的 http_proxy 先于 ALL_PROXY）。
_SOCKS_SCHEMES = {"socks": "socks5h", "socks4": "socks5h", "socks5": "socks5h"}

_CRLF = b"\r\n"


class TransportError(Exception):
    """连不上、代理拒绝、超时等传输层失败。"""


def normalize_proxy_env() -> None:
    """把 `socks://` / `socks4://` 改写成 `socks5h://`（幂等，只动这几个变量）。

    `socks5h` 让代理解析域名——这正是 Clash 之类本地代理的预期行为；若用
    `socks5` 则在本地解析，DNS 污染下会连错。socks4 在现实端口上几乎都由
    SOCKS5 承接，直接按 5 处理。
    """
    for name in _proxy_var_names():
        value = os.environ.get(name)
        if not value:
            continue
        scheme, sep, rest = value.partition("://")
        if not sep:
            continue
        replacement = _SOCKS_SCHEMES.get(scheme.lower())
        if replacement and scheme != replacement:
            os.environ[name] = f"{replacement}://{rest}"


def _proxy_var_names() -> tuple[str, ...]:
    return ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")


def proxy_for(scheme: str, host: str) -> str | None:
    """按 scheme 选代理；命中 NO_PROXY 则不代理。"""
    if _bypassed(host):
        return None
    candidates = (f"{scheme.upper()}_PROXY", f"{scheme.lower()}_proxy", "ALL_PROXY", "all_proxy")
    for name in candidates:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


def _bypassed(host: str) -> bool:
    raw = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
    if not raw.strip():
        return False
    host = host.lower()
    for item in raw.split(","):
        item = item.strip().lower().lstrip(".")
        if not item:
            continue
        if item == "*" or host == item or host.endswith("." + item):
            return True
    return False


# --------------------------------------------------------------------- SOCKS5


def _recv_exact(sock: socket.socket, count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining > 0:
        try:
            chunk = sock.recv(remaining)
        except OSError as exc:
            raise TransportError(f"代理连接中断：{exc}") from None
        if not chunk:
            raise TransportError("代理连接被对端关闭")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def socks5_connect(
    proxy_host: str, proxy_port: int, dest_host: str, dest_port: int, timeout: float
) -> socket.socket:
    """SOCKS5 CONNECT；目标用域名交给代理解析（socks5h 语义）。"""
    try:
        sock = socket.create_connection((proxy_host, proxy_port), timeout=timeout)
    except OSError as exc:
        raise TransportError(f"连不上代理 {proxy_host}:{proxy_port}：{exc}") from None
    try:
        sock.settimeout(timeout)
        # 只声明 no-auth。需要用户名密码的代理（0x02）这里不支持 —— 本地代理默认无认证。
        sock.sendall(b"\x05\x01\x00")
        version, method = _recv_exact(sock, 2)
        if version != 5:
            raise TransportError(f"代理不是 SOCKS5（版本 {version}）")
        if method != 0:
            raise TransportError("代理要求认证（0x%02x），本插件只支持免认证的本地代理" % method)
        host_bytes = dest_host.encode("idna") if _needs_idna(dest_host) else dest_host.encode()
        if len(host_bytes) > 255:
            raise TransportError("目标域名过长")
        request = (
            b"\x05\x01\x00\x03" + bytes([len(host_bytes)]) + host_bytes + struct.pack(">H", dest_port)
        )
        sock.sendall(request)
        head = _recv_exact(sock, 4)
        if head[1] != 0:
            raise TransportError(f"代理拒绝连接（SOCKS5 状态 {head[1]}）")
        atyp = head[3]
        if atyp == 1:
            _recv_exact(sock, 4)
        elif atyp == 3:
            _recv_exact(sock, _recv_exact(sock, 1)[0])
        elif atyp == 4:
            _recv_exact(sock, 16)
        else:
            raise TransportError(f"代理返回未知地址类型 {atyp}")
        _recv_exact(sock, 2)  # 绑定端口，忽略
        return sock
    except Exception:
        sock.close()
        raise


def _needs_idna(host: str) -> bool:
    return not host.isascii()


def _connect_through_http_proxy(
    proxy: urlparse, dest_host: str, dest_port: int, timeout: float
) -> socket.socket:
    """HTTPS 走代理要靠 CONNECT 隧道（明文 HTTP 由调用方用绝对 URI）。"""
    try:
        sock = socket.create_connection((proxy.hostname, proxy.port or 8080), timeout=timeout)
    except OSError as exc:
        raise TransportError(f"连不上代理 {proxy.hostname}:{proxy.port}：{exc}") from None
    try:
        sock.settimeout(timeout)
        authority = f"{dest_host}:{dest_port}"
        head = f"CONNECT {authority} HTTP/1.1\r\nHost: {authority}\r\n"
        if proxy.username:
            import base64

            raw = f"{proxy.username}:{proxy.password or ''}".encode()
            head += "Proxy-Authorization: Basic " + base64.b64encode(raw).decode() + "\r\n"
        sock.sendall(head.encode() + _CRLF)
        status_line = _read_line(sock)
        code = status_line.split(" ")[1] if len(status_line.split(" ")) > 1 else ""
        if not code.startswith("2"):
            raise TransportError(f"代理拒绝 CONNECT：{status_line.strip()}")
        while True:  # 吃掉响应头（含可能的 100-continue 之外的其它头）
            line = _read_line(sock)
            if line in (b"\r\n", b"\n", b""):
                break
        return sock
    except Exception:
        sock.close()
        raise


def _read_line(sock: socket.socket) -> bytes:
    buf = bytearray()
    while not buf.endswith(b"\n"):
        chunk = sock.recv(1)
        if not chunk:
            break
        buf += chunk
        if len(buf) > 65536:
            raise TransportError("响应头过长")
    return bytes(buf)


# ----------------------------------------------------------------- 连接与请求


def _open_connection(scheme: str, host: str, port: int, timeout: float):
    proxy = proxy_for(scheme, host)
    if proxy:
        parsed = urlparse(proxy if "://" in proxy else f"http://{proxy}")
        if parsed.scheme in ("socks5h", "socks5"):
            raw = socks5_connect(parsed.hostname, parsed.port or 1080, host, port, timeout)
        elif parsed.scheme in ("http", "https"):
            raw = _connect_through_http_proxy(parsed, host, port, timeout)
        else:
            raise TransportError(f"不支持的代理协议 {parsed.scheme}://（支持 http/socks5h）")
    else:
        try:
            raw = socket.create_connection((host, port), timeout=timeout)
        except OSError as exc:
            raise TransportError(f"无法连接 {host}:{port}：{exc}") from None
    if scheme == "https":
        context = ssl.create_default_context()
        try:
            return context.wrap_socket(raw, server_hostname=host)
        except ssl.SSLError as exc:
            raw.close()
            raise TransportError(f"TLS 握手失败（{host}）：{exc}") from None
    return raw


class Response:
    """只保留调用方需要的三样东西：状态、头、正文。"""

    def __init__(self, status: int, headers: dict[str, str], body: bytes):
        self.status = status
        self.headers = headers
        self.body = body

    def json(self) -> dict:
        import json

        if not self.body:
            return {}
        try:
            data = json.loads(self.body.decode("utf-8", "replace"))
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {"data": data}

    def text(self) -> str:
        return self.body.decode("utf-8", "replace")


def request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: float = 120.0,
    max_bytes: int | None = None,
) -> Response:
    """发一次请求并读完响应。`max_bytes` 用于流式端点的有界抽取。"""
    parsed = urlparse(url)
    scheme = parsed.scheme or "https"
    host = parsed.hostname or ""
    port = parsed.port or (443 if scheme == "https" else 80)
    if not host:
        raise TransportError(f"非法 URL：{url}")
    target = parsed.path or "/"
    if parsed.query:
        target += "?" + parsed.query

    timeout = float(timeout)
    sock = _open_connection(scheme, host, port, timeout)
    try:
        proxy = proxy_for(scheme, host)
        request_target = target
        if proxy and scheme == "http" and not proxy.startswith("socks"):
            request_target = url  # 明文 HTTP 交给代理时用绝对 URI（RFC 7230 §5.3.2）

        head = [f"{method.upper()} {request_target} HTTP/1.1", f"Host: {_host_header(host, port, scheme)}"]
        send_headers = dict(headers or {})
        send_headers.setdefault("Accept", "application/json")
        send_headers.setdefault("Accept-Encoding", "identity")
        send_headers.setdefault("Connection", "close")
        send_headers.setdefault("User-Agent", "rathflow-codex-plugin/0.1.0")
        if body is not None:
            send_headers.setdefault("Content-Type", "application/json")
            send_headers["Content-Length"] = str(len(body))
        for key, value in send_headers.items():
            head.append(f"{key}: {value}")
        payload = ("\r\n".join(head) + "\r\n\r\n").encode() + (body or b"")
        sock.sendall(payload)
        return _read_response(sock, method.upper(), max_bytes=max_bytes)
    except socket.timeout as exc:
        raise TransportError(f"请求超时（{timeout:.0f}s）：{exc}") from None
    except OSError as exc:
        raise TransportError(f"网络错误：{exc}") from None
    finally:
        sock.close()


def _host_header(host: str, port: int, scheme: str) -> str:
    default = 443 if scheme == "https" else 80
    return host if port == default else f"{host}:{port}"


def _read_response(sock: socket.socket, method: str, *, max_bytes: int | None) -> Response:
    status_line = _read_line(sock).decode("latin-1").strip()
    parts = status_line.split(" ", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise TransportError(f"服务端返回了非 HTTP 响应：{status_line[:120]!r}")
    status = int(parts[1])
    headers: dict[str, str] = {}
    while True:
        line = _read_line(sock)
        if line in (b"\r\n", b"\n", b""):
            break
        name, _, value = line.decode("latin-1").partition(":")
        headers[name.strip().lower()] = value.strip()

    body = _read_body(sock, method, status, headers, max_bytes=max_bytes)
    if headers.get("content-encoding", "").lower() == "gzip":
        try:
            body = gzip.decompress(body)
        except OSError:
            pass
    return Response(status, headers, body)


def _read_body(
    sock: socket.socket, method: str, status: int, headers: dict[str, str], *, max_bytes: int | None
) -> bytes:
    if method == "HEAD" or status in (204, 304):
        return b""
    if headers.get("transfer-encoding", "").lower() == "chunked":
        return _read_chunked(sock, max_bytes=max_bytes)
    length = headers.get("content-length")
    if length and length.isdigit():
        want = int(length)
        if max_bytes is not None:
            want = min(want, max_bytes)
        return _recv_exact(sock, want)
    # 无长度：读到 EOF。`Connection: close` 下这就是全部正文（流式端点也走这里，
    # 用 max_bytes 截断，避免沙箱那类长流把内存吃满）。
    return _read_until_eof(sock, max_bytes=max_bytes)


def _read_chunked(sock: socket.socket, *, max_bytes: int | None) -> bytes:
    out = bytearray()
    while True:
        size_line = _read_line(sock).strip()
        if not size_line:
            break
        size_text = size_line.split(b";")[0]
        try:
            size = int(size_text, 16)
        except ValueError:
            raise TransportError(f"非法 chunk 长度：{size_line[:40]!r}") from None
        if size == 0:
            while True:  # 吃 trailer
                if _read_line(sock) in (b"\r\n", b"\n", b""):
                    break
            break
        out += _recv_exact(sock, size)
        _recv_exact(sock, 2)  # 每个 chunk 后面的 CRLF
        if max_bytes is not None and len(out) >= max_bytes:
            break
    return bytes(out)


def _read_until_eof(sock: socket.socket, *, max_bytes: int | None) -> bytes:
    out = bytearray()
    while True:
        if max_bytes is not None and len(out) >= max_bytes:
            break
        try:
            chunk = sock.recv(65536)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
    return bytes(out)
