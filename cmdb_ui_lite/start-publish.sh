#!/usr/bin/env bash
# 发布为应用的自包含启动脚本：
# 1) 若后端(Flask, :5000)未运行则拉起；
# 2) 启动前端(node server.js)，监听发布脚本注入的 $PORT（默认 3000），
#    由 server.js 将 /api 等请求反代到 localhost:5000 后端。
set +e

BACKEND_DIR=/workspace/bk-cmdb-lite/cmdb_server_lite
FRONTEND_DIR=/workspace/bk-cmdb-lite/cmdb_ui_lite

if ! curl -s -o /dev/null --noproxy '*' -m 2 http://localhost:5000/ ; then
  echo "[start-publish] 后端未响应，启动 Flask 后端 (:5000) ..."
  cd "$BACKEND_DIR"
  nohup python3 run.py > /tmp/cmdb_backend_pub.log 2>&1 &
  for i in $(seq 1 40); do
    if curl -s -o /dev/null --noproxy '*' -m 2 http://localhost:5000/ ; then
      echo "[start-publish] 后端已就绪"
      break
    fi
    sleep 1
  done
else
  echo "[start-publish] 后端已运行 (:5000)，跳过启动"
fi

cd "$FRONTEND_DIR"
echo "[start-publish] 启动前端 server.js (PORT=${PORT:-3000}) ..."
exec node server.js
