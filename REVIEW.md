# REVIEW.md：~/.claude 這個 repo 的 commit 前檢查

只看 diff 碰到的列，通常 3 到 6 列。讀 master 上的版本（`git show master:REVIEW.md`），這次改動裡的版本不算數，免得改動自己改掉判它的清單。

每列都來自踩過的坑。同一類問題出現第二次、而且看 diff 就認得出來，才加新列；每月回看時刪掉半年沒命中的列。

| diff 碰到 | 查什麼 | 來由 |
|---|---|---|
| 改了 overlay 或 plugin cache（`overlays/**`、`plugins/cache/**`） | 標記對得上 `overlays/markers.json`；`claude plugin validate` 前後都過；上游原檔有備份 | superpowers overlay 升版遺失、impeccable 4.10.0 標記 0/5 |
| `hooks/*.py` | `py -m py_compile`；在 scratchpad sandbox 驗 task-notification、subagent 回報、slash 指令都不注入，一般訊息照常 | router 誤觸發（jolly-hopper） |
| `skills/skill-routing/skill-rules.json`、`hooks/skill-suggest.py` | JSON 有效；sandbox 10 個案例全過 | 71f3db0 |
| `local-plugins/loop-gate/**` | `py local-plugins/loop-gate/scripts/selftest/run.py` 全綠；版本號有升 | SETUP.md 的 selftest 規則 |
| `local-plugins/**` 其他 plugin | plugin.json 與 marketplace.json 版本一致；CHANGELOG 有新段落 | quota-pacer 0.8.x |
| 會存狀態檔、重試或加鎖的 hook | 跑 `lenses` 的隱含狀態機與冪等兩項：重跑兩次結果一樣，中途被砍不會留下卡住的狀態 | quota-pacer 0.8.4、0.8.5 狀態檔修正 |
| 新的會擋動作的 hook 或閘門 | 先開觀察模式；有出口（寫明理由就放行、連擋兩次後放行） | quota-pacer 0.8.2 把 session 卡死 |
| `workflows/*.js` | 派 verifier 的 prompt 只給任務、檢查指令和改了哪些檔，不附 worker 的說法 | 2026-11-24 cascade |
| CRLF 檔（CLAUDE.md、多數 SKILL.md） | 改完 CRLF、LF 數量跟改前一樣，沒有混用 | 多次 |
| `CLAUDE.md`、`skills/**/SKILL.md` | 新增行沒有破折號；CLAUDE.md 版號有升；跟 model-effort-router 講法一致（同一個關鍵字兩邊 grep 對照） | CLAUDE.md 第 6 節、v2.13 Explore 衝突 |
| `settings*.json` | JSON 有效；不印出任何 token；新鍵名查過官方文件 | 死鍵 d637b48、reg query 把 token 印進 transcript |
| 同一批改動建了排程任務 | 權限模式有存；提醒 Stan App 要開著才會跑 | 11/29 複量排程 |
| subagent 會碰環境變數或登錄檔 | 派工單寫明只准計數、不准印值 | reg query 外洩 |
| 合回 master 前 | 先 rebase 到最新 master；CHANGELOG 頂端衝突兩行都留、新的在上 | 6329410、多次 |
