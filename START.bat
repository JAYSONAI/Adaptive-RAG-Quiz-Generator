@echo off
REM ONE CLICK: double-click this file. It does everything:
REM   .env check/repair -> venv + packages (only when needed) -> reranker window
REM   -> server (auto-indexes your books, warms up models) -> opens the browser.
setlocal
cd /d "%~dp0"
title Quiz Showdown

if not exist .env (
  copy .env.example .env >nul
  echo Created .env from .env.example with working defaults. Continuing.
  echo ^(Add GROQ_API_KEY to .env later if you want Groq models.^)
)

if not exist .venv (
  py -3 -m venv .venv || (echo Python 3.10+ is required. & pause & exit /b 1)
)
call .venv\Scripts\activate.bat

REM install packages only when requirements-quiz.txt changed
set "STAMP=.venv\.req_stamp"
fc /b requirements-quiz.txt "%STAMP%" >nul 2>nul
if errorlevel 1 (
  echo Installing packages ^(first run or requirements changed^)...
  python -m pip install --upgrade pip >nul
  pip install -r requirements-quiz.txt || (echo Install failed. & pause & exit /b 1)
  copy /y requirements-quiz.txt "%STAMP%" >nul
)

REM add missing .env keys, fix old defaults (never touches your values or keys)
python -m app.quiz.envfix

REM reranker: start in its own window unless already listening on 8765
set "RERANK_ON=1"
findstr /b /i /c:"RERANKER_ENABLED=false" .env >nul && set "RERANK_ON=0"
if "%RERANK_ON%"=="1" (
  netstat -ano | findstr ":8765 " | findstr LISTENING >nul
  if not errorlevel 1 (
    echo Reranker already running on port 8765. Reusing it.
  ) else if exist "%USERPROFILE%\.venv-reranker\Scripts\python.exe" (
    start "BGE reranker" cmd /k "%~dp0start_reranker.bat"
  ) else (
    echo Reranker environment not found; quizzes will use the built-in fallback ordering.
  )
)

echo Starting Quiz Showdown. Your browser opens by itself; books are indexed in the background.
python quiz_server.py
pause
