@echo off
echo ========================================
echo niNE Automated Test Suite
echo ========================================
echo.

REM Убиваем старые процессы Python сервера если есть
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *game_server*" 2>nul

echo Starting server...
start "niNE Server" cmd /c "python -m nine.server.game_server 2>&1 | findstr /V TICK"

echo Waiting for server to initialize (10 seconds)...
timeout /t 10 /nobreak > nul

echo.
echo Running automated tests...
python -m tests.automated_test_suite

echo.
echo ========================================
echo Tests complete!
echo ========================================
echo.

REM Найти последний report
for /f "delims=" %%i in ('dir /b /ad /o-d test_report_* 2^>nul') do (
    set REPORT_DIR=%%i
    goto :found
)

:found
if defined REPORT_DIR (
    if exist "%REPORT_DIR%\report.html" (
        echo Opening report: %REPORT_DIR%\report.html
        start %REPORT_DIR%\report.html
    ) else (
        echo ERROR: Report not generated!
        echo Check logs in %REPORT_DIR%
    )
) else (
    echo ERROR: No test report directory found!
)

echo.
echo Press any key to stop server and exit...
pause > nul

echo Stopping server...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *niNE Server*" 2>nul
