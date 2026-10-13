#!/bin/bash
# claude-mem port sync + ghost-port recovery (Windows)
# If a worker dies and Windows keeps a LISTEN socket (dead PID), claude-mem
# treats the port as taken, refuses to spawn, and SessionStart hooks fail
# closed. This hook finds a healthy worker, kills a hung live owner, or moves
# to a free port and starts the installed worker.

[ -f "$HOME/.claude-mem/.paused" ] && exit 0

SETTINGS_FILE="$HOME/.claude-mem/settings.json"
HOOK_FAIL="$HOME/.claude-mem/state/hook-failures.json"
PORT_MIN=37777
PORT_MAX=37800

health() {
  curl -sf "http://127.0.0.1:${1}/health" --max-time 1 >/dev/null 2>&1
}

# Succeeds if something is listening (live worker OR kernel ghost).
# curl 7 = connection refused = port is free. Do not use Windows timeout.exe.
port_held() {
  local rc=0
  curl -s -o /dev/null --max-time 1 "http://127.0.0.1:${1}/" >/dev/null 2>&1 || rc=$?
  [ "$rc" -ne 7 ]
}

listen_pid() {
  powershell.exe -NoProfile -Command \
    "try { (Get-NetTCPConnection -LocalPort ${1} -State Listen -ErrorAction Stop | Select-Object -First 1).OwningProcess } catch { }" \
    2>/dev/null | tr -d '\r[:space:]'
}

process_alive() {
  powershell.exe -NoProfile -Command \
    "try { Get-Process -Id ${1} -ErrorAction Stop | Out-Null; Write-Output 1 } catch { }" \
    2>/dev/null | tr -d '\r[:space:]'
}

kill_pid() {
  powershell.exe -NoProfile -Command \
    "Stop-Process -Id ${1} -Force -ErrorAction SilentlyContinue" >/dev/null 2>&1
}

set_port() {
  [ -f "$SETTINGS_FILE" ] || return 0
  sed -i "s/\"CLAUDE_MEM_WORKER_PORT\"[[:space:]]*:[[:space:]]*\"[0-9]*\"/\"CLAUDE_MEM_WORKER_PORT\": \"${1}\"/" "$SETTINGS_FILE"
  echo "{\"port\": ${1}}" > "$HOME/.claude-mem/worker.pid"
}

reset_failures() {
  mkdir -p "$HOME/.claude-mem/state"
  printf '%s\n' '{"consecutiveFailures":0,"lastFailureAt":0}' > "$HOOK_FAIL"
}

find_worker_script() {
  local best="" bestkey="000000000000000000000000"
  local d ver key
  for d in "$HOME/.claude/plugins/cache/thedotmack/claude-mem"/[0-9]*/; do
    [ -d "$d" ] || continue
    [ -e "${d}.orphaned_at" ] && continue
    [ -f "${d}scripts/worker-service.cjs" ] || continue
    ver=$(basename "${d%/}")
    key=$(printf '%s' "$ver" | awk -F. '{printf "%08d%08d%08d", $1+0,$2+0,$3+0}')
    if [ "$key" \> "$bestkey" ]; then
      bestkey=$key
      best="${d}scripts/worker-service.cjs"
    fi
  done
  if [ -z "$best" ] && [ -f "$HOME/.claude/plugins/marketplaces/thedotmack/plugin/scripts/worker-service.cjs" ]; then
    best="$HOME/.claude/plugins/marketplaces/thedotmack/plugin/scripts/worker-service.cjs"
  fi
  printf '%s' "$best"
}

to_win_path() {
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$1" 2>/dev/null
  else
    printf '%s' "$1"
  fi
}

spawn_worker() {
  local script_win bun_win
  script_win=$(to_win_path "$1")
  bun_win=$(to_win_path "$HOME/.bun/bin/bun.exe")
  [ -f "$HOME/.bun/bin/bun.exe" ] || bun_win="bun"
  powershell.exe -NoProfile -Command \
    "Start-Process -FilePath '${bun_win}' -ArgumentList '${script_win}' -WindowStyle Hidden" \
    >/dev/null 2>&1
}

wait_health() {
  local port="$1" i
  for i in 1 2 3 4 5 6 7 8 9 10; do
    if health "$port"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

CONFIGURED_PORT=$(grep -o '"CLAUDE_MEM_WORKER_PORT"[[:space:]]*:[[:space:]]*"[0-9]*"' "$SETTINGS_FILE" 2>/dev/null | grep -o '[0-9]*')
CONFIGURED_PORT=${CONFIGURED_PORT:-37777}

if health "$CONFIGURED_PORT"; then
  reset_failures
  exit 0
fi

for PORT in $(seq "$PORT_MIN" "$PORT_MAX"); do
  if health "$PORT"; then
    set_port "$PORT"
    reset_failures
    exit 0
  fi
done

pid=$(listen_pid "$CONFIGURED_PORT")
if [ -n "$pid" ] && [ "$pid" != "0" ] && [ "$(process_alive "$pid")" = "1" ]; then
  kill_pid "$pid"
  sleep 1
  if health "$CONFIGURED_PORT"; then
    reset_failures
    exit 0
  fi
fi

WORKER_SCRIPT=$(find_worker_script)
[ -n "$WORKER_SCRIPT" ] && [ -f "$WORKER_SCRIPT" ] || exit 0

FREE=""
for PORT in $(seq "$PORT_MIN" "$PORT_MAX"); do
  if ! port_held "$PORT"; then
    FREE=$PORT
    break
  fi
done
[ -n "$FREE" ] || exit 0

set_port "$FREE"
spawn_worker "$WORKER_SCRIPT"
if wait_health "$FREE"; then
  reset_failures
fi
exit 0
