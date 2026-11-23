"""PreToolUse / PostToolUse / PostToolUseFailure hook: suggest a skill when the action that needs
it happens. skill-suggest.py matches prompt keywords; this hook looks at tool calls.

PreToolUse, outward text (gh pr/issue/release text, gh api comment bodies, email, Slack, GitHub MCP writes):
  CLAUDE.md section 6 says outward text goes through humanizer first. If neither humanizer
  nor humanizer-zh-tw was loaded in this session, deny the call once per session per kind,
  with a reason that says how to proceed. The retry passes, so a call that is not prose,
  or text already checked by hand, is never stuck.
PostToolUse / PostToolUseFailure, a git command whose output reports a merge/rebase conflict:
  add context suggesting resolving-merge-conflicts, once per session, unless already loaded.
  A conflicting merge/rebase exits 1, which arrives as PostToolUseFailure.

Each nudge is logged to skill-usage/suggestions-<session>.jsonl with zone "event", so the
Stop hook counts it like any other suggestion. Any error exits 0 and never blocks the user.
"""
import json
import os
import re
import sys

STATE_DIR = os.path.join(os.path.expanduser("~"), ".claude", "skill-usage")
HUMANIZERS = {"humanizer", "humanizer-zh-tw"}
MERGE_SKILL = "resolving-merge-conflicts"

# Heredoc bodies are data. The delimiter may contain hyphens or dots, and the closing line
# must be exactly the delimiter (<<- also allows leading tabs). <<< is skipped; $((1<<2))
# is read as a heredoc only if a later line is exactly 2. Only the first heredoc on a line
# is stripped.
HEREDOC = re.compile(
    r"(?<!<)<<(?!<)(-?)[ \t]*(['\"]?)([^\s'\"<>|&;()]+)\2[^\n]*\n.*?^(?(1)\t*)\3$", re.S | re.M)
# Where a command word can start: after a separator, then shell keywords or prefixes
# (for ...; do gh ..., if ! git merge ..., { gh ...; }, time gh ...), then env assignments.
CMD_START = (r"(?:^|[;&|(\n])\s*(?:(?:do|then|else|elif|if|while|until|time|!|\{|exec|command|nohup)\s+)*"
             r"(?:env\s+)?(?:\w+=\S*\s+)*")
GH_TEXT = re.compile(
    CMD_START + r"gh(?:\s+(?:-R|--repo)(?:\s+|=)\S+)*\s+"
    r"(?:(?:pr\s+(?:create|edit|comment|review)|issue\s+(?:create|edit|comment)|release\s+(?:create|edit))\b"
    r"|api\b[^\n;&|]*?(?:-f|-F|--field|--raw-field)(?:\s+|=)body=)")
GIT_CONFLICT_CMD = re.compile(
    CMD_START + r"git(?:\s+(?:-C\s+\S+|-c\s+\S+|--no-pager|--git-dir=\S+|--work-tree=\S+))*\s+"
    r"(?:merge|rebase|cherry-pick|pull|revert|stash|am|status|checkout|switch)\b")
# Anchored to the start of a line, so a git log subject or diff line that quotes one of
# these phrases mid-line does not count.
CONFLICT = re.compile(
    r"^(?:CONFLICT \(|Automatic merge failed|error: could not apply|Unmerged paths:|"
    r"You have unmerged paths|(?:u )?(?:UU|AA|DD|AU|UA|DU|UD) \S|[^\s:]+: needs merge$)", re.M)
MCP_KINDS = (
    (re.compile(r"__(?:send_message|create_draft|update_draft|reply|forward)$"), "email"),
    (re.compile(r"__slack_(?:send_message|send_message_draft|schedule_message)$"), "slack"),
    (re.compile(r"__(?:create_issue|update_issue|add_issue_comment|create_pull_request|"
                r"update_pull_request|create_pull_request_review)$"), "github"),
)


def _placeholder(quoted):
    # gh api -f "body=text" quotes the whole field; keep it recognizable.
    return "body=Q" if quoted.startswith("body=") else "Q"


def _end_of_dquote(text, i):
    """Index just past the double-quoted string opening at text[i]. A $( ... ) inside it is
    skipped whole, so quotes nested in a command substitution do not end the string."""
    n, j = len(text), i + 1
    while j < n:
        if text[j] == "\\":
            j += 2
        elif text[j] == '"':
            return j + 1
        elif text.startswith("$(", j):
            j = _end_of_subst(text, j + 2)
        else:
            j += 1
    return n


def _end_of_subst(text, j):
    """Index just past the ) that closes a $( opened right before text[j]."""
    n, depth = len(text), 1
    while j < n:
        c = text[j]
        if c == "\\":
            j += 2
        elif c == "'":
            k = text.find("'", j + 1)
            j = n if k < 0 else k + 1
        elif c == '"':
            j = _end_of_dquote(text, j)
        else:
            depth += (c == "(") - (c == ")")
            j += 1
            if depth == 0:
                return j
    return n


def _end_of_ansi_c(text, i):
    """Index just past a $'...' string opening at text[i] == '$'; backslash escapes apply."""
    n, j = len(text), i + 2
    while j < n and text[j] != "'":
        j += 2 if text[j] == "\\" else 1
    return min(j + 1, n)


def strip_data(command):
    """The words the shell runs, with data blanked: heredoc bodies, quoted strings, comments
    and backslash-escaped characters. So grep "a|gh pr create", echo "x; gh pr create", a
    commit message or a comment never count, and an apostrophe in a comment or a don\\'t
    cannot pair with a later quote and hide a real command."""
    text = HEREDOC.sub("\n", command.replace("\r\n", "\n"))
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            out.append(" " if text[i + 1:i + 2] == "\n" else "_")
            i += 2
        elif c == "$" and text[i + 1:i + 2] == "'":
            end = _end_of_ansi_c(text, i)
            out.append(_placeholder(text[i + 2:end - 1]))
            i = end
        elif c == "'":
            end = text.find("'", i + 1)
            end = n if end < 0 else end
            out.append(_placeholder(text[i + 1:end]))
            i = end + 1
        elif c == '"':
            end = _end_of_dquote(text, i)
            out.append(_placeholder(text[i + 1:end - 1]))
            i = end
        elif c == "#" and (i == 0 or text[i - 1] in " \t\n;&|("):
            end = text.find("\n", i)
            i = n if end < 0 else end
        else:
            out.append(c)
            i += 1
    return "".join(out)


def outward_kind(tool, tool_input):
    if tool == "Bash":
        return "github-cli" if GH_TEXT.search(strip_data(str(tool_input.get("command", "")))) else None
    # mcp__ccd_* are the desktop app's own tools (session messages etc.), not outward text.
    if tool.startswith("mcp__") and not tool.startswith("mcp__ccd_"):
        for pattern, kind in MCP_KINDS:
            if pattern.search(tool):
                return kind
    return None


def typed_command_names(content):
    """Slash commands the user typed: <command-name> in a user message's own text, not in a tool result."""
    texts = [content] if isinstance(content, str) else [
        b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
    ] if isinstance(content, list) else []
    return {n for t in texts for n in re.findall(r"<command-name>/?([\w:.-]+)</command-name>", t)}


def skills_loaded(transcript):
    """Skills loaded so far: Skill tool calls plus slash commands typed by the user."""
    found = set()
    if not transcript or not os.path.isfile(transcript):
        return found
    with open(transcript, encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if '"Skill"' not in line and "<command-name>" not in line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            message = event.get("message") if isinstance(event.get("message"), dict) else event
            content = message.get("content") if isinstance(message, dict) else None
            if message.get("role") == "user" or event.get("type") == "user":
                found |= typed_command_names(content)
            if not isinstance(content, list):
                continue
            for block in content:
                if (isinstance(block, dict) and block.get("type") == "tool_use"
                        and str(block.get("name", "")).split("__")[-1] == "Skill"):
                    tool_input = block.get("input") or {}
                    name = tool_input.get("skill") or tool_input.get("name") or tool_input.get("command")
                    if name:
                        found.add(str(name))
    return found


def first_time(session, key):
    """True only for the call that creates this session+key marker. The create is atomic
    (O_EXCL), so parallel calls cannot both win. If the marker cannot be written, return
    False: better to skip a reminder than to deny the same call twice."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", "%s-%s" % (session, key))
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        os.close(os.open(os.path.join(STATE_DIR, "event-nudged-%s" % safe), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        return True
    except OSError:
        return False


def log_suggestion(session, skills, snippet):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(session))
    try:
        with open(os.path.join(STATE_DIR, "suggestions-%s.jsonl" % safe), "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"zone": "event", "skills": skills, "snippet": snippet},
                                    ensure_ascii=False) + "\n")
    except OSError:
        pass


def output_text(data):
    response = data.get("tool_response")
    if isinstance(response, dict):
        parts = [response.get("stdout"), response.get("stderr")]
    else:
        parts = [response]
    parts.append(data.get("error"))
    return "\n".join(p for p in parts if isinstance(p, str)).replace("\r\n", "\n")


def emit(obj):
    sys.stdout.write(json.dumps(obj))
    sys.stdout.flush()


def main():
    raw = sys.stdin.buffer.read().decode("utf-8", "surrogateescape")
    data = json.loads(raw) if raw.strip() else {}
    if not isinstance(data, dict):
        return
    event = data.get("hook_event_name", "")
    tool = str(data.get("tool_name", ""))
    tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    session = data.get("session_id") or "default"

    if event == "PreToolUse":
        kind = outward_kind(tool, tool_input)
        if not kind or skills_loaded(data.get("transcript_path")) & HUMANIZERS:
            return
        if not first_time(session, "humanizer-" + kind):
            return
        log_suggestion(session, sorted(HUMANIZERS), "event:outward:" + kind)
        emit({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "對外文字送出前要先過 humanizer（CLAUDE.md §6）：英文載 Skill(humanizer)，"
                "中文載 Skill(humanizer-zh-tw)，改好再重送。如果這次送的不是對外散文，"
                "或文字已經人工確認過，直接重跑同一個呼叫就會放行；這個提醒每個 session 每類只擋一次。"),
        }})
        return

    if event in ("PostToolUse", "PostToolUseFailure") and tool == "Bash":
        # Only git commands that can start or show a conflict; cat or grep of a file that
        # merely contains these phrases (this script, a log) must not trigger.
        if not GIT_CONFLICT_CMD.search(strip_data(str(tool_input.get("command", "")))):
            return
        if not CONFLICT.search(output_text(data)):
            return
        if MERGE_SKILL in skills_loaded(data.get("transcript_path")):
            return
        if not first_time(session, MERGE_SKILL):
            return
        log_suggestion(session, [MERGE_SKILL], "event:git-conflict")
        emit({"hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": (
                "git 回報 merge/rebase 衝突。依 CLAUDE.md §1，卡在衝突時先載 "
                "Skill(resolving-merge-conflicts) 再處理，不要直接手改衝突標記。"),
        }})


try:
    main()
except Exception:
    pass
sys.exit(0)
