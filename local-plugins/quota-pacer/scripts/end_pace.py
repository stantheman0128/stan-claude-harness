"""收工：刪掉 active.json，之後 hook 不再管這個 session。重複跑也沒事。"""
import os

import pace_core as pc

def main():
    gone = False
    for p in (pc.ACTIVE_FILE, pc.ACTIVE_FILE + ".tmp", pc.START_MARK):
        try:
            os.remove(p)
            gone = gone or p == pc.ACTIVE_FILE
        except OSError:
            pass
    print("已收工，pacer 關閉" if gone else "pacer 本來就沒開")

if __name__ == "__main__":
    main()
