#!/usr/bin/env bash
# HiicHiveIDE 初始化脚本
# 用于首次部署和环境配置

set -e

echo "🚀 开始初始化 HiicHiveIDE..."

# ────────────────────────────────────────────────────────────
# 选择（并锁定）Python 解释器：优先 python3.12，无则退回 python3
# ────────────────────────────────────────────────────────────
if command -v python3.12 >/dev/null 2>&1; then
    PY_BIN=$(command -v python3.12)
else
    PY_BIN=$(command -v python3 || true)
fi

if [ -z "$PY_BIN" ]; then
    echo "❌ 未找到可用 Python，请先安装 Python 3.12+"
    exit 1
fi

# ────────────────────────────────────────────────────────────
# 检查 Python 版本
# ────────────────────────────────────────────────────────────
echo "📋 检查 Python 版本..."
python_version=$("$PY_BIN" --version 2>&1 | awk '{print $2}')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python 版本符合要求: $python_version (路径: $PY_BIN)"
else
    echo "❌ Python 版本过低，需要 3.8+，当前版本: $python_version"
    exit 1
fi

# ────────────────────────────────────────────────────────────
# 检查 Node.js 版本
# ────────────────────────────────────────────────────────────
echo "📋 检查 Node.js 版本..."
if command -v node >/dev/null 2>&1; then
    node_major=$(node -p "parseInt(require('process').versions.node.split('.')[0], 10)")
    if [ "$node_major" -ge 16 ]; then
        echo "✅ Node.js 版本符合要求: $(node --version)"
    else
        echo "❌ Node.js 版本过低，需要 16+，当前版本: $(node --version)"
        exit 1
    fi
else
    echo "❌ 未安装 Node.js，请先安装 Node.js 16+"
    exit 1
fi

# ────────────────────────────────────────────────────────────
# 创建虚拟环境
# ────────────────────────────────────────────────────────────
echo "🐍 创建 Python 虚拟环境..."
if [ ! -d "venv" ]; then
    "$PY_BIN" -m venv venv
    echo "✅ 虚拟环境创建完成 (Python $python_version)"
else
    echo "⚠️  虚拟环境已存在，跳过创建"
fi

# ────────────────────────────────────────────────────────────
# 激活虚拟环境
# ────────────────────────────────────────────────────────────
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 编译 sasl 依赖的头文件搜索路径（根据你的机器调整）
export CFLAGS="-I/opt/homebrew/opt/cyrus-sasl/include"
export LDFLAGS="-L/opt/homebrew/opt/cyrus-sasl/lib"

# ────────────────────────────────────────────────────────────
# 安装 Python 依赖
# ────────────────────────────────────────────────────────────
echo "📦 安装 Python 依赖..."
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn -U pip
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn -r requirements.txt
echo "✅ Python 依赖安装完成"

# ────────────────────────────────────────────────────────────
# 安装前端依赖
# ────────────────────────────────────────────────────────────
echo "📦 安装前端依赖..."
pushd frontend >/dev/null
npm install
echo "✅ 前端依赖安装完成"
popd >/dev/null

# ────────────────────────────────────────────────────────────
# 数据库初始化
# ────────────────────────────────────────────────────────────
echo "🗄️  检查并初始化数据库..."

# 确保Django项目存在
if [ ! -f "manage.py" ]; then
    echo "❌ manage.py 文件不存在，请确认在正确的项目目录下运行"
    exit 1
fi

# 检查数据库文件是否存在
if [ ! -f "db.sqlite3" ]; then
    echo "📄 数据库文件不存在，创建新数据库..."
    # 首先检查是否有未创建的迁移文件
    echo "  - 生成迁移文件..."
    "$PY_BIN" manage.py makemigrations apps_core apps_metadata apps_git apps_lineage
    echo "  - 执行数据库迁移..."
    "$PY_BIN" manage.py migrate
    echo "✅ 数据库创建完成"
else
    echo "📄 数据库文件已存在，检查迁移状态..."
    
    # 检查各个应用的迁移状态
    migration_needed=false
    
    # 检查是否有新的迁移需要创建
    if ! "$PY_BIN" manage.py makemigrations --check --dry-run >/dev/null 2>&1; then
        echo "  - 检测到模型更改，生成新的迁移文件..."
        "$PY_BIN" manage.py makemigrations
        migration_needed=true
    fi
    
    # 检查是否有未应用的迁移
    if [ "$("$PY_BIN" manage.py showmigrations --list | grep '\[ \]' | wc -l)" -gt 0 ]; then
        echo "  - 检测到未应用的迁移，执行迁移..."
        migration_needed=true
    fi
    
    if [ "$migration_needed" = true ]; then
        "$PY_BIN" manage.py migrate
        echo "✅ 数据库迁移完成"
    else
        echo "✅ 数据库状态正常，无需迁移"
    fi
fi

# 创建认证Token表（如果不存在）
echo "🔑 确保认证Token表存在..."
"$PY_BIN" manage.py shell -c "
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
# 为所有用户创建Token（如果不存在）
for user in User.objects.all():
    Token.objects.get_or_create(user=user)
print('✅ Token表检查完成')
" 2>/dev/null || echo "  - Token表将在首次登录时自动创建"

# ────────────────────────────────────────────────────────────
# 可选：创建超级用户
# ────────────────────────────────────────────────────────────
echo "👤 是否创建超级用户？(y/n)"
read -r create_superuser
if [[ "$create_superuser" =~ ^[Yy]$ ]]; then
    "$PY_BIN" manage.py createsuperuser
fi

# ────────────────────────────────────────────────────────────
# 创建必要的目录
# ────────────────────────────────────────────────────────────
echo "📁 创建必要的目录..."
mkdir -p logs /tmp/git_repos
chmod 755 logs /tmp/git_repos
echo "✅ 目录创建完成"

# ────────────────────────────────────────────────────────────
# 生成加密密钥
# ────────────────────────────────────────────────────────────
echo "🔐 生成加密密钥..."
"$PY_BIN" - <<'PY'
from cryptography.fernet import Fernet
key = Fernet.generate_key().decode()
print("请将以下密钥添加到 settings.py：")
print(f'GIT_ENCRYPTION_KEY = "{key}"')
PY

echo
echo "🎉 HiicHiveIDE 初始化完成！"
echo
echo "接下来："
echo "1️⃣ 配置 hive_ide/settings.py 中的 Hive 和 SQLFlow 服务地址"
echo "2️⃣ 运行 './scripts/start.sh' 启动服务"
echo "3️⃣ 访问 http://localhost:8000 (后端) 和 http://localhost:5173 (前端)"
echo
echo "更多信息请查看 README.md"