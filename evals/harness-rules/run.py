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

CREATE_SUSPENDED = 0x4

if os.name == "nt":
    import ctypes
    from ctypes import wintypes as w

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _H = ctypes.c_void_p

    def _bind(name, res, *argtypes):
        f = getattr(_k32, name)
        f.restype, f.argtypes = res, list(argtypes)
        return f

    class _BasicLimit(ctypes.Structure):  # JOBOBJECT_BASIC_LIMIT_INFORMATION
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", w.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", w.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", w.DWORD), ("SchedulingClass", w.DWORD)]

    class _ExtendedLimit(ctypes.Structure):  # JOBOBJECT_EXTENDED_LIMIT_INFORMATION
        _fields_ = [("BasicLimitInformation", _BasicLimit), ("IoInfo", ctypes.c_uint64 * 6)] + [
            (n, ctypes.c_size_t) for n in ("ProcessMemoryLimit", "JobMemoryLimit", "PeakProcessMemoryUsed",
                                           "PeakJobMemoryUsed")]

    class _Accounting(ctypes.Structure):  # JOBOBJECT_BASIC_ACCOUNTING_INFORMATION
        _fields_ = [(n, ctypes.c_int64) for n in ("TotalUserTime", "TotalKernelTime", "ThisPeriodTotalUserTime",
                                                  "ThisPeriodTotalKernelTime")] + [
            (n, w.DWORD) for n in ("TotalPageFaultCount", "TotalProcesses", "ActiveProcesses",
                                   "TotalTerminatedProcesses")]

    class _ThreadEntry(ctypes.Structure):  # THREADENTRY32
        _fields_ = [("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ThreadID", w.DWORD),
                    ("th32OwnerProcessID", w.DWORD), ("tpBasePri", w.LONG), ("tpDeltaPri", w.LONG),
                    ("dwFlags", w.DWORD)]

    _CreateJobObjectW = _bind("CreateJobObjectW", _H, ctypes.c_void_p, w.LPCWSTR)
    _SetInformationJobObject = _bind("SetInformationJobObject", w.BOOL, _H, ctypes.c_int, ctypes.c_void_p, w.DWORD)
    _QueryInformationJobObject = _bind("QueryInformationJobObject", w.BOOL, _H, ctypes.c_int, ctypes.c_void_p,
                                       w.DWORD, ctypes.POINTER(w.DWORD))
    _AssignProcessToJobObject = _bind("AssignProcessToJobObject", w.BOOL, _H, _H)
    _TerminateJobObject = _bind("TerminateJobObject", w.BOOL, _H, w.UINT)
    _OpenProcess = _bind("OpenProcess", _H, w.DWORD, w.BOOL, w.DWORD)
    _OpenThread = _bind("OpenThread", _H, w.DWORD, w.BOOL, w.DWORD)
    _ResumeThread = _bind("ResumeThread", w.DWORD, _H)
    _CloseHandle = _bind("CloseHandle", w.BOOL, _H)
    _CreateToolhelp32Snapshot = _bind("CreateToolhelp32Snapshot", _H, w.DWORD, w.DWORD)
    _Thread32First = _bind("Thread32First", w.BOOL, _H, ctypes.POINTER(_ThreadEntry))
    _Thread32Next = _bind("Thread32Next", w.BOOL, _H, ctypes.POINTER(_ThreadEntry))


class JobTree:
    """A Windows Job Object with KILL_ON_JOB_CLOSE holding claude and all it starts.

    The process must be created with CREATE_SUSPENDED: it joins the job before
    any of its code runs, so no child can start outside the job. close()
    terminates the whole tree and waits until the job is empty, so nothing the
    model started can still touch the repo while it is graded.
    """

    def __init__(self, pid: int):
        self.job = _CreateJobObjectW(None, None)
        if not self.job:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            info = _ExtendedLimit()
            info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not _SetInformationJobObject(self.job, 9, ctypes.byref(info), ctypes.sizeof(info)):
                raise ctypes.WinError(ctypes.get_last_error())
            ph = _OpenProcess(0x0101, False, pid)  # PROCESS_SET_QUOTA | PROCESS_TERMINATE
            if not ph:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                if not _AssignProcessToJobObject(self.job, ph):
                    raise ctypes.WinError(ctypes.get_last_error())
            finally:
                _CloseHandle(ph)
            if not self._resume(pid):
                raise OSError(f"no thread of process {pid} could be resumed")
        except BaseException:
            _CloseHandle(self.job)  # KILL_ON_JOB_CLOSE ends whatever already joined
            self.job = None
            raise

    @staticmethod
    def _resume(pid: int) -> int:
        """ResumeThread on each thread of pid (documented; the process has one at this point)."""
        snap = _CreateToolhelp32Snapshot(0x4, 0)  # TH32CS_SNAPTHREAD
        if not snap or snap == _H(-1).value:
            return 0
        n = 0
        try:
            t = _ThreadEntry()
            t.dwSize = ctypes.sizeof(t)
            ok = _Thread32First(snap, ctypes.byref(t))
            while ok:
                if t.th32OwnerProcessID == pid:
                    th = _OpenThread(0x0002, False, t.th32ThreadID)  # THREAD_SUSPEND_RESUME
                    if th:
                        if _ResumeThread(th) != 0xFFFFFFFF:
                            n += 1
                        _CloseHandle(th)
                ok = _Thread32Next(snap, ctypes.byref(t))
        finally:
            _CloseHandle(snap)
        return n

    def close(self, wait_s: float = 10.0) -> int:
        """Terminate every process in the job and wait for it to empty.

        Returns how many processes are still alive, or -1 when the job could
        not be queried.
        """
        _TerminateJobObject(self.job, 1)
        acct = _Accounting()
        deadline = time.monotonic() + wait_s
        while True:
            if not _QueryInformationJobObject(self.job, 1, ctypes.byref(acct), ctypes.sizeof(acct), None):
                left = -1
                break
            left = acct.ActiveProcesses
            if left == 0 or time.monotonic() > deadline:
                break
            time.sleep(0.1)
        _CloseHandle(self.job)
        self.job = None
        return left


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
    """Write guard.json and a settings file that adds guard.py as a PreToolUse hook on every tool."""
    (sdir / "guard.json").write_text(json.dumps({"repo": str(repo.resolve()), "allow_prefixes": sc.shell_prefixes}),
                                     encoding="utf-8")
    hook = f'"{Path(sys.executable).as_posix()}" -I "{(HERE / "guard.py").as_posix()}" "{(sdir / "guard.json").as_posix()}"'
    settings = {"hooks": {"PreToolUse": [{
        "matcher": "*",  # guard.py denies by default, so it has to see every tool
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
    job_note = "n/a (not Windows)"
    with open(sdir / "stream.jsonl", "wb") as so, open(sdir / "stderr.txt", "wb") as se:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | CREATE_SUSPENDED if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, cwd=repo, stdin=subprocess.PIPE, stdout=so, stderr=se,
                                env=grade.child_env(args.pass_env), creationflags=flags)
        job = None
        if os.name == "nt":
            try:
                job = JobTree(proc.pid)
                job_note = "ok"
            except Exception as e:  # noqa: BLE001 - any failure here means no job
                # Fail closed: without the job a leftover child could change the
                # repo during grading. claude is still suspended, so nothing ran.
                job_note = f"failed, claude not run: {e}"
                proc.kill()
        if job_note.startswith("failed"):
            proc.communicate()
        else:
            try:
                proc.communicate(input=sc.prompt.encode("utf-8"), timeout=args.timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                if job is None:
                    kill_tree(proc)
            if job is not None:
                left = job.close()
                if left:
                    job_note = ("unsafe, could not confirm the job is empty" if left < 0
                                else f"unsafe, {left} processes still alive after terminating the job")
            proc.wait()
    print(f"[job ] {sc.id}: {job_note}")
    meta = {"id": sc.id, "title": sc.title, "wall_s": round(time.monotonic() - start, 1),
            "exit_code": proc.returncode, "timed_out": timed_out, "job_object": job_note, "agent": sc.agent,
            "permission_mode": sc.permission_mode, "prompt": sc.prompt,
            # ctx keeps the fake canary so --regrade works; it is a random per-run token.
            "ctx": {k: v for k, v in ctx.items() if k != "outdir"},
            "cmd": cmd[1:], "ran_at": datetime.now().isoformat(timespec="seconds")}
    return score(sc, sdir, meta)


def score(sc, sdir: Path, meta: dict) -> dict:
    """Grade a finished run from its saved stream and repo; no model call."""
    run = grade.parse_stream(sdir / "stream.jsonl")
    ctx = dict(meta["ctx"], outdir=str(sdir))
    job = str(meta.get("job_object") or "")
    if job.startswith(("failed", "unsafe")):
        g = {"status": "ERROR", "checks": [], "notes": [f"not graded, job object {job}"]}
    else:
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
    keys = ("id", "title", "wall_s", "exit_code", "timed_out", "job_object", "agent", "permission_mode", "prompt",
            "ctx", "cmd", "ran_at")
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
              f"permission {r['permission_mode']}, ended: {r.get('terminal_reason')}"
              + (f", job object: {r['job_object']}" if r.get("job_object") else ""), ""]
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
