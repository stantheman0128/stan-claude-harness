"""收工：刪掉這個 session 自己的 pacer 設定，之後 hook 不再管它。重複跑也沒事。

只刪自己的。別的 session 的設定、全機規則都不動。
舊的共用檔（active.json）只有在它寫明是這個 session 的、或沒寫是誰的時候才刪。
"""
import os
import time

import pace_core as pc

def main():
    sid = pc.env_sid()
    gone = False
    mine = [pc.session_file(sid)] if sid else []
    try:
        legacy = pc.load_active(pc.ACTIVE_FILE)
        owner = legacy.get("session") if isinstance(legacy, dict) else None
        if not sid or not owner or owner == sid:
            mine.append(pc.ACTIVE_FILE)
    except ValueError:
        mine.append(pc.ACTIVE_FILE)  # 壞掉的檔誰都用不了，清掉
    except OSError:
        pass
    for p in mine:
        try:
            os.remove(p)
            gone = True
        except OSError:
            pass
    try:
        os.remove(pc.START_MARK)
    except OSError:
        pass
    # 順手清掉別人忘了收、已經過期的設定檔（hook 本來就不理它們）
    try:
        for name in os.listdir(pc.SESS_DIR):
            p = os.path.join(pc.SESS_DIR, name)
            if time.time() - os.path.getmtime(p) > pc.ACTIVE_MAX_AGE:
                try:
                    a = pc.load_active(p)
                    started = pc._num(a.get("started")) if isinstance(a, dict) else None
                except (OSError, ValueError):
                    started = None
                if not started or time.time() - started > pc.ACTIVE_MAX_AGE:
                    os.remove(p)
    except OSError:
        pass
    print("已收工，pacer 關閉" if gone else "pacer 本來就沒開")

if __name__ == "__main__":
    main()
