# 关联属性新增字段 UI 兼容性检查报告

> 检查对象：关联类型新增字段（`src_des` 源→目标描述、`dest_des` 目标→源描述、`direction` 方向、`direction_label`、`ispre`）对 UI 的影响
> 参考：CLI 使用手册 §2.8 asst-type（方向 + 双向描述）
> 时间：2026-09-03 21:30 ~ 21:45
> 结论：**核心 UI 消费链无兼容性破坏**（纯增量字段 + 双层兜底）；顺手修复 1 处规范缺口

## 1. 字段与值域定义

| 字段 | 含义 | 值域 / 约束 | 数据来源 |
|---|---|---|---|
| `bk_asst_name` | 显示名 | 必填 ≤128 | 原有 |
| `src_des` | 源→目标关系描述 | 选填 ≤128；空值回退 `bk_asst_name` | 本轮新增 |
| `dest_des` | 目标→源关系描述 | 选填 ≤128；空值回退 `bk_asst_name` | 本轮新增 |
| `direction` | 方向 | `none/src_to_dest/dest_to_src/bidirectional`（旧脏值 `forward/backward/both` 由 migrate 归一） | 本轮对齐值域 |
| `direction_label` | 方向中文名 | 由 `direction` 映射 | 本轮新增 |
| `ispre` | 是否预置 | 接口不可写 | 本轮改为 bool |

## 2. UI 消费链逐条核对

### 2.1 主链：主机/通用模型详情「关联」tab

```
instance-association/index.vue (associationGroups 分组 + 标题)
  ├── relations ← GET /api/v1/relations  ← relation_service（JOIN cc_AsstDes）
  │     字段：bk_relation_type_id / bk_relation_type_name / src_des / dest_des / direction ✓ 齐全
  ├── associations ← GET /api/v1/instances/<id>/associations（分表，含 bk_relation_type_id）
  └── assocTypes ← POST /api/v1/find/associationtype ← association_type_service（外置 SQL + _serialize）
        字段：bk_asst_id / bk_asst_name / src_des / dest_des / direction / direction_label / ispre ✓ 齐全
```

- 分组 key 匹配：`relations.bk_relation_type_id === associations.bk_relation_type_id`，两边字段名一致（实测 9 条 × 19 条关联均可匹配）；
- 标题生成双层回退：`relation.src_des → relation.bk_relation_type_name`（第 233 行）与 `type.dest_des → bk_asst_name` 兜底完整；
- **方向值域变更对 UI 零影响**：全项目源码搜索确认 UI 无任何 `direction` 业务消费（仅 CSS `flex-direction` 误命中），新建/编辑表单也不设方向。

### 2.2 新建关联弹框（association-create.vue）

- `setAssociationOptions` 三层回退：`type.src_des/dest_des → type.bk_asst_name → 模型名/obj_id`，即使关联类型描述为空也不会出现空文案；
- 关联类型来自 `findAssociationType`（字段已全量包含新增列并做空值兜底）。

### 2.3 空分组骨架（emptyGroupDefs）

- 标题由 `assocTypes`（findAssociationType）提供 `src_des/dest_des`，**不依赖** find/objectassociation 返回——对 UI 无影响。

### 2.4 静态兜底 mock（general-model/details.vue）

- `bkSlbRelations`（`assets/api/models/relations/instance.json`）**已包含 `src_des/dest_des` 新字段**，结构对齐（仅 `bk_relation_type_id: "to"` 与真实 API 的 `default/belong` 值域不同，但仅 API 失败兜底时展示，无运行时影响）。

## 3. 修复：对象关联查询漏返回新增字段（规范缺口）

### 问题

`AssociationService.get_object_associations`（服务于 `POST /find/objectassociation`）一直使用**内联 SQL 仅 JOIN `bk_asst_name`**，与已外置的 `app/sql/association/select_object_associations.sql`（JOIN `src_des/dest_des/direction`）功能重复且字段更少：

```json
// 修复前 API 返回字段：缺 src_des / dest_des / direction
{..., "bk_asst_id": "install", "bk_asst_name": "安装"}
```

### 修复

改用外置 SQL 文件作为主句 + 保留白名单动态 WHERE 拼接（新增列对 UI 是**纯增量**，不改动任何既有字段名/类型）：

```python
from app.db.sql_loader import load_sql
base_sql = load_sql('association', 'select_object_associations.sql')
# ... 白名单字段过滤 + WHERE 拼接（逻辑与原实现一致）
return query_all(sql, params)
```

### 修复后验证

| 验证项 | 结果 |
|---|---|
| `GET/找 /api/v1/find/objectassociation` 字段 | 补全 `src_des/dest_des/direction`，样例 `安装/运行于/src_to_dest` |
| 无条件 / `bk_obj_id` / 别名 `bk_asst_obj_id` / 未知字段过滤 | 9 / 1 / 1 / 9（白名单回退全量），行为与原来一致 |
| 兼容路径 vs v1 镜像一致性 | 9/9 保持 `是` |
| SQL 注释 ASCII 冒号隐患扫描 | 无 |

## 4. 结论

- **UI 兼容性**：本次新增/改动的关联属性字段对 UI 是**纯增量**——所有核心消费链字段齐全且带双层兜底，UI 又从不消费 `direction` 值域，值域归一（`forward`→`src_to_dest`）不会引起任何前端逻辑错乱。
- **数据链路唯一缺口**（`find/objectassociation` 缺三列）已修复，补列前 UI 依赖回退仍可显示，补列后为后续直接消费铺路，双向安全。
- 前端重新构建通过（10.7s），`hash` 未变，无编译期影响。
