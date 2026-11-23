"""loop-gate selftest：對 scripts 餵假 event、斷言行為。

改任何 hook 前後都要跑到全綠（validate-and-revert 的 validate 步）。
用法：py loop-gate/scripts/selftest/run.py
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
PY = sys.executable

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def run_hook(script, event, home, env_extra=None, args=None):
    """以 subprocess 執行 scripts/<script>，stdin 餵 event JSON。"""
    env = os.environ.copy()
    env["LOOP_GATE_HOME"] = str(home)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.update(env_extra or {})
    return subprocess.run(
        [PY, str(SCRIPTS / script), *(args or [])],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


def git(cwd, *args):
    subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        },
    )


def make_repo(tmp):
    """建一個乾淨的 git 專案：一個 committed 檔 + .claude/ 目錄。"""
    root = Path(tmp) / "proj"
    (root / ".claude").mkdir(parents=True)
    (root / "src.txt").write_text("v1\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "src.txt")
    git(root, "commit", "-q", "-m", "init")
    return root


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@test
def smoke_runner_works(tmp):
    """harness 本身可用：跑一個不存在的 script 會丟 FileNotFoundError 以外的行為。"""
    proc = run_hook("verify_gate.py", {"stop_hook_active": True}, home=tmp)
    assert proc.returncode == 0, f"verify_gate 應存在且對 stop_hook_active 放行, got rc={proc.returncode} stderr={proc.stderr}"


@test
def health_guard_catches_crash(tmp):
    """guard 捕捉例外：fail-open（exit 0）+ health log 有紀錄。"""
    proc = run_hook("selftest/fixtures/probe_crash.py", {}, home=tmp)
    assert proc.returncode == 0, f"guard 應 fail-open, got {proc.returncode}"
    log = Path(tmp) / "hook-health.log"
    assert log.exists(), "health log 應存在"
    entry = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert entry["hook"] == "probe"
    assert "ZeroDivisionError" in entry["error"]


@test
def health_log_rotates(tmp):
    """log 超過 1MB 會 rotate 成 .old。"""
    log = Path(tmp) / "hook-health.log"
    log.write_text("x" * 1_100_000, encoding="utf-8")
    proc = run_hook("selftest/fixtures/probe_crash.py", {}, home=tmp)
    assert proc.returncode == 0
    assert (Path(tmp) / "hook-health.log.old").exists(), "應產生 .old"
    assert log.stat().st_size < 10_000, "新 log 應是小檔"


def write_manifest(root, home, command, **extra):
    """寫 verify.json 並經 trust_manifest.py 註冊信任。"""
    manifest = {"command": command, **extra}
    path = root / ".claude" / "verify.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    env = os.environ.copy()
    env["LOOP_GATE_HOME"] = str(home)
    proc = subprocess.run(
        [PY, str(SCRIPTS / "trust_manifest.py"), str(root)],
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert proc.returncode == 0, f"trust_manifest 失敗: {proc.stderr}"


def stop_event(session="s1"):
    return {"session_id": session, "stop_hook_active": False}


@test
def gate_skips_without_manifest(tmp):
    root = make_repo(tmp)
    proc = run_hook("verify_gate.py", stop_event(), home=tmp,
                    env_extra={"CLAUDE_PROJECT_DIR": str(root)})
    assert proc.returncode == 0, proc.stderr


@test
def gate_skips_broken_manifest_but_logs(tmp):
    root = make_repo(tmp)
    (root / ".claude" / "verify.json").write_text("{oops", encoding="utf-8")
    proc = run_hook("verify_gate.py", stop_event(), home=tmp,
                    env_extra={"CLAUDE_PROJECT_DIR": str(root)})
    assert proc.returncode == 0
    log = (Path(tmp) / "hook-health.log").read_text(encoding="utf-8")
    assert "manifest" in log


@test
def gate_skips_untrusted_manifest(tmp):
    root = make_repo(tmp)
    marker = root / "marker.txt"
    (root / ".claude" / "verify.json").write_text(
        json.dumps({"command": f"echo x>>{marker}"}), encoding="utf-8")
    proc = run_hook("verify_gate.py", stop_event(), home=tmp,
                    env_extra={"CLAUDE_PROJECT_DIR": str(root)})
    assert proc.returncode == 0
    assert not marker.exists(), "未信任的 manifest 絕不可執行命令"
    log = (Path(tmp) / "hook-health.log").read_text(encoding="utf-8")
    assert "untrusted-manifest" in log


@test
def gate_skips_stale_trust_after_manifest_change(tmp):
    root = make_repo(tmp)
    marker = root / "marker.txt"
    write_manifest(root, tmp, "echo trusted")
    (root / ".claude" / "verify.json").write_text(
        json.dumps({"command": f"echo x>>{marker}"}), encoding="utf-8")
    proc = run_hook("verify_gate.py", stop_event(), home=tmp,
                    env_extra={"CLAUDE_PROJECT_DIR": str(root)})
    assert proc.returncode == 0
    assert not marker.exists(), "manifest 內容變更後未重註冊，不可執行"


@test
def gate_green_writes_evidence(tmp):
    root = make_repo(tmp)
    marker = root / "marker.txt"
    (root / "src.txt").write_text("v2\n", encoding="utf-8")  # dirty → 必跑
    write_manifest(root, tmp, f"echo x>>{marker}")
    proc = run_hook("verify_gate.py", stop_event(), home=tmp,
                    env_extra={"CLAUDE_PROJECT_DIR": str(root)})
    assert proc.returncode == 0, proc.stderr
    assert marker.exists(), "綠燈命令應被執行"
    ev = json.loads((root / ".claude" / "loop-gate-evidence.json").read_text(encoding="utf-8"))
    assert ev["result"] == "green"


@test
def gate_red_blocks_with_tail(tmp):
    root = make_repo(tmp)
    (root / "src.txt").write_text("v2\n", encoding="utf-8")
    write_manifest(root, tmp, "echo BOOM_DETAIL&& exit 1")
    proc = run_hook("verify_gate.py", stop_event(), home=tmp,
                    env_extra={"CLAUDE_PROJECT_DIR": str(root)})
    assert proc.returncode == 2, f"紅燈應 exit 2, got {proc.returncode}"
    assert "1/3" in proc.stderr
    assert "BOOM_DETAIL" in proc.stderr


@test
def gate_third_strike_lets_through(tmp):
    root = make_repo(tmp)
    (root / "src.txt").write_text("v2\n", encoding="utf-8")
    write_manifest(root, tmp, "exit 1")
    env = {"CLAUDE_PROJECT_DIR": str(root)}
    r1 = run_hook("verify_gate.py", stop_event(), home=tmp, env_extra=env)
    r2 = run_hook("verify_gate.py", stop_event(), home=tmp, env_extra=env)
    r3 = run_hook("verify_gate.py", stop_event(), home=tmp, env_extra=env)
    assert (r1.returncode, r2.returncode) == (2, 2)
    assert r3.returncode == 0, "第 3 次應放行"
    assert "放行" in r3.stderr
    r4 = run_hook("verify_gate.py", stop_event(), home=tmp, env_extra=env)
    assert r4.returncode == 2, "放行後 strikes 應歸零、重新計數"


@test
def gate_timeout_fails_open(tmp):
    root = make_repo(tmp)
    (root / "src.txt").write_text("v2\n", encoding="utf-8")
    write_manifest(root, tmp, "ping -n 6 127.0.0.1 >nul", timeoutSec=1)
    proc = run_hook("verify_gate.py", stop_event(), home=tmp,
                    env_extra={"CLAUDE_PROJECT_DIR": str(root)})
    assert proc.returncode == 0, "timeout 應 fail-open"
    log = (Path(tmp) / "hook-health.log").read_text(encoding="utf-8")
    assert "timeout" in log


@test
def gate_fast_path_skips_rerun(tmp):
    root = make_repo(tmp)
    marker = root / "marker.txt"
    (root / "src.txt").write_text("v2\n", encoding="utf-8")
    write_manifest(root, tmp, f"echo x>>{marker}")
    env = {"CLAUDE_PROJECT_DIR": str(root)}
    run_hook("verify_gate.py", stop_event(), home=tmp, env_extra=env)
    lines_after_first = len(marker.read_text(encoding="utf-8").splitlines())
    run_hook("verify_gate.py", stop_event(), home=tmp, env_extra=env)
    lines_after_second = len(marker.read_text(encoding="utf-8").splitlines())
    assert lines_after_first == 1
    assert lines_after_second == 1, "狀態沒變就不該重跑命令"


@test
def gate_reruns_after_code_change(tmp):
    root = make_repo(tmp)
    marker = root / "marker.txt"
    (root / "src.txt").write_text("v2\n", encoding="utf-8")
    write_manifest(root, tmp, f"echo x>>{marker}")
    env = {"CLAUDE_PROJECT_DIR": str(root)}
    run_hook("verify_gate.py", stop_event(), home=tmp, env_extra=env)
    (root / "src.txt").write_text("v3\n", encoding="utf-8")
    run_hook("verify_gate.py", stop_event(), home=tmp, env_extra=env)
    assert len(marker.read_text(encoding="utf-8").splitlines()) >= 2, "改碼後應重跑"


@test
def gate_clean_tree_writes_baseline(tmp):
    root = make_repo(tmp)  # 乾淨：marker 命令若被執行就是錯
    marker = root / "marker.txt"
    write_manifest(root, tmp, f"echo x>>{marker}")
    git(root, "add", ".claude/verify.json")
    git(root, "commit", "-q", "-m", "manifest")  # 讓樹保持乾淨
    proc = run_hook("verify_gate.py", stop_event(), home=tmp,
                    env_extra={"CLAUDE_PROJECT_DIR": str(root)})
    assert proc.returncode == 0
    assert not marker.exists(), "乾淨樹＋無 evidence 不應冷跑驗證"
    ev = json.loads((root / ".claude" / "loop-gate-evidence.json").read_text(encoding="utf-8"))
    assert ev["result"] == "assumed-baseline"
    proc2 = run_hook("verify_gate.py", stop_event(), home=tmp,
                     env_extra={"CLAUDE_PROJECT_DIR": str(root)})
    assert proc2.returncode == 0 and not marker.exists(), "baseline 之後快路徑應生效"


@test
def gate_non_git_runs_every_time(tmp):
    root = Path(tmp) / "plain"
    (root / ".claude").mkdir(parents=True)
    marker = root / "marker.txt"
    write_manifest(root, tmp, f"echo x>>{marker}")
    env = {"CLAUDE_PROJECT_DIR": str(root)}
    run_hook("verify_gate.py", stop_event(), home=tmp, env_extra=env)
    run_hook("verify_gate.py", stop_event(), home=tmp, env_extra=env)
    assert len(marker.read_text(encoding="utf-8").splitlines()) == 2, "非 git 專案每次 stop 都跑"


@test
def failure_log_appends_jsonl(tmp):
    event = {"session_id": "s9", "tool_name": "Bash", "error": "command not found: foo"}
    proc = run_hook("failure_log.py", event, home=tmp)
    assert proc.returncode == 0, proc.stderr
    lines = (Path(tmp) / "loop-gate" / "tool-failures.jsonl").read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    assert entry["tool_name"] == "Bash"
    assert "not found" in entry["error"]


@test
def report_health_summarizes_recent(tmp):
    log = Path(tmp) / "hook-health.log"
    now_ts = __import__("time").strftime("%Y-%m-%dT%H:%M:%S")
    log.write_text(
        json.dumps({"ts": "2000-01-01T00:00:00", "hook": "old", "error": "ancient"}) + "\n" +
        json.dumps({"ts": now_ts, "hook": "verify_gate", "error": "boom"}) + "\n",
        encoding="utf-8")
    proc = run_hook("report_health.py", {"hook_event_name": "SessionStart"}, home=tmp)
    assert proc.returncode == 0
    assert "1 次 hook 失敗" in proc.stdout
    assert "verify_gate" in proc.stdout


@test
def report_health_silent_when_clean(tmp):
    proc = run_hook("report_health.py", {"hook_event_name": "SessionStart"}, home=tmp)
    assert proc.returncode == 0
    assert proc.stdout.strip() == "", "無失敗時零噪音"


# ---------- B1：信任過的 verify.json 被改時要讓使用者看到 ----------

def stdout_json(proc):
    """hook stdout 若是 JSON 物件就解析回來，空白則回 None。"""
    text = proc.stdout.strip()
    return json.loads(text) if text else None


@test
def b1_unregistered_manifest_stays_silent(tmp):
    root = make_repo(tmp)
    (root / ".claude" / "verify.json").write_text(
        json.dumps({"command": "echo hi"}), encoding="utf-8")
    proc = run_hook("verify_gate.py", stop_event(), home=tmp,
                    env_extra={"CLAUDE_PROJECT_DIR": str(root)})
    assert proc.returncode == 0
    assert proc.stdout.strip() == "", f"未註冊的 root 不該顯示訊息, got {proc.stdout!r}"


@test
def b1_changed_manifest_warns_once_per_session(tmp):
    root = make_repo(tmp)
    marker = root / "marker.txt"
    write_manifest(root, tmp, "echo trusted")
    (root / ".claude" / "verify.json").write_text(
        json.dumps({"command": f"echo x>>{marker}"}), encoding="utf-8")
    env = {"CLAUDE_PROJECT_DIR": str(root)}
    first = run_hook("verify_gate.py", stop_event("b1"), home=tmp, env_extra=env)
    assert first.returncode == 0
    out = stdout_json(first)
    assert out and "systemMessage" in out, f"應輸出 systemMessage, got {first.stdout!r}"
    assert "verify.json" in out["systemMessage"] and "trust_manifest.py" in out["systemMessage"]
    assert "decision" not in out, "B1 只警告，不擋"
    assert not marker.exists(), "改過的 manifest 仍不可執行"
    second = run_hook("verify_gate.py", stop_event("b1"), home=tmp, env_extra=env)
    assert second.stdout.strip() == "", "同一 session 只顯示一次"
    other = run_hook("verify_gate.py", stop_event("b1-other"), home=tmp, env_extra=env)
    assert stdout_json(other) and "systemMessage" in stdout_json(other), "新 session 要再顯示"


# ---------- e2e gate ----------

def make_code_repo(tmp):
    root = Path(tmp) / "app"
    root.mkdir(parents=True)
    (root / "main.py").write_text("print('hi')\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "init")
    return root


def write_code(root, rel, n):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"x{i} = {i}\n" for i in range(n)), encoding="utf-8")


def write_transcript(tmp, entries, name="t.jsonl"):
    path = Path(tmp) / name
    path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
    return path


def tool_use(name, inp):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "toolu_1", "name": name, "input": inp}]}}


def user_text(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def assistant_text(text):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "text", "text": text}]}}


def e2e_config(home, **cfg):
    d = Path(home) / "loop-gate"
    d.mkdir(parents=True, exist_ok=True)
    (d / "e2e_gate.json").write_text(json.dumps(cfg), encoding="utf-8")


def e2e_stop(root, transcript, session="e1", active=False, last=None):
    ev = {"session_id": session, "cwd": str(root), "transcript_path": str(transcript),
          "hook_event_name": "Stop", "stop_hook_active": active}
    if last is not None:
        ev["last_assistant_message"] = last
    return ev


def e2e_log(home):
    path = Path(home) / "loop-gate" / "e2e-gate.jsonl"
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def run_e2e(event_name, event, home):
    return run_hook("e2e_gate.py", event, home=home, args=["--event", event_name])


@test
def e2e_below_threshold_does_nothing(tmp):
    root = make_code_repo(tmp)
    write_code(root, "src/a.py", 10)
    tr = write_transcript(tmp, [])
    proc = run_e2e("stop", e2e_stop(root, tr), tmp)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""
    assert e2e_log(tmp) == [], "門檻以下不寫紀錄"


@test
def e2e_excluded_files_do_not_count(tmp):
    root = make_code_repo(tmp)
    write_code(root, "README.md", 200)
    write_code(root, "docs/guide.py", 200)
    write_code(root, "tests/test_a.py", 200)
    write_code(root, "src/a.test.js", 200)
    write_code(root, "src/b_test.go", 200)
    write_code(root, "src/c.spec.ts", 200)
    write_code(root, "package-lock.json", 200)
    (root / "logo.png").write_bytes(b"\x89PNG\x00\x00" * 500)
    tr = write_transcript(tmp, [])
    proc = run_e2e("stop", e2e_stop(root, tr), tmp)
    assert proc.returncode == 0
    assert e2e_log(tmp) == [], f"排除清單內的檔不該算進程式碼, got {e2e_log(tmp)}"


@test
def e2e_file_count_threshold_triggers(tmp):
    root = make_code_repo(tmp)
    for name in ("a.py", "b.py", "c.py"):
        write_code(root, f"src/{name}", 2)
    tr = write_transcript(tmp, [])
    run_e2e("stop", e2e_stop(root, tr), tmp)
    log = e2e_log(tmp)
    assert len(log) == 1 and log[0]["files"] == 3 and log[0]["lines"] == 6, log


@test
def e2e_observe_logs_and_notices_once(tmp):
    root = make_code_repo(tmp)
    write_code(root, "src/a.py", 50)
    tr = write_transcript(tmp, [])
    first = run_e2e("stop", e2e_stop(root, tr), tmp)
    assert first.returncode == 0, first.stderr
    out = stdout_json(first)
    assert out and "decision" not in out, "observe 不可擋"
    assert "50" in out["systemMessage"] and "/verify" in out["systemMessage"], out
    log = e2e_log(tmp)
    assert len(log) == 1
    rec = log[0]
    assert rec["session"] == "e1" and rec["lines"] == 50 and rec["files"] == 1
    assert rec["would_block"] is True and rec["has_verify_skill"] is False
    assert Path(rec["repo"]).resolve() == root.resolve()
    second = run_e2e("stop", e2e_stop(root, tr), tmp)
    assert second.stdout.strip() == "", "同 session 同 repo 只提醒一次"
    assert len(e2e_log(tmp)) == 2, "紀錄照寫"


@test
def e2e_observe_silent_when_verify_skill_exists(tmp):
    root = make_code_repo(tmp)
    skill = root / ".claude" / "skills" / "verify" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# verify\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "skill")
    write_code(root, "src/a.py", 50)
    proc = run_e2e("stop", e2e_stop(root, write_transcript(tmp, [])), tmp)
    assert proc.stdout.strip() == "", "有 verify skill 時 observe 不打擾"
    assert e2e_log(tmp)[0]["has_verify_skill"] is True


@test
def e2e_evidence_lets_through(tmp):
    root = make_code_repo(tmp)
    write_code(root, "src/a.py", 50)
    e2e_config(tmp, mode="enforce")
    cases = {
        "skill run": [tool_use("Skill", {"skill": "run"})],
        "skill verify": [tool_use("Skill", {"skill": "verify", "args": "x"})],
        "plugin verify": [tool_use("Skill", {"skill": "foo:verify"})],
        "agent verifier": [tool_use("Agent", {"subagent_type": "verifier", "prompt": "p"})],
        "read verify skill": [tool_use("Read", {"file_path": str(root / ".claude" / "skills" / "verify" / "SKILL.md")})],
        "user /verify": [user_text("<command-message>verify</command-message>\n<command-name>/verify</command-name>")],
        "transcript Verified": [assistant_text("做完了\nVerified: 跑了 main.py")],
    }
    for i, (label, entries) in enumerate(cases.items()):
        tr = write_transcript(tmp, entries, name=f"t{i}.jsonl")
        proc = run_e2e("stop", e2e_stop(root, tr, session=f"ev{i}"), tmp)
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", f"{label} 應算驗過, got {proc.stdout!r}"
    assert e2e_log(tmp) == [], "驗過就不記錄"
    # 不算數的近似值：別的 skill、tool_result 裡出現的字串
    tr = write_transcript(tmp, [
        tool_use("Skill", {"skill": "runner"}),
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1",
             "content": "<command-name>/verify</command-name>"}]}},
    ], name="neg.jsonl")
    proc = run_e2e("stop", e2e_stop(root, tr, session="neg"), tmp)
    assert stdout_json(proc) and stdout_json(proc).get("decision") == "block", "近似字串不算證據"


@test
def e2e_verified_line_lets_through(tmp):
    root = make_code_repo(tmp)
    write_code(root, "src/a.py", 50)
    e2e_config(tmp, mode="enforce")
    tr = write_transcript(tmp, [assistant_text("舊訊息")])
    proc = run_e2e("stop", e2e_stop(root, tr, last="改好了。\nVerified: none（純重新命名）"), tmp)
    assert proc.returncode == 0
    assert proc.stdout.strip() == "", proc.stdout
    proc = run_e2e("stop", e2e_stop(root, tr, session="e2", last="說 Verified: 不在行首不算"), tmp)
    assert stdout_json(proc).get("decision") == "block", "Verified: 要在行首"


@test
def e2e_enforce_blocks_twice_then_allows(tmp):
    root = make_code_repo(tmp)
    write_code(root, "src/a.py", 50)
    e2e_config(tmp, mode="enforce")
    tr = write_transcript(tmp, [])
    outs = [run_e2e("stop", e2e_stop(root, tr), tmp) for _ in range(3)]
    assert all(p.returncode == 0 for p in outs), [p.stderr for p in outs]
    d1, d2 = stdout_json(outs[0]), stdout_json(outs[1])
    assert d1["decision"] == "block" and d2["decision"] == "block"
    assert "Verified: none" in d1["reason"] and ".claude/skills/verify/SKILL.md" in d1["reason"]
    d3 = stdout_json(outs[2])
    assert not d3 or d3.get("decision") != "block", "第三次放行"
    assert [r["would_block"] for r in e2e_log(tmp)] == [True, True, True]


@test
def e2e_stop_hook_active_passes(tmp):
    root = make_code_repo(tmp)
    write_code(root, "src/a.py", 50)
    e2e_config(tmp, mode="enforce")
    proc = run_e2e("stop", e2e_stop(root, write_transcript(tmp, []), active=True), tmp)
    assert proc.returncode == 0 and proc.stdout.strip() == ""
    assert e2e_log(tmp) == []


@test
def e2e_non_git_and_off_mode_pass(tmp):
    plain = Path(tmp) / "plain"
    plain.mkdir()
    write_code(plain, "a.py", 100)
    proc = run_e2e("stop", e2e_stop(plain, write_transcript(tmp, [])), tmp)
    assert proc.returncode == 0 and proc.stdout.strip() == "" and e2e_log(tmp) == []
    root = make_code_repo(tmp)
    write_code(root, "src/a.py", 100)
    e2e_config(tmp, mode="off")
    proc = run_e2e("stop", e2e_stop(root, write_transcript(tmp, [])), tmp)
    assert proc.returncode == 0 and proc.stdout.strip() == "" and e2e_log(tmp) == []


@test
def e2e_session_start_baseline_counts_commits(tmp):
    root = make_code_repo(tmp)
    sessions = Path(tmp) / "loop-gate" / "e2e_sessions.json"
    sessions.parent.mkdir(parents=True, exist_ok=True)
    sessions.write_text(json.dumps({"stale": {"repo": "x", "head": "y", "ts": 0}}), encoding="utf-8")
    proc = run_e2e("session-start", {"session_id": "e1", "cwd": str(root), "source": "startup"}, tmp)
    assert proc.returncode == 0 and proc.stdout.strip() == "", proc.stdout
    data = json.loads(sessions.read_text(encoding="utf-8"))
    assert "stale" not in data, "超過 7 天的紀錄要清掉"
    assert Path(data["e1"]["repo"]).resolve() == root.resolve() and len(data["e1"]["head"]) >= 40
    write_code(root, "src/a.py", 45)
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "feature")  # 已 commit 的改動也要算
    run_e2e("stop", e2e_stop(root, write_transcript(tmp, [])), tmp)
    log = e2e_log(tmp)
    assert len(log) == 1 and log[0]["lines"] == 45, log


@test
def e2e_commit_without_verified(tmp):
    root = make_code_repo(tmp)
    oss = Path(tmp) / "oss" / "lib"
    oss.mkdir(parents=True)
    git(oss, "init", "-q")
    e2e_config(tmp, mode="observe", skip_commit_roots=[str(Path(tmp) / "oss")])
    tr = write_transcript(tmp, [])

    def bash(cwd, cmd, session="c1"):
        return {"session_id": session, "cwd": str(cwd), "transcript_path": str(tr),
                "hook_event_name": "PreToolUse", "tool_name": "Bash",
                "tool_input": {"command": cmd}}

    proc = run_e2e("pre-bash", bash(root, 'git commit -m "feat: x"'), tmp)
    assert proc.returncode == 0 and proc.stdout.strip() == "", "observe 不擋"
    log = e2e_log(tmp)
    assert len(log) == 1 and log[0]["check"] == "commit-without-verified" and log[0]["would_block"] is True
    run_e2e("pre-bash", bash(oss, 'git commit -m "fix"'), tmp)
    assert len(e2e_log(tmp)) == 1, "oss 底下照上游慣例，跳過"
    run_e2e("pre-bash", bash(root, 'git commit -m "feat: x\n\nVerified: ran app"'), tmp)
    run_e2e("pre-bash", bash(root, "git log --oneline"), tmp)
    assert len(e2e_log(tmp)) == 1, "有 Verified 或不是 commit 就不記"
    e2e_config(tmp, mode="enforce", skip_commit_roots=[str(Path(tmp) / "oss")])
    proc = run_e2e("pre-bash", bash(root, 'git -C . commit -m "feat"'), tmp)
    out = stdout_json(proc)
    hso = out["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse" and hso["permissionDecision"] == "deny"
    assert "Verified:" in hso["permissionDecisionReason"]


@test
def e2e_pr_create_without_code_review(tmp):
    root = make_code_repo(tmp)

    def bash(tr, session="p1"):
        return {"session_id": session, "cwd": str(root), "transcript_path": str(tr),
                "hook_event_name": "PreToolUse", "tool_name": "Bash",
                "tool_input": {"command": "gh pr create --title t --body b"}}

    bare = write_transcript(tmp, [], name="bare.jsonl")
    proc = run_e2e("pre-bash", bash(bare), tmp)
    assert proc.returncode == 0 and proc.stdout.strip() == ""
    log = e2e_log(tmp)
    assert len(log) == 1 and log[0]["check"] == "pr-without-code-review"
    reviewed = write_transcript(tmp, [tool_use("Skill", {"skill": "code-review"})], name="rv.jsonl")
    typed = write_transcript(tmp, [user_text("<command-name>/code-review</command-name>")], name="ty.jsonl")
    run_e2e("pre-bash", bash(reviewed), tmp)
    run_e2e("pre-bash", bash(typed), tmp)
    assert len(e2e_log(tmp)) == 1, "跑過 code-review 就不記"
    e2e_config(tmp, mode="enforce")
    out = stdout_json(run_e2e("pre-bash", bash(bare), tmp))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "/code-review" in out["hookSpecificOutput"]["permissionDecisionReason"]


@test
def e2e_fails_open_on_garbage(tmp):
    proc = run_hook("e2e_gate.py", {}, home=tmp, args=["--event", "stop"])
    assert proc.returncode == 0
    root = make_code_repo(tmp)
    write_code(root, "src/a.py", 50)
    e2e_config(tmp, mode="enforce")
    ev = e2e_stop(root, Path(tmp) / "missing.jsonl")
    proc = run_e2e("stop", ev, tmp)
    assert proc.returncode == 0, "transcript 不見了也不能讓 hook 爆"
    proc = run_hook("e2e_gate.py", {}, home=tmp, args=["--event", "bogus"])
    assert proc.returncode == 0
    log = (Path(tmp) / "hook-health.log").read_text(encoding="utf-8")
    assert "e2e_gate" in log and "bogus" in log


def main():
    failed = []
    for fn in TESTS:
        tmp = tempfile.mkdtemp(prefix="loopgate-")
        try:
            fn(Path(tmp))
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
            failed.append(fn.__name__)
        except Exception as e:  # noqa: BLE001 - selftest 要報所有爆炸
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
            failed.append(fn.__name__)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"{len(TESTS) - len(failed)}/{len(TESTS)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
