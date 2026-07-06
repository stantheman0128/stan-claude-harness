---
name: colonist-postmortem
description: Colonist（卡坦島）對局賽後檢討／敗因分析。主動使用本 skill 當 Stan 說「分析最新那局」「這局怎麼輸」「這局怎麼贏的」「colonist 敗因分析」「postmortem」「賽後檢討」「分析卡坦」「分析這局」「analyze my last colonist game」「why did I lose」，或問「迷思查核」「我是不是特別容易被7」「一蓋房子就骰7」「手牌爆了就來7」「跨局統計」「被偷是騎士還是7」，或貼出 cst-game-*.json / colonist dump 檔要求分析時。流程：找最新 dump → 跑 tools/summarize.js 產脈絡摘要（含迷思查核與偷牌歸因）→ 多維度敗因分析 → 報告寫進 reports\；跨局問題跑 tools/aggregate.js。
---

# Colonist 對局賽後檢討

把 colonist-stats-tracker 下載的整局 WebSocket dump 變成敗因分析報告。
專案根目錄：`C:\Users\stans\Projects\colonist-analysis\`（下稱 `<ROOT>`）。

## 1. 找最新 dump

依序找，取修改時間最新的一份（Stan 指名某局時用那份）：

1. `<ROOT>\games\*.json`
2. `%USERPROFILE%\Downloads\colonist-logs\*.json`
3. `%USERPROFILE%\Downloads\cst-game-*.json`
4. `%USERPROFILE%\Downloads\cst-ws-frames*.json`（舊版 capture，欄位較少）

在 2–4 找到的檔先搬進 `<ROOT>\games\` 歸檔再處理。

dump 形狀：`{ frames: [最後500幀], log: {index: 整局gameLogState條目}, fullState: 最近一次type-4完整快照的frame, savedAtFrame }`。
`fullState` 的 payload 在 `.data.payload`；事件字典見記憶 [[colonist_ws_protocol]]
（10/141=骰、47=產出、55=棄牌、86=壟斷、115/116=交易、14/15/16=偷牌、48=銀行缺牌、45=勝利）。

## 2. 產脈絡摘要（免 token）

若 `<ROOT>\reports\<名稱>.summary.md` 尚不存在：

```
cd C:\Users\stans\Projects\colonist-analysis
node tools\summarize.js games\<檔名>.json -o reports
```

先讀 `<名稱>.summary.md` 與 `.summary.json` 掌握全局——玩家、贏家、骰運直方圖、
達成率、偷牌/壟斷/棄牌/缺牌、🔮 迷思查核（蓋建築→下一骰是不是 7、手牌超上限 vs 7）、
💔 偷牌歸因（被偷是 7 搶匪還是騎士卡）、值得注意的轉折、資料品質備註。
summary 裡標示省略或「幾何不完整」的欄位不要自己腦補數字。

Stan 問「迷思查核」「我是不是特別容易被 7」「跨局統計」這類跨局問題時，跑：

```
node tools\aggregate.js
```

它會掃 `games\*.json`、缺摘要自動補產，輸出 `reports\aggregate-myths.md`
（兩個迷思的合併樣本統計＋偷牌歸因合計；局數少會自動印統計力不足警語）。
單局的逐事件 log index 證據在各局 `summary.json` 的 `myths` 欄位。

## 3. 多維度敗因分析

以 summary.json 為底，需要細節時再回 dump 抽 log 原文（依 index 引用，勿整檔讀入）。
維度（建議派 subagent 並行、各扛 2-3 個維度再彙整；記憶規則：subagent 一律 `model: "opus"`）：

1. **開局落子品質** — pip 覆蓋、資源組合缺口、港口配合（注意 summary 用的是終局盤面）
2. **骰運校正** — 先分清運氣與決策：直方圖偏差、達成率互比、零收入乾旱段
3. **資源引擎與交易效率** — 產出結構 vs 建造需求、銀行 4:1 換的浪費、玩家交易的得失
4. **搶匪攻防** — 被卡損失、偷牌收支、7 點棄牌管理（手牌上限意識）
5. **發展卡與時機** — 打出時機、騎士 vs 分數卡
6. **節奏轉折** — 壟斷、爆棄牌、缺牌等轉折點前後的局勢變化

分析原則：每個論點都要能指回 summary 欄位或 log index；運氣歸運氣、決策歸決策，
不把骰運差說成打得差。

## 4. 產出

- 完整報告寫到 `<ROOT>\reports\<名稱>-analysis.md`（繁體中文 Markdown）。
- 聊天裡給結論摘要：**3 個關鍵敗因（或勝因），各配一句具體改進建議**，不要贅述報告全文。
