@echo off
chcp 65001 >nul 2>&1
REM Startup Batch File for All Services
REM LangGraph Research Agent - Startup Menu

echo ============================================================
echo LangGraph Research Agent
echo Startup Menu
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
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
    echo Using virtual environment Python.
) else (
    set "PYTHON_EXE=python"
    echo WARNING: Virtual environment not found.
    echo Create virtual environment: python -m venv venv
    echo.
    echo Continue anyway? (Y/N)
    set /p CONTINUE=
    if /i not "%CONTINUE%"=="Y" (
        exit /b 1
    )
)

echo.
echo ============================================================
echo Select startup option:
echo ============================================================
echo 1. Start API Server only
echo 2. Start GUI Application only
echo 3. Start both API Server and GUI Application (Recommended)
echo 4. Exit
echo.
set /p CHOICE="Select (1-4): "

if "%CHOICE%"=="1" (
    echo.
    echo Starting API Server...
    set "PYTHON_EXE=%PYTHON_EXE%"
    call start_api_server.bat
    goto :end
)

if "%CHOICE%"=="2" (
    echo.
    echo Starting GUI Application...
    set "PYTHON_EXE=%PYTHON_EXE%"
    call start_gui.bat
    goto :end
)

if "%CHOICE%"=="3" (
    echo.
    echo ============================================================
    echo Starting both API Server and GUI Application
    echo ============================================================
    echo.
    echo NOTE: Two windows will open
    echo   - Window 1: API Server
    echo   - Window 2: GUI Application
    echo.
    echo Continue? (Y/N)
    set /p CONTINUE=
    if /i not "%CONTINUE%"=="Y" (
        goto :end
    )
    echo.
    echo Starting API Server...
    start "API Server" cmd /k "cd /d %SCRIPT_DIR% && call start_api_server.bat"
    timeout /t 3 /nobreak >nul
    echo.
    echo Starting GUI Application...
    start "GUI Application" cmd /k "cd /d %SCRIPT_DIR% && call start_gui.bat"
    echo.
    echo ============================================================
    echo Both services started
    echo ============================================================
    echo.
    echo Press Ctrl+C in each window to stop
    echo.
    pause
    goto :end
)

if "%CHOICE%"=="4" (
    echo Exiting...
    goto :end
)

echo Invalid selection.
pause

:end

