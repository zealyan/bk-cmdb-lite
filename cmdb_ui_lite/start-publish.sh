#!/bin/bash
# 自包含启动脚本（供发布自启动使用）
# 确保后端(run.py)在 5000 运行，再以前台方式启动前端 server.js（监听 $PORT，代理到 5000）。
# 注意：自启动环境会注入 PORT=3000（给前端用）。后端必须显式 PORT=5000，
# 否则会继承 3000 抢占前端端口，导致 node 起不来。
#
# 认证：开启内置 RBAC（ENABLE_AUTH）并关闭免登录（SKIP_LOGIN=false），
# 走真实账号/token 登录。AUTH_BEARER 保持默认 false（网关注入的
# Authorization: Bearer 是平台 token，开启会污染真实登录态）。

BACKEND_DIR=/workspace/bk-cmdb-lite/cmdb_server_lite
UI_DIR=/workspace/bk-cmdb-lite/cmdb_ui_lite

# 认证环境变量（可被外部覆盖；默认：开启 RBAC + 强制登录）
export CMDB_ENABLE_AUTH="${CMDB_ENABLE_AUTH:-true}"
export CMDB_SKIP_LOGIN="${CMDB_SKIP_LOGIN:-false}"
# 关键：不启用 Bearer 承载（避免 workbuddy.link 网关注入的平台 token 遮蔽真实 token）
export CMDB_AUTH_BEARER="${CMDB_AUTH_BEARER:-false}"

# 1) 确保后端在 5000 运行（显式 PORT=5000，避免继承自启动注入的 PORT=3000）
if ! curl -s -m 2 http://127.0.0.1:5000/api/v1/common/health >/dev/null 2>&1; then
  echo "[start-publish] 后端未运行，启动中..."
  cd "$BACKEND_DIR"
  PORT=5000 nohup python3 run.py > /tmp/cmdb_backend.log 2>&1 &
  for i in $(seq 1 30); do
    if curl -s -m 2 http://127.0.0.1:5000/api/v1/common/health >/dev/null 2>&1; then
      echo "[start-publish] 后端就绪(5000)"
      break
    fi
    sleep 1
  done
else
  echo "[start-publish] 后端已在 5000 运行"
fi

# 2) 前台启动前端（监听 $PORT，默认 3000，代理到 5000）
cd "$UI_DIR"
exec node server.js
