@echo off
chcp 65001 >nul
title 翻译助手
echo ========================================
echo          一键翻译助手 v1.0
echo ========================================
echo.
echo 正在启动...
echo.

cd /d "%~dp0"
set "PYTHON312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PYTHON312%" (
    "%PYTHON312%" hotkey_listener.py
    goto end
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 hotkey_listener.py
    goto end
) else (
    python hotkey_listener.py
)

:end
pause
