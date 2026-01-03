@echo off
chcp 65001 >nul 2>&1
REM API Server Startup Batch File
REM LangGraph Research Agent - API Server

echo ============================================================
echo Starting API Server...
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

REM Check environment variables
echo Checking environment variables...
"%PYTHON_EXE%" -c "import os; print('OPENAI_API_KEY:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')" 2>nul
"%PYTHON_EXE%" -c "import os; print('TAVILY_API_KEY:', 'SET' if os.getenv('TAVILY_API_KEY') else 'NOT SET')" 2>nul
echo.

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
echo Access URLs:
echo   - API Documentation: http://localhost:8000/docs
echo   - Health Check: http://localhost:8000/health
echo.
echo Press Ctrl+C to stop
echo ============================================================
echo.

REM Start API server
"%PYTHON_EXE%" run_api_server.py

REM Handle errors
if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: Failed to start API server
    echo ============================================================
    echo.
    echo Check the following:
    echo 1. Virtual environment is activated
    echo 2. Dependencies installed: pip install -r requirements.txt
    echo 3. Environment variables set: Check .env file
    echo 4. Run from project root directory
    echo.
    pause
)

