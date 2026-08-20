# bk-cmdb-lite 高级筛选 Bug 修复与 e2e 验证报告

> 验证时间：2026-08-13
> 验证方式：Playwright 真实浏览器驱动（`:3000`），登录 admin/admin，业务 #/business/2/index
> 结论：**Bug1、Bug2、星标收藏「选中/取消选中」toggle、带 IP 收藏的还原，均已修复并对齐上游，e2e 全绿（Bug1/2/3/4 全部 PASS）**

---

## 一、e2e 验证结果

| 用例 | 验证点 | 结果 |
|------|--------|------|
| **Bug1** | 高级筛选弹框 → 收藏此条件 → 提交后，星标下拉列出该收藏 | ✅ PASS（星标下拉列出 `e2e收藏Bug1_1786580289`） |
| **Bug2（单字符 $in）** | 提交后 filter tag 出现，点击 tag X 清除「内网IP」条件 | ✅ PASS |
| **Bug2（$range 日期）** | 提交后 filter tag 出现，点击 tag X 清除「验证日期」条件 | ✅ PASS |
| **Bug3（选中）** | 点击星标下拉收藏 → `activeCollection` 设置、`selected=[主机名称]`、`condition={bk_host_name}`、filter tag 增加、其他条件状态同步 | ✅ PASS |
| **Bug3（取消选中）** | 再次点击同一收藏 → `activeCollection=null`、`selected=[]`、全量 condition/tag 清空 | ✅ PASS |
| **Bug4（IP 收藏选中）** | 高级筛选填 IP=192.168.1.5 → 收藏此条件 → 星标选中该收藏 → `FilterStore.IP` 还原为 `192.168.1.5`、IP filter tag 出现、URL `ip=` 参数同步 | ✅ PASS |
| **Bug4（IP 收藏取消选中）** | 再次点击同一收藏 → `activeCollection=null`、IP 清空、IP tag 移除 | ✅ PASS |

验证脚本：`e2e_verify.py`（真实点击「收藏此条件」按钮 + 真实点击 tag 删除按钮，走修复后的生产代码）。

---

## 二、Bug1：收藏此条件提交后，星标下拉无数据

该 Bug 实际由**两个独立根因**叠加导致，需分别修复。

### 根因 A：收藏机制错位（收藏写入与读取走两套不同存储）

| 维度 | 现象 |
|------|------|
| 写入侧 | `FilterStore.createCollection` 原把收藏写入 `user_custom.config_key=filter_collection`（**机制 B**，仅 `filter-collection.vue` 用，前端无任何地方渲染） |
| 读取侧 | 界面可见的星标下拉是 `host-favourite.vue`，读取的是服务端 `cc_HostFavourite`（**机制 A**） |
| 结果 | 收藏写进去后，星标下拉永远读不到 |

**修复**：参考上游 bk-cmdb（业务拓扑主机列表的「已收藏条件」本就是 HostFavourite），将 `FilterStore` 的 `loadCollections / createCollection / updateCollection / removeCollection` 全部改走 HostFavourite API（`favourite.listFavourites / createFavourite / updateFavourite / deleteFavourite`），与 `host-favourite.vue` 一致。并补充后端 `PUT /api/v1/hosts/favorites/<id>` 路由与 `update_favourite` service/SQL。

### 根因 B：`_favToken` 命名导致收藏列表永不被填充（隐藏的 Vue2 陷阱）

`host-favourite.vue` 用 `_favToken` 作为「代际 token」防竞态：

```js
const token = ++this._favToken
const list = await favourite.listFavourites(this.bizId)
if (token !== this._favToken) return   // 过期请求丢弃
this.favourites = list
```

**问题**：`data()` 中以 `_` 开头的属性（如 `_favToken`）在 **Vue2 中不会被代理到组件实例**（Vue 保留 `_`/`$` 前缀）。因此 `this._favToken` 恒为 `undefined`，`++undefined` 得到 `NaN`，进而 `NaN !== NaN` 永远为 `true` → **每次 `loadFavourites` 都在 `if` 处提前 return，`this.favourites = list` 永远不执行**，星标下拉永远为空。

> 诊断佐证：`[DIAG-FAV] biz=2 res.info=[2项]`（API 正常返回），但组件 `favCount=0`、`token=nan`。

**修复**：将 `_favToken` 重命名为 `favToken`（非保留前缀），Vue 正常代理，`++this.favToken` 计数正确，竞态丢弃逻辑按预期工作。

---

## 三、Bug2：提交后 filter tag 出现，但点击 X 无法清除条件

### 根因：`getOperatorSideEffect` 对 `$range`（日期/时间）返回 `['','']` 而非 `[]`

`filter-tag.vue` 的 `selected` 计算属性按「值是否非空」判断 tag 是否展示：数组类型 `value.length > 0` 才算有值。

| 操作符 | 修复前 reset 返回值 | 修复后 | 影响 |
|--------|-------------------|--------|------|
| `$in`/`$nin` 等 | `[]`（正确） | `[]` | 正常清除 |
| `$range`（日期/时间） | `['','']` ❌ | `[]` ✅ | 修复前：`['','']` 长度 2 > 0，被判定「仍有值」→ tag **永不消失**；修复后：`[]` 长度 0 → tag 正常清除 |

**修复**：`utils.js` 的 `getOperatorSideEffect` 对 `$range` 改为 `return Array.isArray(value) ? value : []`，与上游 bk-cmdb 语义一致。

---

## 四、Bug4：带 IP 的收藏，选中后无法恢复 IP 条件（无 tag、查不出 IP、不同步）

### 根因：IP 是独立于属性条件的「第二维度」，而收藏只序列化了属性条件，IP 既没被存储、也没被还原

上游 bk-cmdb 的收藏结构里，条件分为**两个独立序列化字段**：

- `query_params`：属性条件数组（`bk_obj_id` / `field` / `operator` / `value`）
- `info`：IP 筛选对象（`{ text, inner, outer, exact }`）

应用收藏时（上游 `setActiveCollection`）：

```js
const IP = JSON.parse(collection.info)              // ← 还原 IP 维度
const queryParams = JSON.parse(collection.query_params)
...
this.setCondition({ IP, condition })                // ← 同时写入 IP 与属性条件
```

而 lite 此前：

- `createCollection` 只把 `selected/condition`（属性条件）JSON 序列化进 `query_params`，**完全没把 `FilterStore.IP` 写进 `info`**；
- `setActiveCollection` 只由 `collection.conditions` 重建 `selected/condition`，**从不还原 IP**；
- 后端 `cc_HostFavourite` 表虽已有 `info` 列、`create_favourite` 也会落 `info`，但前端从不传 `info`；`update_favourite` 也从不更新 `info`。

结果：带 IP 的收藏，选中后 IP 维度彻底丢失 → 查不出 IP、无 filter tag、高级筛选不同步（正是用户反馈的现象）。

### 修复（对齐上游，复用 `info` 字段）

| 层 | 改动 |
|----|------|
| 序列化（存） | `filter-form.vue` 的 `handleSaveCollection`/`handleUpdateCollection`、`host-favourite.vue` 的 `handleCreate`、store 的 `createCollection`/`updateCollection`：新增 `info: JSON.stringify(IP)`，IP 维度随收藏一并落库 |
| 反序列化（读） | store `loadCollections` 新增 `IP: this.parseIP(fav)`；新增 `parseIP(fav)` 解析 `fav.info` 为 IP 对象 |
| 还原（应用） | store `setActiveCollection` 在应用时 `this.IP = { ...Utils.getDefaultIP(), ...collection.IP }`，使 `filter-tag-ip` 渲染 IP tag、高级筛选抽屉 IP 输入同步、`dispatchSearch` 把 IP 写入 URL 并触发列表按 IP 过滤 |
| 后端 | `update_favourite.sql` 增加 `info = :info`；`favourite_service.update_favourite` 传入 `info`（`create` 侧此前已支持，无需改） |

> 向后兼容：空/非法 `info`（老数据或纯属性收藏）`parseIP` 返回 `null`，`setActiveCollection` 据此回退默认 IP——应用纯属性收藏时 IP 归零，与上游「保存时即序列化 IP」语义一致。
> 另：`createCollection` 的「收藏即应用」也改用 `saved` 行的 `info` 还原 IP，保证即时应用同样不丢 IP 维度。

---

## 五、星标收藏「选中 ↔ 取消选中」联动筛选状态（对齐上游）

### 需求

星标下拉（已收藏的条件）的**选中**与**取消选中**应：

1. 实现筛选状态参数（condition / selected）的选中与取消；
2. 联动 filter tag 的增加与移除；
3. 同步其他条件状态（高级筛选抽屉 `storageSelected` watch、`FilterStore.IP` 等）。

### 上游实现（`bk-cmdb/src/ui/src/components/filters/filter-collection.vue`）

上游用 `bk-select multiple` + 计算属性 `selected`（getter/setter）实现 toggle：

```js
computed: {
  selected: {
    get() { return this.storageCollection ? [this.storageCollection.id] : [] },   // storageCollection = FilterStore.activeCollection
    set(value) { this.handleApply(value) }
  }
},
methods: {
  handleApply(value) {
    this.$refs.selector.close()
    const now = value.length === 2 ? value[1] : value[0]   // 取消选中时 value=[] → now=undefined
    const collection = now ? this.collections.find(c => c.id === now) : null
    FilterStore.setActiveCollection(collection)            // collection=null → resetAll 清空全部条件
  }
}
```

关键点：**再次点击已激活收藏 → `setActiveCollection(null)` → `resetAll()` 清空全部筛选状态（含 IP）**，filter tag 随之全部移除。

### lite 现状与本次改动

lite 的 `host-favourite.vue` 此前 `handleApply(fav)` **只 apply、不 toggle**——无法取消选中。本次对齐上游补充 toggle 语义：

- 抽出 `applyFav(fav)`（非 toggle 的纯应用）；
- `handleApply(fav)` 增加判断：`if (this.activeFav && this.activeFav.id === fav.id)` → 取消选中（`setActiveCollection(null)` + `activeFav=null`），否则 `applyFav`；
- `handleCreate` 改为调用 `applyFav(fav)`（因创建时已把 `activeFav` 置为该 fav，复用 `handleApply` 会误判为「再次点击」而触发取消选中）。

复用链路（无需新增 store 方法）：

| 动作 | 调用 | 效果 |
|------|------|------|
| 选中 | `FilterStore.setActiveCollection({id,name,conditions})` | 由 `conditions` 重建 `selected`/`condition` → 列表与 filter tag 刷新；`activeCollection` 置位 |
| 取消选中 | `FilterStore.setActiveCollection(null)` → `resetAll()` | `selected=[]`、`condition={}`、`IP` 复位 → 全部 filter tag 移除 |

`filter-form.vue` 已对 `FilterStore.selected`（`storageSelected` watch，immediate）与 `FilterStore.activeCollection`（`collection` 计算属性）响应式，因此选中/取消选中会自动驱动**高级筛选抽屉条件行**与「更新条件」按钮同步，满足"其他条件状态同步"。

---

## 六、修改文件清单

| 文件 | 改动 |
|------|------|
| `cmdb_ui_lite/src/components/filters/store.js` | `FilterStore` 收藏方法改走 HostFavourite；新增 `parseIP(fav)`；`loadCollections`/`createCollection`/`updateCollection` 处理 IP（`info` 字段），`setActiveCollection` 应用时还原 IP；末尾暴露 `window.__FilterStore`（e2e 测试钩子） |
| `cmdb_ui_lite/src/components/filters/utils.js` | `$range` 重置返回值 `['','']` → `[]` |
| `cmdb_ui_lite/src/components/filters/host-favourite.vue` | `_favToken` → `favToken`（修复收藏列表永不被填充）；新增 `applyFav` 并让 `handleApply` 支持选中/取消选中 toggle（对齐上游 `filter-collection.vue`）；`applyFav`/`handleCreate` 传入并序列化 IP 到 `info` |
| `cmdb_ui_lite/src/components/filters/filter-form.vue` | 「收藏此条件」(`handleSaveCollection`) 与「更新条件」(`handleUpdateCollection`) 携带 `info: JSON.stringify(IPCondition)`，对齐上游 IP 维度序列化 |
| `cmdb_ui_lite/src/api/favourite.js` | 新增 `updateFavourite`（PUT）；`listFavourites` 返回 `res.info` 数组 |
| `cmdb_server_lite/app/api/v1/favourite.py` | 新增 `PUT /favorites/<id>` 路由 |
| `cmdb_server_lite/app/service/favourite_service.py` | 新增 `update_favourite`（含 `info` 写入） |
| `cmdb_server_lite/app/sql/favourite/update_favourite.sql` | 新增更新 SQL（含 `info = :info`） |
| `e2e_verify.py` | 新增 Playwright e2e 验证脚本（Bug1 + Bug2 单字符/$range 两类 + Bug3 选中/取消选中 + **Bug4 带 IP 收藏的还原**） |

---

## 七、遗留问题（非本次范围，不影响修复）

控制台仍存在历史报错：

```
[App] ❌ 初始化加载失败: TypeError: Cannot read properties of undefined (reading '__ob__')
    at p.LOAD_ALL_USERCUSTOM (app...:1:66194)
```

这是 Vuex `userCustom` 命名空间与 root state 冲突导致的初始化问题，与本次两个筛选 Bug 无关，e2e 不受其影响。如需彻底消除，需修正 `LOAD_ALL_USERCUSTOM` mutation 中对 undefined 的 `$set` 写法（不在本次任务范围内，未处理）。
