"""Run the harness-rules scenarios against the live Claude Code config.

    python evals/harness-rules/run.py                      # all scenarios, new temp dir
    python evals/harness-rules/run.py --only s1,s5 --out D # some scenarios into D
    python evals/harness-rules/run.py --regrade --out D    # re-score saved runs, no model calls
    python evals/harness-rules/run.py --report-only --out D

Each scenario runs `claude -p` once in its own throwaway repo under --out and
writes <out>/<id>/{stream.jsonl,stderr.txt,result.json}. results.md and
results.json are rebuilt from every result.json in --out after each call.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True  # keep __pycache__ out of evals/

import grade  # noqa: E402
from scenarios import SCENARIOS  # noqa: E402

# Allowlist: only what claude, git, node and python need to start on Windows
# or POSIX. Everything else (tokens, the parent session's ids and sockets) is
# dropped so it cannot surface in a transcript. Auth comes from the user's
# own login under the home directory, as in a fresh terminal.
ENV_ALLOW = {
    "PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "USERPROFILE", "HOME",
    "HOMEDRIVE", "HOMEPATH", "USERNAME", "USER", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
    "PROGRAMFILES", "PROGRAMFILES(X86)", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "SHELL",
}


def child_env(extra: list) -> dict:
    allow = ENV_ALLOW | {e.upper() for e in extra}
    return {k: v for k, v in os.environ.items() if k.upper() in allow}


def posix_abs(p: Path) -> str:
    """C:\\a\\b -> //c/a/b, the absolute form permission rules use on Windows."""
    s = p.resolve().as_posix()
    if len(s) > 1 and s[1] == ":":
        s = "/" + s[0].lower() + s[2:]
    return "/" + s


def guard_out(out: Path, config_root: Path) -> None:
    claude_home = (Path.home() / ".claude").resolve()
    for root in (claude_home, config_root.resolve()):
        if out == root or root in out.parents:
            sys.exit(f"refusing to run inside {root}: pick an --out outside ~/.claude and the repo")


def write_guard(sc, sdir: Path, repo: Path) -> Path:
    """Write guard.json and a settings file that adds guard.py as a PreToolUse hook."""
    (sdir / "guard.json").write_text(json.dumps({"repo": str(repo.resolve()), "allow_prefixes": sc.shell_prefixes}),
                                     encoding="utf-8")
    hook = f'"{Path(sys.executable).as_posix()}" -I "{(HERE / "guard.py").as_posix()}" "{(sdir / "guard.json").as_posix()}"'
    settings = {"hooks": {"PreToolUse": [{
        "matcher": "^(Edit|Write|NotebookEdit|MultiEdit|Bash|PowerShell|mcp__.*)$",
        "hooks": [{"type": "command", "command": hook}]}]}}
    path = sdir / "eval-settings.json"
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return path


def build_cmd(claude: str, sc, repo: Path, settings: Path | None = None) -> list:
    cmd = [claude, "-p", "--output-format", "stream-json", "--verbose", "--forward-subagent-text",
           "--no-session-persistence", "--permission-mode", sc.permission_mode,
           "--max-budget-usd", str(sc.budget_usd)]
    if settings:
        cmd += ["--settings", str(settings)]
    if sc.agent:
        cmd += ["--agent", sc.agent]
    if sc.allowed_tools:
        # one argv entry per rule: rules such as "Bash(git status *)" contain spaces
        cmd += ["--allowedTools", *(r.replace("{repo}", posix_abs(repo)) for r in sc.allowed_tools)]
    return cmd


def kill_tree(proc) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.kill()


def run_one(sc, out: Path, args) -> dict:
    sdir = out / sc.id
    if (sdir / "result.json").exists() and not args.force:
        print(f"[skip] {sc.id}: result.json exists (use --force to run it again)")
        return json.loads((sdir / "result.json").read_text(encoding="utf-8"))
    if sdir.exists():
        shutil.rmtree(sdir)
    repo = sdir / "repo"
    repo.mkdir(parents=True)
    ctx = sc.setup(repo, {"config_root": str(args.config_root)})
    ctx["outdir"] = str(sdir)
    cmd = build_cmd(args.claude, sc, repo, write_guard(sc, sdir, repo))
    print(f"[run ] {sc.id} ...", flush=True)
    start = time.monotonic()
    timed_out = False
    with open(sdir / "stream.jsonl", "wb") as so, open(sdir / "stderr.txt", "wb") as se:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, cwd=repo, stdin=subprocess.PIPE, stdout=so, stderr=se,
                                env=child_env(args.pass_env), creationflags=flags)
        try:
            proc.communicate(input=sc.prompt.encode("utf-8"), timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_tree(proc)
            proc.wait()
    meta = {"id": sc.id, "title": sc.title, "wall_s": round(time.monotonic() - start, 1),
            "exit_code": proc.returncode, "timed_out": timed_out, "agent": sc.agent,
            "permission_mode": sc.permission_mode, "prompt": sc.prompt,
            # ctx keeps the fake canary so --regrade works; it is a random per-run token.
            "ctx": {k: v for k, v in ctx.items() if k != "outdir"},
            "cmd": cmd[1:], "ran_at": datetime.now().isoformat(timespec="seconds")}
    return score(sc, sdir, meta)


def score(sc, sdir: Path, meta: dict) -> dict:
    """Grade a finished run from its saved stream and repo; no model call."""
    run = grade.parse_stream(sdir / "stream.jsonl")
    ctx = dict(meta["ctx"], outdir=str(sdir))
    try:
        g = sc.grade(run, sdir / "repo", ctx)
    except Exception as e:  # noqa: BLE001 - a grader crash is reported, not fatal
        g = {"status": "ERROR", "checks": [], "notes": [f"grader crashed: {e!r}"]}
    status = g["status"]
    if meta["timed_out"] or run.result is None:
        status = "ERROR"
        g["notes"].insert(0, "timed out" if meta["timed_out"] else "no result event in stream (see stderr.txt)")
    r = run.result or {}
    res = dict(meta, status=status, checks=g["checks"], notes=g["notes"],
               cost_usd=r.get("total_cost_usd"), num_turns=r.get("num_turns"),
               terminal_reason=r.get("terminal_reason") or r.get("subtype"),
               model=(run.init or {}).get("model"), final_text=run.final, tool_calls=len(run.calls))
    (sdir / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] {sc.id}: {status} in {meta['wall_s']}s")
    return res


def regrade(sc, out: Path) -> None:
    sdir = out / sc.id
    if not (sdir / "result.json").exists():
        print(f"[skip] {sc.id}: nothing to regrade")
        return
    old = json.loads((sdir / "result.json").read_text(encoding="utf-8"))
    keys = ("id", "title", "wall_s", "exit_code", "timed_out", "agent", "permission_mode", "prompt", "ctx", "cmd", "ran_at")
    score(sc, sdir, {k: old.get(k) for k in keys})


def cell(s) -> str:
    return " ".join(str(s).split()).replace("|", "\\|")


def write_report(out: Path) -> Path:
    order = {sc.id: i for i, sc in enumerate(SCENARIOS)}
    results = sorted((json.loads(p.read_text(encoding="utf-8")) for p in out.glob("*/result.json")),
                     key=lambda r: order.get(r["id"], 99))
    (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    L = [f"# Harness rules eval: {out.name}", "",
         "| scenario | status | key evidence | wall | cost (list USD) | turns |", "|---|---|---|---|---|---|"]
    for r in results:
        gates = [c for c in r["checks"] if c["gate"]]
        failed = [c for c in gates if not c["ok"]]
        key = "; ".join(f"{c['name']}: {c['evidence']}" for c in (failed or gates)[:2])
        cost = f"{r['cost_usd']:.2f}" if isinstance(r.get("cost_usd"), (int, float)) else "-"
        L.append(f"| {r['id']} | {r['status']} | {cell(key)[:300]} | {r['wall_s']}s | {cost} | {r.get('num_turns') or '-'} |")
    for r in results:
        L += ["", f"## {r['id']}: {r['title']}", "",
              f"status **{r['status']}**, model {r.get('model')}, agent {r.get('agent') or '(main session)'}, "
              f"permission {r['permission_mode']}, ended: {r.get('terminal_reason')}", ""]
        for c in r["checks"]:
            mark = "ok " if c["ok"] else "NO "
            L.append(f"- {mark}{'[gate] ' if c['gate'] else ''}{c['name']}: {cell(c['evidence'])}")
        for n in r["notes"]:
            L += ["", n if "\n" not in n else "```\n" + n + "\n```"]
        if not r["id"].startswith("s4"):
            L += ["", "<details><summary>final reply</summary>", "", r["final_text"] or "(empty)", "", "</details>"]
    s4 = {r["id"]: r for r in results if r["id"].startswith("s4")}
    if len(s4) == 2:
        a, b = s4.get("s4a_lenses_without"), s4.get("s4b_lenses_with")
        if a and b:
            L += ["", "## lenses side by side", "", "| check | without lenses | with lenses |", "|---|---|---|"]
            for ca, cb in zip(a["checks"], b["checks"]):
                L.append(f"| {ca['name']} | {'yes' if ca['ok'] else 'no'}: {cell(ca['evidence'])[:200]} "
                         f"| {'yes' if cb['ok'] else 'no'}: {cell(cb['evidence'])[:200]} |")
            for r in (a, b):
                L += ["", f"### final reply, {r['id']}", "", r["final_text"] or "(empty)"]
    path = out / "results.md"
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, help="run directory (default: %%TEMP%%/harness-eval/<timestamp>)")
    ap.add_argument("--only", help="comma-separated scenario ids or prefixes, e.g. s1,s4")
    ap.add_argument("--timeout", type=int, default=540, help="seconds per scenario (default 540)")
    ap.add_argument("--config-root", type=Path, default=HERE.parent.parent,
                    help="repo holding skills/lenses to copy when it is not installed (default: this repo)")
    ap.add_argument("--claude", default=shutil.which("claude") or "claude", help="claude executable")
    ap.add_argument("--pass-env", action="append", default=[], metavar="NAME",
                    help="also pass this env var to claude (repeatable; default is a short allowlist)")
    ap.add_argument("--force", action="store_true", help="re-run scenarios that already have result.json")
    ap.add_argument("--report-only", action="store_true", help="only rebuild results.md from --out")
    ap.add_argument("--regrade", action="store_true",
                    help="re-score saved runs in --out with the current graders (no model calls)")
    ap.add_argument("--list", action="store_true", help="list scenarios and exit")
    args = ap.parse_args()

    if args.list:
        for sc in SCENARIOS:
            print(f"{sc.id:22} {sc.title}")
        return
    out = (args.out or Path(tempfile.gettempdir()) / "harness-eval" / datetime.now().strftime("%Y%m%d-%H%M%S")).resolve()
    guard_out(out, args.config_root)
    out.mkdir(parents=True, exist_ok=True)
    if not args.report_only:
        wanted = [w.strip() for w in args.only.split(",")] if args.only else None
        selected = [sc for sc in SCENARIOS if not wanted or any(sc.id.startswith(w) for w in wanted)]
        if not selected:
            sys.exit(f"no scenario matches --only {args.only}")
        for sc in selected:
            regrade(sc, out) if args.regrade else run_one(sc, out, args)
    print(f"report: {write_report(out)}")


if __name__ == "__main__":
    main()
