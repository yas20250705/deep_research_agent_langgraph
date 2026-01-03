@echo off
chcp 65001 >nul 2>&1
REM GUI Application Startup Batch File
REM LangGraph Research Agent - GUI Application

echo ============================================================
echo Starting GUI Application...
echo ============================================================
echo.

REM Get current directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Check Python installation
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not found in PATH
    echo Please install Python or add it to PATH
    echo.
    pause
    exit /b 1
)

REM Check and set Python executable path
if defined PYTHON_EXE (
    REM Use Python executable from parent script
    echo Using Python executable from parent script.
) else if exist "venv\Scripts\python.exe" (
    REM Use relative path to avoid path concatenation issues
    set "PYTHON_EXE=venv\Scripts\python.exe"
    echo Using virtual environment Python.
) else (
    set "PYTHON_EXE=python"
    echo WARNING: Virtual environment not found.
    echo Create virtual environment: python -m venv venv
    echo.
)

REM Check API server connection (with retry)
echo Checking API server connection...
set API_CONNECTED=0
set RETRY_COUNT=0
:check_api_retry
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8000/health' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo API Server: Connected
    set API_CONNECTED=1
    goto :api_check_done
)
set /a RETRY_COUNT+=1
if %RETRY_COUNT% geq 5 (
    echo API Server: Not connected (will continue anyway)
    goto :api_check_done
)
timeout /t 1 /nobreak >nul
goto :check_api_retry
:api_check_done
if %API_CONNECTED%==0 (
    echo.
    echo ============================================================
    echo WARNING: Cannot connect to API server
    echo ============================================================
    echo.
    echo The API server may still be starting up.
    echo GUI will start anyway and will retry connection.
    echo.
    timeout /t 2 /nobreak >nul
)

REM Check Python version
echo Python version:
"%PYTHON_EXE%" --version
if errorlevel 1 (
    echo ERROR: Failed to check Python version
    pause
    exit /b 1
)
echo.

echo ============================================================
echo Browser will open automatically
echo Press Ctrl+C to stop
echo ============================================================
echo.

REM Start GUI application
"%PYTHON_EXE%" run_gui.py

REM Handle errors
if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: Failed to start GUI application
    echo ============================================================
    echo.
    echo Check the following:
    echo 1. Virtual environment is activated
    echo 2. Dependencies installed: pip install -r requirements.txt
    echo 3. Streamlit installed: pip install streamlit
    echo 4. API server is running
    echo 5. Run from project root directory
    echo.
    pause
)

