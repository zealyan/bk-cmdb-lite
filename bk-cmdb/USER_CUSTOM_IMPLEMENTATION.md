# 用户自定义列配置 - 前后端完整实现方案

## 概述

实现了用户自定义列配置的完整前后端数据持久化流程，包括：
- 前端：Vuex Store 共享状态管理
- 后端：DuckDB 数据库持久化存储
- API：RESTful 接口支持

## 数据流程

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (Vue.js)                           │
│                                                              │
│  ┌─────────────────┐    ┌─────────────────┐                  │
│  │  实例列表页     │    │  关联列表页     │                  │
│  │  general-model  │    │  instance-      │                  │
│  │  /index.vue     │    │  association    │                  │
│  └────────┬────────┘    └────────┬────────┘                  │
│           │                      │                           │
│           │  保存/加载列配置        │                           │
│           ▼                      │                           │
│  ┌────────────────────────────────────────┐                  │
│  │           Vuex Store                    │                  │
│  │  state.userCustom.customTableColumns   │                  │
│  │  = {                                   │                  │
│  │    "bk_slb_custom_table_columns":      │                  │
│  │      ["id", "name", ...]                │                  │
│  │  }                                     │                  │
│  └────────┬───────────────────────────────┘                  │
└───────────┼──────────────────────────────────────────────────┘
            │
            │  API 调用
            ▼
┌─────────────────────────────────────────────────────────────┐
│                      后端 (FastAPI)                          │
│                                                              │
│  ┌────────────────────────────────────────┐                  │
│  │           DuckDB 数据库                  │                  │
│  │  表: user_custom                       │                  │
│  │  字段:                                 │                  │
│  │    - id (主键)                         │                  │
│  │    - user_name (用户名)                 │                  │
│  │    - config_key (配置键)               │                  │
│  │    - config_value (配置值 JSON)         │                  │
│  │    - created_at (创建时间)               │                  │
│  │    - updated_at (更新时间)               │                  │
│  └────────┬───────────────────────────────┘                  │
│           │                                                    │
│           ▼                                                    │
│  ┌────────────────────────────────────────┐                  │
│  │           API 端点                       │                  │
│  │  POST /api/usercustom/user/search      │                  │
│  │  POST /api/usercustom                  │                  │
│  │  GET  /api/usercustom/model/{obj_id}   │                  │
│  │  POST /api/usercustom/model/{obj_id}   │                  │
│  └────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## 数据库表结构

```sql
CREATE TABLE user_custom (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name VARCHAR NOT NULL DEFAULT 'admin',
    config_key VARCHAR NOT NULL,
    config_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_name, config_key)
);
```

## API 接口

### 1. 获取用户所有配置
```
POST /api/usercustom/user/search
Headers:
  x-user-name: admin (可选，默认 admin)

Response:
{
  "bk_slb_custom_table_columns": ["id", "name", "status"],
  "bk_slb_server_custom_table_columns": ["id", "ip", "port"],
  ...
}
```

### 2. 保存用户配置
```
POST /api/usercustom
Headers:
  x-user-name: admin (可选，默认 admin)
Body:
{
  "bk_slb_custom_table_columns": ["id", "name", "status"]
}

Response:
{
  "message": "User custom saved successfully",
  "user_name": "admin"
}
```

### 3. 获取模型列配置
```
GET /api/usercustom/model/{obj_id}
Headers:
  x-user-name: admin (可选，默认 admin)

Response:
{
  "columns": ["id", "name", "status"]
}
```

### 4. 保存模型列配置
```
POST /api/usercustom/model/{obj_id}
Headers:
  x-user-name: admin (可选，默认 admin)
Body:
{
  "columns": ["id", "name", "status"]
}

Response:
{
  "message": "Model custom saved successfully",
  "obj_id": "bk_slb",
  "columns": ["id", "name", "status"]
}
```

## 前端实现

### 1. Vuex Store 配置

**文件**: `cmdb_ui_lite/src/store/index.js`

```javascript
export default new Vuex.Store({
  state: {
    userCustom: {
      customTableColumns: {}  // 存储所有模型的自定义列配置
    }
  },
  mutations: {
    SET_USERCUSTOM(state, payload) {
      state.userCustom.customTableColumns = {
        ...state.userCustom.customTableColumns,
        ...payload
      }
    }
  },
  actions: {
    saveUsercustom({ commit }, payload) {
      const key = Object.keys(payload)[0]
      const value = payload[key]
      commit('SET_USERCUSTOM', payload)
      console.log('[UserCustom] 保存自定义配置:', key, value)
    },
    // 批量加载所有配置
    loadAllUserCustom({ commit }, usercustom) {
      commit('SET_USERCUSTOM', usercustom)
      console.log('[UserCustom] 加载所有配置:', Object.keys(usercustom))
    }
  },
  getters: {
    getCustomColumns: (state) => (objId) => {
      const key = `${objId}_custom_table_columns`
      return state.userCustom.customTableColumns[key] || []
    }
  }
})
```

### 2. API 客户端

**文件**: `cmdb_ui_lite/src/api/user-custom.js`

```javascript
export default {
  // 获取用户配置
  searchUserCustom(config = {}) {
    return api.post('/api/usercustom/user/search', {}, config)
  },
  
  // 保存用户配置
  saveUsercustom(usercustom, config = {}) {
    return api.post('/api/usercustom', usercustom, config)
  },
  
  // 获取模型列配置
  getModelCustomColumns(objId, config = {}) {
    return api.get(`/api/usercustom/model/${objId}`, config)
  },
  
  // 保存模型列配置
  saveModelCustomColumns(objId, columns, config = {}) {
    return api.post(`/api/usercustom/model/${objId}`, { columns }, config)
  }
}
```

### 3. 应用初始化

**文件**: `cmdb_ui_lite/src/main.js`

```javascript
// 在应用启动时加载用户配置
import userCustom from '@/api/user-custom'

const app = new Vue({
  router,
  store,
  async created() {
    // 加载用户配置到 Vuex Store
    try {
      const allCustom = await userCustom.searchUserCustom()
      this.$store.dispatch('loadAllUserCustom', allCustom)
      console.log('[App] 用户配置已加载到 Vuex Store')
    } catch (e) {
      console.error('[App] 加载用户配置失败:', e)
    }
  },
  render: h => h(App)
})
```

### 4. 实例列表页

**文件**: `cmdb_ui_lite/src/views/general-model/index.vue`

保存时同步到 Vuex Store：

```javascript
async handleApplyColumns(properties) {
  // 保存到 API
  await userCustom.saveModelCustomColumns(this.objId, this.columnsConfig.selected)
  
  // 同步到 Vuex store（供关联列表使用）
  const configKey = `${this.objId}_custom_table_columns`
  this.$store.dispatch('saveUsercustom', { [configKey]: this.columnsConfig.selected })
}
```

### 5. 关联列表

**文件**: `cmdb_ui_lite/src/components/instance-association/index.vue`

使用 Vuex Store 中的配置：

```javascript
getColumnsForModel(objId) {
  // 从 Vuex store 获取用户自定义列配置
  const customColumns = this.$store.getters.getCustomColumns(objId)
  
  // 获取模型的所有属性
  const propsObj = this.propertiesMap[objId]
  const propsArray = (propsObj && propsObj.info) ? propsObj.info : []
  
  // 如果有自定义配置，按配置顺序取前6个
  if (customColumns.length > 0) {
    return customColumns
      .map(propId => propsArray.find(p => p.bk_property_id === propId))
      .filter(Boolean)
      .slice(0, 6)
  }
  
  // 否则使用默认列（前6个属性）
  return propsArray.slice(0, 6)
}
```

## 后端实现

### API 端点

**文件**: `cmdb_server_lite/main.py`

1. **初始化用户配置表**
2. **搜索用户配置** - `POST /api/usercustom/user/search`
3. **保存用户配置** - `POST /api/usercustom`
4. **获取模型列配置** - `GET /api/usercustom/model/{obj_id}`
5. **保存模型列配置** - `POST /api/usercustom/model/{obj_id}`

## 测试验证

### 1. 启动后端服务
```bash
cd /workspace/bk-cmdb/cmdb_server_lite
python3 main.py
```

### 2. 测试 API

#### 保存列配置
```bash
curl -X POST "http://localhost:8000/api/usercustom/model/bk_slb" \
  -H "Content-Type: application/json" \
  -d '{"columns": ["id", "name", "status", "ip"]}'
```

#### 获取列配置
```bash
curl -X GET "http://localhost:8000/api/usercustom/model/bk_slb"
```

#### 获取所有配置
```bash
curl -X POST "http://localhost:8000/api/usercustom/user/search"
```

### 3. 前端测试

1. 进入实例列表页（如：负载均衡）
2. 点击右上角的"列设置"按钮
3. 选择要显示的列
4. 点击"应用"
5. 进入该实例的详情页
6. 切换到"关联"标签
7. 查看关联实例列表，应该使用相同的列配置

## 注意事项

1. **配置键名规范**: `{obj_id}_custom_table_columns`
   - 例如: `bk_slb_custom_table_columns`, `bk_slb_server_custom_table_columns`

2. **默认用户**: 如果没有指定用户名，使用 `admin`

3. **列数量限制**: 最多显示前6列（与原项目一致）

4. **顺序保留**: 按用户配置的顺序显示列

5. **实时同步**: 保存时同时更新 API 和 Vuex Store

## 文件清单

### 新增/修改的文件

1. **前端**:
   - `cmdb_ui_lite/src/store/index.js` - Vuex Store 配置
   - `cmdb_ui_lite/src/api/user-custom.js` - API 客户端
   - `cmdb_ui_lite/src/main.js` - 应用初始化
   - `cmdb_ui_lite/src/views/general-model/index.vue` - 保存时同步
   - `cmdb_ui_lite/src/components/instance-association/index.vue` - 使用配置

2. **后端** (已存在):
   - `cmdb_server_lite/main.py` - API 端点实现
   - `cmdb_server_lite/cmdb.duckdb` - DuckDB 数据库

## 总结

本实现提供了完整的用户自定义列配置前后端解决方案：

- ✅ **前后端分离**: API 接口标准化
- ✅ **数据持久化**: DuckDB 数据库存储
- ✅ **状态共享**: Vuex Store 实现跨组件共享
- ✅ **配置一致**: 实例列表和关联列表使用相同配置
- ✅ **向后兼容**: 与原项目保持一致的配置键名和逻辑
