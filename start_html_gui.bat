@echo off
chcp 65001 >nul 2>&1
REM HTML GUI Startup Batch File
REM LangGraph Research Agent - HTML/CSS/JavaScript GUI

echo ============================================================
echo Starting HTML GUI...
echo ============================================================
echo.

REM Get current directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

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
    echo To start API server, run: start_api_server.bat
    echo.
    timeout /t 2 /nobreak >nul
)

echo ============================================================
echo Starting HTML GUI...
echo ============================================================
echo.
echo Opening HTML GUI in browser...
echo.
echo NOTE: If the browser doesn't open automatically:
echo   1. Open gui/index.html in your browser
echo   2. Or start a local web server:
echo      cd gui
echo      python -m http.server 8080
echo      Then open http://localhost:8080
echo.
echo ============================================================
echo Access URLs:
echo   - HTML GUI: gui/index.html (open in browser)
echo   - Or use: http://localhost:8080 (if using local server)
echo   - API Server: http://localhost:8000
echo.
echo Press any key to open HTML GUI in default browser...
echo ============================================================
echo.
pause >nul

REM Try to open HTML file in default browser
if exist "gui\index.html" (
    start "" "gui\index.html"
    echo.
    echo HTML GUI opened in browser.
    echo.
    echo To stop, close the browser window.
    echo.
) else (
    echo.
    echo ERROR: gui/index.html not found
    echo.
    echo Please check that the GUI files are in the gui directory.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo HTML GUI started
echo ============================================================
echo.
echo The HTML GUI should now be open in your browser.
echo.
echo If you need to start a local web server instead:
echo   cd gui
echo   python -m http.server 8080
echo.
echo Press any key to exit...
pause >nul
