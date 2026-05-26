#!/bin/bash

# CMDB Lite - 本地开发环境启动脚本
# 用于本地开发调试，支持热重载

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_ROOT="/workspace/bk-cmdb"
BACKEND_DIR="$PROJECT_ROOT/cmdb_server_lite"
FRONTEND_DIR="$PROJECT_ROOT/cmdb_ui_lite"

# 端口配置
BACKEND_PORT=8000
FRONTEND_PORT=3001

# 日志文件
BACKEND_LOG="/tmp/cmdb_backend.log"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  CMDB Lite - 本地开发环境启动脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查函数
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 停止服务函数
stop_services() {
    echo -e "${YELLOW}正在停止已有服务...${NC}"

    # 停止后端服务
    if pgrep -f "python.*main.py" > /dev/null; then
        pkill -f "python.*main.py" || true
        echo -e "${GREEN}✓ 后端服务已停止${NC}"
    fi

    # 停止前端开发服务器
    if pgrep -f "vue-cli-service" > /dev/null; then
        pkill -f "vue-cli-service" || true
        echo -e "${GREEN}✓ 前端开发服务器已停止${NC}"
    fi

    sleep 2
}

# 启动后端服务
start_backend() {
    echo -e "${YELLOW}启动后端服务...${NC}"

    cd "$BACKEND_DIR"

    # 检查数据库文件
    if [ ! -f "cmdb.duckdb" ]; then
        echo -e "${RED}✗ 错误: 数据库文件不存在${NC}"
        echo "请确保在 $BACKEND_DIR 目录下运行初始化脚本"
        exit 1
    fi

    # 启动后端服务
    nohup python3 main.py > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!

    # 等待服务启动
    sleep 3

    # 检查服务是否启动成功
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 后端服务启动成功 (PID: $BACKEND_PID)${NC}"
        echo "  - 地址: http://localhost:$BACKEND_PORT"
        echo "  - 日志: $BACKEND_LOG"
    else
        echo -e "${RED}✗ 后端服务启动失败${NC}"
        echo "请查看日志: tail -f $BACKEND_LOG"
        exit 1
    fi
}

# 启动前端开发服务器
start_frontend_dev() {
    echo -e "${YELLOW}启动前端开发服务器 (热重载模式)...${NC}"

    cd "$FRONTEND_DIR"

    # 检查node_modules
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}安装依赖...${NC}"
        npm install
    fi

    # 启动开发服务器
    npm run dev &
    DEV_PID=$!

    # 等待服务启动
    sleep 5

    # 检查服务是否启动成功
    if check_port $FRONTEND_PORT; then
        echo -e "${GREEN}✓ 前端开发服务器启动成功 (PID: $DEV_PID)${NC}"
        echo "  - 地址: http://localhost:$FRONTEND_PORT"
        echo "  - 特点: 支持热重载，代码变更自动刷新"
    else
        echo -e "${RED}✗ 前端开发服务器启动失败${NC}"
        exit 1
    fi
}

# 主流程
main() {
    # 解析参数
    case "${1:-}" in
        --stop)
            stop_services
            echo -e "${GREEN}所有服务已停止${NC}"
            exit 0
            ;;
        --restart)
            stop_services
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --stop     停止所有服务"
            echo "  --restart  重启所有服务"
            echo "  --help     显示帮助信息"
            exit 0
            ;;
    esac

    # 停止已有服务
    stop_services

    # 启动后端
    start_backend

    # 启动前端开发服务器
    start_frontend_dev

    # 完成
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  所有服务启动完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "访问地址: ${BLUE}http://localhost:$FRONTEND_PORT${NC}"
    echo ""
    echo "特点:"
    echo "  - 支持热重载，代码变更自动刷新"
    echo "  - 适合快速开发和调试"
    echo ""
    echo "常用命令:"
    echo "  查看后端日志: tail -f $BACKEND_LOG"
    echo "  停止服务:     $0 --stop"
    echo ""
}

main "$@"
