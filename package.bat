@echo off
chcp 65001 >nul
echo ========================================
echo    PLC监控系统 - 打包工具
echo ========================================
echo.

set PACKAGE_NAME=PLCMonitor_Package
set SOURCE_DIR=%~dp0
set OUTPUT_DIR=%USERPROFILE%\Desktop

:: 创建临时打包目录
echo [提示] 准备打包文件...
if exist "%TEMP%\%PACKAGE_NAME%" rmdir /s /q "%TEMP%\%PACKAGE_NAME%"
mkdir "%TEMP%\%PACKAGE_NAME%"

:: 复制项目文件
echo [提示] 复制项目文件...
xcopy "%SOURCE_DIR%config" "%TEMP%\%PACKAGE_NAME%\config\" /e /i /y >nul
xcopy "%SOURCE_DIR%public" "%TEMP%\%PACKAGE_NAME%\public\" /e /i /y >nul
xcopy "%SOURCE_DIR%src" "%TEMP%\%PACKAGE_NAME%\src\" /e /i /y >nul
xcopy "%SOURCE_DIR%tests" "%TEMP%\%PACKAGE_NAME%\tests\" /e /i /y >nul
xcopy "%SOURCE_DIR%tools" "%TEMP%\%PACKAGE_NAME%\tools\" /e /i /y >nul

copy "%SOURCE_DIR%config\config.py" "%TEMP%\%PACKAGE_NAME%\config\config.py" >nul
copy "%SOURCE_DIR%config\plc_tags.py" "%TEMP%\%PACKAGE_NAME%\config\plc_tags.py" >nul
copy "%SOURCE_DIR%public\index.html" "%TEMP%\%PACKAGE_NAME%\public\index.html" >nul
copy "%SOURCE_DIR%src\server.py" "%TEMP%\%PACKAGE_NAME%\src\server.py" >nul
copy "%SOURCE_DIR%src\analysis\data_analyzer.py" "%TEMP%\%PACKAGE_NAME%\src\analysis\data_analyzer.py" >nul
copy "%SOURCE_DIR%src\analysis\fault_engine.py" "%TEMP%\%PACKAGE_NAME%\src\analysis\fault_engine.py" >nul
copy "%SOURCE_DIR%src\analysis\plc_variable_loader.py" "%TEMP%\%PACKAGE_NAME%\src\analysis\plc_variable_loader.py" >nul
copy "%SOURCE_DIR%src\data\data_storage.py" "%TEMP%\%PACKAGE_NAME%\src\data\data_storage.py" >nul
copy "%SOURCE_DIR%src\plc\plc_client.py" "%TEMP%\%PACKAGE_NAME%\src\plc\plc_client.py" >nul
copy "%SOURCE_DIR%src\plc\plc_data_collector.py" "%TEMP%\%PACKAGE_NAME%\src\plc\plc_data_collector.py" >nul

:: 复制依赖和配置文件
copy "%SOURCE_DIR%requirements.txt" "%TEMP%\%PACKAGE_NAME%\requirements.txt" >nul
copy "%SOURCE_DIR%start.bat" "%TEMP%\%PACKAGE_NAME%\start.bat" >nul
copy "%SOURCE_DIR%start.sh" "%TEMP%\%PACKAGE_NAME%\start.sh" >nul
copy "%SOURCE_DIR%README.md" "%TEMP%\%PACKAGE_NAME%\README.md" >nul

:: 复制参考文件
copy "%SOURCE_DIR%GLABAL.db" "%TEMP%\%PACKAGE_NAME%\GLABAL.db" >nul 2>&1
copy "%SOURCE_DIR%PLCValues.xlsx" "%TEMP%\%PACKAGE_NAME%\PLCValues.xlsx" >nul 2>&1

:: 创建部署目录结构说明
echo [提示] 创建目录结构...
(
echo S7Test/
echo ├── config/              # 配置文件
echo ├── public/              # 前端页面
echo ├── src/                # 源代码
echo │   ├── analysis/        # 数据分析
echo │   ├── api/            # API路由
echo │   ├── data/           # 数据存储
echo │   └── plc/            # PLC通信
echo ├── tests/              # 测试脚本
echo ├── tools/              # 工具脚本
echo ├── logs/               # 日志目录
echo ├── requirements.txt     # Python依赖
echo ├── start.bat           # Windows启动
echo ├── start.sh           # Linux启动
echo ├── README.md           # 部署说明
echo ├── GLABAL.db          # PLC定义（参考）
echo └── PLCValues.xlsx     # 变量表（参考）
) > "%TEMP%\%PACKAGE_NAME%\DIRECTORY_STRUCTURE.txt"

:: 创建压缩包
echo [提示] 创建压缩包...
set DATE=%date:~0,4%%date:~5,2%%date:~8,2%
cd "%TEMP%"
powershell -command "Compress-Archive -Path '%PACKAGE_NAME%' -DestinationPath '%OUTPUT_DIR%\%PACKAGE_NAME%_%DATE%.zip' -Force"

if exist "%OUTPUT_DIR%\%PACKAGE_NAME%_%DATE%.zip" (
    echo.
    echo ========================================
    echo    打包完成！
    echo ========================================
    echo.
    echo 打包文件位置:
    echo %OUTPUT_DIR%\%PACKAGE_NAME%_%DATE%.zip
    echo.
    echo 文件包含:
    echo   - 完整源代码
    echo   - 配置文件
    echo   - 启动脚本
    echo   - 部署说明
    echo   - 参考文档
    echo.
    echo 部署步骤:
    echo   1. 解压文件到目标目录
    echo   2. 双击运行 start.bat
    echo   3. 打开浏览器访问 http://localhost:3000
    echo.
) else (
    echo [错误] 打包失败！
)

:: 清理临时目录
rmdir /s /q "%TEMP%\%PACKAGE_NAME%" >nul 2>&1

pause
