@echo off
title phantom-ctrl

:: 检查是否以管理员权限运行
net session >nul 2>&1
if errorlevel 1 (
    echo 需要管理员权限，正在请求提权...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo 启动 phantom-ctrl 服务...

cd /d "%~dp0"
call venv\Scripts\activate
if errorlevel 1 (
    echo 错误：无法激活虚拟环境，请检查 venv 目录是否存在。
    pause
    exit /b 1
)

python main.py
if errorlevel 1 (
    echo.
    echo 错误：服务启动失败，请检查端口是否被占用或其他错误信息。
    pause
    exit /b 1
)
