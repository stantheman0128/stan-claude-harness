"""selftest 用：故意爆炸，驗證 hook_health.guard 的 fail-open + 記錄行為。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import hook_health  # noqa: E402


def main():
    return 1 / 0


if __name__ == "__main__":
    hook_health.guard("probe", main)
