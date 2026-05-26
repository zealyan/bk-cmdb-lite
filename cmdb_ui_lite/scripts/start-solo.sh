#!/bin/bash

# CMDB Lite - SOLO云端环境预览脚本
# 用于SOLO云端预览和测试环境
# 注意：使用 server.js 提供静态文件 + API 代理

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

# 日志文件
BACKEND_LOG="/tmp/cmdb_backend.log"
PROXY_LOG="/tmp/cmdb_proxy.log"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  CMDB Lite - SOLO云端环境预览${NC}"
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

    # 停止 Node.js 服务器
    if pgrep -f "node.*server.js" > /dev/null; then
        pkill -f "node.*server.js" || true
        echo -e "${GREEN}✓ 预览服务已停止${NC}"
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
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 后端服务启动成功 (PID: $BACKEND_PID)${NC}"
        echo "  - 地址: http://localhost:8000"
        echo "  - 日志: $BACKEND_LOG"
    else
        echo -e "${RED}✗ 后端服务启动失败${NC}"
        echo "请查看日志: tail -f $BACKEND_LOG"
        exit 1
    fi
}

# 构建前端
build_frontend() {
    echo -e "${YELLOW}构建前端...${NC}"

    cd "$FRONTEND_DIR"

    # 检查node_modules
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}安装依赖...${NC}"
        npm install
    fi

    # 构建前端
    npm run build

    echo -e "${GREEN}✓ 前端构建完成${NC}"
}

# 启动预览服务（带 API 代理）
start_preview() {
    echo -e "${YELLOW}启动预览服务（带 API 代理）...${NC}"

    cd "$FRONTEND_DIR"

    # 启动 Node.js 服务器（带 API 代理）
    nohup node server.js > "$PROXY_LOG" 2>&1 &
    PREVIEW_PID=$!

    # 等待服务启动
    sleep 3

    # 捕获实际分配的端口
    if [ -f "$PROXY_LOG" ]; then
        PREVIEW_URL=$(grep -oP 'localhost:\K[0-9]+' "$PROXY_LOG" | head -1 || echo "")
    fi

    # 如果没有捕获到端口，尝试检测
    if [ -z "$PREVIEW_URL" ]; then
        for port in 3000 3001 3002 3003 5000 5001 8080; do
            if check_port $port; then
                PREVIEW_URL=$port
                break
            fi
        done
    fi

    # 如果仍然是空的，默认为 3000
    if [ -z "$PREVIEW_URL" ]; then
        PREVIEW_URL=3000
    fi

    # 验证服务状态
    if curl -s http://localhost:$PREVIEW_URL/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 预览服务启动成功${NC}"
        echo "  - PID: $PREVIEW_PID"
        echo "  - 地址: http://localhost:$PREVIEW_URL"
        echo "  - 日志: $PROXY_LOG"
        echo ""
        echo -e "${BLUE}预览地址: http://localhost:$PREVIEW_URL${NC}"
    else
        echo -e "${RED}✗ 预览服务启动失败${NC}"
        echo "请查看日志: tail -f $PROXY_LOG"
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
            echo ""
            echo "注意: 使用 server.js 提供静态文件 + API 代理"
            exit 0
            ;;
    esac

    # 停止已有服务
    stop_services

    # 启动后端
    start_backend

    # 构建前端
    build_frontend

    # 启动预览服务
    start_preview

    # 完成
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  预览服务已启动！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "架构说明:"
    echo "  - 静态文件: dist/"
    echo "  - API 代理: /api/* -> localhost:8000"
    echo ""
    echo "常用命令:"
    echo "  查看后端日志: tail -f $BACKEND_LOG"
    echo "  查看预览日志: tail -f $PROXY_LOG"
    echo "  停止服务:     $0 --stop"
    echo ""
}

main "$@"
