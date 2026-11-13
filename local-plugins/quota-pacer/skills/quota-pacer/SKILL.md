---
name: quota-pacer
description: 額度感知的任務節奏器。Stan 用白話給這個 session 設用量上限時就載入，不用等他打斜線指令：例如「不要用超過 5% 的 weekly」「這次最多用 X%」「weekly 到 60% 就停」「別把額度燒光」「用量省著點、快到就收手」。也用於在有限用量下跑較長任務、要邊做邊看用量、接近限制前主動收手並寫交接。觸發詞：不要用超過、最多用、用量上限、額度上限、到 X% 就停、quota pacer、額度感知、邊做邊看用量、燒到快沒之前收手、pace against quota、5h-override、在 weekly 見底前收手。
---

# Quota Pacer

Stan 的用量是每週重置的固定額度，一個 session 燒太多，其他專案就沒得用。這個 skill 讓你在他給的上限內工作：開工記下起點，每做完一段看一次用量，快到線就收手，沒做完就留交接。

Stan 多半不打 `/quota-pace`，而是交代任務時順口講一句上限。聽到就照這份做，不用請他改用指令。

## 先判斷要不要開

一兩個工具呼叫就能答完的事（回答問題、看一個檔、改一行），直接做，回覆裡帶一句「這點用量遠低於你給的上限」就好。開 pacer 本身要五六個工具呼叫，比這種任務還貴。

預期會超過十來個工具呼叫的任務（多檔修改、大範圍掃描、重構、派 subagent）才開。拿不準就開。

## 四個步驟

下面的指令都是完整路徑，照抄就能跑，Bash 和 PowerShell 都行。

### 1. 讀用量

開工前、以及之後每次檢查前都做：

1. 有 `mcp__ccd_session_mgmt__get_usage` 就呼叫它，不帶參數（桌面 App 才有；列在 deferred tools 時先用 ToolSearch 載入）。它走 App 自己的登入，比腳本自己去拉可靠。
2. 回傳可能是結構化欄位，也可能是一段文字。從裡面找每條限額的「已用百分比」，寫進檔：
   ```
   py "C:/Users/stans/.claude/local-plugins/quota-pacer/scripts/write_usage.py" --weekly 49 --scoped fable=52
   ```
   - `--weekly`：全部模型的週限額。
   - `--scoped 名稱=數字`：某個模型專用的週限額，每條一個。名稱用模型的英文名、全小寫（`fable`、`opus`），整個 session 都用同一個名稱，不然開工時記的那條後面會對不上。
   - `--five-hour`：5 小時限額。回傳裡沒有這條就不要給。
   - 工具給的是「剩餘」就先換成已用（100 減它）。重置時間不用給，裁決不看它。
3. 工具不存在、被權限擋、或回報用量不可用：跳過這一步繼續往下。後面的腳本發現檔案過舊會自己去官方 endpoint 拉。

### 2. 開工

```
py "C:/Users/stans/.claude/local-plugins/quota-pacer/scripts/start_pace.py" [--budget 數字 | --cap 數字] [--minutes 數字] [--mode 5h-override]
```

| Stan 的說法 | 意思 | 參數 |
|---|---|---|
| 「不要用超過 5%」「這次最多用 5%」「只給你 5% 的額度」 | 這個 session 最多再花 5 個百分點 | `--budget 5` |
| 「weekly 到 60% 就停」「不要讓 weekly 超過 60%」「停在 60%」 | weekly 的絕對水位 | `--cap 60` |
| 「跑 30 分鐘就停」 | 時間上限，可跟上面併用 | `--minutes 30` |
| 沒講數字，只說「別燒光」「省著點」 | 只防撞到 100% | 都不帶 |
| 「5h 不用管」「只看 weekly」 | 忽略 5 小時限額 | `--mode 5h-override` |

「不要超過 N%」分不出是再花多少還是絕對水位時，用現在的 weekly 用量判斷：

- N 不高於現在用量：只可能是「再花 N」，用 `--budget`。
- 現在用量加 N 超過 100：只可能是絕對水位，用 `--cap`。
- 兩種都說得通：N 小（大約 15 以下）當 `--budget`，N 大當 `--cap`。

不管怎麼選，都在回報裡講明你用了哪種解讀，Stan 看一眼就能糾正。沒講數字的那種，也順便告訴他「沒給數字，所以只防撞到 100%」。

`--budget` 會同時套在 weekly 和每條模型專用的週限額上，各自從自己的起點加，先到的先停。原因是這個 session 用哪個模型，燒的就是那條，而那條通常漲得比全部模型那條快。`--cap` 只管全部模型的 weekly。

腳本會印出每條限制在幾 % 收尾、停手、硬擋。把那幾行濃縮成一兩行轉給 Stan，然後開始做事。

- 印「沒開工」且 exit 4：用量讀不到。把它印的原因原樣轉給 Stan（裡面有處置，例如 token 過期要去 PowerShell 跑一次 CLI）。Stan 有給時間上限就只帶 `--minutes` 重跑，當純時間盒做；沒給就先停下來回報，因為沒有任何東西能告訴你何時該停。
- 印「沒開工」且 exit 2：參數不對（例如 `--cap` 低於現在用量），照訊息修正或回問。

### 3. 邊做邊檢查

把任務切成段落，每做完一段先做步驟 1，再跑：

```
py "C:/Users/stans/.claude/local-plugins/quota-pacer/scripts/eval_pace.py"
```

它印一行，開頭是裁決。把那一行原樣貼給 Stan（這就是他要的進度），再照裁決做：

- `CONTINUE`：做下一段。
- `WINDDOWN`：不開新的大段落，把手上的收到一個乾淨的停點。
- `HARDSTOP`：不接新工作，進步驟 4。
- `EMERGENCY`：已到上限，hook 會擋掉 pacer 腳本以外的所有工具。直接進步驟 4，這時不寫交接檔，交接內容寫在回覆裡。

段落大小跟著預算走，因為兩次檢查之間沒有任何東西攔你：

- 這裡的預算指「上限減掉開工時的用量」，`--budget` 和 `--cap` 都這樣算。預算在 5 個百分點以下時，一段控制在十來個工具呼叫以內。
- 預算小的時候不要一次平行派好幾個 subagent。一次派一個，回來就檢查一次。subagent 的用量算在同一條額度上，而且它跑的時候你看不到。
- 行尾出現 `⚠` 代表某條用量這次沒讀到，那條上限等於沒人看。先重做步驟 1（多半是 `--scoped` 的名稱跟開工時不同，或漏帶了）再跑一次 `eval_pace.py`。還是讀不到就當成 `WINDDOWN` 處理並告訴 Stan，因為沒讀到的常常是漲得最快的那條。

### 4. 收工

任務做完、到了 `HARDSTOP`、或 Stan 喊停，都要收工：

1. 做完了：回報做了什麼。
2. 沒做完：留交接。看任務動到哪裡，不看目前的工作目錄：只動到一個專案，就用 `handoff` skill 在那個專案的資料夾寫 HANDOFF.md；動到好幾個專案或不屬於任何專案，就不寫檔，把進度、還沒做的、下次怎麼接直接寫在回覆裡。
3. 關掉 pacer：
   ```
   py "C:/Users/stans/.claude/local-plugins/quota-pacer/scripts/end_pace.py"
   ```
   這支在 `EMERGENCY` 時也跑得動。忘了跑的話，hook 會繼續用舊的上限擋這個 session 的工具。
4. 因為到線而收工的話，這一輪到此為止。`end_pace.py` 跑完 hook 就不擋了，但 Stan 給的上限還在，不要接著做原本的任務，等他說要不要加預算。

## 出狀況時

- 工具呼叫被擋，訊息開頭是 `[quota-pacer] EMERGENCY`：上限到了。照步驟 4 收工（交接寫在回覆裡），不要換別的工具繞，收工後也不要繼續做。
- 讀數看起來不對：看 `C:/Users/stans/.claude/quota-pacer/refresh.log` 最後幾行，每次去 endpoint 拉用量的結果都記在那。
- 預算只有 1 到 2 個百分點：用量是整數百分比，所以只分得出「還沒到」和「到了」，不會有收尾的緩衝。開工時跟 Stan 講一聲。
- 一次只有一個 session 能開 pacer。hook 只擋開工的那個 session，但 `active.json` 是共用的，第二個 session 開工會蓋掉第一個的設定。
- 開工超過 24 小時沒收工的設定會被 hook 當成殘留，不再生效。

門檻的算法、`active.json` 格式、可調的環境變數在 `C:/Users/stans/.claude/local-plugins/quota-pacer/skills/quota-pacer/references/internals.md`，除錯或測試時才需要讀。
