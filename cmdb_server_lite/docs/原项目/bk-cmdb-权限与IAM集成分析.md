# bk-cmdb 权限体系与 IAM / ABAC 集成分析

> 基于 `TencentBlueKing/bk-cmdb` 源码 `release-v3.10.41` 分析
> 目标：搞清 cmdb 的 auth 接口、如何用 IAM 支撑"用户/权限/资源"ABAC 体系、IAM 是否有通用适配应用，以及结合 apisix / 自定义 Python 的落地思路

---

## 1. 你当前配置的含义

```yaml
authscheme: internal           # 内置权限模式，不使用 IAM
login:
  version: opensource          # 开源登录方式
authServer:
  address: ""
  appCode: bk_cmdb
  appSecret: ""
```

这段配置的**真实语义**是：

- `authscheme: internal` 表示 **不接入外部 IAM**；配合 `authServer.address: ""`，后端实际处于**鉴权放行**状态——任意通过登录校验的用户都能执行任意操作（即"内置/免鉴权"模式，不是"自带一套 RBAC"）。
- cmdb v3.10.41 **源码里只有一套 `iam` 协议的 Authorizer 实现**（`iam.NewAuthorizer`），并不存在 `internal`/`local` 的另一套鉴权引擎。`internal` 的"免鉴权"是通过全局开关 `auth.EnableAuthorize()` 短路实现的：开关关闭时，所有 `Authorize*` 调用直接返回"通过"。
- 因此，"支持用户/权限/资源 ABAC"的第一步，就是**从 `internal` 切到 `iam`，并部署一个 IAM 作为策略决策点（PDP）**。

---

## 2. cmdb 的 auth 接口与调用链（源码分析）

### 2.1 统一入口：请求 → ResourceAttribute

每个 cmdb API 在执行业务逻辑前，都会经过 `src/ac/parser` 把 HTTP 请求**解析成一个标准化的资源描述**：

```go
// src/ac/meta/resource.go / meta.go
meta.ResourceAttribute{
    Basic: meta.Basic{
        Type:       meta.ResourceType(res.ResourceType),  // 资源类型: business/host/model...
        Action:     meta.Action(res.Action),              // 操作: 查看/编辑/删除...
        InstanceID: res.ResourceID,                       // 资源实例 ID
        InstanceIDEx: res.ResourceIDEx,
    },
    SupplierAccount: ownerID,
    BusinessID:      res.BizID,
    Layers:          [...],  // 父级链路（用于层级资源授权）
}
```

这套"资源 + 动作 + 实例 + 层级"的抽象，本身就是**做 ABAC 的好骨架**——用户、资源、动作、环境都可以挂属性。

### 2.2 Authorizer 抽象（唯一实现 = BlueKing IAM 协议）

```go
// src/apiserver/service/service.go:66
s.authorizer = iam.NewAuthorizer(clientSet)
```

`authorizer` 提供的核心方法（被各场景调用）：

| 方法 | 调用方/场景 | 说明 |
|------|-------------|------|
| `AuthorizeBatch` | `apiserver/service/auth.go:AuthVerify`（批量精确授权） | 校验用户对**具体实例**是否有权 |
| `AuthorizeAnyBatch` | 同上（`GetAnyAuthorizedAppList` 等"是否有任一权限"场景） | 校验用户对任意实例是否有权 |
| `ListAuthorizedResources` | `GetAnyAuthorizedAppList` | 拉取用户有权限的资源 ID 列表（如"我可见的业务"） |
| `GetNoAuthSkipUrl` | 无权限时的跳转/申请链接 | 跳到 IAM 权限申请页 |

### 2.3 总开关 `EnableAuthorize`

```go
// src/common/auth/auth.go
func EnableAuthorize() bool { return enableAuth }
```

- `authscheme: internal` / 未配置 IAM 时，该开关为 `false`，所有 `Authorize*` 直接放行 → 即你现在的"免鉴权"。
- 切到 IAM 时该开关为 `true`，`iam.NewAuthorizer` 才会真正去连 IAM（见 `src/ac/iam/iam.go:45` 的 `if !auth.EnableAuthorize() { return new(IAM), nil }`）。

### 2.4 `auth_server` 微服务：两类端点

`src/scene_server/auth_server` 是 cmdb 对接 IAM 的"适配层"，对外暴露**两类端点**：

**(A) cmdb 内部鉴权代理**（其他微服务调用它来鉴权）：

| 端点 | 说明 |
|------|------|
| `POST /authorize/batch` | 批量精确鉴权 |
| `POST /authorize/any/batch` | 批量"任一权限"鉴权 |
| `POST /findmany/authorized_resource` | 拉取有权资源 |
| `POST /find/no_auth_skip_url` | 无权限申请链接 |
| `POST /find/permission_to_apply` | 权限申请详情 |
| `POST /register/resource_creator_action` `/batch_*` | 资源创建者默认权限注册 |

**(B) IAM "接入系统"回调协议**（IAM 反向调用 cmdb 来发现资源）：实现在 `src/scene_server/auth_server/logics/*`：

| 函数 | 对应 IAM 回调 | 作用 |
|------|---------------|------|
| `FetchInstanceInfo` | `fetch_instance_info` | IAM 拉取实例详情（含拓扑路径 `getResourceIamPath`） |
| `ListAttr` | `list_attr` | **列出资源的可授权属性（ABAC 挂钩点）** |
| `ListAttrValue` | `list_attr_value` | 列出属性枚举值 |
| `ListInstanceByPolicy` | `list_instance_by_policy` | 按策略列出实例（"可见资源"渲染） |
| `listInstance` / `searchAuthResource` | `list_instance` / `search_resource` | 列出/搜索实例 |

> 这些回调端点正是"你能用 Python 自研一个 IAM 兼容后端"时必须实现的协议边界。

### 2.5 注册到 IAM 的资源/动作模型（ABAC 挂钩点）

`src/scene_server/admin_server/iam/iam.go` 的 `Register` 会把 cmdb 注册为一个 IAM **接入系统**，注册顺序（依赖关系）为：

```
System → ResourceType → InstanceSelection → Action → (ActionGroup / ResCreatorAction / CommonAction)
```

已注册的资源类型（`src/ac/meta/resource.go`）包括：
`business`、`bizSet`、`model`、`mainlineObject`、`mainlineInstance`、`host`、`process`、`modelAssociation`、`modelAttribute` … 等。

**ABAC 的关键挂钩点就是 `ResourceType` 上注册的属性（`ListAttr`）与 `InstanceSelection`（实例选择条件）**——IAM 的策略可以基于这些属性/环境写条件表达式。

### 2.6 关键代码定位

| 内容 | 文件 |
|------|------|
| 鉴权总开关 | `src/common/auth/auth.go` |
| 解析请求为 ResourceAttribute | `src/ac/parser/*`、`src/ac/meta/resource.go` |
| Authorizer 装配 | `src/apiserver/service/service.go:66` |
| 鉴权 HTTP 接口 | `src/apiserver/service/auth.go` |
| IAM 客户端（连外部 IAM） | `src/ac/iam/iam.go`、`src/scene_server/auth_server/sdk/client/policy.go` |
| IAM API 路径 | `/api/v1/policy/query`、`/api/v1/policy/query_by_actions`、`/api/v1/model/systems/{id}/token` |
| 接入系统回调实现 | `src/scene_server/auth_server/logics/{fetch_instance_info,list_attr,list_attr_value,list_instance_by_policy,list_instance}.go` |
| 注册 cmdb 到 IAM | `src/scene_server/admin_server/iam/iam.go` `Register`；`src/scene_server/admin_server/service/authcenter.go` `InitAuthCenter`/`RegisterAuthAccount` |
| `authscheme` 读取 | `src/web_server/app/server.go:129`、`src/web_server/app/options/options.go:64` |

---

## 3. 如何用 IAM 让 cmdb 支持 用户/权限/资源 ABAC

### 3.1 从 `internal` 切到 `iam` 的步骤

1. **部署一个 IAM 作为 PDP**（见第 4 节：直接用开源 `bk-iam`，或自研 IAM 协议兼容后端）。
2. **改配置**：
   ```yaml
   authscheme: iam
   authServer:
     address: "http://<iam-host>:<port>"   # 必填，指向 IAM
     appCode: bk_cmdb
     appSecret: "<iam-system-token>"
   ```
   并确保启动参数 `--enable-auth=true`（让 `EnableAuthorize()` 为 `true`）。
3. **注册 cmdb 到 IAM**：调用 admin_server 的 `migrate/v3/authcenter/register`（`RegisterAuthAccount`），把 cmdb 作为接入系统写入 System/ResourceType/InstanceSelection/Action。
4. **初始化资源模型**：`migrate/v3/authcenter/init`（或带 host 的 `InitAuthCenter`），把已有自定义模型同步给 IAM。
5. **在 IAM 里配置用户/用户组/权限**（用户来自你的用户目录，权限=动作+实例范围+条件）。

### 3.2 BlueKing IAM 的模型（天然支持 ABAC）

IAM 的授权模型是 **System → ResourceType → Action（含 InstanceSelection）→ Policy（用户/组 + 实例范围 + 条件）**：

- **用户**：IAM 的用户/用户组，可对接你的 IdP（LDAP/SSO/OIDC）。
- **权限**：Policy = 把"某用户/组"授予"某 Action"，并可限定**实例范围**与**条件表达式**。
- **资源**：cmdb 的 business/host/model 等，通过 `ResourceType` + 属性建模。
- **ABAC**：IAM 的策略**支持条件（condition）**，条件可基于**资源属性**、**环境属性**（如时间、来源 IP、登录方式）做表达式判断——这就是 ABAC 的落点。

> 换句话说：cmdb 已经把"资源/动作/实例/层级"抽象好了，你只要在 IAM 侧把**用户属性、资源属性、环境属性**纳入策略条件，就能从 RBAC 升级到 ABAC，而**不需要改 cmdb 业务代码**。

### 3.3 cmdb 侧需要的配合

- **注册资源属性**：让 `ListAttr` 返回你想要用于 ABAC 的字段（如主机的 `bk_os_type`、业务的 `bk_biz_dept`），IAM 才能基于它们写条件。
- **用 InstanceSelection / 拓扑路径**：`getResourceIamPath` 已能把实例映射成 IAM 的资源路径（如 `business,2/set,10/module,100`），支持"对某业务下所有主机"这类层级授权。
- **自定义模型**：你在第 7 章新增的 `app_sys` 主线模型，注册到 IAM 后自动成为可授权的 ResourceType，可直接纳入 ABAC 策略。

---

## 4. IAM 是否有"通用应用"可以适配

### 4.1 BlueKing IAM（bk-iam）本身就是通用权限中心

- BlueKing IAM 是**通用、可独立部署**的授权平台（开源，Apache-2.0），设计目的就是被多个"接入系统"（cmdb、job、bk-monitor…）共用。
- 它**不是 cmdb 专属**，而是一个独立的 PDP/策略中心。**你不需要再找一个"通用应用"去适配 IAM——IAM 自己就是那个通用应用**，cmdb 只是它的一个接入方。

### 4.2 "接入系统（access system）"机制

任何系统接入 IAM 的标准动作：

1. **注册为接入系统**：声明自己的 `ResourceType`、`Action`、`InstanceSelection`、属性。
2. **实现回调端点**：IAM 在授权/渲染时会回调你的 `list_instance` / `fetch_instance_info` / `list_attr` / `list_attr_value` / `list_instance_by_policy`（正是 cmdb `auth_server` 已实现的那套）。
3. **调用 IAM 鉴权 API**：`/api/v1/policy/query` 等。

### 4.3 是否必须整套蓝鲸？—— 最小化部署

- **不需要整套蓝鲸 PaaS**。开源 `bk-iam` 可单独部署（后端 + SaaS 管控台）。但 IAM 本身的部署/运维有一定成本。
- **自研 IAM 兼容后端**：如果你不想部署 `bk-iam`，可以自研一个**只实现 cmdb 所需协议子集**的后端（见 4.4）。但注意：cmdb 的 `authorizer` 是**硬编码调用 IAM 协议**的（`iam.NewAuthorizer` 写死），所以你的后端必须"长得像 IAM"（至少实现 `/api/v1/policy/query` 与那几个回调端点），**否则 cmdb 不会认**。

### 4.4 自定义适配层必须实现的协议边界

若自研后端（无论 Go/Python），需实现：

| 类别 | 端点/能力 | 说明 |
|------|-----------|------|
| 鉴权 | `POST /api/v1/policy/query`、`/api/v1/policy/query_by_actions` | cmdb SDK 调用来拿策略并判定 |
| 注册 | `/api/v1/model/systems/{id}/token` 等 | 系统注册/模型同步 |
| 回调 | `list_instance` / `fetch_instance_info` / `list_attr` / `list_attr_value` / `list_instance_by_policy` | IAM 反向发现 cmdb 资源（cmdb 的 `auth_server/logics` 就是范例） |

---

## 5. 结合 apisix / 自定义 Python 的落地方案（重点：apisix + internal 的权限颗粒度）

### 5.1 前提：apisix + internal 时，网关能看到什么

当 `authscheme: internal`，cmdb 内部**完全不鉴权**。此时若把 **apisix 放在 cmdb 前面做网关**，apisix 作为一个反向代理，能直接观察到的只有：

- **HTTP 路径**：如 `/api/v3/hosts/modules`、`/api/v3/dynamicgroup`、`/api/v3/admin/update/system_config/platform_setting`
- **HTTP 方法**：GET / POST / PUT / DELETE
- **请求头**：含经 authn 插件注入的用户身份（consumer）
- **请求体**：仅当在自定义插件里主动解析时才能拿到

而 cmdb 真正的"动作 × 资源实例"语义，是由 `src/ac/parser` 在**服务内部**从请求体解析出来的。以 `src/ac/parser/host.go` 为例：

```go
// 路径 /api/v3/dynamicgroup + POST → 动作 Create、资源 DynamicGrouping
// 业务 ID 来自：
func (ps *parseStream) parseBusinessID() (int64, error) {
    val, err := ps.RequestCtx.getValueFromBody(common.BKAppIDField) // ← 读的是 请求体 里的 bk_biz_id
    ...
}
```

> **关键事实**：cmdb 把"对象类型 + 动作(verb)"编码在 **URL 路径**里，但把"业务 ID / 实例 ID"放在 **请求体**里。apisix 在网关层**看得到前者、看不到后者**。

### 5.2 apisix + internal 能达到的最小（最细）颗粒度

| 授权层级 | apisix(internal) 能否稳定实现 | 说明 |
|----------|-------------------------------|------|
| 消费者 / 用户级 | ✅ | `key-auth` / `jwt-auth` / `openid-connect` 识别调用方 |
| API 路径（对象+动作）级 | ✅ | `/api/v3/hosts/*` vs `/api/v3/admin/*`，路径通配匹配 |
| HTTP 方法级 | ✅ | GET（只读）vs POST/PUT/DELETE（写） |
| **业务级（bk_biz_id）** | ⚠️ 仅自定义插件解析 body | 需写插件从 body 抽 `bk_biz_id`，且仅对 body 结构稳定的端点有效 |
| **实例级（具体 host/set ID）** | ❌ 不稳定 | 实例 ID 在 body，各 API schema 不一，无法通用匹配 |
| **属性级 ABAC（如 dept==资源.owner）** | ❌ | 需完整复刻 `ac/parser` + 属性模型，等于重写一个 IAM |

→ **apisix + internal 的最小（最细）稳定颗粒度 = `用户(consumer) × API 端点(路径+方法) × 对象类型(动作)`**，也就是**"功能 / 接口级"授权**（等价于 RBAC 里"角色能调哪些接口"），**到不了 cmdb 原生的"业务 / 实例级"**。

一句话概括：

> **apisix + internal 能做到「张三能调主机的增删改接口，但不能碰业务管理接口」；做不到「张三只能改业务 2 下的主机」。**

### 5.3 想比"接口级"更细？只有两条路

- **路 1（业务级，有限增强）**：用 `apisix-python-plugin-runner` 写插件，对请求体 JSON 做 `gjson` 式提取 `bk_biz_id`，按 `consumer + 业务ID` 放行/拒绝。只对 **body 结构可预测** 的端点有效，且要随 cmdb API 演进持续维护匹配规则——**脆弱，不建议作为主授权模型**。
- **路 2（实例 / 属性级，正道）**：放弃 `internal`，把 cmdb 切到 `authscheme: iam`。cmdb 内部 `ac/parser` 已经把"动作 × 业务 × 实例 × 层级"解析好并交给 IAM 决策，apisix 退居 `authn + 路由`。这才是"用户 / 权限 / 资源 ABAC"的正确落点。

### 5.4 三档颗粒度对照：apisix+internal（网关层） vs cmdb iam（内部层）

| 维度 | apisix + internal（网关层） | cmdb iam（内部层） |
|------|------------------------------|--------------------|
| 识别调用方 | consumer / header | IAM 用户 / 用户组 |
| 授权对象 | API 路径 + 方法（对象类型 + 动作） | 资源实例（business/host/set…）+ 实例范围 |
| 业务隔离 | 需自定义插件解析 body | 原生（`bk_biz_id` 已在 `ResourceAttribute`） |
| 实例级授权 | ❌ 不稳定 | ✅ |
| 属性 / ABAC 条件 | ❌（除非复刻 parser） | ✅（IAM 条件表达式） |
| 改动 cmdb | 无（仅关 `--enable-auth`） | 切配置 + 部署 IAM |
| 适合场景 | 接口级管控、服务隔离、限流、authn | 业务 / 资源级细粒度 ABAC |

### 5.5 自定义 Python 在其中的位置

- **作为 apisix 插件（路 1）**：`apisix-python-plugin-runner` 写 body 解析 + 业务级判定，后端可接你的 Python 规则 / `OPA`。
- **作为 IAM 兼容后端（路 2 的替代实现）**：用 `bk-iam` Python SDK 实现第 4.4 节端点，背后接 `OPA` / `pycasbin`，让 cmdb 的 `iam.NewAuthorizer` 零改动对接——这样能拿到**实例 / 属性级**，但代价是"部署一个 IAM 协议后端"。

### 5.6 结论

> **apisix + internal 的最小颗粒度是「接口级（consumer × 路径 × 方法）」，属于功能 / 角色级授权，到不了业务 / 实例级。** 它非常适合做：统一认证、服务间鉴权、接口黑白名单、限流、审计。
>
> 如果你的目标是 cmdb 的「用户 × 权限 × 资源」ABAC（业务 / 实例级），要么**接受接口级上限**，要么**切到 `authscheme: iam`** 让 cmdb 内部完成细粒度决策（apisix 退居 authn + 路由）。**不要试图在网关层复刻 `ac/parser`**——那等于重写一个 IAM，且随 cmdb 版本升级极易破碎。

---

## 6. 关键结论与推荐

1. **你现在的 `authscheme: internal` = 不鉴权**。要上 ABAC，必须先切 `iam` 并准备一个 IAM/PDP。
2. **cmdb 只认 BlueKing IAM 协议**（`iam.NewAuthorizer` 写死）。最省事的路是**直接部署开源 `bk-iam`**，它本身就是通用权限中心，cmdb 是现成的接入系统，几乎零代码改造即可获得"用户/权限/资源"的 ABAC（靠 IAM 策略条件表达式）。
3. **apisix 与 Python 是"增强/替代"角色，不是必需**：
   - 想用 apisix → 放前面做认证+路由即可，授权仍交给 IAM（思路 A，最稳）。
   - 想完全自控 → 用 `apisix-python-plugin-runner` 或独立 Python 服务实现 PDP，可接 `OPA`/`pycasbin` 做 ABAC，cmdb 关内部鉴权（思路 B）。
   - 自研 Python 后端时，**必须实现 IAM 协议子集**（第 4.4 节端点），否则 cmdb 不认；除非你 fork `src/ac` 加自定义 authorizer。
4. **ABAC 的真正钩子在 IAM 策略条件 + cmdb 的 `ResourceType` 属性（`ListAttr`）**：把用户属性、资源属性、环境属性纳入 IAM 条件，即可在不改 cmdb 业务代码的前提下完成 ABAC 升级；你在第 7 章新增的 `app_sys` 模型注册到 IAM 后自动成为可授权资源。

---

> 注：本文的"ABAC"指以属性（用户/资源/环境）为条件的授权模型。BlueKing IAM 底层以 RBAC + 实例级授权 + 条件表达式为主，条件表达式足以表达常见 ABAC 场景；若需要任意属性表达式（如"部门==资源.owner 且 时间<18:00"），可通过 IAM 的自定义条件/属性能力或上层 PDP（OPA）实现。
