@echo off
REM Double-click this file to launch Smart Sugarcane AI.
REM It opens the backend and frontend in two separate windows.
cd /d "%~dp0"

echo Launching Smart Sugarcane AI ...
echo.

start "Smart Sugarcane AI - Backend" cmd /k call "%~dp0run-backend.bat"

REM Give the backend a head start so it is listening before the browser opens.
timeout /t 6 /nobreak >nul

start "Smart Sugarcane AI - Frontend" cmd /k call "%~dp0run-frontend.bat"

echo ============================================================
echo   Two windows are starting:
echo.
echo     Backend   http://127.0.0.1:8000/docs
echo     Frontend  http://localhost:5173
echo.
echo   The browser opens automatically once Vite is ready.
echo.
echo   IMPORTANT: keep BOTH windows open while using the app.
echo   Closing one stops that server.
echo.
echo   To stop everything, close both windows (or press Ctrl+C
echo   in each of them).
echo ============================================================
echo.
echo This launcher window can be closed safely.
pause
