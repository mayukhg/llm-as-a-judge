@echo off
setlocal
echo =====================================================
echo  Starting HHH Judge - Streamlit (Windows)
echo =====================================================

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Python not found. Install Python 3.11+ and ensure it is on PATH.
    pause
    exit /b 1
)

cd /d "%~dp0"

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

python -c "import streamlit" >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing dependencies (first run^)...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo pip install failed.
        pause
        exit /b 1
    )
)

echo Starting Streamlit in a new window...
start "HHHJudgeStreamlit" /D "%~dp0" cmd /k "streamlit run streamlit_app.py --server.headless true"

echo Server window launched.
timeout /t 2 >nul
echo Open the UI at: http://localhost:8501
endlocal
