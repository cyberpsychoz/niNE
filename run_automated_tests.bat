@echo off
echo ========================================
echo niNE Automated Test Suite
echo ========================================
echo.

echo Starting server in background...
start /B python -m nine.server.game_server > server_test.log 2>&1

echo Waiting for server to start...
timeout /t 5 /nobreak > nul

echo Running automated tests...
python -m tests.automated_test_suite

echo.
echo Tests complete! Check test_report_* folder for results.
echo Opening report...

for /f "delims=" %%i in ('dir /b /ad /o-d test_report_*') do (
    start %%i\report.html
    goto :done
)

:done
echo.
echo Press any key to stop server and exit...
pause > nul

taskkill /F /IM python.exe /FI "WINDOWTITLE eq nine.server.game_server*" 2>nul
