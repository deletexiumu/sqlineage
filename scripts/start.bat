 @echo off
REM HiicHiveIDE 启动脚本 (Windows批处理版)
REM 用于启动前端和后端服务

chcp 65001 >nul

if "%1"=="--help" goto :show_help
if "%1"=="-h" goto :show_help
if "%1"=="--stop" goto :stop_services
if "%1"=="--status" goto :show_status

echo 🎯 HiicHiveIDE 启动脚本 (Windows版)
echo 模式: 开发模式
echo ================================

REM 停止现有服务
echo 停止现有服务...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
taskkill /F /IM java.exe >nul 2>&1
timeout /t 2 >nul

REM 启动SQLFlow服务
echo 🔧 启动SQLFlow服务...

if not exist sqlflow_engine_lite\java_data_lineage-1.1.2.jar (
    echo ❌ SQLFlow jar文件不存在
    goto :start_backend
)

java -version >nul 2>&1
if errorlevel 1 (
    echo ❌ Java未安装，跳过SQLFlow服务启动
    goto :start_backend
)

echo 启动SQLFlow引擎...
start "SQLFlow Engine" java -jar sqlflow_engine_lite\java_data_lineage-1.1.2.jar --server.host=localhost --server.port=19600

REM 等待SQLFlow服务启动
timeout /t 5 >nul

REM 检查SQLFlow服务状态
netstat -an | findstr ":19600" >nul
if errorlevel 1 (
    echo ⚠️  SQLFlow服务启动失败，但继续启动其他服务
) else (
    echo ✅ SQLFlow服务启动成功
)

:start_backend
REM 启动后端服务
echo 🚀 启动后端服务...

REM 检查虚拟环境
if not exist venv (
    echo ❌ 虚拟环境不存在，请先运行 scripts\init.bat
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate
if errorlevel 1 (
    echo ❌ 虚拟环境激活失败
    pause
    exit /b 1
)

REM 检查数据库状态
echo 检查数据库状态...
if exist manage.py (
    if not exist db.sqlite3 (
        echo 数据库文件不存在，自动创建...
        python manage.py makemigrations
        python manage.py migrate
        echo 数据库创建完成
    ) else (
        python manage.py makemigrations --check --dry-run >nul 2>&1
        if errorlevel 1 (
            echo 执行数据库迁移...
            python manage.py makemigrations
            python manage.py migrate
        )
    )
)

REM 启动Django服务（后台）
echo 开发模式启动后端...
start "Django Backend" python manage.py runserver 0.0.0.0:8000

REM 等待后端启动
timeout /t 3 >nul

REM 检查后端服务状态
netstat -an | findstr ":8000" >nul
if errorlevel 1 (
    echo ❌ 后端服务启动失败
    pause
    exit /b 1
) else (
    echo ✅ 后端服务启动成功
)

REM 启动前端服务
echo 🚀 启动前端服务...

REM 检查前端依赖
if not exist frontend\node_modules (
    echo ❌ 前端依赖未安装，请先运行 scripts\init.bat
    pause
    exit /b 1
)

REM 切换到前端目录并启动
cd frontend
echo 开发模式启动前端...
start "Vue Frontend" npm run dev

REM 等待前端启动
timeout /t 5 >nul

REM 检查前端服务状态
netstat -an | findstr ":5173" >nul
if errorlevel 1 (
    echo ❌ 前端服务启动失败
    cd ..
    pause
    exit /b 1
) else (
    echo ✅ 前端服务启动成功
)

cd ..

echo.
echo 🎉 HiicHiveIDE 启动完成！
echo ================================
echo 🔧 SQLFlow引擎: http://localhost:19600
echo 📱 后端服务: http://localhost:8000
echo 🔧 管理后台: http://localhost:8000/admin
echo 📚 API文档: http://localhost:8000/api
echo 🌐 前端界面: http://localhost:5173
echo.
echo 常用管理命令:
echo   爬取元数据: python manage.py crawl_metadata
echo   创建用户:   python manage.py createsuperuser
echo   查看日志:   type logs\hive_ide.log
echo.
echo 按任意键停止服务...
pause >nul

REM 停止服务
goto :stop_services

:show_help
echo HiicHiveIDE 启动脚本 (Windows批处理版)
echo.
echo 用法: scripts\start.bat [选项]
echo.
echo 选项:
echo   --help, -h        显示此帮助信息
echo   --stop            停止所有服务
echo   --status          显示服务状态
echo.
echo 示例:
echo   scripts\start.bat           启动所有服务
echo   scripts\start.bat --stop    停止所有服务
echo   scripts\start.bat --status  显示服务状态
pause
exit /b 0

:stop_services
echo 🛑 停止 HiicHiveIDE 服务...
taskkill /F /IM java.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
echo ✅ 所有服务已停止
if "%1"=="--stop" pause
exit /b 0

:show_status
echo 📊 服务状态检查
echo ================================
netstat -an | findstr ":19600" >nul
if errorlevel 1 (
    echo ❌ SQLFlow引擎 未运行 (端口 19600)
) else (
    echo ✅ SQLFlow引擎 正在运行 (端口 19600)
)

netstat -an | findstr ":8000" >nul
if errorlevel 1 (
    echo ❌ Django后端 未运行 (端口 8000)
) else (
    echo ✅ Django后端 正在运行 (端口 8000)
)

netstat -an | findstr ":5173" >nul
if errorlevel 1 (
    echo ❌ Vue前端 未运行 (端口 5173)
) else (
    echo ✅ Vue前端 正在运行 (端口 5173)
)
echo ================================
pause
exit /b 0