#!/bin/bash

# CMDB Lite - 一键构建脚本
# 用于构建前端生产版本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/cmdb_ui_lite"

# 目标目录
DIST_DIR="$FRONTEND_DIR/dist"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  CMDB Lite - 构建脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 清理函数
clean() {
    echo -e "${YELLOW}清理构建产物...${NC}"
    cd "$FRONTEND_DIR"

    if [ -d "dist" ]; then
        rm -rf dist
        echo -e "${GREEN}✓ 清理完成${NC}"
    else
        echo -e "${YELLOW}无需清理${NC}"
    fi
}

# 构建函数
build() {
    echo -e "${YELLOW}开始构建...${NC}"
    cd "$FRONTEND_DIR"

    # 安装依赖（如果需要）
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}安装依赖...${NC}"
        npm install
    fi

    # 执行构建
    echo -e "${YELLOW}执行 npm run build...${NC}"
    npm run build

    echo -e "${GREEN}✓ 构建完成${NC}"
}

# 验证函数
verify() {
    echo -e "${YELLOW}验证构建产物...${NC}"

    if [ ! -d "$DIST_DIR" ]; then
        echo -e "${RED}✗ 错误: 构建产物目录不存在${NC}"
        exit 1
    fi

    if [ ! -f "$DIST_DIR/index.html" ]; then
        echo -e "${RED}✗ 错误: index.html 不存在${NC}"
        exit 1
    fi

    # 统计文件数量
    FILE_COUNT=$(find "$DIST_DIR" -type f | wc -l)
    echo -e "${GREEN}✓ 构建产物验证通过${NC}"
    echo "  - 文件数量: $FILE_COUNT"
    echo "  - 产物目录: $DIST_DIR"
}

# 部署提示
deploy() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  构建完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "构建产物位置: $DIST_DIR"
    echo ""
    echo "部署选项:"
    echo "  1. SOLO云端部署: node $FRONTEND_DIR/server.js"
    echo "  2. Nginx部署:   配置静态文件目录为 $DIST_DIR"
    echo "  3. 其他CDN:     上传 $DIST_DIR 目录到CDN"
    echo ""
}

# 主流程
main() {
    case "${1:-}" in
        --clean)
            clean
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --clean  只清理构建产物，不构建"
            echo "  --help   显示帮助信息"
            echo ""
            echo "示例:"
            echo "  $0         # 执行完整构建"
            echo "  $0 --clean # 清理构建产物"
            ;;
        *)
            clean
            build
            verify
            deploy
            ;;
    esac
}

main "$@"
