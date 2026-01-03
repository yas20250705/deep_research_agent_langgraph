@echo off
chcp 65001 >nul 2>&1
REM Startup Batch File for All Services
REM LangGraph Research Agent - Auto Start (Option 3)

echo ============================================================
echo LangGraph Research Agent
echo Starting both API Server and GUI Application
echo ============================================================
echo.

REM Get current directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo NOTE: Two windows will open
echo   - Window 1: API Server
echo   - Window 2: GUI Application
echo.
echo Starting API Server...
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)
start "API Server" cmd /k "cd /d %SCRIPT_DIR% && set PYTHON_EXE=%PYTHON_EXE% && call start_api_server.bat"
echo Waiting for API server to start...
timeout /t 5 /nobreak >nul
echo Checking API server status...
REM Wait for API server to be ready (up to 30 seconds)
set RETRY_COUNT=0
:wait_for_api
REM Try curl first (Windows 10+), then PowerShell as fallback
where curl >nul 2>&1
if not errorlevel 1 (
    curl -s -o nul -w "%%{http_code}" http://localhost:8000/health 2>nul | findstr /C:"200" >nul 2>&1
    if not errorlevel 1 (
        echo API Server is ready!
        goto :api_ready
    )
) else (
    REM Use PowerShell as fallback
    powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8000/health' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; if ($response.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        echo API Server is ready!
        goto :api_ready
    )
)
set /a RETRY_COUNT+=1
if %RETRY_COUNT% geq 30 (
    echo WARNING: API server may not be ready after 30 seconds, but continuing...
    goto :api_ready
)
if %RETRY_COUNT% equ 10 (
    echo Still waiting for API server... (attempt %RETRY_COUNT% of 30)
)
timeout /t 1 /nobreak >nul
goto :wait_for_api
:api_ready
echo.
echo Starting GUI Application...
start "GUI Application" cmd /k "cd /d %SCRIPT_DIR% && set PYTHON_EXE=%PYTHON_EXE% && call start_gui.bat"
timeout /t 2 /nobreak >nul
echo.
echo ============================================================
echo Both services started
echo ============================================================
echo.
echo Press Ctrl+C in each window to stop
echo.
pause

