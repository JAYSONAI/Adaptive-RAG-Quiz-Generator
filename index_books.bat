@echo off
REM Reads every book in agents\library\knowledge, embeds it with Ollama (bge-m3) and stores it. Safe to re-run.
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv || (echo Python 3.10+ is required & pause & exit /b 1)
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip >nul
  pip install -r requirements-quiz.txt || (echo Install failed & pause & exit /b 1)
) else (
  call .venv\Scripts\activate.bat
)
python -m app.quiz.indexer %*
pause
