#!/usr/bin/env bash
# 零先验安装演练：造一个"新用户"环境 —— 干净 HOME/CODEX_HOME、没装过 rathflow、
# 没有任何 RATHFLOW_* 变量、没有账号 —— 然后从 GitHub 装插件。
#
#   scripts/naive-install.sh                    # 准备环境并打印进入方式（沿用本机代理）
#   scripts/naive-install.sh --run              # 准备完直接进 Codex 交互会话
#   scripts/naive-install.sh --prompt "我想试试 RathFlow"   # 非交互跑一轮
#   scripts/naive-install.sh --local ..         # 用本地目录当 marketplace（改 skill 后回归用）
#   scripts/naive-install.sh --prompt "…" --assert          # 跑完再断言行为
#
# 代理（默认沿用本机 *_PROXY，因为真实用户就是这样）：
#   --proxy socks5h://127.0.0.1:7897   强制指定；socks:// 会自动规范成 socks5h://
#   --proxy auto                       探测常见本地代理端口
#   --no-proxy                         完全直连（离线/直连场景）
#   --http1                            强制 git 走 HTTP/1.1
# 克隆报 HTTP2 framing layer 时会自动改用 HTTP/1.1 重试一次。
#
# 目的是压住那些"写 skill 的人已经知道答案"的盲区：新用户不知道怎么登录、
# 不知道 MCP 要重开会话、更不该被引导去找源码或本地部署。
set -euo pipefail

REPO="Rath-Team/rathflow-codex-plugin"
PLUGIN="rathflow-codex-plugin"
MARKETPLACE="rathflow-marketplace"
LOCAL_SRC=""
PROMPT=""
RUN=0
ASSERT=0
PROXY_MODE="inherit"   # inherit | force | off
PROXY_ARG=""
HTTP1=0

while [ $# -gt 0 ]; do
  case "$1" in
    --prompt) PROMPT="${2:-}"; shift 2 ;;
    --local) LOCAL_SRC="${2:-}"; shift 2 ;;
    --proxy) PROXY_ARG="${2:-}"; PROXY_MODE="force"; shift 2 ;;
    --no-proxy) PROXY_MODE="off"; shift ;;
    --http1) HTTP1=1; shift ;;
    --run) RUN=1; shift ;;
    --assert) ASSERT=1; shift ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    *) echo "未知参数：$1" >&2; exit 2 ;;
  esac
done

# ---------------------------------------------------------------- 代理判定

# httpx 只认 socks5/socks5h；git/curl 也不认 socks:// 与 socks4://，落到它们之前先规范化。
normalize_proxy() {
  case "${1:-}" in
    socks://*)  printf 'socks5h://%s' "${1#socks://}" ;;
    socks4://*) printf 'socks5h://%s' "${1#socks4://}" ;;
    *)          printf '%s' "${1:-}" ;;
  esac
}

detect_inherited_proxy() {
  local name
  for name in HTTPS_PROXY https_proxy ALL_PROXY all_proxy HTTP_PROXY http_proxy; do
    if [ -n "${!name:-}" ]; then printf '%s' "${!name}"; return 0; fi
  done
}

probe_url() {  # probe_url URL [proxy]
  if [ -n "${2:-}" ]; then
    curl -s -o /dev/null -m 8 --proxy "$2" -w '%{http_code}' "$1" 2>/dev/null || true
  else
    curl -s -o /dev/null -m 8 -w '%{http_code}' "$1" 2>/dev/null || true
  fi
}

detect_local_proxy() {
  local cand code
  for cand in socks5h://127.0.0.1:7897 socks5h://127.0.0.1:7890 \
              http://127.0.0.1:7897 http://127.0.0.1:7890 \
              http://127.0.0.1:1080 http://127.0.0.1:8888; do
    code="$(probe_url https://github.com "$cand")"
    case "$code" in 2*|3*) printf '%s' "$cand"; return 0 ;; esac
  done
  return 1
}

case "$PROXY_MODE" in
  off) EFFECTIVE_PROXY="" ;;
  force)
    if [ "$PROXY_ARG" = "auto" ]; then
      EFFECTIVE_PROXY="$(detect_local_proxy || true)"
      [ -n "$EFFECTIVE_PROXY" ] || { echo "--proxy auto 没探测到可用代理；改用 --no-proxy 或显式给 URL" >&2; exit 2; }
    else
      [ -n "$PROXY_ARG" ] || { echo "--proxy 需要 URL（或 auto）" >&2; exit 2; }
      case "$PROXY_ARG" in
        *://*) ;;
        *) echo "--proxy 的 URL 得带协议，例如 socks5h://127.0.0.1:7897（socks:// 也行）" >&2; exit 2 ;;
      esac
      EFFECTIVE_PROXY="$(normalize_proxy "$PROXY_ARG")"
    fi ;;
  inherit) EFFECTIVE_PROXY="$(normalize_proxy "$(detect_inherited_proxy)")" ;;
esac

# git 只认 http.proxy/https.proxy；用 GIT_CONFIG_* 传参，绝不写用户全局配置。
GIT_KEYS=(); GIT_VALUES=()
git_cfg() { GIT_KEYS+=("$1"); GIT_VALUES+=("$2"); }
[ -n "$EFFECTIVE_PROXY" ] && { git_cfg http.proxy "$EFFECTIVE_PROXY"; git_cfg https.proxy "$EFFECTIVE_PROXY"; }
[ "$HTTP1" = 1 ] && git_cfg http.version HTTP/1.1

add_runtime_git_cfg() {  # add_runtime_git_cfg KEY VALUE（当前进程生效，供 codex 子进程继承）
  local n="${GIT_CONFIG_COUNT:-0}"
  export "GIT_CONFIG_KEY_$n=$1" "GIT_CONFIG_VALUE_$n=$2"
  export GIT_CONFIG_COUNT=$((n + 1))
}

# 写进 env.sh 的两段环境：代理变量 + git 的按命令配置。
proxy_lines() {
  if [ -n "$EFFECTIVE_PROXY" ]; then
    printf 'export ALL_PROXY=%q\nexport all_proxy=%q\nexport HTTPS_PROXY=%q\nexport https_proxy=%q\nexport HTTP_PROXY=%q\nexport http_proxy=%q\n' \
      "$EFFECTIVE_PROXY" "$EFFECTIVE_PROXY" "$EFFECTIVE_PROXY" \
      "$EFFECTIVE_PROXY" "$EFFECTIVE_PROXY" "$EFFECTIVE_PROXY"
  else
    printf 'unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy\n'
  fi
}

git_cfg_lines() {
  printf 'export GIT_CONFIG_COUNT=%d\n' "${#GIT_KEYS[@]}"
  local i
  for i in "${!GIT_KEYS[@]}"; do
    printf 'export GIT_CONFIG_KEY_%d=%q\nexport GIT_CONFIG_VALUE_%d=%q\n' \
      "$i" "${GIT_KEYS[$i]}" "$i" "${GIT_VALUES[$i]}"
  done
}

T="$(mktemp -d "${TMPDIR:-/tmp}/rf-naive-XXXXXX")"
mkdir -p "$T/bin" "$T/.codex"

echo "== 1/4 造隔离环境：$T"

# 只把"新用户本来就有"的工具暴露出来；**刻意不放 rathflow**。
for tool in uv node npm npx codex git python3 curl rg sed grep cat env bash sh sqlite3; do
  src="$(command -v "$tool" 2>/dev/null || true)"
  [ -n "$src" ] && ln -sf "$src" "$T/bin/$tool"
done

# 模型 provider 配置要带过去，否则新环境里 Codex 跑不起来；但 marketplace/plugin
# 注册必须剥掉 —— 否则不算"从零"。
python3 - "$T" <<'PY'
import pathlib, re, shutil, sys
T = pathlib.Path(sys.argv[1])
home = pathlib.Path.home()
text = (home / ".codex" / "config.toml").read_text(encoding="utf-8")
for section in ("marketplaces", "plugins"):
    text = re.sub(rf"\n\[{section}\.[^\]]+\][^\n]*\n(?:[^\[\n][^\n]*\n)*", "\n", text)
(T / ".codex" / "config.toml").write_text(text, encoding="utf-8")
auth = home / ".codex" / "auth.json"
if auth.exists():
    shutil.copy(auth, T / ".codex" / "auth.json")
PY

# 继承的 PATH 里只要某个目录藏着 rathflow，那台机器就算不上"新用户"。
# 挑掉这些目录，其余保留（免得 nvm / brew 之类的东西找不到）。
CLEAN_PATH="$T/bin:$T/.local/bin"
IFS=':' read -r -a _parts <<< "$PATH"
for _d in "${_parts[@]}"; do
  [ -n "$_d" ] || continue
  [ "$_d" = "$T/bin" ] && continue
  [ "$_d" = "$T/.local/bin" ] && continue
  [ -x "$_d/rathflow" ] && { echo "   剔除含 rathflow 的目录：$_d"; continue; }
  CLEAN_PATH="$CLEAN_PATH:$_d"
done

cat > "$T/env.sh" <<EOF
# 零先验演练环境（source 它再跑 codex）
export T="$T"
export HOME="$T"
export CODEX_HOME="$T/.codex"
export PATH="$CLEAN_PATH"
# 新用户不该继承任何 RathFlow 残留；代理是本机的正常环境，按上面的判定保留/清除
unset RATHFLOW_BASE_URL RATHFLOW_TOKEN RATHFLOW_PROJECT RATHFLOW_CONFIG_DIR RATHFLOW_MCP_WRITE
$(proxy_lines)
$(git_cfg_lines)
EOF

# shellcheck disable=SC1090
source "$T/env.sh"

echo '== 2/4 确认这是个「没装过 CLI」的环境' 
if command -v rathflow >/dev/null 2>&1; then
  echo "   ！PATH 上仍有 rathflow（$(command -v rathflow)）—— 演练不成立" >&2
  exit 1
fi
echo "   rathflow: 不存在 ✓   CODEX_HOME=$CODEX_HOME"

echo "== 2.5/4 网络/代理体检"
if [ -n "$EFFECTIVE_PROXY" ]; then
  echo "   代理：$EFFECTIVE_PROXY（规范化后）"
else
  echo "   代理：未设置（直连）"
fi
for target in "https://pypi.org/simple/rathflow-cli/" \
              "https://github.com/Rath-Team/rathflow-codex-plugin.git"; do
  code="$(probe_url "$target" "$EFFECTIVE_PROXY")"
  case "$code" in
    2*|3*) echo "   $target → $code ✓" ;;
    *)     echo "   $target → ${code:-超时}（可能需要代理：--proxy <url> / --proxy auto）" ;;
  esac
done

echo "== 3/4 装插件（$([ -n "$LOCAL_SRC" ] && echo "本地 $LOCAL_SRC" || echo "GitHub $REPO")）"
if [ -n "$LOCAL_SRC" ]; then
  SOURCE="$(cd "$LOCAL_SRC" && pwd)"
else
  SOURCE="$REPO"
fi
# marketplace add 要克隆远端；网络抖动和 HTTP2 framing 层问题都很常见。
attempt=0
http1_tried=0
while :; do
  attempt=$((attempt + 1))
  if codex plugin marketplace add "$SOURCE"; then break; fi
  if [ "$http1_tried" = 0 ]; then
    http1_tried=1
    echo "   克隆失败；改用 HTTP/1.1 重试一次（HTTP2 framing 层已知问题）"
    add_runtime_git_cfg http.version HTTP/1.1
    continue
  fi
  if [ "$attempt" -ge 3 ]; then
    cat >&2 <<'EOF'
   marketplace add 连续失败。看起来是网络/代理问题，按顺序试：
     scripts/naive-install.sh --proxy socks5h://127.0.0.1:7897   # 显式代理（socks:// 写 socks5h://）
     scripts/naive-install.sh --proxy auto                       # 探测常见本地代理端口
     scripts/naive-install.sh --no-proxy                         # 已确认直连可用时
     scripts/naive-install.sh --local .                          # 完全不联网，用本地工作树
EOF
    exit 1
  fi
  echo "   marketplace add 失败，重试（$attempt/3）…"
  sleep 3
done
codex plugin add "$PLUGIN@$MARKETPLACE"
echo "   已装：$(ls "$CODEX_HOME/plugins/cache/$MARKETPLACE/$PLUGIN")"

echo "== 4/4 就绪"
if [ -n "$PROMPT" ]; then
  LOG="$T/run.log"
  echo "   跑一轮：$PROMPT"
  set +e
  (cd "$T" && codex exec --dangerously-bypass-approvals-and-sandbox \
      --skip-git-repo-check "$PROMPT" >"$LOG" 2>&1)
  rc=$?
  set -e
  echo "   codex 退出码 $rc，日志 $LOG"
  echo "--- 回复 ---"
  tail -20 "$LOG"
  if [ "$ASSERT" = 1 ]; then
    echo "--- 断言 ---"
    fail=0
    bad=$(grep -cE "git clone|my_workspace/RathFlow|find / |locate |pip install -e|go build|docker run" "$LOG" || true)
    [ "$bad" = 0 ] && echo "   没有找源码/本地部署痕迹 ✓" || { echo "   出现找源码/本地部署痕迹 $bad 处 ✗"; fail=1; }
    grep -qE "auth (login|register)" "$LOG" && echo "   给了注册/登录路径 ✓" \
      || { echo "   没给注册/登录路径 ✗"; fail=1; }
    grep -qE "重开|重启|restart" "$LOG" && echo "   提醒了重开会话 ✓" \
      || echo "   （本次会话若无 MCP 启动失败，可不提重开）"
    [ "$fail" = 0 ] || exit 1
  fi
elif [ "$RUN" = 1 ]; then
  echo "   进入 Codex 会话（退出即结束）"
  cd "$T" && exec codex
else
  cat <<EOF

体验方式（照抄两行）：

    source $T/env.sh
    cd $T && codex

然后随便问一句，比如「我想试试 RathFlow」。
代理：本次判定为 $([ -n "$EFFECTIVE_PROXY" ] && echo "$EFFECTIVE_PROXY" || echo "直连（未设置代理）")；env.sh 里已固定，重进也一致。
环境是一次性的：删掉 $T 即全部消失。
EOF
fi
