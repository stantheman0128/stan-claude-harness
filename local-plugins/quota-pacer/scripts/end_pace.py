"""收工：刪掉這個 session 自己的 pacer 設定。重複跑也沒事。

還沒到線就收工（任務做完了），之後 hook 不再管這個 session。
到線才收工（HARDSTOP、EMERGENCY），會留下一個鎖：工具照擋，直到 Stan 親口豁免。
不留鎖的話，到線的 session 跑一次收工就把自己的上限解除了。

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
    hit = ""
    if sid:
        try:
            usage = pc.load_usage()      # 多舊都拿來看：用量只會往上，舊讀數到線就是到線
        except (OSError, ValueError):
            usage = None
        for p in mine:
            a = pc._live(p, sid)
            if a is None:
                continue
            verdict, trigger = pc.evaluate(usage, a)
            if pc.RANK[verdict] >= pc.RANK["HARDSTOP"]:
                hit = trigger or verdict
        if hit and not pc.bypassed(sid):
            pc.lock(sid, hit)
        else:
            hit = ""
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
    if hit:
        print("已收工。上限已到（%s），這個 session 的工具從現在起鎖住，"
              "直到 Stan 本人在對話裡說「豁免」「bypass」「繞過用量限制」這類的話。"
              "把做到哪、還沒做什麼、下次怎麼接寫在回覆裡，結束這一輪。" % hit)
    else:
        print("已收工，pacer 關閉" if gone else "pacer 本來就沒開")

if __name__ == "__main__":
    main()
