# Quota Pacer CHANGELOG

## 0.3.3 — 2026-11-13
token 檔換過就免冷卻。

- `refresh_usage()`：`.credentials.json` 的修改時間比上次嘗試的冷卻標記新時，不套 60 秒冷卻。401 之後去 PowerShell 跑完 CLI，馬上重讀就會重拉，不用等也不用 `--force`。
- token 檔沒動時冷卻照舊。
- 驗證：「401 → 換 token → 2 秒內重讀」從被冷卻擋下變成拉到新資料；12 個情境回歸全過（含 token 沒換時仍被冷卻擋下）。

## 0.3.2 — 2026-11-13
刷新嘗試留紀錄，事後查得到當時為什麼沒拉到。

- `refresh_usage()` 每次嘗試寫一行 JSONL 到 `~/.claude/quota-pacer/refresh.log`（可用 `QP_REFRESH_LOG` 改路徑）：時間、status、HTTP code、`expires_at`、是否 `force`、pid、呼叫的腳本、冷卻標記的年齡。被冷卻擋下的也記。不記 token 與回應內容。超過 64KB 只留後半。
- 起因：11-13 09:48:58 token 已有效，`read_usage.py` 仍回舊資料，45 秒後直接呼叫 `fetch_usage()` 成功，當時原因被吞掉。
- 重現結果：「401 失敗後 60 秒內 token 修好再讀」會被冷卻擋下並回舊資料，症狀相同（0.3.1 起會印「冷卻中」）。09:48:58 那次是不是這個原因無法確認，當時的冷卻標記已被後來的嘗試蓋掉。
- 驗證：12 個情境回歸全過，紀錄檔裡搜不到測試用的假 token 字串。

## 0.3.1 — 2026-11-13
刷新失敗不再無聲回舊資料：分得出原因，印得出處置。

- 起因：桌面 App 的 session 自己換 token、不寫回 `~/.claude/.credentials.json`，檔裡的 access token 約 8 小時後過期，`fetch_usage()` 回 401；`refresh_usage()` 用 `except Exception: return None` 吞掉，`read_usage.py` 印出 `5h None% | weekly None%` 且 exit 0。
- `pace_core`：失敗改丟 `RefreshFail(status)`，`refresh_usage()` 把結果記在 `LAST_REFRESH`。status 有 `cooldown`、`auth`（401/403，對照 `expiresAt` 分成已過期與未過期）、`http`、`network`、`cred`、`parse`、`empty`、`write`、`error`。`refresh_advice()` 轉成一行「原因 → 處置」，不含 token 值。
- token 過期的處置只有提示：請 Stan 在一般 PowerShell 跑一次 `claude -p "ok" --model claude-haiku-5-5`。不自己做 OAuth refresh，也不寫 `.credentials.json`。
- `usable()`：5h 與 weekly 兩條 pct 都是 None 的檔不算讀數。這種檔就算 ts 很新也會觸發重拉；endpoint 回 200 但兩條都空時不寫檔。
- `read_usage.py`：讀數不可用時第一行印 `UNUSABLE 原因 → 處置`，舊資料另起一行標明別拿來記基準；exit 4（完全沒檔是 3）。`--json` 加 `usable`、`refresh`、`advice`。新增 `--force` 跳過冷卻。單一條是 None 時印 `5h n/a`（endpoint 目前就不回 5h）。
- `eval_pace.py`：STALE 的註記帶上同一行原因。
- 驗證：假 credentials 加本機假 endpoint 跑 12 個情境全過（401 過期／未過期、500、連線被拒、冷卻、`--force`、全 None 新鮮檔、200 全空、缺 credentials、eval_pace）。

## 0.3.0 — 2026-08-13
脫離 CLI statusline：用量自己拉，任何 harness（桌面 App／SDK／headless）都能用用量 guard。

- `pace_core.fetch_usage()`/`refresh_usage()`：讀 `~/.claude/.credentials.json` 的 OAuth token，直接打 `api.anthropic.com/api/oauth/usage`，寫回 `usage-state.json`（原子寫、失敗保留舊檔、60s 冷卻 `QP_REFRESH_COOLDOWN_SEC`）。
- STALE/MISSING 自動刷新：`read_usage.py` 與 `eval_pace.py` 讀到過舊或缺檔會先自拉一次；「請去 CLI 敲 Enter」流程淘汰。`hardstop_guard`（PreToolUse hook）刻意不刷新，避免每次工具呼叫揹網路延遲。
- **per-model scoped weekly guard**（roadmap 兌現）：endpoint 的 `limits[]` 裡 `weekly_scoped`（如 Fable）寫進 `usage-state.json` 的 `scoped`；`u0.scoped` 記基準後，`evaluate` 對每條 scoped 套同一門檻公式，trigger 顯示 `weekly[fable]`。`5h-override` 不豁免 scoped（本質是 weekly）。
- statusline 蓋檔防護：eval 發現 u0 有 scoped 基準但檔案沒 scoped 資料時補刷一次（吃冷卻）。
- 新參數：`QP_CRED_FILE`、`QP_USAGE_URL`、`QP_REFRESH_COOLDOWN_SEC`(60)。
- 驗證：refresh 實打 endpoint 綠、evaluate 合成資料 7 case 綠（含舊版抓不到的紅燈對照）、STALE 自動刷新實測綠。

## 0.2.0 — 2026-07-18
新增時間 guard（time-box）：跟用量 guard 並存、先到者觸發。
- 時間 guard 只靠牆鐘，不碰 statusline/用量，所以在讀不到 usage 的環境（SDK/桌面 App）照樣有效。
- `active.json` 可帶 `minutes`（時間上限）：wind-down 在 `minutes−GRACE−NOTICE`、hard-stop 在 `minutes−GRACE`（留 GRACE 分寫交接）、emergency 在 `minutes` 整（hook 硬擋死線）。
- hook 與 eval 重構：用量讀不到只跳過用量那條，時間 guard 照擋；沒有任一有效 guard 時保守 HARDSTOP。
- `/quota-pace [<N>m] …`、SKILL 支援純時間盒（可省 u0）。
- 新參數：`QP_GRACE_MIN`(3)、`QP_NOTICE_MIN`(2)。
- 防禦：`started`/`minutes` 非數字時安全略過（`_num`），不再拋未捕捉例外（verifier 抓出）。

## 0.1.0 — 2026-07-18
初版。額度感知任務節奏器：邊做邊看用量、接近限制前主動收手並寫交接。只在互動式 CLI 有效。

- 門檻模型：每條限制 session 起點記 U0，available=100−U0，wind-down 剩餘≤10%×avail、hard-stop 剩餘≤max(5%×avail, FLOOR=3pp)、EMERGENCY 剩餘≤1pp。5h + weekly 先到者觸發。
- `5h-override` 模式：忽略 5h、只管 weekly。
- 三層：skill 逐塊裁決（收手 / 停+寫交接，未完成呼叫 handoff skill）；PreToolUse hook 只在 EMERGENCY 擋（刻意不擋 hard-stop，保護寫交接的 buffer）；`active.json` 當啟用旗標。
- 資料源：statusline.sh 正式輸出 `~/.claude/usage-state.json`（扶正原本的 debug dump 副作用）。
- 元件：pace_core.py / read_usage.py / eval_pace.py / hooks/hardstop_guard.py / skills/quota-pacer / commands/quota-pace（`/quota-pace` 斜線指令）。
- 驗證：Python 單元 + hook 四情境全綠；fresh verifier 獨立複驗 CONFIRMED；Stan 互動式 CLI 實測兩輪通過（both→HARDSTOP 5h、5h-override→HARDSTOP weekly、收手+交接+清理全對）。

## Roadmap
- 同一 session 靠消耗速率預測，無縫接下一個 5h 窗續跑（免重開 session、免跨 session handoff）。
- 全自動精準 pause N 分鐘再自醒。
- FLOOR 實際 pp 值校準；null-pct（statusline 沒帶 rate_limits）是否改為保守處理。
- statusline.sh 也寫 scoped（目前互動 CLI 下它會用無 scoped 版本蓋檔，靠補刷 workaround）。
