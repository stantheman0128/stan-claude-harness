"""loop-gate Stop hook：收工前由機器驗證，不經過模型。

決策表見 docs/specs/2026-07-11-loop-gate-design.md。
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import hook_health

TAIL_LINES = 40
MAX_STRIKES = 3


def read_event():
    try:
        return json.load(sys.stdin)
    except ValueError:
        return {}


def project_root(event):
    root = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd")
    return Path(root) if root else None


def load_manifest(root):
    path = root / ".claude" / "verify.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("command"), str):
            raise ValueError("缺 command 字串欄位")
        return data
    except (ValueError, OSError) as e:
        hook_health.log_failure("verify_gate", f"manifest 解析失敗 {path}: {e}")
        return None


def manifest_trusted(root):
    path = root / ".claude" / "verify.json"
    trusted_file = hook_health.state_dir() / "trusted.json"
    try:
        registry = json.loads(trusted_file.read_text(encoding="utf-8")) if trusted_file.exists() else {}
    except (ValueError, OSError):
        registry = {}
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if registry.get(str(root.resolve())) == digest:
        return True
    hook_health.log_failure(
        "verify_gate",
        f"untrusted-manifest: {path} 未註冊或內容已變，gate 跳過。"
        f"確認 command 內容安全後執行 trust_manifest.py 重新信任。")
    return False


def _git(root, *args):
    try:
        out = subprocess.run(["git", "-C", str(root), *args],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout if out.returncode == 0 else None


def _strip_evidence_lines(text):
    return "\n".join(
        line for line in text.splitlines()
        if "loop-gate-evidence.json" not in line)


def fingerprint(root):
    head = _git(root, "rev-parse", "HEAD")
    if head is None:
        return None  # 非 git repo → 視為狀態永遠在變
    status = _strip_evidence_lines(_git(root, "status", "--porcelain") or "")
    # 注意：用完整 diff 而非 --stat——--stat 只報行數，內容不同但行數相同的
    # 編輯（如 v2→v3 都是改同一行）會被誤判成同一狀態，快路徑會漏跑驗證。
    diffstat = _strip_evidence_lines(_git(root, "diff", "HEAD") or "")
    return hashlib.sha1((head + status + diffstat).encode("utf-8")).hexdigest()


def evidence_path(root):
    return root / ".claude" / "loop-gate-evidence.json"


def load_evidence(root):
    try:
        return json.loads(evidence_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save_evidence(root, fp, result, command):
    path = evidence_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "fingerprint": fp,
        "result": result,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "command": command,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def _strikes_path(session_id):
    d = hook_health.state_dir() / "strikes"
    d.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(session_id))[:64]
    return d / f"{safe or 'unknown'}.json"


def get_strikes(session_id):
    try:
        return int(json.loads(_strikes_path(session_id).read_text(encoding="utf-8"))["count"])
    except (OSError, ValueError, KeyError):
        return 0


def set_strikes(session_id, count):
    _strikes_path(session_id).write_text(json.dumps({"count": count}), encoding="utf-8")


def clear_strikes(session_id):
    try:
        _strikes_path(session_id).unlink()
    except OSError:
        pass


def run_verify(root, manifest, session_id):
    command = manifest["command"]
    timeout_sec = int(manifest.get("timeoutSec", 300))
    cwd = root / manifest.get("cwd", ".")
    try:
        # shell=True 是刻意的：command 是信任註冊表核可過的 shell 語句（見 spec 安全模型）
        run = subprocess.run(command, shell=True, cwd=str(cwd),
                             capture_output=True, text=True, timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        hook_health.log_failure("verify_gate", f"verify 命令 timeout({timeout_sec}s): {command}")
        sys.exit(0)

    if run.returncode == 0:
        save_evidence(root, fingerprint(root), "green", command)
        clear_strikes(session_id)
        sys.exit(0)

    strikes = get_strikes(session_id) + 1
    if strikes >= MAX_STRIKES:
        clear_strikes(session_id)
        hook_health.log_failure("verify_gate", f"連續 {MAX_STRIKES} 次紅燈後放行: {command}")
        print(f"[loop-gate] 驗證連續 {MAX_STRIKES} 次未過，放行但已標記失敗，請人工介入。"
              f"命令：{command}", file=sys.stderr)
        sys.exit(0)
    set_strikes(session_id, strikes)
    tail = "\n".join(
        ((run.stdout or "") + "\n" + (run.stderr or "")).splitlines()[-TAIL_LINES:])
    print(f"[loop-gate] 驗證未過（第 {strikes}/{MAX_STRIKES} 次），修好才能收工。"
          f"命令：{command}\n輸出尾段：\n{tail}", file=sys.stderr)
    sys.exit(2)


def main():
    event = read_event()
    if event.get("stop_hook_active"):
        sys.exit(0)
    root = project_root(event)
    if root is None or not root.exists():
        sys.exit(0)
    manifest = load_manifest(root)
    if manifest is None:
        sys.exit(0)
    if not manifest_trusted(root):
        sys.exit(0)
    fp = fingerprint(root)
    evidence = load_evidence(root)
    if fp is not None and evidence \
            and evidence.get("fingerprint") == fp \
            and evidence.get("result") in ("green", "assumed-baseline"):
        sys.exit(0)  # 快路徑：本狀態已驗過
    if fp is not None and evidence is None:
        status = _git(root, "status", "--porcelain")
        if status is not None and _strip_evidence_lines(status).strip() == "":
            save_evidence(root, fp, "assumed-baseline", manifest["command"])
            sys.exit(0)  # 純問答 session 不冷跑全套測試
    session_id = str(event.get("session_id", "unknown"))
    run_verify(root, manifest, session_id)


if __name__ == "__main__":
    hook_health.guard("verify_gate", main)
