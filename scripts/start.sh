#!/bin/bash

# HiicHiveIDE 启动脚本
# 用于启动前端和后端服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo "HiicHiveIDE 启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help        显示此帮助信息"
    echo "  -b, --backend     仅启动后端服务"
    echo "  -f, --frontend    仅启动前端服务"
    echo "  -d, --dev         开发模式（默认）"
    echo "  -p, --prod        生产模式"
    echo "  --stop            停止所有服务"
    echo ""
    echo "示例:"
    echo "  $0                启动所有服务（开发模式）"
    echo "  $0 --backend      仅启动后端"
    echo "  $0 --prod         生产模式启动"
    echo "  $0 --stop         停止所有服务"
}

# 检查服务状态
check_service() {
    local service_name=$1
    local port=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${GREEN}✅ $service_name 正在运行 (端口 $port)${NC}"
        return 0
    else
        echo -e "${RED}❌ $service_name 未运行 (端口 $port)${NC}"
        return 1
    fi
}

# 停止服务
stop_services() {
    echo -e "${YELLOW}🛑 停止 HiicHiveIDE 服务...${NC}"
    
    # 停止SQLFlow服务
    echo "停止SQLFlow服务..."
    pkill -f "java.*java_data_lineage-1.1.2.jar" || true
    
    # 停止后端服务（Django/Daphne）
    echo "停止后端服务..."
    pkill -f "python.*manage.py.*runserver" || true
    pkill -f "daphne.*hive_ide.asgi" || true
    
    # 停止前端服务（Vite）
    echo "停止前端服务..."
    pkill -f "vite" || true
    pkill -f "node.*vite" || true
    
    echo -e "${GREEN}✅ 所有服务已停止${NC}"
    exit 0
}

# 启动SQLFlow服务
start_sqlflow() {
    echo -e "${BLUE}🔧 启动SQLFlow服务...${NC}"
    
    # 检查jar文件是否存在
    if [ ! -f "sqlflow_engine_lite/java_data_lineage-1.1.2.jar" ]; then
        echo -e "${RED}❌ SQLFlow jar文件不存在${NC}"
        return 1
    fi
    
    # 检查Java是否安装
    if ! command -v java >/dev/null 2>&1; then
        echo -e "${RED}❌ Java未安装，请先安装Java 8+${NC}"
        return 1
    fi
    
    # 检查端口是否被占用
    if lsof -Pi :19600 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  端口19600已被占用，停止现有服务...${NC}"
        pkill -f "java.*java_data_lineage-1.1.2.jar" || true
        sleep 2
    fi
    
    # 启动SQLFlow服务
    echo "启动SQLFlow引擎..."
    nohup java -jar sqlflow_engine_lite/java_data_lineage-1.1.2.jar \
        --server.host=localhost \
        --server.port=19600 > logs/sqlflow.log 2>&1 &
    
    SQLFLOW_PID=$!
    echo "SQLFlow服务 PID: $SQLFLOW_PID"
    
    # 等待服务启动
    echo "等待SQLFlow服务启动..."
    sleep 5
    
    # 检查服务状态
    if check_service "SQLFlow引擎" 19600; then
        echo -e "${GREEN}✅ SQLFlow服务启动成功${NC}"
        return 0
    else
        echo -e "${RED}❌ SQLFlow服务启动失败${NC}"
        echo "请检查日志: tail -f logs/sqlflow.log"
        return 1
    fi
}

# 启动后端服务
start_backend() {
    echo -e "${BLUE}🚀 启动后端服务...${NC}"
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        echo -e "${RED}❌ 虚拟环境不存在，请先运行 ./scripts/init.sh${NC}"
        exit 1
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 检查数据库状态
    echo "检查数据库状态..."
    if [ ! -f "db.sqlite3" ]; then
        echo "数据库文件不存在，自动创建..."
        python manage.py makemigrations
        python manage.py migrate
        echo "数据库创建完成"
    else
        # 检查数据库迁移
        python manage.py makemigrations --check --dry-run >/dev/null 2>&1 || {
            echo "执行数据库迁移..."
            python manage.py makemigrations
            python manage.py migrate
        }
    fi
    
    # 设置Django环境变量
    export DJANGO_SETTINGS_MODULE=hive_ide.settings
    
    # 启动Django服务
    if [ "$MODE" = "prod" ]; then
        echo "生产模式启动后端（ASGI）..."
        daphne -b 0.0.0.0 -p 8000 hive_ide.asgi:application &
    else
        echo "开发模式启动后端（ASGI支持WebSocket）..."
        daphne -b 0.0.0.0 -p 8000 hive_ide.asgi:application &
    fi
    
    BACKEND_PID=$!
    echo "后端服务 PID: $BACKEND_PID"
    
    # 等待服务启动
    sleep 3
    if check_service "Django后端" 8000; then
        echo -e "${GREEN}✅ 后端服务启动成功${NC}"
    else
        echo -e "${RED}❌ 后端服务启动失败${NC}"
        exit 1
    fi
}

# 启动前端服务
start_frontend() {
    echo -e "${BLUE}🚀 启动前端服务...${NC}"
    
    # 检查前端依赖
    if [ ! -d "frontend/node_modules" ]; then
        echo -e "${RED}❌ 前端依赖未安装，请先运行 ./scripts/init.sh${NC}"
        exit 1
    fi
    
    cd frontend
    
    if [ "$MODE" = "prod" ]; then
        echo "生产模式构建前端..."
        npm run build
        echo "前端构建完成，文件位于 frontend/dist/"
        # 生产模式下通常使用 nginx 等服务器托管静态文件
    else
        echo "开发模式启动前端..."
        npm run dev &
        FRONTEND_PID=$!
        echo "前端服务 PID: $FRONTEND_PID"
        
        # 等待服务启动
        sleep 5
        if check_service "Vue前端" 5173; then
            echo -e "${GREEN}✅ 前端服务启动成功${NC}"
        else
            echo -e "${RED}❌ 前端服务启动失败${NC}"
            exit 1
        fi
    fi
    
    cd ..
}

# 显示服务状态
show_status() {
    echo -e "${BLUE}📊 服务状态检查${NC}"
    echo "================================"
    check_service "SQLFlow引擎" 19600
    check_service "Django后端" 8000
    if [ "$MODE" != "prod" ]; then
        check_service "Vue前端" 5173
    fi
    echo "================================"
}

# 主函数
main() {
    # 默认参数
    START_BACKEND=false
    START_FRONTEND=false
    START_ALL=true
    MODE="dev"
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -b|--backend)
                START_BACKEND=true
                START_ALL=false
                shift
                ;;
            -f|--frontend)
                START_FRONTEND=true
                START_ALL=false
                shift
                ;;
            -d|--dev)
                MODE="dev"
                shift
                ;;
            -p|--prod)
                MODE="prod"
                shift
                ;;
            --stop)
                stop_services
                ;;
            --status)
                show_status
                exit 0
                ;;
            *)
                echo "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    echo -e "${YELLOW}🎯 HiicHiveIDE 启动脚本${NC}"
    echo "模式: $MODE"
    echo "================================"
    
    # 停止现有服务
    echo "停止现有服务..."
    pkill -f "java.*java_data_lineage-1.1.2.jar" 2>/dev/null || true
    pkill -f "python.*manage.py.*runserver" 2>/dev/null || true
    pkill -f "daphne.*hive_ide.asgi" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    sleep 2
    
    # 根据参数启动相应服务
    if [ "$START_ALL" = true ]; then
        # 启动SQLFlow服务
        start_sqlflow
        if [ $? -ne 0 ]; then
            echo -e "${YELLOW}⚠️  SQLFlow服务启动失败，但继续启动其他服务${NC}"
        fi
        
        start_backend
        if [ "$MODE" != "prod" ]; then
            start_frontend
        fi
    elif [ "$START_BACKEND" = true ]; then
        # 仅启动后端时也启动SQLFlow
        start_sqlflow
        start_backend
    elif [ "$START_FRONTEND" = true ]; then
        start_frontend
    fi
    
    echo ""
    echo -e "${GREEN}🎉 HiicHiveIDE 启动完成！${NC}"
    echo "================================"
    
    if [ "$START_BACKEND" = true ] || [ "$START_ALL" = true ]; then
        echo -e "🔧 SQLFlow引擎: ${BLUE}http://localhost:19600${NC}"
        echo -e "📱 后端服务: ${BLUE}http://localhost:8000${NC}"
        echo -e "🔧 管理后台: ${BLUE}http://localhost:8000/admin${NC}"
        echo -e "📚 API文档: ${BLUE}http://localhost:8000/api${NC}"
    fi
    
    if [ "$START_FRONTEND" = true ] || ([ "$START_ALL" = true ] && [ "$MODE" != "prod" ]); then
        echo -e "🌐 前端界面: ${BLUE}http://localhost:5173${NC}"
    fi
    
    echo ""
    echo "常用管理命令:"
    echo "  爬取元数据: python manage.py crawl_metadata"
    echo "  创建用户:   python manage.py createsuperuser"
    echo "  查看日志:   tail -f logs/hive_ide.log"
    echo ""
    echo "按 Ctrl+C 停止服务"
    
    # 保持脚本运行，等待 Ctrl+C
    if [ "$START_ALL" = true ] || [ "$START_BACKEND" = true ] || [ "$START_FRONTEND" = true ]; then
        trap 'echo -e "\n${YELLOW}收到停止信号，正在关闭服务...${NC}"; stop_services' INT
        wait
    fi
}

# 执行主函数
main "$@"