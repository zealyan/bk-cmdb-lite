#!/bin/bash

# CMDB Lite - 停止所有服务脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  CMDB Lite - 停止所有服务${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 停止后端服务
echo -e "${YELLOW}停止后端服务...${NC}"
if pgrep -f "python.*main.py" > /dev/null; then
    pkill -f "python.*main.py"
    echo -e "${GREEN}✓ 后端服务已停止${NC}"
else
    echo -e "${YELLOW}后端服务未运行${NC}"
fi

# 停止代理服务器
echo -e "${YELLOW}停止API代理服务器...${NC}"
if pgrep -f "node.*server.js" > /dev/null; then
    pkill -f "node.*server.js"
    echo -e "${GREEN}✓ API代理服务器已停止${NC}"
else
    echo -e "${YELLOW}API代理服务器未运行${NC}"
fi

# 停止前端开发服务器
echo -e "${YELLOW}停止前端开发服务器...${NC}"
if pgrep -f "vue-cli-service" > /dev/null; then
    pkill -f "vue-cli-service"
    echo -e "${GREEN}✓ 前端开发服务器已停止${NC}"
else
    echo -e "${YELLOW}前端开发服务器未运行${NC}"
fi

echo ""
echo -e "${GREEN}所有服务已停止${NC}"
echo -e "${GREEN}========================================${NC}"
