@echo off
REM Starts the Smart Sugarcane AI frontend. Keep this window open while using the app.
cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo [ERROR] Frontend dependencies are not installed.
    echo.
    echo Install them first:
    echo     cd frontend
    echo     npm install
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    echo Creating frontend\.env from .env.example ...
    copy ".env.example" ".env" >nul
)

echo ============================================================
echo   Smart Sugarcane AI - FRONTEND
echo   App: http://localhost:5173
echo.
echo   The backend must also be running, or the app will show
echo   "Cannot reach the backend". Press Ctrl+C to stop.
echo ============================================================
echo.

call npm run dev

echo.
echo Frontend stopped.
pause
