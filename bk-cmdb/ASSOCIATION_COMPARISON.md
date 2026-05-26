# 原项目 vs ui_lite 关联 Tab 实现对比

## 1. 功能对比

| 特性 | 原项目 (association-list-table.vue) | ui_lite (instance-association/index.vue) |
|------|-------------------------------------|------------------------------------------|
| **分页** | ✅ 支持 (size=10) | ✅ 已实现 (size=10) |
| **翻页控件** | ✅ 左右箭头按钮 | ✅ 左右箭头按钮 |
| **页码显示** | ✅ "第X页/共Y页" | ✅ "第X页/共Y条" |
| **展开/折叠** | ✅ 支持 | ✅ 支持 |
| **实例详情** | ✅ 点击跳转 | ✅ 点击跳转 |
| **取消关联** | ✅ 支持 | ❌ 占位功能 |

## 2. API 调用方式对比

### 原项目
```javascript
// 按关联ID列表 IN 查询
getModelInstances(config) {
  return instanceService.find({
    bk_obj_id: this.id,
    params: {
      fields: [],
      page: {
        start: 0,
        limit: this.pagination.size
      },
      conditions: {
        condition: 'AND',
        rules: [{
          field: 'bk_inst_id',
          operator: 'in',
          value: this.currentPageInstanceIds
        }]
      }
    }
  })
}
```

### ui_lite (当前)
```javascript
// 一次加载所有实例到内存
// 按ID匹配关联记录
const instance = this.instancesMap[relatedObjId]?.find(
  inst => inst.id === asst.bk_asst_inst_id
)
```

## 3. 布局样式对比

### 原项目样式
```html
<div class="table-info clearfix">
  <div class="info-title fl">
    <i class="icon"></i>
    <span class="title-text">{{title}}</span>
    <span class="title-count">({{associationInstances.length}})</span>
  </div>
  <div class="info-pagination fr" v-show="pagination.count">
    <span class="pagination-info">{{getPaginationInfo()}}</span>
    <span class="pagination-toggle">
      <i class="pagination-icon left" :class="{ disabled: ... }"></i>
      <i class="pagination-icon right" :class="{ disabled: ... }"></i>
    </span>
  </div>
</div>
```

### ui_lite 实现
```html
<div class="group-info">
  <div class="info-title fl">
    <i class="icon"></i>
    <span class="title-text">{{ item.relationTypeName }}</span>
    <span class="title-count">({{ item.total }})</span>
  </div>
  <div class="info-pagination fr" v-if="item.total > pageSize">
    <span class="pagination-info">{{ getPaginationText(item) }}</span>
    <span class="pagination-toggle">
      <i class="pagination-icon left" :class="{ disabled: ... }"></i>
      <i class="pagination-icon right" :class="{ disabled: ... }"></i>
    </span>
  </div>
</div>
```

## 4. 关键实现差异

### 4.1 分页数据结构

**原项目**：
```javascript
pagination: {
  count: 0,      // 总数
  current: 1,    // 当前页
  size: 10       // 每页大小
},
totalPage() {
  return Math.ceil(this.pagination.count / this.pagination.size)
}
```

**ui_lite**：
```javascript
groupStates: {}  // 响应式状态管理

// 每个分组的状态
{
  expanded: true,
  current: 1
}

// 计算属性
total: group.allInstances.length,
totalPages: Math.ceil(total / this.pageSize),
displayInstances: group.allInstances.slice(start, start + this.pageSize)
```

### 4.2 翻页方法

**原项目**：
```javascript
togglePage(step) {
  const { current } = this.pagination
  const newCurrent = current + step
  if (newCurrent < 1 || newCurrent > this.totalPage) {
    return false
  }
  this.pagination.current = newCurrent
  this.getInstances()  // 重新请求 API
}
```

**ui_lite**：
```javascript
togglePage(item, step) {
  const newCurrent = item.current + step
  if (newCurrent < 1 || newCurrent > item.totalPages) {
    return
  }
  const state = this.groupStates[item.key]
  if (state) {
    state.current = newCurrent
  }
  this.$forceUpdate()  // 重新计算 displayInstances
}
```

### 4.3 实例查找

**原项目**：
- 通过 API 根据 ID 列表查询实例详情
- 支持 HOST 特殊处理（关联查询 biz/set/module）

**ui_lite**：
- 预先加载所有模型实例到 `instancesMap`
- 按 ID 匹配关联记录
- 简化实现，适合小数据量场景

## 5. 样式对比

### 原项目样式
```scss
.info-pagination {
  color: #8b8d95;
  .pagination-toggle {
    margin-left: 10px;
    .pagination-icon {
      font-size: 14px;
      color: #979BA5;
      &.disabled {
        color: #C4C6CC;
        cursor: not-allowed;
      }
      &.left { transform: rotate(90deg); }
      &.right { transform: rotate(-90deg); }
    }
  }
}
```

### ui_lite 样式
```scss
.info-pagination {
  display: flex;
  align-items: center;
  color: #8b8d95;
  font-size: 12px;
  .pagination-info {
    margin-right: 8px;
  }
  .pagination-toggle {
    display: flex;
    align-items: center;
    .pagination-icon {
      font-size: 14px;
      color: #979BA5;
      padding: 4px;
      &.disabled {
        color: #C4C6CC;
        cursor: not-allowed;
      }
      &.left { transform: rotate(90deg); }
      &.right { transform: rotate(-90deg); }
      &:hover:not(.disabled) {
        color: #3a84ff;
      }
    }
  }
}
```

## 6. 优缺点分析

### 原项目实现
**优点**：
- 支持大数据量分页（API分页）
- 权限控制完善
- 支持 HOST 特殊关联查询

**缺点**：
- 实现复杂
- 需要多次 API 调用

### ui_lite 实现
**优点**：
- 实现简洁
- 一次加载所有数据
- 适合小数据量场景

**缺点**：
- 不适合大数据量
- 缺少权限控制

## 7. 后续优化建议

1. **大数据量支持**：当实例数量超过阈值（如100）时，考虑后端分页
2. **权限控制**：增加权限校验
3. **取消关联**：实现完整的取消关联功能
4. **加载状态**：增加 loading 状态显示
5. **空状态**：完善空数据展示

## 8. 已完成功能

✅ 分页功能（每页10条）
✅ 翻页控件（左右箭头）
✅ 页码信息显示
✅ 展开/折叠功能
✅ 实例点击跳转
✅ 与原项目样式一致
