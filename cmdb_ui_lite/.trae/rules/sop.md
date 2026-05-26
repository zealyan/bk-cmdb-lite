# SOP 参考

项目规范已迁移至根目录：

- **完整规范**: `/workspace/bk-cmdb/.trae/rules/project_rules.md`
- **检查清单**: `/workspace/bk-cmdb/.trae/rules/sop-checklist.md`

---

## SOLO 预览标准流程

### 1. 启动后端
```bash
cd /workspace/bk-cmdb/cmdb_server_lite
python3 main.py
# API: http://localhost:8000
```

### 2. 验证后端
```bash
curl http://localhost:8000/health
# 应返回: {"status":"healthy",...}
```

### 3. 构建前端
```bash
cd /workspace/bk-cmdb/cmdb_ui_lite
npm run build
```

### 4. 启动预览服务（带 API 代理）

⚠️ **必须使用 `node server.js`**，不是 `npx serve`！

```bash
cd /workspace/bk-cmdb/cmdb_ui_lite
node server.js
# 默认端口: 3000
```

### 5. 验证前端代理
```bash
curl http://localhost:3000/health
# 应返回: {"status":"healthy",...}
```

### 6. 使用 OpenPreview
- 使用 `OpenPreview` 工具将预览地址报告给用户
- 告知用户预览地址

---

## 重要提示

### 为什么必须使用 `node server.js`？

| 服务类型 | 命令 | API 代理 | 后端连接 |
|----------|------|----------|----------|
| **带代理服务器** | `node server.js` | ✅ 支持 | ✅ 正常 |
| 纯静态服务器 | `npx serve -s dist` | ❌ 不支持 | ❌ 失败 |

使用 `npx serve` 会导致前端页面加载正常，但后端 API 请求全部失败，错误信息：
```
TypeError: undefined is not an object (evaluating 'e.database.status')
```

### 常见问题排查

1. **后端依赖缺失**：`pip install -r requirements.txt`
2. **端口被占用**：`pkill -f "node.*server.js" && node server.js`
3. **API 连接失败**：检查是否使用了 `server.js` 而非 `npx serve`
