@echo off
REM ---------------------------------------------------------------------------
REM Auto-label Label Studio - launcher Windows
REM
REM   auto_label.bat                 -> auto-label project 2 (mac dinh)
REM   auto_label.bat 5               -> auto-label project co id 5
REM   auto_label.bat "Ten Project"   -> auto-label project theo ten
REM
REM Bien moi truong truoc khi chay:
REM   set LS_API_TOKEN=<token>
REM ---------------------------------------------------------------------------
setlocal
set "PROJECT=%~1"
if "%PROJECT%"=="" set "PROJECT=2"

cd /d "%~dp0.."
set "PYTHONIOENCODING=utf-8"

echo [auto-label] project = %PROJECT%
python tools\auto_label_ls.py --project "%PROJECT%" %2 %3 %4 %5 %6 %7 %8 %9
if errorlevel 1 (
  echo.
  echo [auto-label] THAT BAI. Kiem tra Label Studio co chay o http://localhost:8081 chua.
  pause
)
endlocal
