# 原项目属性列配置分析报告

## 1. 属性列配置的获取流程

### 1.1 数据源

原项目中的属性列配置来自用户自定义配置（`usercustom`），存储在服务端。

**API 调用**：
```javascript
// 获取用户自定义配置
$http.post('usercustom/user/search', {})

// 保存用户自定义配置
$http.post('usercustom', usercustom)

// 获取默认配置
$http.post('usercustom/default/search')
```

### 1.2 存储结构

```javascript
// 存储在 store/modules/api/user-custom.js
state: {
  usercustom: {},
  globalUsercustom: {}
}
```

**示例数据结构**：
```javascript
{
  "host_custom_table_columns": ["bk_host_innerip", "bk_host_name", "bk_cloud_id", ...],
  "biz_custom_table_columns": ["bk_biz_name", "bk_biz_id", ...],
  ...
}
```

## 2. 表头属性获取函数

### 2.1 核心函数：`getHeaderProperties`

**位置**：`src/ui/src/utils/tools.js`

```javascript
export function getHeaderProperties(properties, customColumns, fixedPropertyIds = []) {
  let headerProperties
  
  // 1. 如果有自定义列配置，使用自定义列
  if (customColumns && customColumns.length) {
    headerProperties = getCustomHeaderProperties(properties, customColumns)
  } else {
    // 2. 否则使用默认列（前6个，按优先级排序）
    headerProperties = getDefaultHeaderProperties(properties)
  }
  
  // 3. 处理固定列
  if (fixedPropertyIds.length) {
    headerProperties = headerProperties.filter(property => !fixedPropertyIds.includes(property.bk_property_id))
    const fixedProperties = fixedPropertyIds.map(id => properties.find(p => p.bk_property_id === id))
    return [...fixedProperties, ...headerProperties]
  }
  
  return headerProperties
}
```

### 2.2 自定义列获取

```javascript
export function getCustomHeaderProperties(properties, customColumns) {
  const columnProperties = []
  customColumns.forEach((propertyId) => {
    const columnProperty = properties.find(property => property.bk_property_id === propertyId)
    if (columnProperty) {
      columnProperties.push(columnProperty)
    }
  })
  return columnProperties
}
```

### 2.3 默认列获取

```javascript
export function getDefaultHeaderProperties(properties) {
  return [...properties]
    .sort((A, B) => getPropertyPriority(A) - getPropertyPriority(B))  // 按优先级排序
    .slice(0, 6)  // 取前6个
}
```

## 3. 关联列表的表头处理

### 3.1 association-list-table.vue

**位置**：`src/ui/src/views/host-details/children/association-list-table.vue`

```javascript
header() {
  // 1. 确定固定属性ID
  const fixedPropertyIds = this.id === BUILTIN_MODELS.HOST 
    ? ['bk_host_innerip', 'bk_host_innerip_v6'] 
    : []
  
  // 2. 获取表头属性
  const headerProperties = this.$tools.getHeaderProperties(
    this.properties,  // 属性列表
    [],                // 自定义列（关联列表不使用用户自定义配置）
    fixedPropertyIds    // 固定列
  )
  
  // 3. 转换为表头格式
  const header = headerProperties.map(property => ({
    id: property.bk_property_id,
    name: this.$tools.getHeaderPropertyName(property),
    property
  }))
  
  return header
}
```

### 3.2 关联列表的特点

**关键发现**：关联列表的 `customColumns` 参数为空数组 `[]`！

这意味着：
- 关联列表**不使用**用户保存的持久化属性列配置
- 关联列表使用**默认表头**（前6个属性）
- 但对于 HOST 类型的关联，会固定显示 `bk_host_innerip` 和 `bk_host_innerip_v6`

## 4. 用户自定义列配置的组件

### 4.1 ColumnsConfig 组件

**位置**：`src/ui/src/components/columns-config/columns-config.vue`

```javascript
// 保存自定义列配置
async handleSave(columnsConfig) {
  const columnsConfigKey = this.getColumnsConfigKey()
  const params = {
    [columnsConfigKey]: this.properties.map(property => property.bk_property_id)
  }
  
  // 调用 store 保存
  await this.$store.dispatch('userCustom/saveUsercustom', params)
}
```

### 4.2 使用示例（pod-list.vue）

```javascript
const columnsConfigKey = 'host_pod_custom_table_columns'

// 获取用户保存的配置
const customColumns = computed(() => usercustom.value[columnsConfigKey] || [])

// 应用配置到表头
const headerProperties = getHeaderProperties(
  properties.value,
  configColumns,
  columnsConfig.disabledColumns
)
```

## 5. ui_lite 中的实现差异

### 5.1 当前实现

```javascript
// instance-association/index.vue
if (!groupedMap.has(groupKey)) {
  const propsObj = this.propertiesMap[relatedObjId]
  const propsArray = (propsObj && propsObj.info) ? propsObj.info : []
  const columns = propsArray.slice(0, 4)  // 硬编码取前4个
}
```

### 5.2 差异点

| 特性 | 原项目 | ui_lite |
|------|--------|---------|
| 属性来源 | 用户持久化配置或默认 | 硬编码前4个 |
| 优先级排序 | ✅ 支持 | ❌ 不支持 |
| 固定列 | ✅ 支持 | ❌ 不支持 |
| 自定义保存 | ✅ 支持 | ❌ 不支持 |

## 6. 建议实现方案

### 6.1 短期方案

保持当前实现（硬编码取前4个属性），因为关联列表通常只需要显示关键字段。

### 6.2 长期方案

如需支持用户自定义：

1. **创建用户配置 API**：
   - 保存列配置：`POST /api/user-custom`
   - 获取列配置：`GET /api/user-custom`

2. **实现配置获取逻辑**：
   ```javascript
   async loadColumnConfig() {
     const config = await $http.get('/api/user-custom', {
       params: { key: `${this.modelId}_association_columns` }
     })
     return config || this.getDefaultColumns()
   }
   ```

3. **应用配置**：
   ```javascript
   const columns = this.customColumns.length 
     ? this.customColumns 
     : this.getDefaultColumns()
   ```

## 7. 总结

### 7.1 原项目逻辑

1. **获取用户配置**：通过 `$http.post('usercustom/user/search')` 获取
2. **处理逻辑**：`getHeaderProperties()` 函数处理自定义列和默认列
3. **关联列表**：不使用用户配置，使用默认表头（前6个属性 + 固定列）

### 7.2 ui_lite 当前实现

1. **属性来源**：从 `propertiesMap` 获取
2. **处理逻辑**：直接 `slice(0, 4)` 取前4个
3. **关联列表**：硬编码实现，不支持用户自定义

### 7.3 关键代码位置

- 表头获取函数：`src/ui/src/utils/tools.js` (getHeaderProperties)
- 用户配置API：`src/ui/src/store/modules/api/user-custom.js`
- 列配置组件：`src/ui/src/components/columns-config/columns-config.vue`
- 关联列表实现：`src/ui/src/views/host-details/children/association-list-table.vue`

### 7.4 结论

**原项目的关联列表不使用用户持久化配置**，而是使用默认表头（前6个属性）。ui_lite 当前取前4个属性的实现是合理的简化方案。
