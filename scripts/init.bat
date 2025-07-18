 @echo off
REM HiicHiveIDE 初始化脚本 (Windows批处理版)
REM 用于首次部署和环境配置

chcp 65001 >nul

echo 🚀 开始初始化 HiicHiveIDE...

REM ────────────────────────────────────────────────────────────
REM 检查Python版本
REM ────────────────────────────────────────────────────────────
echo 📋 检查 Python 版本...

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version') do (
    echo ✅ Python 版本: %%v
)

REM ────────────────────────────────────────────────────────────
REM 检查Node.js版本
REM ────────────────────────────────────────────────────────────
echo 📋 检查 Node.js 版本...

node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Node.js，请先安装 Node.js 16+
    pause
    exit /b 1
)

for /f %%v in ('node --version') do (
    echo ✅ Node.js 版本: %%v
)

REM ────────────────────────────────────────────────────────────
REM 创建虚拟环境
REM ────────────────────────────────────────────────────────────
echo 🐍 创建 Python 虚拟环境...

if not exist venv (
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo ✅ 虚拟环境创建完成
) else (
    echo ⚠️  虚拟环境已存在，跳过创建
)

REM ────────────────────────────────────────────────────────────
REM 激活虚拟环境
REM ────────────────────────────────────────────────────────────
echo 🔧 激活虚拟环境...

call venv\Scripts\activate
if errorlevel 1 (
    echo ❌ 虚拟环境激活失败
    pause
    exit /b 1
)

REM ────────────────────────────────────────────────────────────
REM 安装Python依赖
REM ────────────────────────────────────────────────────────────
echo 📦 安装 Python 依赖...

python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn -U pip
if errorlevel 1 (
    echo ❌ pip 升级失败
    pause
    exit /b 1
)

if exist requirements.txt (
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn -r requirements.txt
    if errorlevel 1 (
        echo ❌ Python 依赖安装失败
        pause
        exit /b 1
    )
    echo ✅ Python 依赖安装完成
) else (
    echo ⚠️  requirements.txt 文件不存在，跳过依赖安装
)

REM ────────────────────────────────────────────────────────────
REM 安装前端依赖
REM ────────────────────────────────────────────────────────────
echo 📦 安装前端依赖...

if exist frontend (
    cd frontend
    npm install
    if errorlevel 1 (
        echo ❌ 前端依赖安装失败
        cd ..
        pause
        exit /b 1
    )
    echo ✅ 前端依赖安装完成
    cd ..
) else (
    echo ⚠️  frontend 目录不存在，跳过前端依赖安装
)

REM ────────────────────────────────────────────────────────────
REM 数据库初始化
REM ────────────────────────────────────────────────────────────
echo 🗄️  检查并初始化数据库...

if not exist manage.py (
    echo ❌ manage.py 文件不存在，请确认在正确的项目目录下运行
    pause
    exit /b 1
)

if not exist db.sqlite3 (
    echo 📄 数据库文件不存在，创建新数据库...
    echo   - 生成迁移文件...
    python manage.py makemigrations apps_core apps_metadata apps_git apps_lineage
    if errorlevel 1 (
        echo ❌ 迁移文件生成失败
        pause
        exit /b 1
    )
    echo   - 执行数据库迁移...
    python manage.py migrate
    if errorlevel 1 (
        echo ❌ 数据库创建失败
        pause
        exit /b 1
    )
    echo ✅ 数据库创建完成
) else (
    echo 📄 数据库文件已存在，检查迁移状态...
    
    set migration_needed=false
    
    REM 检查是否有新的迁移需要创建
    python manage.py makemigrations --check --dry-run >nul 2>&1
    if errorlevel 1 (
        echo   - 检测到模型更改，生成新的迁移文件...
        python manage.py makemigrations
        set migration_needed=true
    )
    
    REM 检查是否有未应用的迁移
    python manage.py showmigrations --list | findstr /C:"[ ]" >nul
    if not errorlevel 1 (
        echo   - 检测到未应用的迁移，需要执行迁移...
        set migration_needed=true
    )
    
    if "%migration_needed%"=="true" (
        python manage.py migrate
        if errorlevel 1 (
            echo ❌ 数据库迁移失败
            pause
            exit /b 1
        )
        echo ✅ 数据库迁移完成
    ) else (
        echo ✅ 数据库状态正常，无需迁移
    )
)

REM 创建认证Token表
echo 🔑 确保认证Token表存在...
python -c "from django.contrib.auth.models import User; from rest_framework.authtoken.models import Token; [Token.objects.get_or_create(user=user) for user in User.objects.all()]; print('✅ Token表检查完成')" 2>nul || echo   - Token表将在首次登录时自动创建

REM ────────────────────────────────────────────────────────────
REM 可选：创建超级用户
REM ────────────────────────────────────────────────────────────
set /p create_user=👤 是否创建超级用户？(y/n): 
if /i "%create_user%"=="y" (
    python manage.py createsuperuser
)

REM ────────────────────────────────────────────────────────────
REM 创建必要的目录
REM ────────────────────────────────────────────────────────────
echo 📁 创建必要的目录...

if not exist logs mkdir logs
if not exist tmp mkdir tmp
if not exist tmp\git_repos mkdir tmp\git_repos
echo ✅ 目录创建完成

REM ────────────────────────────────────────────────────────────
REM 生成加密密钥
REM ────────────────────────────────────────────────────────────
echo 🔐 生成加密密钥...

python -c "from cryptography.fernet import Fernet; key = Fernet.generate_key().decode(); print('请将以下密钥添加到 hive_ide/settings.py：'); print(f'GIT_ENCRYPTION_KEY = \"{key}\"')"

echo.
echo 🎉 HiicHiveIDE 初始化完成！
echo.
echo 接下来：
echo 1️⃣ 配置 hive_ide/settings.py 中的 Hive 和 SQLFlow 服务地址
echo 2️⃣ 运行 'scripts\start.bat' 启动服务
echo 3️⃣ 访问 http://localhost:8000 (后端) 和 http://localhost:5173 (前端)
echo.
echo 更多信息请查看 README.md

pause