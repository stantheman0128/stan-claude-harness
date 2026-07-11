@echo off
rem CheckSkillsUpdate - weekly headless skill upstream update check (原名 ClaudeSetup-DriftSweep)
cd /d C:\Users\stans\.claude\ops\check-skills-update
"C:\Users\stans\.local\bin\claude.exe" -p "跑 check-skills-update：完整照 C:\Users\stans\.claude\ops\check-skills-update\check\prompt.md 的指示執行。報告檔寫進 C:\Users\stans\.claude\ops\check-skills-update\reports\（檔名 check-skills-update-當天日期.md）。" --output-format text > "C:\Users\stans\.claude\ops\check-skills-update\reports\last-run.log" 2>&1
