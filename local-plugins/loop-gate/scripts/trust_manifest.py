"""註冊某專案 verify.json 為受信任（寫入 sha256 到 trusted.json）。

用法：py trust_manifest.py <project_root>
前置條件：<project_root>/.claude/verify.json 已存在且你已人工看過 command 內容。
"""
import hashlib
import json
import sys
from pathlib import Path

import hook_health


def main():
    if len(sys.argv) != 2:
        print("用法：py trust_manifest.py <project_root>", file=sys.stderr)
        sys.exit(1)
    root = Path(sys.argv[1]).resolve()
    manifest = root / ".claude" / "verify.json"
    if not manifest.exists():
        print(f"找不到 {manifest}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("command"), str):
        print("verify.json 缺 command 字串欄位", file=sys.stderr)
        sys.exit(1)
    trusted = hook_health.state_dir() / "trusted.json"
    registry = {}
    if trusted.exists():
        registry = json.loads(trusted.read_text(encoding="utf-8"))
    registry[str(root)] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    trusted.write_text(json.dumps(registry, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    print(f"已信任 {root} 的 verify.json（command: {data['command']}）")


if __name__ == "__main__":
    main()
