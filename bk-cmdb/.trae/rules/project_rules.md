# CMDB 项目开发规范

## 项目架构

```
bk-cmdb/
├── cmdb_ui_lite/           # 前端子项目 (Vue 2 + bk-magic-vue)
└── cmdb_server_lite/       # 后端子项目 (Python + FastAPI + DuckDB)
```

---

## 一、项目概述

### 前端项目 (cmdb_ui_lite)

| 项目 | 说明 |
|------|------|
| 技术栈 | Vue 2 + bk-magic-vue + Vue Router + Vuex + Axios |
| 构建工具 | Vue CLI |
| 端口 | 3000 (预览)、开发服务器动态端口 |

### 后端项目 (cmdb_server_lite)

| 项目 | 说明 |
|------|------|
| 技术栈 | Python 3 + FastAPI + DuckDB 1.0 |
| 数据库 | DuckDB 关系型数据库 |
| 端口 | 8000 |
| API 文档 | http://localhost:8000/docs |

---

## 二、开发流程 SOP

### 标准开发周期

```
需求确认 → 开发实现 → 构建验证 → 服务启动 → Web 测试 → 完成
```

### 1. 需求分析与任务分解

**执行步骤**:
1. 理解需求目标和功能点
2. 确定涉及的项目（前端/后端/两者）
3. 分解任务为可测试的功能点
4. 创建 TodoWrite 任务清单

### 2. 开发实现

**前端开发规范**:
- 使用 Vue 2 语法
- 组件命名: PascalCase
- 方法命名: camelCase
- CSS 类名: kebab-case

**后端开发规范**:
- 使用 Python 3 + FastAPI
- 数据库操作使用 DuckDB
- RESTful API 设计
- 返回 JSON 格式数据

**代码注释规范**:
所有代码必须添加注释，遵循以下规则：

1. **函数和方法注释** - 必须标注输入参数和输出
2. **条件判断注释** - 标注条件逻辑和数据变化
3. **循环处理注释** - 标注数据转换过程
4. **API端点注释** - 标注请求和响应格式

**API 调用规范**:
```javascript
// 前端 API 调用
import { modelAPI } from '@/api/client'

// 获取模型实例列表
const result = await modelAPI.listInstances('bk_slb', {
  page: 1,
  page_size: 20,
  search: 'keyword',
  sort: 'id',
  order: 'asc'
})
```

### 3. 构建验证

**前端构建**:
```bash
cd cmdb_ui_lite
npm run build
```

**后端验证**:
```bash
cd cmdb_server_lite
python3 main.py
```

### 4. 服务启动

**启动后端**:
```bash
cd cmdb_server_lite
python3 main.py
# 运行在 http://localhost:8000
```

**启动前端开发服务器**:
```bash
cd cmdb_ui_lite
npm run dev
```

**启动前端预览（SOLO Dev 环境）**:
```bash
cd cmdb_ui_lite
npm run build
npx serve -s dist -l 3000
```

### 5. Web 智能体测试

**重要**: 请参考 [web-test-agent-rules.md](./web-test-agent-rules.md) 获取完整的 Web 测试执行路径和方法。

**快速执行**:

```bash
cd cmdb_ui_lite

# 1. 确保服务运行
curl -s http://localhost:8000/health
curl -s http://localhost:3000/ -o /dev/null -w "%{http_code}"

# 2. 使用本地 Playwright 执行测试
./node_modules/.bin/playwright test tests/demo.spec.js

# 3. UI 模式运行
./node_modules/.bin/playwright test --ui
```

---

## 三、验收交付标准

### 每次开发任务完成后必须完成以下步骤

| 序号 | 步骤 | 前端命令 | 后端命令 | 说明 |
|------|------|----------|----------|------|
| 1 | 后端构建 | - | `python3 migrate_*.py` | 数据迁移验证 |
| 2 | 前端构建 | `npm run build` | - | 确保代码无编译错误 |
| 3 | 后端启动 | - | `python3 main.py` | API 服务运行 |
| 4 | 前端预览 | `npx serve -s dist -l 3000` | - | 预览服务运行 |
| 5 | SOLO 预览 | 使用 `OpenPreview` | - | 报告实际预览地址给用户 |
| 6 | 用户验收 | 用户确认功能 | - | 验证功能交互 |

---

## 四、前端项目结构 (cmdb_ui_lite)

```
cmdb_ui_lite/
├── src/
│   ├── api/                # API 客户端
│   ├── assets/             # 静态资源 (Mock 数据)
│   ├── components/         # 公共组件
│   ├── views/             # 页面视图
│   ├── router/            # 路由配置
│   └── store/             # Vuex 状态
├── dist/                  # 构建输出
└── package.json
```

---

## 五、后端项目结构 (cmdb_server_lite)

```
cmdb_server_lite/
├── cmdb.duckdb            # DuckDB 数据库文件
├── main.py                # FastAPI 主程序
├── migrate_data.py        # 实例数据迁移脚本
├── migrate_attributes.py  # 属性数据迁移脚本
└── requirements.txt      # Python 依赖
```

### 数据库表结构

| 表名 | 说明 |
|------|------|
| models | 模型定义 |
| model_attributes | 模型属性定义 |
| relations | 关联关系 |
| associations | 实例关联数据 |
| {model}_instances | 各模型实例表 |

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/models` | 模型列表 |
| GET | `/api/models/{model_id}` | 模型详情 |
| GET | `/api/models/{model_id}/attributes` | 模型属性 |
| GET | `/api/models/{model_id}/instances` | 实例列表 |
| GET | `/api/models/{model_id}/instances/{id}` | 实例详情 |
| GET | `/api/instances/{id}/associations` | 实例关联 |
| GET | `/api/instances/{id}/related` | 关联实例 |
| GET | `/api/relations` | 关联关系列表 |
| GET | `/api/statistics` | 统计信息 |
| GET | `/health` | 健康检查 |

---

## 六、数据迁移流程

### 迁移步骤

1. **分析源数据结构** (前端 Mock JSON)
2. **创建目标表结构** (DuckDB)
3. **编写迁移脚本**
4. **执行迁移并验证**

---

## 七、常用命令

### 前端命令

```bash
cd cmdb_ui_lite

npm run build                    # 生产构建（必须在预览前执行）
npx serve -s dist -l 3000        # 预览服务（端口动态分配）
```

### 后端命令

```bash
cd cmdb_server_lite

python3 main.py                        # 启动 API 服务
python3 migrate_data.py                 # 迁移实例数据
python3 migrate_attributes.py           # 迁移属性数据
python3 -c "import duckdb; ..."          # 数据库调试
```

---

## 八、快速参考路径

| 路径 | 说明 |
|------|------|
| `/workspace/bk-cmdb/cmdb_ui_lite/` | 前端项目根目录 |
| `/workspace/bk-cmdb/cmdb_server_lite/` | 后端项目根目录 |
| `/workspace/bk-cmdb/src/ui/src/` | 原项目 UI 源码 |
| `/workspace/bk-cmdb/cmdb_ui_lite/src/api/` | 前端 API 调用 |
| `/workspace/bk-cmdb/cmdb_server_lite/cmdb.duckdb` | 数据库文件 |

---

## 九、当前运行服务状态

| 服务 | 端口 | 状态 | 用途 |
|------|------|------|------|
| **API代理** | 3000 | ✅ 运行中 | SOLO云端访问后端 |
| **前端开发服务器** | 3001 | ✅ 运行中 | 本地热重载开发 |
| **后端API** | 8000 | ✅ 运行中 | 数据服务 |

---

## 十、端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 3000 | 前端预览 + API代理 | `node server.js` 提供静态文件 + API 代理 |
| 3001 | 开发服务器 | Vue CLI 开发模式（热重载） |
| 8000 | 后端 API | FastAPI 服务 |

---

## 十一、RouterQuery 状态管理

### 概述

RouterQuery 是 CMDB UI Lite 中的 URL 参数状态管理工具，用于实现组件状态与 URL 参数的同步。

### API 方法

| 方法 | 说明 | 参数 | 返回值 |
|------|------|------|--------|
| `get(key, defaultValue)` | 获取单个参数 | key: string, defaultValue?: any | any |
| `getAll()` | 获取所有参数 | - | Object |
| `set(key, value)` | 设置单个参数或批量设置 | key: string\|Object, value?: any | void |
| `setAll(query)` | 替换所有参数 | query: Object | void |
| `delete(key)` | 删除单个参数 | key: string | void |
| `refresh()` | 刷新页面（添加时间戳） | - | void |
| `clear()` | 清除所有参数 | - | void |
| `getAs(key, type, defaultValue)` | 获取并转换类型 | key: string, type: 'int'\|'float'\|'bool', defaultValue: any | any |

---

## 十二、Web 智能体测试依赖安装规则

### 概述

当 Web 智能体测试需要 Python、Node.js/npm、Chromium 等依赖时，应优先使用国内镜像源安装。如果 Chromium 无法安装或使用，依次尝试 Firefox 或 Chrome CDP。

### 依赖安装优先级

```
1. Python 依赖（优先使用国内 pip 镜像）
   ↓ 如果失败
2. Node.js/npm 依赖（优先使用 npmmirror 镜像）
   ↓ 如果失败
3. Chromium 浏览器（优先使用 Playwright 内置）
   ↓ 如果失败
4. Firefox 浏览器（Playwright 支持）
   ↓ 如果失败
5. Chrome CDP 协议（连接已安装的 Chrome）
```

### 1. Python 依赖安装

#### 优先使用国内镜像

```bash
# 设置 pip 镜像（永久）
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用阿里云镜像
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 安装依赖时指定镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 如果上述镜像失败，尝试其他国内镜像
pip install playwright -i https://repo.huaweicloud.com/repository/pypi/simple/
pip install playwright -i https://mirrors.cloud.tencent.com/pypi/simple/
```

#### pip 安装命令示例

```bash
# 安装 Playwright
pip install playwright

# 安装其他常用测试依赖
pip install pytest pytest-playwright selenium requests

# 验证安装
python3 -c "import playwright; print('Playwright installed successfully')"
```

### 2. Node.js/npm 依赖安装

#### 优先使用国内镜像

```bash
# 设置 npm 镜像（永久）
npm config set registry https://registry.npmmirror.com

# 安装依赖时指定镜像
npm install playwright -g --registry https://registry.npmmirror.com

# 如果镜像失败，尝试官方源
npm install playwright -g --registry https://registry.npmjs.org
```

#### npm 安装命令示例

```bash
# 全局安装 Playwright
npm install -g playwright

# 安装 Chromium（自动下载）
npx playwright install chromium

# 使用 --with-deps 安装系统依赖
npx playwright install --with-deps chromium

# 项目本地安装
npm install playwright --save-dev
```

### 3. Chromium 浏览器安装

#### 安装优先级

```
1. Playwright 内置 Chromium
2. 系统包管理器安装
3. 手动下载 Chromium
```

#### 使用 Playwright 安装 Chromium

```bash
# 标准安装
playwright install chromium

# 如果网络问题，设置镜像
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright \
playwright install chromium

# 使用 --with-deps 安装系统依赖
playwright install --with-deps chromium
```

#### 使用系统包管理器安装

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y chromium-browser

# 如果 apt 源慢，使用国内镜像
sudo sed -i 's|http://archive.ubuntu.com|https://mirrors.aliyun.com|g' /etc/apt/sources.list
sudo apt-get update
sudo apt-get install -y chromium-browser
```

### 4. Firefox 浏览器（备选方案）

如果 Chromium 无法使用，尝试 Firefox：

```bash
# 使用 Playwright 安装 Firefox
playwright install firefox

# 或使用系统包管理器
sudo apt-get install -y firefox
sudo apt-get install -y firefox-esr
```

### 5. Chrome CDP 协议（最后备选）

如果无法安装任何浏览器，尝试使用 Chrome CDP 协议连接已安装的 Chrome：

```bash
# 1. 启动 Chrome 并开启远程调试
google-chrome --remote-debugging-port=9222

# 2. 使用 CDP 连接
python3 << 'EOF'
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    page = browser.new_page()
    page.goto("http://example.com")
    page.screenshot(path="example.png")
    browser.close()
EOF
```

### 6. 调试和问题排查

#### 检查安装状态

```bash
# 检查 Playwright 安装
python3 -c "from playwright._impl._driver import compute_driver_executable; print(compute_driver_executable())"

# 检查浏览器安装
ls -la ~/.cache/ms-playwright/

# 检查系统浏览器
which chromium chromium-browser google-chrome firefox
```

#### 常见问题及解决方案

| 问题 | 症状 | 解决方案 |
|------|------|----------|
| **pip 安装超时** | Connection timeout | 使用国内镜像：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| **npm 安装失败** | npm ERR! network | 使用 npmmirror：`npm config set registry https://registry.npmmirror.com` |
| **Chromium 下载慢** | 下载超时 | 使用国内镜像或手动下载 |
| **浏览器无法启动** | Executable doesn't exist | 运行 `playwright install --with-deps` |
| **权限问题** | Permission denied | 使用 sudo 或设置 PLAYWRIGHT_BROWSERS_PATH |
| **端口被占用** | EADDRINUSE | 使用其他端口或杀死占用进程 |

#### 环境变量配置

```bash
# Playwright 浏览器路径
export PLAYWRIGHT_BROWSERS_PATH=/tmp/playwright-browsers

# Playwright 下载镜像
export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright

# npm 镜像
export NPM_CONFIG_REGISTRY=https://registry.npmmirror.com

# pip 镜像
export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

### 7. 完整安装脚本示例

```bash
#!/bin/bash
# Web 测试环境快速配置脚本

set -e

echo "=== 开始配置 Web 测试环境 ==="

# 1. 设置国内镜像
echo "[1/5] 设置国内镜像源..."
npm config set registry https://registry.npmmirror.com
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 安装 Python 依赖
echo "[2/5] 安装 Python 依赖..."
pip install playwright pytest pytest-playwright requests -q

# 3. 安装 Playwright
echo "[3/5] 安装 Playwright..."
npm install -g playwright

# 4. 安装浏览器
echo "[4/5] 安装浏览器..."
# 优先尝试 Chromium
if playwright install chromium 2>/dev/null; then
    echo "Chromium 安装成功"
else
    echo "Chromium 安装失败，尝试 Firefox..."
    playwright install firefox
fi

# 5. 验证安装
echo "[5/5] 验证安装..."
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright 验证成功')"

echo "=== Web 测试环境配置完成 ==="
```

### 8. 快速检查清单

```bash
# 检查所有依赖
echo "=== 依赖检查 ==="

# Python
python3 --version && pip show playwright | grep Version && echo "✅ Python/Playwright OK"

# Node.js/npm
node --version && npm --version && echo "✅ Node.js/npm OK"

# 浏览器
which chromium || which chromium-browser || which google-chrome || which firefox && echo "✅ 浏览器 OK"

# Playwright 浏览器
ls ~/.cache/ms-playwright/*/chrome-linux/chrome 2>/dev/null && echo "✅ Playwright 浏览器 OK"
```

### 9. 镜像源汇总

| 依赖 | 镜像名称 | URL |
|------|----------|-----|
| **pip/PyPI** | 清华 | https://pypi.tuna.tsinghua.edu.cn/simple |
| **pip/PyPI** | 阿里云 | https://mirrors.aliyun.com/pypi/simple/ |
| **pip/PyPI** | 腾讯云 | https://mirrors.cloud.tencent.com/pypi/simple/ |
| **pip/PyPI** | 华为云 | https://repo.huaweicloud.com/repository/pypi/simple/ |
| **npm** | npmmirror | https://registry.npmmirror.com |
| **npm** | 淘宝 | https://registry.npmmirror.com |
| **apt** | 阿里云 | https://mirrors.aliyun.com |
| **Chromium** | npmmirror | https://npm.taobao.org/mirrors/chromium-browser-snapshots/ |
| **Playwright** | npmmirror | https://npmmirror.com/mirrors/playwright |

### 10. 注意事项

1. **优先国内镜像**：所有依赖安装优先使用国内镜像源，避免网络超时
2. **Chrome/CDP 连接**：SOLO 云端环境优先尝试连接已运行的 Chrome 实例
3. **权限问题**：避免使用 `sudo`，设置合适的权限或使用用户目录
4. **版本兼容性**：确保 Playwright 版本与浏览器版本兼容
5. **环境变量**：使用环境变量配置镜像，避免每次手动指定
6. **缓存目录**：如果磁盘空间不足，设置 PLAYWRIGHT_BROWSERS_PATH 到 /tmp
7. **网络问题**：如果所有镜像都失败，尝试使用 VPN 或代理

---
