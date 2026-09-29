#!/usr/bin/env bash
# 零先验安装演练：造一个"新用户"环境 —— 干净 HOME/CODEX_HOME、没装过 rathflow、
# 没有任何 RATHFLOW_* 变量、没有账号 —— 然后从 GitHub 装插件。
#
#   scripts/naive-install.sh                    # 准备环境并打印进入方式
#   scripts/naive-install.sh --run              # 准备完直接进 Codex 交互会话
#   scripts/naive-install.sh --prompt "我想试试 RathFlow"   # 非交互跑一轮
#   scripts/naive-install.sh --local ..         # 用本地目录当 marketplace（改 skill 后回归用）
#   scripts/naive-install.sh --prompt "…" --assert          # 跑完再断言行为
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

while [ $# -gt 0 ]; do
  case "$1" in
    --prompt) PROMPT="${2:-}"; shift 2 ;;
    --local) LOCAL_SRC="${2:-}"; shift 2 ;;
    --run) RUN=1; shift ;;
    --assert) ASSERT=1; shift ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "未知参数：$1" >&2; exit 2 ;;
  esac
done

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
# 新用户不该继承任何 RathFlow / 代理残留
unset RATHFLOW_BASE_URL RATHFLOW_TOKEN RATHFLOW_PROJECT RATHFLOW_CONFIG_DIR RATHFLOW_MCP_WRITE
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy
EOF

# shellcheck disable=SC1090
source "$T/env.sh"

echo '== 2/4 确认这是个「没装过 CLI」的环境' 
if command -v rathflow >/dev/null 2>&1; then
  echo "   ！PATH 上仍有 rathflow（$(command -v rathflow)）—— 演练不成立" >&2
  exit 1
fi
echo "   rathflow: 不存在 ✓   CODEX_HOME=$CODEX_HOME"

echo "== 3/4 装插件（$([ -n "$LOCAL_SRC" ] && echo "本地 $LOCAL_SRC" || echo "GitHub $REPO")）"
if [ -n "$LOCAL_SRC" ]; then
  SOURCE="$(cd "$LOCAL_SRC" && pwd)"
else
  SOURCE="$REPO"
fi
# marketplace add 要克隆远端，网络抖动很常见；失败重试两次再放弃。
for attempt in 1 2 3; do
  if codex plugin marketplace add "$SOURCE"; then break; fi
  [ "$attempt" = 3 ] && { echo "   marketplace add 连续失败，放弃" >&2; exit 1; }
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
环境是一次性的：删掉 $T 即全部消失。
EOF
fi
