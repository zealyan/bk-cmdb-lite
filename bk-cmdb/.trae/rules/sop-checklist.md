# CMDB 项目 SOP 流程检查清单

## 项目: bk-cmdb (前端 + 后端)

```
需求确认 → 开发实现 → 构建验证 → 服务启动 → Web 测试 → 完成
```

---

## 阶段一: 需求分析

- [ ] 理解需求目标
- [ ] 确定涉及项目 (前端/后端/两者)
- [ ] 分解任务为可测试的功能点
- [ ] 创建 TodoWrite 任务清单

---

## 阶段二: 开发实现

### 前端开发 (cmdb_ui_lite)

- [ ] 参考原项目组件实现
- [ ] 使用 Vue 2 响应式规范
  ```javascript
  // ✅ 正确
  this.expandedKeys = { ...this.expandedKeys, [key]: value }
  ```
- [ ] 遵循命名规范
  - 组件: PascalCase
  - 方法: camelCase
  - CSS 类: kebab-case

### 后端开发 (cmdb_server_lite)

- [ ] 设计/修改数据库表结构
- [ ] 实现 API 端点
- [ ] 数据迁移 (如有需要)
  ```bash
  python3 migrate_data.py
  python3 migrate_attributes.py
  ```

### API 调用规范

- [ ] 前端使用 API 客户端
  ```javascript
  import { modelAPI } from '@/api/client'
  const result = await modelAPI.listInstances('bk_slb')
  ```

---

## 阶段三: 构建验证

### 前端构建

- [ ] 执行生产构建
  ```bash
  cd cmdb_ui_lite
  npm run build
  ```
- [ ] 构建无错误

### 后端验证

- [ ] 数据库迁移成功
  ```bash
  cd cmdb_server_lite
  python3 -c "import duckdb; print(duckdb.connect('cmdb.duckdb').execute('SHOW TABLES').fetchall())"
  ```

---

## 阶段四: 服务启动

### 启动后端

- [ ] 启动后端服务
  ```bash
  cd cmdb_server_lite
  python3 main.py
  ```
- [ ] 验证 API 可访问
  ```bash
  curl http://localhost:8000/health
  ```

### 启动前端

- [ ] 开发模式 (可选)
  ```bash
  cd cmdb_ui_lite
  npm run dev
  ```
- [ ] 预览模式 (推荐)
  ```bash
  cd cmdb_ui_lite
  npx serve -s dist -l 3000
  ```
- [ ] 验证前端可访问
  ```bash
  curl http://localhost:3000
  ```

---

## 阶段五: Web 智能体测试

- [ ] 确认服务运行状态
- [ ] 使用智能体 Web 测试能力验证功能
- [ ] 验证要点:
  - [ ] 页面正常加载
  - [ ] 数据从后端正确获取
  - [ ] 功能交互正常
  - [ ] UI 显示正确
  - [ ] 无控制台错误

---

## 阶段六: 验收交付

### 必须完成的交付步骤

| 序号 | 交付物 | 说明 |
|------|--------|------|
| 1 | 后端数据 | 数据迁移完成，API 可用 |
| 2 | 前端代码 | 代码符合规范 |
| 3 | 构建成功 | npm run build 通过 |
| 4 | 服务运行 | 后端 + 前端预览运行 |
| 5 | Web 测试 | 智能体测试验证通过 |
| 6 | 预览地址 | 报告服务访问地址 |

### 禁止跳过

⚠️ **重要**: 任何开发任务完成后，必须按顺序执行以下验收步骤：

1. **后端数据** - `python3 migrate_*.py`
2. **前端构建** - `npm run build`
3. **后端启动** - `python3 main.py` (端口 8000)
4. **前端启动** - `npx serve -s dist -l 3000`
5. **Web 测试** - 智能体测试验证
6. **提供预览** - 报告预览 URL

未完成上述步骤的任务视为未完成。

---

## 快速参考命令

### 前端

```bash
cd cmdb_ui_lite
npm run dev              # 开发服务器
npm run build            # 生产构建
npx serve -s dist -l 3000  # 预览服务
```

### 后端

```bash
cd cmdb_server_lite
python3 main.py            # 启动 API
python3 migrate_data.py    # 迁移实例数据
python3 migrate_attributes.py # 迁移属性数据
```

---

## 常用路径

| 路径 | 说明 |
|------|------|
| `/workspace/bk-cmdb/cmdb_ui_lite/` | 前端项目 |
| `/workspace/bk-cmdb/cmdb_server_lite/` | 后端项目 |
| `/workspace/bk-cmdb/src/ui/src/` | 原项目 UI |
| `/workspace/bk-cmdb/.trae/rules/` | 项目规范 |
