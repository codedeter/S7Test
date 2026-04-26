@echo off
chcp 65001 >nul
echo ========================================
echo    PLC数据监控系统 - 启动脚本
echo ========================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [提示] 未检测到虚拟环境，正在创建...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [成功] 虚拟环境创建完成
)

:: 激活虚拟环境
echo [提示] 激活虚拟环境...
call venv\Scripts\activate.bat

:: 安装依赖
echo [提示] 检查依赖库...
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo [提示] 安装依赖库，请稍候...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

:: 启动服务器
echo.
echo ========================================
echo    启动PLC数据监控系统
echo ========================================
echo.
echo 访问地址: http://localhost:3000
echo 按 Ctrl+C 停止服务器
echo.

python src\server.py

:: 如果服务器异常退出，等待用户按键
if errorlevel 1 (
    echo.
    echo [错误] 服务器启动失败，请检查错误信息
    pause
)
