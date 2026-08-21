@echo off
REM Starts the Smart Sugarcane AI backend. Keep this window open while using the app.
cd /d "%~dp0backend"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at backend\venv
    echo.
    echo Create it first:
    echo     cd backend
    echo     python -m venv venv
    echo     venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    echo Creating backend\.env from .env.example ...
    copy ".env.example" ".env" >nul
)

echo ============================================================
echo   Smart Sugarcane AI - BACKEND
echo   API   : http://127.0.0.1:8000
echo   Docs  : http://127.0.0.1:8000/docs
echo.
echo   Wait for "Application startup complete." before using
echo   the web app. Press Ctrl+C to stop.
echo ============================================================
echo.

venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

echo.
echo Backend stopped.
pause
