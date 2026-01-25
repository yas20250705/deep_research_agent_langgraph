@echo off
chcp 65001 >nul 2>&1
REM Startup Batch File for All Services
REM LangGraph Research Agent - Auto Start (API Server + HTML GUI)

echo ============================================================
echo LangGraph Research Agent
echo Starting API Server and HTML GUI
echo ============================================================
echo.

REM Get current directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo NOTE: Two windows will open
echo   - Window 1: API Server
echo   - Window 2: HTML GUI (browser)
echo.
echo Starting API Server...
REM Python実行ファイルのパスを決定
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
    echo Using virtual environment Python: %PYTHON_EXE%
) else (
    set "PYTHON_EXE=python"
    echo Using system Python: %PYTHON_EXE%
    echo WARNING: Virtual environment not found. Using system Python.
)
echo.

REM 環境変数を正しく渡すために、変数を展開してからstartコマンドを実行
REM パスにスペースが含まれる可能性があるため、引用符で囲む
set "PYTHON_PATH=%PYTHON_EXE%"
start "API Server" cmd /k "cd /d "%SCRIPT_DIR%" && set PYTHON_EXE=%PYTHON_PATH% && call start_api_server.bat"
echo Waiting for API server to start...
timeout /t 5 /nobreak >nul
echo Checking API server status...
REM Wait for API server to be ready (up to 30 seconds)
set RETRY_COUNT=0
:wait_for_api_html
REM Try curl first (Windows 10+), then PowerShell as fallback
where curl >nul 2>&1
if not errorlevel 1 (
    curl -s -o nul -w "%%{http_code}" http://localhost:8000/health 2>nul | findstr /C:"200" >nul 2>&1
    if not errorlevel 1 (
        echo API Server is ready!
        goto :api_ready_html
    )
) else (
    REM Use PowerShell as fallback
    powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8000/health' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; if ($response.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        echo API Server is ready!
        goto :api_ready_html
    )
)
set /a RETRY_COUNT+=1
if %RETRY_COUNT% geq 30 (
    echo WARNING: API server may not be ready after 30 seconds, but continuing...
    goto :api_ready_html
)
if %RETRY_COUNT% equ 10 (
    echo Still waiting for API server... (attempt %RETRY_COUNT% of 30)
)
timeout /t 1 /nobreak >nul
goto :wait_for_api_html
:api_ready_html
echo.
echo API Server is ready!
echo.
echo Starting local web server for HTML GUI...
REM ローカルWebサーバーを起動（バックグラウンド）
start "HTML GUI Server" cmd /k "cd /d "%SCRIPT_DIR%\gui" && python -m http.server 8080"
echo Waiting for web server to start...
timeout /t 2 /nobreak >nul
echo.
echo Opening HTML GUI in browser...
REM ブラウザでローカルWebサーバーのURLを開く
start http://localhost:8080
echo.
echo ============================================================
echo Both services started
echo ============================================================
echo.
echo API Server: Running in separate window (port 8000)
echo HTML GUI Server: Running in separate window (port 8080)
echo HTML GUI: Opened in browser at http://localhost:8080
echo.
echo Press Ctrl+C in each window to stop
echo Close browser window to close HTML GUI
echo.
echo ============================================================
echo.

