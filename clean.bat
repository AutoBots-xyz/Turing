@echo off
echo ==========================================
echo CLEANING PROJECT WORKING DIRECTORY
echo ==========================================

echo.
echo 1. Removing __pycache__ directories...
FOR /d /r . %%d in (__pycache__) DO (
    IF EXIST "%%d" (
        echo Deleting: %%d
        rd /s /q "%%d"
    )
)

echo.
echo 2. Removing isolated .pyc files...
del /S /Q *.pyc 2>nul

echo.
echo 3. Purging Git Cache (Untracking ignored files)...
git rm -r --cached . >nul 2>&1

echo.
echo 4. Staging files with updated gitignore...
git add .

echo.
echo Cleanup Complete!
echo You can now check 'git status' to verify the clean index.
pause
