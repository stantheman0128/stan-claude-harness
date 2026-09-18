#!/usr/bin/env sh
# SessionStart hook (Stan fork of i-have-adhd/always-on.sh): injects the trimmed
# ruleset from ~/.claude/skills/i-have-adhd/SKILL.md when .i-have-adhd-always exists.
# Never blocks session start: any failure exits 0.
claude_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
flag_path="$claude_dir/.i-have-adhd-always"
[ -f "$flag_path" ] || exit 0
skill_path="$claude_dir/skills/i-have-adhd/SKILL.md"
[ -f "$skill_path" ] || exit 0
body=$(awk '
  NR == 1 && $0 ~ /^---[[:space:]]*$/ { in_fm = 1; next }
  in_fm && $0 ~ /^---[[:space:]]*$/   { in_fm = 0; next }
  !in_fm                              { print }
' "$skill_path") || exit 0
printf 'ADHD MODE ACTIVE (always-on, Stan fork). The ruleset below applies to every response. "stop adhd mode" turns it off for this session; delete %s to turn always-on off for good.\n\n%s\n' "$flag_path" "$body"
