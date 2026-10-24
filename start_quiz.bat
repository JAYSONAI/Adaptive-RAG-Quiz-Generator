@echo off
REM Starts the reranker service in its own window, then your existing start.bat.
cd /d "%~dp0"
netstat -ano | findstr ":8765 " | findstr LISTENING >nul
if not errorlevel 1 (
  echo Reranker already running on port 8765. Reusing it.
) else if exist "%USERPROFILE%\.venv-reranker\Scripts\python.exe" (
  start "BGE reranker" cmd /k "%~dp0start_reranker.bat"
  echo Waiting for the reranker to load...
  timeout /t 10 /nobreak >nul
) else (
  echo Reranker environment not found. Quizzes will report "reranker_unavailable"
  echo unless RERANKER_ENABLED=false or RERANKER_FALLBACK=true in .env.
)
call "%~dp0start.bat"
