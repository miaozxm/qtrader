@echo off
rem ============================================================
rem   QTrader Platform Launcher
rem   Data: EastMoney + Tencent (auto fallback)
rem   Markets: A-Share / HK
rem   Uses project-local virtualenv .venv (self-contained)
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"
set "FALLBACK_PY=python"

echo.
echo  ============================================
echo     QTrader Quant Trading Platform
echo     Starting...
echo  ============================================
echo.

if exist "%VENV_PY%" (
    set "PYTHON=%VENV_PY%"
    echo  [env] using local virtualenv
) else (
    set "PYTHON=%FALLBACK_PY%"
    echo  [env] virtualenv not found, using system python
)

"%PYTHON%" run.py
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Failed to start.
    echo  If using system python, make sure dependencies are installed:
    echo    python -m pip install -r requirements.txt
    pause
)
