@echo off
echo ==========================================
echo TURING MULTI-COMMIT BATCH SCRIPT
echo ==========================================

echo.
echo Unstaging all files to prepare for split commits...
git reset >nul

echo.
echo [1/4] Committing Config and Build scripts...
git add .gitignore .env.example README.md clean.bat commit.bat
git commit -m "chore: update environment configuration and cleanup batch scripts"

echo.
echo [2/4] Committing Backend API and Pipeline Engine...
git add python-engine/
git commit -m "feat(backend): autonomous pipeline orchestration, layer services, and cache cleanup"

echo.
echo [3/4] Committing Frontend Graph Visualization Refactor...
git add src/components/graph/ src/hooks/useGraphAnimation.ts src/types/graph.ts
git commit -m "refactor(frontend): implement continuous D3 physics graph and fix interaction bugs"

echo.
echo [4/4] Committing Frontend Dashboard and Reports...
git add src/components/layer2/ src/components/layer3/ src/components/layer4/ src/hooks/useReportStream.ts src/types/report.ts src/app/
git commit -m "feat(frontend): update layer panels and streaming report schemas"

echo.
echo [Final] Checking for any remaining miscellaneous files...
git add .
git commit -m "chore: miscellaneous dashboard and minor tweaks" 2>nul

echo.
echo ==========================================
echo ALL COMMITS SUCCESSFULLY SPLIT AND SAVED!
echo ==========================================
pause
