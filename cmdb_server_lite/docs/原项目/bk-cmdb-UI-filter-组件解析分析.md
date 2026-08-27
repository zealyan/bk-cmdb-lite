# bk-cmdb UI `filter` 组件：分隔符解析与条件表达式分析

> 基于 `TencentBlueKing/bk-cmdb` 源码 `release-v3.10.41` 的 `src/ui/src` 前端代码
> 聚焦：form 输入中分隔符/换行/逗号/Tab 的解析规则、解析后的展示样式、全部条件表达式与数据类型

---

## 1. 组件族与数据流

filter 相关组件位于 `src/ui/src/components/filters/`：

| 组件 | 角色 |
|------|------|
| `filter-collection.vue` / `filter-fast-search.vue` | 筛选条件集合 / 快捷搜索（把一行文本解析成多条件） |
| `filter-form.vue` / `filter-tag-form.vue` | 单条件编辑表单（点属性弹出的小表单） |
| `filter-tag.vue` / `filter-tag-item.vue` / `filter-tag-ip.vue` | **已生效条件的展示（chip 标签）** |
| `operator-selector.vue` | 操作符下拉（按数据类型给出可选操作符） |
| `store.js` / `utils.js` | 条件状态管理 / 解析与序列化工具 |
| `general-model-filter-*.vue` | 通用模型（非内置）的同类组件 |

**数据流**：用户输入 → `cmdb-search-{type}` 输入组件（按属性类型切换）→ 多值被解析成数组 → 存入 `FilterStore.condition` → 由 `filter-tag-item.vue` 渲染成 chip 展示。

输入组件列表（`src/ui/src/components/search/`）：`singlechar / int / float / longchar / enum / list / objuser / organization / timezone / foreignkey / table / bool / date / time / service-template / biz / set / module` 等。

---

## 2. 条件表达式（操作符）全集

### 2.1 操作符定义（`src/ui/src/utils/query-builder-operator.js`）

`QUERY_OPERATOR`（L15-28）定义了全部操作符，**前端内部值**与**界面符号/中文**如下：

| 内部值 | 界面符号 | 中文 | mapping（传给后台语义） |
|--------|----------|------|--------------------------|
| `$eq` | `=` | 等于 | equal |
| `$ne` | `≠` | 不等于 | not_equal |
| `$in` | `in` | 精确 | in |
| `$nin` | `not in` | 精确 | not_in |
| `$lt` | `<` | 小于 | less |
| `$gt` | `>` | 大于 | greater |
| `$lte` | `≤` | 小于等于 | less_or_equal |
| `$gte` | `≥` | 大于等于 | greater_or_equal |
| `$range` | `≤ ≥` | 数值范围 | between（**前端构造**，实际拆成 `$gte`+`$lte` 下发） |
| `$nrange` | — | 非区间 | not_between（常量存在，但 UI 未暴露） |
| `$regex` | `like` | 模糊 | contains |

> 注：`$nrange` 虽在常量中定义，但 `operator-selector` 的 `defaultTypeMap` 未把它挂到任何类型，故 UI 不会让用户选到。`$regex`(like) 仅 `singlechar`/`longchar` 可用。

### 2.2 各数据类型可用的操作符映射（`operator-selector.vue` L74-90）

```js
const defaultTypeMap = {
  bool:            [EQ, NE],
  date:            [GTE, LTE],          // 实为标准区间（≥/≤）
  enum:            [IN, NIN],
  float:           [EQ, NE, GT, LT, RANGE],
  int:             [EQ, NE, GT, LT, RANGE],
  list:            [IN, NIN],
  longchar:        [IN, NIN, LIKE],
  objuser:         [IN, NIN],
  organization:    [IN, NIN],
  singlechar:      [IN, NIN, LIKE],
  time:            [GTE, LTE],
  timezone:        [IN, NIN],
  foreignkey:      [IN, NIN],
  table:           [IN, NIN],
  'service-template': [IN]
}
```

**关键结论**：
- **`in`（`$in`）/ `not in`（`$nin`）支持的数据类型**：`enum、list、longchar、objuser、organization、singlechar、timezone、foreignkey、table、service-template`（共 10 种）。
- **`int` / `float` 不支持 `in`/`not in`**——它们只有 `=`/`≠`/`<`/`>`/`数值范围`，多值输入走的是"起-止"两个数字框（见 §4.1）。
- **`like`（`$regex`）仅 `singlechar` / `longchar`**。
- **`bool` 仅 `=`/`≠`**；**`date`/`time` 仅 `≥`/`≤`**（区间）。

---

## 3. 支持的数据类型总表

| 数据类型 (`bk_property_type`) | 多值输入形态 | 是否支持 IN/NIN | 备注 |
|-------------------------------|--------------|----------------|------|
| `singlechar` | `bk-tag-input`（自由输入） | ✅ | 支持 LIKE |
| `longchar` | `bk-tag-input`（自由输入） | ✅ | 支持 LIKE |
| `table` | `bk-tag-input`（自由输入） | ✅ | 自由输入多值 |
| `enum` | `bk-select` 多选下拉 | ✅ | 从枚举项勾选 |
| `list` | `bk-select` 多选下拉 | ✅ | 从选项勾选 |
| `timezone` | `bk-select` 多选下拉 | ✅ | 时区列表 |
| `foreignkey` | `bk-select` 多选下拉 | ✅ | 云区域等 |
| `service-template` | 专用选择器 | ✅（仅 in） | 服务模板 |
| `objuser` | 成员选择器（弹窗勾选） | ✅ | 非自由文本 |
| `organization` | 组织架构选择器（弹窗勾选） | ✅ | 非自由文本 |
| `int` | 数字框（单值 / 起止区间） | ❌ | 无 IN/NIN |
| `float` | 数字框（单值 / 起止区间） | ❌ | 无 IN/NIN |
| `bool` | 开关/下拉（单值） | ❌ | 仅 =/≠ |
| `date` | 日期（≥/≤） | ❌ | 区间 |
| `time` | 时间（≥/≤） | ❌ | 区间 |

---

## 4. 多值输入解析（in / not in 焦点）

### 4.1 输入组件按类型切换（`filter-tag-form.vue` `getComponentType()`）

值输入组件由属性类型决定：`cmdb-search-{bk_property_type}`。当操作符为 `in`/`not in`（或当前值已是数组）时，组件进入 **multiple 模式**：

- **自由文本多值**（`singlechar` / `longchar` / `table`）：渲染 `<bk-tag-input allow-create>`，用户输入即生成"标签（tag）"。
- **下拉多选**（`enum` / `list` / `timezone` / `foreignkey`）：`<bk-select multiple>` 勾选。
- **弹窗选择器**（`objuser` / `organization`）：成员/组织弹窗勾选，**不走文本分隔符解析**。
- **数字**（`int` / `float`）：单值数字框或"起-止"双框（`int.vue` 的 multiple 是 `start`-`end` 区间，并非 tag 列表）。

> 因此，"分隔符解析"只对**自由文本多值**（`bk-tag-input` 系列）有意义；下拉/弹窗类本来就结构化了，不存在"分隔符"概念。

### 4.2 解析规则（分隔符正则）—— 核心

自由文本多值的解析分两种场景，源码完全一致：

**(A) 粘贴（paste）解析** —— `src/ui/src/components/search/singlechar.vue` `handlePaste`（L93-99）：

```js
handlePaste(event) {
  const text = event.clipboardData.getData('text')
  const values = text.split(/,|;|\n/).map(value => value.trim())
    .filter(value => value.length)
  const value = [...new Set([...this.localValue, ...values])]  // 去重
  this.localValue = value
}
```

- 分隔符集合：**逗号 `,`、分号 `;`、换行 `\n`**（半角）。
- 每个片段 `trim()`，空白片段丢弃，结果用 `Set` **去重**。
- `longchar.vue`、`table.vue` 的 `handlePaste` 同此逻辑（均为 `split(/,|;|\n/)`）。

**(B) IP 类专用解析** —— `src/ui/src/components/filters/utils.js` `splitIP`（L276-284）：

```js
raw.trim().split(/\n|;|；|,|，/)
```

- 额外支持**全角分号 `；`、全角逗号 `，`**（中文输入常见）。用于主机 IP 快捷搜索。
- 快捷搜索 `filter-fast-search.vue:41` 也用 `currentValue.trim().split(/,|;|\n/g)`。

### 4.3 直接回答：in / not in 是否支持 Tab、回车、换行？

| 输入方式 | 是否作为分隔/生成依据 | 说明 |
|----------|----------------------|------|
| **回车 (Enter)** | ✅ 支持 | `bk-tag-input` 内置行为：键入值后按 Enter 即**生成一个 tag**；即"回车=确认一项多值" |
| **换行 (Newline `\n`)** | ✅ 支持 | 粘贴时正则 `split(/,|;|\n/)` 含 `\n`，多行文本被拆成多项；输入框内按 Enter 等同生成新 tag |
| **Tab** | ❌ **不支持** | 所有拆分正则（`/,|;|\n/` 与 `/\n|;|；|,|，/`）**均不含 `\t`**；`bk-tag-input` 也不会把 Tab 当作生成 tag 的键（Tab 通常触发失焦/焦点切换）。Tab **不会**把值拆开 |
| 逗号 `,` | ✅ | 半角 |
| 分号 `;` | ✅ | 半角 |
| 全角逗号 `，` / 全角分号 `；` | ✅（仅 IP/快捷搜索路径） | `splitIP` 与 `filter-fast-search` 支持；自由文本 `singlechar/longchar` 的 paste 仅半角 |

> **结论**：`in` / `not in` 多值**支持回车与换行作为分隔/逐项确认**（换行来自粘贴拆分 + Enter 生成 tag），但**不支持 Tab 作为分隔符**。若用户用 Tab 分隔多个值，它们会被当作**同一个 tag 的值里的普通字符**（Tab 字面量），而不会拆成多项。

### 4.4 解析细节补充

- **trim + 去空**：每个片段 `trim()`，`value.length` 为 0 的丢弃。
- **去重**：paste 时通过 `[...new Set([...旧值, ...新值])]` 去重。
- **展示侧合并**：多个值最终在 chip 里以 ` | ` 连接显示（见 §5）。
- **`$range` 特例**：`int`/`float` 的"数值范围"是**两个独立数字输入**（start/end），不是分隔符解析；序列化时拆成 `{operator: $gte, value: start}` + `{operator: $lte, value: end}`（`utils.js` L168-183）。

---

## 5. 解析后的展示组件与样式

已生效条件由 `src/ui/src/components/filters/filter-tag-item.vue` 渲染成 **chip（标签）**。

### 5.1 结构（L13-31）

```
[属性名] : [操作符 值1 | 值2 | 值3] [×]
```

- `tag-name`：属性显示名（`bk_property_name`）。
- `tag-colon`：仅 `$range` 时显示冒号。
- `tag-value`：值文本；多值用 ` | ` 拼接（`displayText` L81-87）：
  ```js
  // 普通操作符
  `${this.operatorSymbol} ${this.transformedValue.join(' | ')}`
  // $range 特例
  `${start} ~ ${end}`
  ```
  例：`主机名 in  web01 | web02 | web03`。
- `tag-delete`：右侧 `bk-icon icon-close`，点击 `FilterStore.resetValue` 移除该条件。
- 点击 chip 整体会弹出 `filter-tag-form` 浮层（popover）重新编辑。

### 5.2 样式（L147-184）

```scss
.filter-tag {
  display: inline-flex; align-items: center;
  margin: 0 3px 10px; padding: 0 0 0 5px;
  border-radius: 2px; font-size: 12px;
  background: #f0f1f5;          // 浅灰底
  line-height: 22px; cursor: pointer;
  &:hover { background-color: #DCDEE5; }
  .tag-name    { max-width: 150px; color: #63656E; @include ellipsis; }  // 属性名灰
  .tag-value   { max-width: 220px; color: #313238; @include ellipsis; }  // 值深灰
  .tag-delete  { font-size: 20px; color: #9b9ea8; &:hover { color: #313238; } }
}
```

- 外观：**圆角 2px 的浅灰（#f0f1f5）内联标签**，hover 变深（#DCDEE5）。
- 文本超长用 `ellipsis` 省略；hover 有 `v-bk-overflow-tips` 气泡显示完整内容。
- `foreignkey` / `service-template` 类型不走纯文本，而是用 `display-type="info"` 的只读内联组件，操作符符号作为前缀（`slot="info-prepend"`）。

### 5.3 IP 类展示

`filter-tag-ip.vue` 用 `Utils.splitIP` 拆分后同样以标签形式展示，规则同上（支持全角逗号/分号）。

---

## 6. 结论速览

1. **全部条件表达式**：`=、≠、in、not in、<、>、≤、≥、数值范围(起-止)、like`（外加仅常量的 `非区间`/`模糊` 未在 UI 暴露）。
2. **支持 `in`/`not in` 的数据类型**：`enum、list、longchar、objuser、organization、singlechar、timezone、foreignkey、table、service-template`；**`int`/`float`/`bool`/`date`/`time` 不支持 IN/NIN**。
3. **分隔符解析规则**：自由文本多值（`bk-tag-input`）在**粘贴**时按 **`,` `;` `\n`** 拆分并 `trim`+去重；`singlechar`/`longchar`/`table` 的 paste 用 `/,|;|\n/`；IP/快捷搜索额外支持全角 `，` `；`。
4. **in / not in 对 Tab/回车/换行**：✅ **回车、换行支持**（Enter 生成 tag；`\n` 参与粘贴拆分）；❌ **Tab 不支持**作为分隔符（拆分正则无 `\t`，Tab 只会被当作值内普通字符）。
5. **展示形态**：每个条件渲染为浅灰圆角 chip（属性名 : 操作符 值1 | 值2 | 值3），右侧带删除图标，点击可重新编辑；多值以 ` | ` 连接，超长省略并 hover 提示。

---

> 代码定位索引：
> - 操作符定义：`src/ui/src/utils/query-builder-operator.js`（L15-68）
> - 类型→操作符映射：`src/ui/src/components/filters/operator-selector.vue`（L74-90）
> - 默认数据/解析序列化：`src/ui/src/components/filters/utils.js`（getDefaultData L62-80、splitIP L276-284、RANGE 拆分 L168-183）
> - 快捷搜索拆分：`src/ui/src/components/filters/filter-fast-search.vue`（L41）
> - 自由文本多值输入+粘贴解析：`src/ui/src/components/search/singlechar.vue`（L14-24、L93-99）、`longchar.vue`、`table.vue`
> - 数值区间输入：`src/ui/src/components/search/int.vue`（L13-32）
> - 下拉多选：`src/ui/src/components/search/enum.vue`、`list.vue`、`timezone.vue`、`foreignkey.vue`
> - 成员/组织选择器：`src/ui/src/components/search/objuser.vue`、`organization.vue`
> - 展示 chip：`src/ui/src/components/filters/filter-tag-item.vue`（结构 L13-31、样式 L147-184）
