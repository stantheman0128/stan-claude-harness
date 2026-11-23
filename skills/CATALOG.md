# 自製 skill 目錄

忘記自己有哪些 skill 時看這份。使用次數取自 2026-11-23 的 `/skill-doctor`，之後重跑它就能更新。冷藏中的 skill 在 `~/.claude/cold/skills/`，不列在這裡。

## 怎麼審：三道關

**第一關，裝之前：它裝了什麼模型不知道的東西？**
用一句話說得出來才裝。會被用到的只有三種：你的偏好與風格、你的流程與路徑、踩過的坑。通用工程方法（TDD、除錯、規劃）模型本來就會，superpowers 和 agent-skills 9 月後幾乎沒被叫過就是證據。另外問：下個月有沒有一個具體任務會用到？沒有就記進 `skill-routing/EVALUATIONS.md` 的重評觸發，先不裝。整包 plugin 裡只有幾條有用時，把那幾條搬進常駐檔就好。

**第二關，裝之後：真的有被叫到嗎？**
1. 跑 `/skill-doctor`，看用過幾次、多久沒用。
2. 看 router 建議後有沒有真的載入（2026-11-23 算過一次：09-15 起 334 個 session，humanizer 系列 71%，其餘多數 0 到 2%）。建議了一百次卻幾乎沒載的規則就是雜訊，要縮關鍵字或刪掉。
3. 依數字分三桶：
   - 60 天內用過 → 留著。
   - 用過，但超過 60 天沒用 → 只留名字。在 `settings.json` 的 `skillOverrides` 寫 `"name-only"`，打 `/名字` 照樣能用。
   - 從沒用過，也想不出下個月會用 → 冷藏。把資料夾搬到 `~/.claude/cold/skills/`，要用再搬回來。

**第三關，常用的那幾支：真的有幫助嗎？**
用得多不代表有幫助，humanizer 用得多是因為 CLAUDE.md 規定要用。只挑最常用、最花 token 的幾支，拿 2 到 3 個真實舊任務，有載和沒載各跑一次，用模型自評以外的東西判：數得出來的指標（例如 AI 痕跡剩幾處），或你盲選哪份比較好。贏不了沒載的版本，就砍到只剩造成差別的那幾條規則，或冷藏。

每月做第二關，跟 `_scratch` 的月報一起；第三關每季挑 1 到 2 支做。

## 常用，留著

| skill | 做什麼 | 什麼時候叫它 | 用過 | 最後一次 |
|---|---|---|---|---|
| humanizer | 去掉英文的 AI 腔 | 英文 email、PR 描述定稿前 | 224 | 11-23 |
| humanizer-zh-tw | 去掉中文的 AI 腔，改成台灣用語 | 作業、報告、對外中文定稿前 | 103 | 11-23 |
| oss-factory | 管開源貢獻：挖 issue、認領、開 PR、記帳 | 想再開一支 PR | 49 | 40 天前 |
| guided-dev | 你出產品決策、我做技術決策，切小片逐片驗證 | 「幫我做一個 app」 | 18 | 2 天前 |
| lenses | 動手前從 14 個角度回看：隱含狀態機、不變量、故障演練等 | 做有狀態、會存資料、會重試或長時間跑的東西前；修第二次還沒好 | 0 | 11-24 新增 |
| new-skill | 評估新 skill 或 plugin 該不該裝 | 看到 GitHub 上的新 skill | 17 | 11-23 |
| diagnosing-bugs | 難抓的 bug 先做出穩定重現的紅燈，再查原因 | 時有時無的錯，或猜錯一次原因 | 16 | 15 天前 |
| model-effort-router | 決定任務用哪個模型、哪個思考檔位 | 不確定該用 Opus 還是 Sonnet | 12 | 9 天前 |
| cross-model-handoff | 寫給 Codex 的任務單，或修 Codex 寫的提示 | 想把任務丟給 Codex | 10 | 7 天前 |
| resolving-merge-conflicts | 逐段解 git 衝突，不放棄 | rebase 到一半卡衝突 | 6 | 30 天前 |
| write-like-shasha77 | 用志祺七七風格寫影片腳本 | 要寫志祺風格口播稿 | 4 | 40 天前 |
| grilling | 動手前一次一題追問計畫；需求不清時先訪談你 | 有架構草稿想先被挑毛病 | 3 | 20 天前 |
| i-have-adhd | 每則回覆先講結論、編號、估時間 | 常駐，hook 每個 session 自動載入 | 由 hook 載入 | 每天 |

## 用過但很久沒用，建議只留名字

| skill | 做什麼 | 什麼時候叫它 | 用過 | 最後一次 |
|---|---|---|---|---|
| handoff | 收工時寫 HANDOFF.md 讓下次接手 | 「收工」「寫 handoff」 | 23 | 107 天前 |
| video-lens | YouTube 影片做成帶時間戳的重點摘要 | 想快速知道一支長影片在講什麼 | 6 | 156 天前 |
| skill-routing | 功能重疊時告訴你預設用哪支 | 不確定該載哪個 skill | 6 | 94 天前 |
| security-audit | 整個程式庫深度資安稽核，很吃 token | 專案上線前徹底查一次 | 4 | 107 天前 |
| research-mode | 整個 session 變唯讀 | 研究陌生 codebase，怕改到東西 | 3 | 147 天前 |
| cutting-demo-videos | 長螢幕錄影剪成精華短片、燒字幕 | 30 分鐘展示剪成 3 分鐘 | 2 | 133 天前 |
| transcribe | YouTube 或音檔轉繁中逐字稿 | 要訪談的逐字稿 | 1 | 156 天前 |
| adhd | 用 5 個角度平行發想再淘汰，約 10 個 agent，很耗額度 | 命名、架構有好幾種做法 | 1 | 109 天前 |
| mineru | 本機把 PDF 轉 Markdown，公式表格都行，很慢 | 含公式的論文 PDF | 0 | 沒用過 |
| careful | 擋掉 rm -rf、強制推送這類危險指令 | 動正式資料庫前打 `/careful` | 0 | 沒用過 |
| writing-great-skills | 寫 skill 的原則參考，已設成只能手動叫 | 要新寫一個 skill | 0 | 沒用過 |

## 從沒用過或幾乎沒用，建議冷藏

| skill | 做什麼 | 用過 | 備註 |
|---|---|---|---|
| paxel-remote-setup | 在遠端開發機設定 Paxel 收集對話紀錄 | 0 | alpha 版 |
| project-skill-library | 把專案知識寫成專案內的 skill 庫 | 0 | 內文用舊模型名 |
| colonist-postmortem | 分析卡坦島對局輸贏原因 | 0 | 需要 `Projects\colonist-analysis` |
| apply-grant | 填 Solana Earn 的 200 USDG 補助申請 | 1 | 內含外部遙測，你的設定是關閉的；第 60 行有沒展開的範本佔位符 |

## 已經關閉，不佔 context

- skill：adversarial-review、mistral-ocr-tts、report-verifier、upstream-insights-report、write-like-joyce。`video-lens-gallery` 只剩 `settings.json` 一行，資料夾已不存在。
- 舊斜線指令 17 個，在 `commands/` 的 api、misc、supabase、ui 和 4 個單檔。多數固定用 `claude-sonnet-4-5`，已全部關閉。
