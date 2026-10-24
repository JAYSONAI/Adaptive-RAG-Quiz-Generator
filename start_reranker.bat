@echo off
REM Runs the local BGE reranker in its own environment. Localhost only.
cd /d "%~dp0"
set RERANKER_MODEL=BAAI/bge-reranker-v2-m3
set RERANKER_DEVICE=cpu
set HF_HUB_OFFLINE=1
set RPY=%USERPROFILE%\.venv-reranker\Scripts\python.exe
if not exist "%RPY%" (
  echo Reranker environment not found at %USERPROFILE%\.venv-reranker
  pause
  exit /b 1
)
"%RPY%" -c "import fastapi, uvicorn" 2>nul
if errorlevel 1 (
  echo Installing the small web server packages ^(fastapi, uvicorn^) into the reranker environment...
  "%RPY%" -m pip install fastapi uvicorn
  if errorlevel 1 (
    echo Install failed. Run: "%RPY%" -m pip install fastapi uvicorn
    pause
    exit /b 1
  )
)
"%RPY%" -c "import FlagEmbedding" 2>nul
if errorlevel 1 (
  echo FlagEmbedding is not installed in the reranker environment.
  pause
  exit /b 1
)
"%RPY%" -m uvicorn tools.reranker_service:app --host 127.0.0.1 --port 8765
