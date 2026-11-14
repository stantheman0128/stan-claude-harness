#!/bin/bash
# Shared port lookup for claude-mem hooks.
# Windows: Get-NetTCPConnection + taskkill.
# Linux/macOS: lsof or ss, then kill. powershell and taskkill are absent there,
# and treating a failed lookup as "port free" leaves the zombie socket bound.

port_owner() {
  local port="$1" pid=""
  if command -v powershell >/dev/null 2>&1; then
    pid=$(powershell -NoProfile -Command "
      \$c = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
      if (\$c) { \$c.OwningProcess } else { '' }
    " 2>/dev/null | tr -d '[:space:]')
    printf '%s' "$pid"
    return 0
  fi
  if command -v lsof >/dev/null 2>&1; then
    pid=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | awk 'NR==1 { print; exit }')
    printf '%s' "$pid"
    return 0
  fi
  if command -v ss >/dev/null 2>&1; then
    pid=$(ss -ltnpH "sport = :$port" 2>/dev/null | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | awk 'NR==1 { print; exit }')
    printf '%s' "$pid"
    return 0
  fi
  return 0
}

kill_pid_tree() {
  local pid="$1" child
  [ -n "$pid" ] || return 0
  if command -v taskkill >/dev/null 2>&1; then
    taskkill //PID "$pid" //T //F >/dev/null 2>&1
    return 0
  fi
  if command -v pgrep >/dev/null 2>&1; then
    for child in $(pgrep -P "$pid" 2>/dev/null); do
      kill_pid_tree "$child"
    done
  fi
  kill -TERM "$pid" 2>/dev/null || true
  sleep 0.2
  kill -KILL "$pid" 2>/dev/null || true
}
