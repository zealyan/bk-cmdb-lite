#!/usr/bin/env bash
#
# bk-cmdb-lite 本地安装部署脚本（trae/agent-CL9BZC）
# 对应文档: .trae/rules/sop.md / project_rules.md
# 说明: 该仓库为 bk-cmdb 的 Python+Vue 轻量重写版，后端 Flask+SQLAlchemy+SQLite，前端 Vue2。
#       与原始 Go 版（MongoDB/Redis/ZooKeeper）无关，请勿混淆。
#
set -euo pipefail

REPO_ROOT=/workspace/bk-cmdb-lite
SERVER=$REPO_ROOT/cmdb_server_lite
UI=$REPO_ROOT/cmdb_ui_lite

echo "==> [1/6] 确保 SOP 绝对路径软链可用"
ln -sfn "$SERVER" /workspace/cmdb_server_lite
ln -sfn "$UI"     /workspace/cmdb_ui_lite
ln -sfn "$REPO_ROOT/bk-cmdb" /workspace/bk-cmdb
ln -sfn "$REPO_ROOT/.trae"    /workspace/.trae

echo "==> [2/6] 安装后端 Python 依赖（清华镜像）"
cd "$SERVER"
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "==> [3/6] 清库并重新迁移（建表 + 预置关联类型 + 初始化数据）"
rm -f cmdb_dev.db
python3 -m app.migrate.migrate

echo "==> [4/6] 启动后端 (http://localhost:5000)"
nohup python3 run.py > /tmp/cmdb_backend.log 2>&1 &
echo "    后端 PID: $!"
sleep 4
curl -s -m 5 http://localhost:5000/api/v1/common/health

echo "==> [5/6] 安装前端依赖并构建（npmmirror）"
cd "$UI"
npm config set registry https://registry.npmmirror.com
npm install
npm run build

echo "==> [6/6] 启动前端预览 (http://localhost:3000, 代理到 5000)"
nohup node server.js > /tmp/cmdb_frontend.log 2>&1 &
echo "    前端 PID: $!"
sleep 3
curl -s -m 5 -o /dev/null -w "前端根路径 HTTP %{http_code}\n" http://localhost:3000/

echo ""
echo "部署完成:"
echo "  后端 API : http://localhost:5000  (健康: /api/v1/common/health)"
echo "  前端预览 : http://localhost:3000  (API 代理已开启)"
echo "  日志     : /tmp/cmdb_backend.log  /tmp/cmdb_frontend.log"
