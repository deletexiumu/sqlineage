#!/bin/bash

# HiicHiveIDE 生产环境部署脚本
# 用于生产环境的部署和更新

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_NAME="HiicHiveIDE"
DEPLOY_USER="hive_ide"
DEPLOY_PATH="/opt/hive_ide"
BACKUP_PATH="/opt/backups/hive_ide"
NGINX_CONFIG="/etc/nginx/sites-available/hive_ide"
SYSTEMD_BACKEND="/etc/systemd/system/hive_ide_backend.service"

# 显示帮助信息
show_help() {
    echo "HiicHiveIDE 生产环境部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help        显示此帮助信息"
    echo "  --install         首次安装部署"
    echo "  --update          更新现有部署"
    echo "  --backup          备份当前部署"
    echo "  --rollback        回滚到上一个版本"
    echo "  --status          查看服务状态"
    echo "  --logs            查看服务日志"
    echo ""
}

# 检查权限
check_permissions() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}❌ 请使用 root 权限运行此脚本${NC}"
        exit 1
    fi
}

# 创建部署用户
create_deploy_user() {
    echo -e "${BLUE}👤 创建部署用户...${NC}"
    
    if ! id "$DEPLOY_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d $DEPLOY_PATH -m $DEPLOY_USER
        echo -e "${GREEN}✅ 用户 $DEPLOY_USER 创建成功${NC}"
    else
        echo -e "${YELLOW}⚠️  用户 $DEPLOY_USER 已存在${NC}"
    fi
}

# 安装系统依赖
install_system_dependencies() {
    echo -e "${BLUE}📦 安装系统依赖...${NC}"
    
    # 更新系统包
    apt update
    
    # 安装基础依赖
    apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        nodejs \
        npm \
        nginx \
        supervisor \
        git \
        curl \
        wget \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3-dev
    
    # 安装 Kerberos 客户端（如需要）
    apt install -y krb5-user libkrb5-dev
    
    echo -e "${GREEN}✅ 系统依赖安装完成${NC}"
}

# 配置 Nginx
configure_nginx() {
    echo -e "${BLUE}🌐 配置 Nginx...${NC}"
    
    cat > $NGINX_CONFIG << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # 修改为您的域名
    
    # 前端静态文件
    location / {
        root /opt/hive_ide/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
    
    # API 请求代理到后端
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
    
    # Django 管理后台
    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 静态文件（Django）
    location /static/ {
        alias /opt/hive_ide/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # 日志配置
    access_log /var/log/nginx/hive_ide_access.log;
    error_log /var/log/nginx/hive_ide_error.log;
}
EOF
    
    # 启用站点
    ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/hive_ide
    rm -f /etc/nginx/sites-enabled/default  # 删除默认站点
    
    # 测试配置
    nginx -t
    systemctl restart nginx
    systemctl enable nginx
    
    echo -e "${GREEN}✅ Nginx 配置完成${NC}"
}

# 配置 Systemd 服务
configure_systemd() {
    echo -e "${BLUE}⚙️  配置 Systemd 服务...${NC}"
    
    cat > $SYSTEMD_BACKEND << EOF
[Unit]
Description=HiicHiveIDE Backend Service
After=network.target

[Service]
Type=exec
User=$DEPLOY_USER
Group=$DEPLOY_USER
WorkingDirectory=$DEPLOY_PATH
Environment=PATH=$DEPLOY_PATH/venv/bin
ExecStart=$DEPLOY_PATH/venv/bin/gunicorn hive_ide.wsgi:application \\
    --bind 127.0.0.1:8000 \\
    --workers 4 \\
    --worker-class sync \\
    --timeout 300 \\
    --keepalive 2 \\
    --max-requests 1000 \\
    --max-requests-jitter 100 \\
    --access-logfile $DEPLOY_PATH/logs/gunicorn_access.log \\
    --error-logfile $DEPLOY_PATH/logs/gunicorn_error.log \\
    --log-level info
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable hive_ide_backend
    
    echo -e "${GREEN}✅ Systemd 服务配置完成${NC}"
}

# 部署应用
deploy_application() {
    echo -e "${BLUE}🚀 部署应用...${NC}"
    
    # 创建目录
    mkdir -p $DEPLOY_PATH
    mkdir -p $BACKUP_PATH
    mkdir -p $DEPLOY_PATH/logs
    
    # 设置权限
    chown -R $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH
    chown -R $DEPLOY_USER:$DEPLOY_USER $BACKUP_PATH
    
    # 切换到部署用户
    sudo -u $DEPLOY_USER bash << 'EOSU'
cd /opt/hive_ide

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装 Python 依赖
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 构建前端
cd frontend
npm install
npm run build
cd ..

# 数据库迁移
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate

# 创建必要目录
mkdir -p logs
mkdir -p /tmp/git_repos
chmod 755 logs
chmod 755 /tmp/git_repos

EOSU
    
    echo -e "${GREEN}✅ 应用部署完成${NC}"
}

# 创建环境配置文件
create_env_config() {
    echo -e "${BLUE}⚙️  创建环境配置...${NC}"
    
    cat > $DEPLOY_PATH/.env << 'EOF'
# 生产环境配置
ENVIRONMENT=production
DEBUG=False

# 安全配置
SECRET_KEY=your-secret-key-here  # 请修改为随机生成的密钥
ALLOWED_HOSTS=your-domain.com,localhost,127.0.0.1

# 数据库配置
DATABASE_URL=sqlite:///opt/hive_ide/db.sqlite3

# Hive 配置
HIVE_HOST=your-hive-host
HIVE_PORT=10000
HIVE_AUTH=KERBEROS

# SQLFlow 服务配置
SQLFLOW_URL=http://localhost:9600/sqlflow/datalineage

# Git 加密密钥
GIT_ENCRYPTION_KEY=your-encryption-key-here  # 请修改为生成的密钥

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/opt/hive_ide/logs/hive_ide.log
EOF
    
    chown $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH/.env
    chmod 600 $DEPLOY_PATH/.env
    
    echo -e "${YELLOW}⚠️  请编辑 $DEPLOY_PATH/.env 文件并设置正确的配置${NC}"
}

# 备份当前部署
backup_deployment() {
    echo -e "${BLUE}💾 备份当前部署...${NC}"
    
    if [ -d "$DEPLOY_PATH" ]; then
        BACKUP_NAME="hive_ide_backup_$(date +%Y%m%d_%H%M%S)"
        tar -czf "$BACKUP_PATH/$BACKUP_NAME.tar.gz" -C "$(dirname $DEPLOY_PATH)" "$(basename $DEPLOY_PATH)"
        echo -e "${GREEN}✅ 备份完成: $BACKUP_PATH/$BACKUP_NAME.tar.gz${NC}"
    else
        echo -e "${YELLOW}⚠️  没有找到现有部署，跳过备份${NC}"
    fi
}

# 查看服务状态
show_status() {
    echo -e "${BLUE}📊 服务状态${NC}"
    echo "================================"
    
    # 检查 Nginx
    if systemctl is-active --quiet nginx; then
        echo -e "${GREEN}✅ Nginx: 运行中${NC}"
    else
        echo -e "${RED}❌ Nginx: 未运行${NC}"
    fi
    
    # 检查后端服务
    if systemctl is-active --quiet hive_ide_backend; then
        echo -e "${GREEN}✅ 后端服务: 运行中${NC}"
    else
        echo -e "${RED}❌ 后端服务: 未运行${NC}"
    fi
    
    # 检查端口
    if netstat -tuln | grep -q :80; then
        echo -e "${GREEN}✅ 端口 80: 监听中${NC}"
    else
        echo -e "${RED}❌ 端口 80: 未监听${NC}"
    fi
    
    if netstat -tuln | grep -q :8000; then
        echo -e "${GREEN}✅ 端口 8000: 监听中${NC}"
    else
        echo -e "${RED}❌ 端口 8000: 未监听${NC}"
    fi
    
    echo "================================"
}

# 查看日志
show_logs() {
    echo -e "${BLUE}📋 查看服务日志${NC}"
    echo "================================"
    
    echo "选择要查看的日志:"
    echo "1. Nginx 错误日志"
    echo "2. Nginx 访问日志"
    echo "3. 后端应用日志"
    echo "4. Gunicorn 错误日志"
    echo "5. Systemd 服务日志"
    
    read -p "请输入选择 (1-5): " choice
    
    case $choice in
        1) tail -f /var/log/nginx/hive_ide_error.log ;;
        2) tail -f /var/log/nginx/hive_ide_access.log ;;
        3) tail -f $DEPLOY_PATH/logs/hive_ide.log ;;
        4) tail -f $DEPLOY_PATH/logs/gunicorn_error.log ;;
        5) journalctl -u hive_ide_backend -f ;;
        *) echo "无效选择" ;;
    esac
}

# 启动服务
start_services() {
    echo -e "${BLUE}🚀 启动服务...${NC}"
    
    systemctl start hive_ide_backend
    systemctl start nginx
    
    echo -e "${GREEN}✅ 服务启动完成${NC}"
}

# 停止服务
stop_services() {
    echo -e "${BLUE}🛑 停止服务...${NC}"
    
    systemctl stop hive_ide_backend
    systemctl stop nginx
    
    echo -e "${GREEN}✅ 服务停止完成${NC}"
}

# 主函数
main() {
    case "${1:-}" in
        --install)
            check_permissions
            echo -e "${YELLOW}🎯 开始首次安装部署${NC}"
            create_deploy_user
            install_system_dependencies
            deploy_application
            configure_nginx
            configure_systemd
            create_env_config
            start_services
            show_status
            echo -e "${GREEN}🎉 安装部署完成！${NC}"
            echo -e "请访问: ${BLUE}http://your-domain.com${NC}"
            ;;
        --update)
            check_permissions
            echo -e "${YELLOW}🔄 开始更新部署${NC}"
            backup_deployment
            stop_services
            deploy_application
            start_services
            show_status
            echo -e "${GREEN}🎉 更新完成！${NC}"
            ;;
        --backup)
            check_permissions
            backup_deployment
            ;;
        --status)
            show_status
            ;;
        --logs)
            show_logs
            ;;
        --start)
            check_permissions
            start_services
            ;;
        --stop)
            check_permissions
            stop_services
            ;;
        -h|--help|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"