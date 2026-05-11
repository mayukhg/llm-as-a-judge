@echo off
echo =====================================================
echo  Shutting down HHH Judge - Streamlit
echo =====================================================

echo Stopping Streamlit window (if started via startup.bat^)...
taskkill /FI "WINDOWTITLE eq HHHJudgeStreamlit*" /T /F >nul 2>nul
if %errorlevel% equ 0 (
    echo Streamlit window process stopped.
) else (
    echo No window titled HHHJudgeStreamlit found.
)

echo Stopping any process listening on port 8501...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8501 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>nul
)

if exist "%~dp0.streamlit.pid" del /f /q "%~dp0.streamlit.pid" >nul 2>nul

echo Shutdown complete.
timeout /t 2 >nul
