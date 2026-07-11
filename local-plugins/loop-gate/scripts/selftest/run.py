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


def run_hook(script, event, home, env_extra=None):
    """以 subprocess 執行 scripts/<script>，stdin 餵 event JSON。"""
    env = os.environ.copy()
    env["LOOP_GATE_HOME"] = str(home)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.update(env_extra or {})
    return subprocess.run(
        [PY, str(SCRIPTS / script)],
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
