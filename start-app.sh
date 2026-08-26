#!/usr/bin/env bash
#
# bk-cmdb-lite 一键启动（供发布 skill 作为单端口应用入口）
# 同时拉起：后端 Flask (localhost:5000) + 前端 Node (监听 $PORT，反代 /api -> 5000)
# 前端 server.js 最终以 exec 接管本进程，确保发布探针命中 $PORT。
set -e

REPO=/workspace/bk-cmdb-lite
SERVER=$REPO/cmdb_server_lite
UI=$REPO/cmdb_ui_lite

# 清理可能残留的旧实例，避免端口冲突
pkill -f "python3 run.py" 2>/dev/null || true
pkill -f "node server.js" 2>/dev/null || true
sleep 1

# ---- 依赖（幂等，缺才装）----
cd "$SERVER"
if ! python3 -c "import flask" >/dev/null 2>&1; then
  pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
fi

cd "$UI"
if [ ! -d node_modules ]; then
  npm config set registry https://registry.npmmirror.com
  npm install
fi

# ---- 数据库（不存在才迁移，保留已有数据）----
cd "$SERVER"
if [ ! -f cmdb_dev.db ]; then
  python3 -m app.migrate.migrate
fi

# ---- 启动后端（固定 5000，避免发布注入的 $PORT 泄漏到后端）----
cd "$SERVER"
PORT=5000 nohup python3 run.py > /tmp/cmdb_backend.log 2>&1 &
for i in $(seq 1 30); do
  if curl -s -m 2 http://localhost:5000/api/v1/common/health >/dev/null 2>&1; then
    echo "[start-app] 后端就绪 (5000)"
    break
  fi
  sleep 1
done

# ---- 启动前端（接管进程，监听 $PORT）----
cd "$UI"
exec node server.js
