@echo off
REM ---------------------------------------------------------------------------
REM Chay Label Studio o port 8081 (CVAT giu port 8080)
REM
REM   start_label_studio.bat          -> chay nen, khong mo trinh duyet
REM   start_label_studio.bat --stop   -> tat Label Studio
REM ---------------------------------------------------------------------------
setlocal
set "LS_PORT=8081"
set "LOG_OUT=%TEMP%\label_studio_out.log"
set "LOG_ERR=%TEMP%\label_studio_err.log"

if /i "%~1"=="--stop" goto :stop

echo [label-studio] dang khoi dong o port %LS_PORT% ...
start "Label Studio" /min label-studio start --port %LS_PORT% --no-browser 1>"%LOG_OUT%" 2>"%LOG_ERR%"
echo [label-studio] giao dien: http://localhost:%LS_PORT%
echo [label-studio] log: %LOG_OUT%
timeout /t 8 /nobreak >nul
goto :eof

:stop
echo [label-studio] dang tat...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:":%LS_PORT% .*LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
)
echo [label-studio] da tat.
goto :eof
