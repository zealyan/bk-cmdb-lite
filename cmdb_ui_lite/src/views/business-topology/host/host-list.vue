<template>
  <div class="list-layout">
    <!-- 工具栏：新增、编辑、转移、搜索等 -->
    <host-list-options
      ref="hostListOptions"
      :selection="table.selection"
      :count="table.pagination.count"
      :selected-node="node"
      @transfer="handleTransfer"
      @refresh="handleRefresh"
      @search="handleSearch"
      @add-host="handleAddHost"
      @edit="handleMultipleEdit"
      @export="handleExport"
      @batch-export="handleBatchExport"
      @set-filters="handleSetFilters">
    </host-list-options>

    <!-- 筛选标签展示区 -->
    <host-filter-tag class="filter-tag" ref="filterTag"></host-filter-tag>

    <!-- 主机数据表格 -->
    <bk-table
      class="host-table"
      ref="tableRef"
      v-bkloading="{ isLoading: loading, opacity: 1 }"
      :data="table.data"
      :pagination="table.pagination"
      :max-height="$APP.height - filtersTagHeight - 250"
      :shift-multi-checked="true"
      @page-change="handlePageChange"
      @page-limit-change="handleLimitChange"
      @sort-change="handleSortChange"
      @selection-change="handleSelectionChange"
      @header-click="handleHeaderClick"
      :key="tableKey">

      <!-- 选择列 -->
      <bk-table-column type="selection" width="50" align="center" fixed></bk-table-column>

      <!-- 动态列：根据 tableHeader 渲染 -->
      <bk-table-column
        v-for="column in tableHeader"
        :key="column.bk_property_id"
        :prop="column.bk_property_id"
        :label="getHeaderLabel(column)"
        :render-header="makeHeaderRenderer(column)"
        :min-width="getColumnMinWidth(column)"
        :sortable="getColumnSortable(column)"
        :fixed="column.bk_property_id === 'bk_host_id'"
        :show-overflow-tooltip="true">
        <template slot-scope="{ row }">
          <span
            :class="{ 'host-id-link': column.bk_property_id === 'bk_host_id' }"
            @click.stop="handleValueClick(row, column)">
            {{ getPropertyValue(row, column) }}
          </span>
        </template>
      </bk-table-column>

      <!-- 表格设置列（列配置） - 与原项目一致：使用 type="setting"，通过 mixin 禁用内置 popover -->
      <bk-table-column type="setting"></bk-table-column>

      <!-- 空数据占位 -->
      <div slot="empty" class="table-empty">
        <bk-exception type="empty" scene="part">
          <div>{{ searchKeyword ? '未找到匹配的主机' : '暂无主机数据' }}</div>
        </bk-exception>
      </div>
      </bk-table>

      <!-- 转移至模块对话框（业务模块 / 空闲模块）
           必须放在 bk-table 之外、与表格平级。
           原先误置于 bk-table 默认 slot 内，被 el-table 的渲染机制丢弃，
           导致弹框外壳弹出但内部 module-selector 内容缺失。 -->
      <!-- 使用原项目自定义 cmdb-dialog 组件（components/ui/dialog/dialog.vue，已移植进 lite 并全局注册），
           定位逻辑与原项目一致：.dialog-body{margin:0 auto; margin-top: calc((100vh - var(--height))/3)}，
           并经 :height="600" 把 --height 设成 600px 驱动内层布局。
           注意：与原项目一致，cmdb-dialog 不渲染可见的标题栏（其 dialog-header 为空、0 高度），
           标题由 module-selector-with-tab 的 tab 标签（"转移到空闲模块"/"转移到业务模块"）呈现，
           因此内层 .module-selector-layout{height: var(--height)=600px} 恰好填满 600px 弹框主体，避免产生纵向滚动条。 -->
      <cmdb-dialog
        v-model="transferDialog.visible"
        :width="1100"
        :height="600"
        :show-footer="false"
        @close="handleTransferCancel"
        @cancel="handleTransferCancel">
        <div class="transfer-dialog-body" style="height: 100%;">
          <module-selector-with-tab
            v-if="transferDialog.visible"
            :active="transferDialog.type"
            :business="transferDialog.business"
            :modules="transferDialog.modules"
            :confirm-loading="transferDialog.confirmLoading"
            @confirm="handleTransferConfirm"
            @cancel="handleTransferCancel">
          </module-selector-with-tab>
        </div>
      </cmdb-dialog>

      <!-- 跨业务转移：第一步「确认哪些主机不能转移」 -->
      <cmdb-dialog
        v-model="acrossConfirm.visible"
        :width="700"
        :height="430"
        :show-footer="false"
        @close="handleTransferCancel"
        @cancel="handleTransferCancel">
        <across-business-confirm
          v-if="acrossConfirm.visible"
          :count="acrossConfirm.count"
          :invalid-list="acrossConfirm.invalidList"
          @confirm="handleAcrossConfirmNext"
          @cancel="handleTransferCancel">
        </across-business-confirm>
      </cmdb-dialog>

      <!-- 跨业务转移：第二步「选择目标业务 + 目标模块」 -->
      <cmdb-dialog
        v-model="acrossSelector.visible"
        :width="1100"
        :height="600"
        :show-footer="false"
        @close="handleTransferCancel"
        @cancel="handleTransferCancel">
        <div class="transfer-dialog-body" style="height: 100%;">
          <across-business-module-selector
            v-if="acrossSelector.visible"
            :business="acrossSelector.business"
            :type="acrossBusinessType"
            :confirm-loading="acrossSelector.confirmLoading"
            @confirm="handleAcrossSelectorConfirm"
            @cancel="handleTransferCancel">
          </across-business-module-selector>
        </div>
      </cmdb-dialog>

      <!-- 批量编辑主机抽屉：复用原项目 edit-multiple-host 外壳 + cmdb-form-multiple 组件，
           与 general-model「批量更新」走同一套 modelAPI.batchUpdateInstancesWithSameData 调用。 -->
      <edit-multiple-host
        ref="editMultipleHost"
        :properties="allProperties"
        :selection="table.selection"
        :biz-id="nodeData.bk_biz_id || nodeData.bk_inst_id || 0"
        @refresh="loadHostList">
      </edit-multiple-host>
  </div>
</template>

<script>
import HostListOptions from './host-list-options.vue'
import HostFilterTag from '@/components/filters/filter-tag.vue'
import ModuleSelectorWithTab from './module-selector-with-tab.vue'
import EditMultipleHost from './edit-multiple-host.vue'
import AcrossBusinessConfirm from './across-business-confirm.vue'
import AcrossBusinessModuleSelector from './across-business-module-selector.vue'
import { ONE_TO_ONE } from '@/dictionary/host-transfer-type.js'
import ColumnsConfig from '@/components/columns-config/columns-config.js'
import FilterForm from '@/components/filters/filter-form.js'
import FilterStore, { setupFilterStore } from '@/components/filters/store'
import Utils from '@/components/filters/utils'
import tableMixin from '@/mixins/table'
import { topoAPI } from '@/api/topo'
import { modelAPI, userCustom, freezeList, cancelRequest, isCancelError } from '@/api/client'
import RouterQuery from '@/utils/router-query'
import { MENU_BUSINESS_HOST_DETAILS } from '@/dictionary/menu-symbol'
import { isPropertySortable, getSort } from '@/utils/property-sort'
import { formatPropertyValue } from '@/utils/property-value'

// 默认表头列定义（简化版，与原项目 host 属性对应）
// 与原项目 model-constants.js BUILTIN_MODEL_PROPERTY_KEYS 一致：
//   BUILTIN_MODELS.HOST = 'host'
//   BUILTIN_MODEL_PROPERTY_KEYS.host = { ID: 'bk_host_id', NAME: 'bk_host_name' }
// 注意：bk_host_id 是前端注入属性（bk_issystem=true，后端API不返回）
// 参考：/workspace/bk-cmdb/src/ui/src/components/filters/store.js L641-648
const HOST_ID_PROPERTY = {
  bk_property_id: 'bk_host_id',
  bk_property_name: 'ID',
  bk_property_type: 'int',
  bk_obj_id: 'host',
  bk_issystem: true,
  bk_isapi: false,
  bk_property_index: -Infinity
}

// 主线拓扑模型“名称”属性（前端注入，确保即使后端未配置属性也存在）。
// 与原项目 filters/store.js defaultConditionProperties.NORMAL 一致，
// 高级筛选“添加其他条件”除主机属性外，还包含集群(set)/模块(module)的名称属性。
// 参考：/workspace/bk-cmdb/src/ui/src/components/filters/store.js L58-81
const SET_NAME_PROPERTY = {
  bk_property_id: 'bk_set_name',
  bk_property_name: '集群名称',
  bk_property_type: 'singlechar',
  bk_obj_id: 'set',
  bk_issystem: false,
  bk_isapi: false,
  bk_property_index: 1
}
const MODULE_NAME_PROPERTY = {
  bk_property_id: 'bk_module_name',
  bk_property_name: '模块名称',
  bk_property_type: 'singlechar',
  bk_obj_id: 'module',
  bk_issystem: false,
  bk_isapi: false,
  bk_property_index: 1
}

// 模型中文名（用于表头后缀），复刻原项目 renderHeader 的 getModelById(modelId).bk_obj_name。
// 对应原项目 MODEL_INFO / objectModelClassify：set=集群、module=模块、biz=业务、host=主机。
const MODEL_OBJ_NAME = {
  biz: '业务',
  set: '集群',
  module: '模块',
  host: '主机'
}

const DEFAULT_TABLE_HEADER = [
  { bk_property_id: 'bk_host_id', bk_property_name: 'ID', bk_property_type: 'int', bk_obj_id: 'host', bk_issystem: true, bk_isapi: false },
  { bk_property_id: 'bk_host_innerip', bk_property_name: '内网IP', bk_property_type: 'singlechar', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_host_name', bk_property_name: '主机名称', bk_property_type: 'singlechar', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_host_outerip', bk_property_name: '外网IP', bk_property_type: 'singlechar', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_cloud_id', bk_property_name: '云区域', bk_property_type: 'int', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_os_type', bk_property_name: '操作系统类型', bk_property_type: 'enum', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false, option: [{ id: '1', name: 'Linux' }, { id: '2', name: 'Windows' }] },
  { bk_property_id: 'bk_os_name', bk_property_name: '操作系统名称', bk_property_type: 'singlechar', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_os_version', bk_property_name: '操作系统版本', bk_property_type: 'singlechar', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_cpu', bk_property_name: 'CPU核数', bk_property_type: 'int', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_mem', bk_property_name: '内存容量', bk_property_type: 'int', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_disk', bk_property_name: '磁盘容量', bk_property_type: 'int', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_mac', bk_property_name: 'MAC地址', bk_property_type: 'singlechar', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_sn', bk_property_name: '设备序列号', bk_property_type: 'singlechar', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_asset_id', bk_property_name: '资产编号', bk_property_type: 'singlechar', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'operator', bk_property_name: '运维人员', bk_property_type: 'singlechar', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_comment', bk_property_name: '备注', bk_property_type: 'text', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'create_time', bk_property_name: '创建时间', bk_property_type: 'datetime', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'last_time', bk_property_name: '最后修改时间', bk_property_type: 'datetime', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false }
]

export default {
  name: 'HostList',
  mixins: [tableMixin],
  components: {
    HostListOptions,
    HostFilterTag,
    ModuleSelectorWithTab,
    EditMultipleHost,
    AcrossBusinessConfirm,
    AcrossBusinessModuleSelector
  },
  props: {
    // 当前选中的拓扑节点
    node: {
      type: Object,
      required: true
    },
    // tab 是否激活
    active: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      hostId: null,
      hostName: null,
      table: {
        data: [],
        selection: [],
        sort: 'bk_host_id',
        pagination: {
          count: 0,
          current: parseInt(this.$route.query.page, 10) || 1,
          limit: 10,
          'limit-list': [10, 50, 100, 500]
        }
      },
      tableHeader: DEFAULT_TABLE_HEADER,
      customColumns: [],
      columnsConfig: {
        show: false,
        selected: [],
        // 与原项目 FilterStore.fixedPropertyIds 一致：
        // /workspace/bk-cmdb/src/ui/src/components/filters/store.js L57
        // fixedPropertyIds: ['bk_host_id', 'bk_host_innerip', 'bk_host_innerip_v6', 'bk_cloud_id']
        // 复刻原项目 FilterStore.fixedPropertyIds（store.js L57）：仅固定业务无关的主键/网络列，
        // 集群名称(bk_set_name)/模块名称(bk_module_name) 不在此列 → 在“列表显示属性配置”中可编辑/可移除。
        // 注：set/module 列仍由后端聚合（row.set/row.module）并在 defaultIds 中默认展示，
        // 只是不再强制固定，符合原项目“presetHeader 默认带出、但用户可自由配置”的语义。
        disabledColumns: ['bk_host_id', 'bk_host_innerip', 'bk_cloud_id']
      },
      allProperties: [],
      // 集群(set)/模块(module)模型属性，用于高级筛选“添加其他条件”的拓扑属性目录
      setProperties: [],
      moduleProperties: [],
      searchKeyword: '',
      filtersTagHeight: 0,
      lastNodeId: null,
      isTableReady: false,
      // 表格 key：列配置（顺序/成员）变更后自增，强制 bk-table 整体重渲染，
      // 使表头立刻刷新。el-table 对“列顺序/成员”变更的内置响应不积极，
      // 仅靠 tableHeader 数组变更无法保证表头顺序与成员即时更新。
      tableKey: 0,
      // 表格 loading 状态：必须声明在 data() 中才能驱动 bk-table 上的
      // v-bkloading="{ isLoading: loading }" 指令（参考项目内 host-details /
      // general-model / module-selector 等 loading 组件约定）。
      // 生命周期：loadHostList() 在发起 searchHosts 请求前置 true，
      // 请求结束（finally）置 false，覆盖节点切换 / 分页 / 搜索 / 排序 /
      // 高级筛选变更 / 刷新等全部触发列表重载的 API 调用。
      loading: false,
      // 转移至模块对话框状态
      transferDialog: {
        visible: false,
        type: '',
        business: { bk_biz_id: 0, bk_biz_name: '' },
        modules: [],
        confirmLoading: false
      },
      // 跨业务转移（转移到其他业务）弹窗状态
      acrossConfirm: {
        visible: false,
        count: 0,
        invalidList: []
      },
      acrossSelector: {
        visible: false,
        business: {},
        confirmLoading: false
      },
      acrossBiz: {
        srcBizId: null,
        hostIds: []
      },
      acrossBusinessType: ONE_TO_ONE
    }
  },
  computed: {
    // 节点数据
    nodeData() {
      return this.node?.data || {}
    },
    // 节点类型
    objId() {
      return this.nodeData.bk_obj_id
    },
    // 高级筛选可用的全部属性（host + set + module 合并，按 bk_property_id 去重）
    // 用于从 URL 还原条件时（restoreFromUrl）能正确识别 set/module 属性并绑定 bk_obj_id
    filterProperties() {
      const merged = {}
      ;[...this.allProperties, ...this.setProperties, ...this.moduleProperties].forEach((p) => {
        if (p && p.bk_property_id) {
          merged[p.bk_property_id] = p
        }
      })
      return Object.values(merged)
    }
  },
  watch: {
    node: {
      deep: false,
      immediate: true,
      handler(node) {
        if (node && node.data) {
          const nodeId = node.id
          const page = this.$route.query.page ? parseInt(this.$route.query.page, 10) : 1
          this.table.pagination.current = page
          // 恢复 URL 中的排序状态（从主机详情返回时，路径从 /host/:id 回到 /index，
          // node watcher 重新触发，读取 query.sort 恢复 table.sort）
          const sortQuery = this.$route.query.sort
          if (sortQuery) {
            this.table.sort = sortQuery
          }
          
          if (nodeId === this.lastNodeId) {
            this.scheduleLoadHostList()
            return
          }

          this.lastNodeId = nodeId
          // 属性加载与筛选条件恢复已在 created() 的 initFilterData() 中完成，
          // 节点切换时仅触发列表重载（避免重复 restore 清空已恢复的条件）
          this.scheduleLoadHostList()
        }
      }
    },
    active(active) {
      // tab 激活时，如果无数据则加载
      if (active && this.node && !this.table.data.length) {
        this.loadHostList()
      }
    }
  },
  created() {
    this.initFilterData().then(() => {
      this.registerFilterRouteWatch()
      this.registerFilterStoreWatch()
    })
  },
  mounted() {
    this.disabledTableSettingDefaultBehavior()

    this.$nextTick(() => {
      this.isTableReady = true
    })

    this.unwatchFilter = this.$watch(() => [FilterStore.selected, FilterStore.condition, FilterStore.IP], () => {
      this.$nextTick(() => {
        const el = this.$el.querySelector('.filter-tag .filter-wrapper')
        if (el && el.getBoundingClientRect) {
          this.filtersTagHeight = el.getBoundingClientRect().height
        } else {
          this.filtersTagHeight = 0
        }
      })
    }, { immediate: true, deep: true })
  },
  beforeDestroy() {
    this.unwatchFilter && this.unwatchFilter()
    this.unwatchRouter && this.unwatchRouter()
    this.unwatchFilterStore && this.unwatchFilterStore()
    // 取消进行中的主机列表请求，释放大列表数据引用，避免组件销毁后陈旧 500+ 行响应挂载/驻留（GC）
    cancelRequest('biz-host-list')
  },
  methods: {
    /**
     * 初始化筛选数据：先并行加载 host/set/module 三类模型属性，
     * 再初始化 FilterStore（注入 set/module 属性映射），最后从 URL 还原筛选条件。
     * 与原项目一致：高级筛选“添加其他条件”除主机属性外，还包含主线拓扑
     * 模型（集群 set / 模块 module）的属性。
     * 参考：/workspace/bk-cmdb/src/ui/src/components/filters/store.js L58-81
     */
    async initFilterData() {
      await Promise.all([
        this.loadHostAttributes(),
        this.loadSetAttributes(),
        this.loadModuleAttributes()
      ])
      await this.initFilterStore()
      // 属性映射已就绪，使用合并后的属性列表正确还原 set/module 条件
      FilterStore.restoreFromUrl(this.filterProperties)
      this.scheduleLoadHostList()
    },

    /**
     * 加载集群（set）模型属性，用于高级筛选“添加其他条件”的集群属性目录
     */
    async loadSetAttributes() {
      try {
        const result = await modelAPI.getModelAttributes('set')
        const attrs = result.data?.attributes || result.attributes || result.data || result || []
        this.setProperties = Array.isArray(attrs) ? attrs.filter(p => !p.bk_isapi) : []
      } catch (e) {
        console.error('加载集群属性失败:', e)
        this.setProperties = []
      }
    },

    /**
     * 加载模块（module）模型属性，用于高级筛选“添加其他条件”的模块属性目录
     */
    async loadModuleAttributes() {
      try {
        const result = await modelAPI.getModelAttributes('module')
        const attrs = result.data?.attributes || result.attributes || result.data || result || []
        this.moduleProperties = Array.isArray(attrs) ? attrs.filter(p => !p.bk_isapi) : []
      } catch (e) {
        console.error('加载模块属性失败:', e)
        this.moduleProperties = []
      }
    },

    /**
     * 初始化 FilterStore
     * modelPropertyMap 同时注入 host / set / module 三类属性，
     * 使高级筛选的“添加其他条件”可选取集群、模块模型属性（如 集群名称、模块名称）。
     */
    async initFilterStore() {
      const bizId = this.node?.data?.bk_biz_id || this.$route.params.bizId || 1
      await setupFilterStore({
        bk_biz_id: bizId,
        modelIds: ['host', 'module', 'set'],
        urlSync: true,
        modelPropertyMap: {
          host: this.allProperties.length ? this.allProperties : DEFAULT_TABLE_HEADER,
          set: this.setProperties.length ? this.setProperties : [SET_NAME_PROPERTY],
          module: this.moduleProperties.length ? this.moduleProperties : [MODULE_NAME_PROPERTY]
        }
      })
    },

    /**
     * 注册路由查询监听：仅处理分页（page/limit）变化触发的列表刷新。
     * 筛选条件 / IP 的变更改由 registerFilterStoreWatch 直接监听 FilterStore
     * 来触发重载，避免依赖 URL 深监听在“移除条件”场景下不触发的问题。
     */
    registerFilterRouteWatch() {
      this.unwatchRouter = RouterQuery.watch('*', (query, oldQuery = {}) => {
        // 仅分页变化触发重载，筛选条件 / IP 交给 FilterStore 监听
        const reloadKeys = ['page', 'limit']
        const changed = reloadKeys.some(key => query[key] !== (oldQuery || {})[key])
        if (!changed) return
        if (query.page) {
          this.table.pagination.current = parseInt(query.page, 10)
        }
        if (query.limit) {
          this.table.pagination.limit = parseInt(query.limit, 10)
        }
        this.loadHostList()
      }, { throttle: 16 })
    },

    /**
     * 直接监听「有效筛选签名」来触发列表重载，而非原始 FilterStore.condition 对象。
     *
     * 为什么不能 deep watch FilterStore.condition：
     * 在高级筛选抽屉中点击「添加其他条件」时，handleConditionPickerChange 会更新
     * FilterStore.selected，进而触发 store 内部 selected 监听 → initCondition()，
     * 给新属性写入默认空值（Utils.getDefaultData 返回 value: '' / []），从而替换掉
     * FilterStore.condition 的对象引用。若此处 deep watch 整个 condition 对象，
     * 这次“仅添加空条件行、尚未查询”的变更就会被判定为 condition 变化并立即发起重载，
     * 表现为“添加条件后主机列表 loading 转圈”——但列表内容其实没变。
     *
     * 改为监听 FilterStore.getQuery() 序列化后的有效查询串（filter|ip），
     * 它与 loadHostList 实际发出的请求完全一致（空值被忽略）。
     * 因此：
     *  - 添加一条尚未填值的空条件 → 签名不变 → 不重载（修复本 bug）；
     *  - 填值后点「查询」/ 删 tag（resetValue 置空）/ 清空条件 → 签名变化 → 重载。
     */
    registerFilterStoreWatch() {
      this.unwatchFilterStore = this.$watch(
        () => {
          const q = FilterStore.getQuery(FilterStore.condition)
          return `${q.filter}|${q.ip}`
        },
        () => {
          this.scheduleLoadHostList()
        }
      )
    },

    /**
     * 防抖触发列表重载：多个同步的响应式变更（如 restoreFromUrl 同时改 condition 与 IP）
     * 会合并为一次请求，避免重复加载。
     */
    scheduleLoadHostList() {
      if (this._filterReloadTimer) {
        clearTimeout(this._filterReloadTimer)
      }
      this._filterReloadTimer = setTimeout(() => {
        this._filterReloadTimer = null
        this.loadHostList()
      }, 30)
    },

    /**
     * 加载主机模型属性列表
     * 与原项目一致：bk_host_id 因 bk_issystem=true 被后端过滤，
     * 需要前端注入。参考：/workspace/bk-cmdb/src/ui/src/components/filters/store.js L641-648
     */
    async loadHostAttributes() {
      try {
        const result = await modelAPI.getModelAttributes('host')
        const attrs = result.data?.attributes || result.attributes || result.data || result || []
        // 过滤掉 bk_isapi 为 true 的属性（与后端 for_web 逻辑一致）
        let filteredAttrs = Array.isArray(attrs) ? attrs.filter(p => !p.bk_isapi) : []
        if (filteredAttrs.length) {
          // 注入 bk_host_id 属性（后端因 bk_issystem=true 不返回）
          const hasHostId = filteredAttrs.some(p => p.bk_property_id === 'bk_host_id')
          if (!hasHostId) {
            filteredAttrs = [HOST_ID_PROPERTY, ...filteredAttrs]
          }
          this.allProperties = filteredAttrs
        } else {
          // 内置模型 host 无属性配置时，使用默认属性列表
          this.allProperties = DEFAULT_TABLE_HEADER
        }
      } catch (e) {
        console.error('加载主机属性失败:', e)
        this.allProperties = DEFAULT_TABLE_HEADER
      }
      // 复刻原项目 columnsConfigProperties（store/modules/view/business-host.js）：
      // 主机列表列 = set属性 + module属性 + host属性。将“集群名称/模块名称”注入为常驻列，
      // 确保业务拓扑主机列表始终具备聚合展示主机所属集群/模块的能力。
      this.allProperties = [...this.allProperties, SET_NAME_PROPERTY, MODULE_NAME_PROPERTY]
      // 加载自定义列配置
      this.loadCustomColumns()
    },

    /**
     * 加载用户自定义列配置
     */
    async loadCustomColumns() {
      try {
        const result = await userCustom.getModelCustomColumns('host')
        const saved = result?.data?.columns || result?.columns || []
        if (saved && saved.length) {
          this.customColumns = saved
        }
      } catch (e) {
        console.error('加载自定义列配置失败:', e)
      }
      // 设置表头
      this.setTableHeader()
    },

    /**
     * 设置表格表头
     */
    setTableHeader() {
      if (!this.allProperties.length) return

      const disabledIds = this.columnsConfig.disabledColumns || []
      let headerProps = []

      if (this.customColumns && this.customColumns.length) {
        // 使用自定义列配置
        headerProps = this.customColumns
          .map(id => this.allProperties.find(p => p.bk_property_id === id))
          .filter(Boolean)
      } else {
        // 默认列：与原项目 presetHeader 一致，取前6个属性
        // 参考：/workspace/bk-cmdb/src/ui/src/components/filters/store.js L176-200
        // 复刻 presetHeader 将 模块名称(bk_module_name)/集群名称(bk_set_name) 也推入默认表头，
        // 与固定列(bk_host_id/bk_host_innerip/bk_cloud_id)共同构成业务拓扑主机列表默认视图。
        const defaultIds = ['bk_host_id', 'bk_host_innerip', 'bk_cloud_id', 'bk_module_name', 'bk_set_name', 'bk_host_name', 'bk_host_outerip', 'bk_os_name']
        headerProps = defaultIds
          .map(id => this.allProperties.find(p => p.bk_property_id === id))
          .filter(Boolean)
          .slice(0, 6)
      }

      // 确保固定列（ID、内网IP、云区域）在最前面（与原项目 defaultHeader 一致）
      const fixedProps = disabledIds
        .map(id => this.allProperties.find(p => p.bk_property_id === id))
        .filter(Boolean)
      const otherProps = headerProps.filter(p => !disabledIds.includes(p.bk_property_id))

      this.tableHeader = [...fixedProps, ...otherProps]
      // 同步 columnsConfig.selected
      this.columnsConfig.selected = this.tableHeader.map(p => p.bk_property_id)
    },

    /**
     * 应用列配置
     */
    async handleApplyColumns(properties) {
      this.customColumns = properties.map(p => p.bk_property_id)
      this.columnsConfig.show = false
      this.setTableHeader()
      // 强制表格重渲染：列顺序/成员变更后，el-table 不会积极刷新表头，
      // 通过自增 tableKey 触发整体重渲染，确保表头立即更新。
      this.tableKey += 1

      // 保存到存储
      try {
        await userCustom.saveModelCustomColumns('host', this.customColumns)
      } catch (e) {
        console.error('保存列配置失败:', e)
      }
      this.$bkMessage({ message: '配置已应用', theme: 'success' })
    },

    /**
     * 取消列配置
     */
    handleCancelColumns() {
      this.columnsConfig.show = false
    },

    /**
     * 还原默认列配置
     */
    async handleResetColumns() {
      this.customColumns = []
      this.columnsConfig.show = false
      this.setTableHeader()
      // 还原默认后同样强制重渲染，使表头顺序/成员立即刷新
      this.tableKey += 1

      // 清空存储
      try {
        await userCustom.saveModelCustomColumns('host', [])
      } catch (e) {
        console.error('重置列配置失败:', e)
      }
      this.$bkMessage({ message: '已还原默认配置', theme: 'success' })
    },

    /**
     * 侧边抽屉隐藏回调
     */
    handleSidesliderHidden() {
      this.columnsConfig.show = false
    },

    /**
     * 加载主机列表数据
     * 使用统一的 searchHosts 接口，支持节点联动、搜索、筛选
     */
    async loadHostList() {
      this.loading = true
      try {
        const data = this.nodeData
        const objId = this.objId

        // 获取业务ID：业务节点用 bk_inst_id，其他节点用 bk_biz_id
        const bkBizId = objId === 'biz' ? data.bk_inst_id : (data.bk_biz_id || 0)

        if (!bkBizId) {
          this.table.data = []
          this.table.pagination.count = 0
          return
        }

        // 构建 HostCommonSearch 请求载荷
        const payload = {
          bk_biz_id: bkBizId,
          page: {
            start: (this.table.pagination.current - 1) * this.table.pagination.limit,
            limit: this.table.pagination.limit,
            sort: this.table.sort
          },
          condition: []
        }

        // 根据节点类型添加拓扑条件
        if (objId === 'biz') {
          // 业务节点：条件为空，仅通过 bk_biz_id 过滤
        } else if (objId === 'set') {
          // 集群节点：添加 set 条件
          payload.condition.push({
            bk_obj_id: 'set',
            fields: [],
            condition: [
              { field: 'bk_set_id', operator: '$eq', value: data.bk_inst_id }
            ]
          })
        } else if (objId === 'module') {
          // 模块节点：添加 module 条件
          payload.condition.push({
            bk_obj_id: 'module',
            fields: [],
            condition: [
              { field: 'bk_module_id', operator: '$eq', value: data.bk_inst_id }
            ]
          })
        } else {
          // 自定义主线层（如 appsys）：后端按该实例递归收集其下所有 module 实例 id，
          // 聚合其下全部主机。与 biz/set/module 等价，支持业务拓扑任意层级节点查主机。
          payload.condition.push({
            bk_obj_id: objId,
            fields: [],
            condition: [
              { field: 'bk_inst_id', operator: '$eq', value: data.bk_inst_id }
            ]
          })
        }

        // 添加搜索关键词条件（主机名称模糊搜索）
        if (this.searchKeyword) {
          payload.condition.push({
            bk_obj_id: 'host',
            fields: [],
            condition: [
              { field: 'bk_host_name', operator: 'contains', value: this.searchKeyword }
            ]
          })
        }

        // 添加 FilterStore 中的高级筛选条件
        const filterCondition = FilterStore.condition
        const filterIP = FilterStore.IP
        const filterSelected = FilterStore.selected || []
        if (filterCondition && Object.keys(filterCondition).length > 0) {
          Object.keys(filterCondition).forEach(key => {
            const cond = filterCondition[key]
            if (cond === null || cond === undefined) return
            // 跳过空值和空数组
            const val = cond.value
            if (val === null || val === undefined || val === '') return
            if (Array.isArray(val) && val.length === 0) return

            // 通过 selected 属性列表查找 bk_obj_id
            const property = filterSelected.find(p => p.bk_property_id === key)
            const modelId = property ? property.bk_obj_id : 'host'
            const fieldId = key

            // $range 操作符拆分为 $gte + $lte（与原项目一致）
            if (cond.operator === '$range' && Array.isArray(val) && val.length >= 2) {
              const existing = payload.condition.find(c => c.bk_obj_id === modelId)
              const rangeConds = [
                { field: fieldId, operator: '$gte', value: val[0] },
                { field: fieldId, operator: '$lte', value: val[1] }
              ]
              if (existing) {
                existing.condition.push(...rangeConds)
              } else {
                payload.condition.push({
                  bk_obj_id: modelId,
                  fields: [],
                  condition: rangeConds
                })
              }
              return
            }

            // $in/$nin 操作符：将字符串分割为数组
            let submitValue = val
            if (['$in', '$nin'].includes(cond.operator)) {
              if (typeof val === 'string') {
                submitValue = val.split(/[\n,，;；]/).map(s => s.trim()).filter(s => s.length > 0)
              } else if (!Array.isArray(val)) {
                submitValue = [val]
              }
            }

            const existing = payload.condition.find(c => c.bk_obj_id === modelId)
            if (existing) {
              existing.condition.push({
                field: fieldId,
                operator: cond.operator || '$eq',
                value: submitValue
              })
            } else {
              payload.condition.push({
                bk_obj_id: modelId,
                fields: [],
                condition: [{
                  field: fieldId,
                  operator: cond.operator || '$eq',
                  value: submitValue
                }]
              })
            }
          })
        }

        // 添加 IP 筛选条件
        if (filterIP && filterIP.text) {
          const ipList = Utils.splitIP(filterIP.text)
          if (ipList.length > 0) {
            const flagParts = []
            if (filterIP.inner) flagParts.push('bk_host_innerip')
            if (filterIP.outer) flagParts.push('bk_host_outerip')
            payload.ip = {
              data: ipList,
              exact: filterIP.exact ? 1 : 0,
              flag: flagParts.join('|')
            }
          }
        }

        // 调用新的 searchHosts 接口（翻页/筛选/排序重载时用 requestId 取消上一批未完成的请求，
        // 避免陈旧的大列表响应在竞态下挂载，造成 500+ 行反复重建导致卡顿）
        const result = await topoAPI.searchHosts(payload,
          { requestId: 'biz-host-list', cancelPrevious: true })

        // 兼容后端返回的数据结构
        const resData = result
        // 冻结大列表数据，跳过 Vue 对每行每列的深度响应式代理（与上游/资源主机列表一致，
        // 避免业务拓扑下 500+ 主机在重载时产生大量响应式 getter 与内存开销，DOM 替换/GC 更快）
        this.table.data = freezeList(resData.info || [])
        this.table.pagination.count = resData.count || 0
      } catch (e) {
        // 请求被取消（翻页/筛选/排序重载时的 cancelPrevious）属预期行为，静默忽略，
        // 保留旧数据：由取代它的新请求负责重新填充（避免清空表格闪烁）
        if (isCancelError(e)) {
          console.log('[HostList] 请求已取消（被新请求取代）')
          return
        }
        console.error('加载主机列表失败:', e)
        this.table.data = []
        this.table.pagination.count = 0
      } finally {
        this.loading = false
      }
    },

    /**
     * 获取属性显示值
     * @param {Object} row 行数据
     * @param {Object} column 列定义
     * @returns {string} 显示值
     */
    getPropertyValue(row, column) {
      const propId = column.bk_property_id
      const objId = column.bk_obj_id

      // 集群(set)/模块(module)列：值由后端按主机拓扑关系聚合，内嵌在 row.set / row.module 数组中。
      // 对齐原项目：主机列表“集群名称/模块名称”列展示该主机所属全部集群/模块名称（多值拼接显示）。
      // 对应原项目 logics/hostsearch.go 的 fillHostSetInfo / fillHostModuleInfo（search_hosts 返回内嵌 set/module）。
      // 注意：属性 id 取自 SET_NAME_PROPERTY / MODULE_NAME_PROPERTY 常量（单一数据源），避免硬编码字面量。
      if (objId === 'set' && propId === SET_NAME_PROPERTY.bk_property_id) {
        const names = (Array.isArray(row.set) ? row.set : [])
          .map(s => s[SET_NAME_PROPERTY.bk_property_id])
          .filter(Boolean)
        return names.length ? names.join(', ') : '--'
      }
      if (objId === 'module' && propId === MODULE_NAME_PROPERTY.bk_property_id) {
        const names = (Array.isArray(row.module) ? row.module : [])
          .map(m => m[MODULE_NAME_PROPERTY.bk_property_id])
          .filter(Boolean)
        return names.length ? names.join(', ') : '--'
      }

      // host 类型直接取属性，其他类型从子对象取
      const modelData = objId === 'host' ? row : (row[objId] || row)
      let value = modelData[propId]

      // 云区域ID特殊处理
      if (propId === 'bk_cloud_id' && value !== undefined && value !== null) {
        return value === 0 ? '默认云区域' : `云区域${value}`
      }

      // 空值处理（保持 host 列表既有 '--' 占位约定）
      if (value === undefined || value === null || value === '') {
        return '--'
      }

      // 属性类型转换：枚举/多选枚举/列表按 option 映射为显示名（如 操作系统类型 '1' → 'Linux'），
      // bool 转 是/否，其余按原类型格式化。统一复用全站 property-value.js 的 formatPropertyValue，
      // 避免业务拓扑主机列表与资源/关联列表在属性格式化上实现漂移。
      // 注意：column 来自后端属性（含 bk_property_type 与 option），未加载到属性时回退到
      // DEFAULT_TABLE_HEADER（bk_os_type 已声明为 enum 并带 option），保证降级路径也能正确映射。
      return formatPropertyValue(value, column)
    },

    /**
     * 获取模型中文名（用于表头 (模型名) 后缀）
     * 复刻原项目 renderHeader 的 getModelById(modelId).bk_obj_name。
     * 模型中文名集中在 MODEL_OBJ_NAME 单一数据源，按 bk_obj_id 动态查表，
     * 渲染路径不出现“集群/模块”等字面量（非硬编码）。
     * @param {string} objId 模型 id（set/module/host/biz）
     * @returns {string} 模型中文名
     */
    getModelName(objId) {
      return MODEL_OBJ_NAME[objId] || objId
    },

    /**
     * 生成表头 render-header 函数（复刻原项目 host-list.vue 的 renderHeader）。
     * 原项目用 this.$createElement 渲染“属性名 + 灰色 (模型中文名)” 两段 span，
     * 且 (模型中文名) span 直接 inline style: { color: '#979BA5', marginLeft: '4px' }。
     * 此处通过闭包捕获当前 column 定义（bk_property_name / bk_obj_id），
     * 避免硬编码字面量：列名取 column.bk_property_name，模型名取 getModelName(bk_obj_id)。
     * 注意：render-header 创建的 VNode 不带 scoped 样式属性，故 (模型名) 灰色样式必须用
     * inline style（与原项目一致），不能依赖 scoped CSS。
     * @param {Object} column 列定义
     * @returns {Function} element-ui render-header(h, context) => VNode
     */
    makeHeaderRenderer(column) {
      return (h) => {
        const children = [column.bk_property_name || column.bk_property_id]
        if (column.bk_obj_id && column.bk_obj_id !== 'host') {
          children.push(h('span', {
            class: 'header-model-name',
            style: { color: '#979BA5', marginLeft: '4px' }
          }, `(${this.getModelName(column.bk_obj_id)})`))
        }
        return h('span', { class: 'header-column-name' }, children)
      }
    },

    /**
     * 获取表头列名称（带模型中文名后缀）
     * 复刻原项目 host-list.vue 的 renderHeader：非主机属性（set/module）追加
     * “(模型中文名)” 后缀，例如 “集群名称(集群)” / “模块名称(模块)”。
     * 对应原项目：name = `${name}(${model.bk_obj_name})`（无空格、半角括号）。
     * 列名取自 column.bk_property_name（属性定义），模型名取自 getModelName（按 bk_obj_id 查表），
     * 二者均为数据驱动，非硬编码字面量。
     * @param {Object} column 列定义
     * @returns {string} 表头文本（作为无 header slot 时的兜底 label）
     */
    getHeaderLabel(column) {
      const name = column.bk_property_name || column.bk_property_id
      const objId = column.bk_obj_id
      // 仅非主机属性追加 (模型中文名)；host 列直接显示属性名
      if (objId && objId !== 'host') {
        const modelName = this.getModelName(objId)
        return `${name}(${modelName})`
      }
      return name
    },

    /**
     * 获取列最小宽度
     */
    getColumnMinWidth(column) {
      const widthMap = {
        bk_host_id: 80,
        bk_host_name: 150,
        bk_host_innerip: 130,
        bk_host_outerip: 130,
        bk_cloud_id: 100
      }
      return widthMap[column.bk_property_id] || 120
    },

    /**
     * 获取列是否可排序（按属性类型规则，复刻原项目 isPropertySortable）
     * - 主机属性：排除 foreignkey / topology / inner_table
     * - 非主机属性：排除 inner_table
     * 其余类型（int / singlechar / enum / datetime / bool ...）均可排序
     */
    getColumnSortable(column) {
      return isPropertySortable(column) ? 'custom' : false
    },

    /**
     * 分页变更
     */
    /**
     * 分页变更
     */
    handlePageChange(current = 1) {
      this.table.pagination.current = current
      this.loadHostList()
      RouterQuery.set({
        page: current,
        node: RouterQuery.get('node'),
        _t: Date.now()
      })
    },

    /**
     * 每页条数变更
     */
    handleLimitChange(limit) {
      this.table.pagination.limit = limit
      this.table.pagination.current = 1
      this.loadHostList()
      RouterQuery.set({
        page: 1,
        _t: Date.now()
      })
    },

    /**
     * 排序变更（复刻原项目 handleSortChange：通过 getSort 转换后下发 page.sort，
     * 同时重置页码到第 1 页，确保排序后显示排序后的第 1 页数据；
     * 排序状态同步到 URL 参数 sort，使返回主机列表时能恢复；
     * 恢复默认排序时显式传递 sort=null 以从 URL 中清除旧排序参数）
     */
    handleSortChange(sort) {
      this.table.sort = getSort(sort) || 'bk_host_id'
      this.table.pagination.current = 1
      this.loadHostList()
      // 持久化排序状态到 URL；默认值时传 null 以清除 URL 中的 sort 参数
      RouterQuery.set({
        sort: this.table.sort !== 'bk_host_id' ? this.table.sort : null,
        _t: Date.now()
      })
    },

    /**
     * 选择行变更
     */
    handleSelectionChange(selection) {
      this.table.selection = selection
    },

    /**
     * 表头点击（列设置）
     */
    handleHeaderClick(column) {
      if (column.type !== 'setting') {
        return
      }
      ColumnsConfig.open({
        props: {
          properties: this.allProperties,
          selected: this.columnsConfig.selected,
          disabledColumns: this.columnsConfig.disabledColumns,
          max: 20
        },
        handler: {
          apply: async (properties) => {
            await this.handleApplyColumns(properties)
          },
          reset: async () => {
            await this.handleResetColumns()
          }
        }
      })
    },

    /**
     * 值点击（主机ID跳转详情）
     */
    handleValueClick(row, column) {
      console.log('[HostList] handleValueClick called', { row, column })
      if (column.bk_property_id !== 'bk_host_id') return
      
      const hostId = row.host?.bk_host_id || row.bk_host_id || row.id
      console.log('[HostList] handleValueClick: hostId=', hostId)
      if (!hostId) return
      
      const bizId = this.$route.params.bizId
      const page = this.table.pagination.current
      const node = RouterQuery.get('node')

      // 携带当前高级筛选条件（filter / ip）进入详情，
      // 否则返回列表时 URL 中无筛选参数，FilterStore 被重置后条件即丢失
      const query = {
        _f: page,
        node: node,
        _t: Date.now()
      }
      const currentFilter = RouterQuery.get('filter')
      const currentIp = RouterQuery.get('ip')
      if (currentFilter) query.filter = currentFilter
      if (currentIp) query.ip = currentIp

      // 复刻原项目：原项目 handleValueClick 用 $routerActions.redirect 且不传 query，
      // vue-router 会自动保留当前 URL 的全部 query（含 topology-tree 的 keyword）。
      // lite 这里显式构造 query 会抹掉 keyword，导致从主机详情返回后拓扑树搜索词丢失。
      // 因此此处必须把拓扑树的 keyword 一并带入，保证往返过程中关键词不丢失。
      const currentKeyword = RouterQuery.get('keyword')
      if (currentKeyword) query.keyword = currentKeyword

      console.log('[HostList] navigating to host details:', { bizId, hostId, page, node, filter: currentFilter, ip: currentIp })

      this.$router.push({
        name: MENU_BUSINESS_HOST_DETAILS,
        params: {
          bizId: bizId,
          id: hostId
        },
        query
      })
    },

    /**
     * 搜索
     */
    handleSearch(keyword) {
      this.searchKeyword = keyword
      this.table.pagination.current = 1
      // 预留：带搜索条件查询
      this.loadHostList()
    },

    /**
     * 转移主机：打开"转移至模块"对话框
     * Phase 1：弹出对话框并加载/返回 API 数据（业务拓扑树 / 空闲机池 / 主机模块绑定），
     * 暂不执行写操作。
     */
    handleTransfer(type) {
      // 跨业务转移（转移到其他业务）：源业务 A → 目标业务 B
      if (type === 'acrossBusiness') {
        return this.handleAcrossBusinessTransfer()
      }
      // Phase 1 聚焦"业务模块"与"空闲模块"；主机池/跨业务转移留待后续阶段
      if (!['idle', 'business'].includes(type)) {
        this.$bkMessage({
          message: `「${type}」转移为 Phase 1 范围外，暂未实现`,
          theme: 'warning'
        })
        return
      }

      const bkBizId = this.objId === 'biz'
        ? this.nodeData.bk_inst_id
        : (this.nodeData.bk_biz_id || 0)
      if (!bkBizId) {
        this.$bkMessage({ message: '无法确定业务，无法执行转移', theme: 'warning' })
        return
      }

      // 业务名同步取自节点数据（无需再拉业务列表接口 getBizList）
      const bizName = this.nodeData.bk_biz_name
        || (this.objId === 'biz' ? this.nodeData.bk_inst_name : '')

      // 预选模块同步取自表格行数据：后端 search_hosts 已按主机拓扑聚合 row.module[]
      // （元素含 bk_module_id，见 topo_service._enrich_hosts_with_topo），
      // 无需再查 getHostModuleConfig，对齐原项目 selection[0].module 语义。
      const modules = this.collectSelectionModules()

      // 立即弹出对话框（与侧边抽屉一致：先出现外壳，内容由子组件异步加载），
      // 不再被串行接口 await 阻塞"点击→出现"时间。
      this.transferDialog = {
        visible: true,
        type,
        business: { bk_biz_id: bkBizId, bk_biz_name: bizName },
        modules,
        confirmLoading: false
      }
    },

    // 从选中主机行聚合其当前所属模块（row.module 由后端填充，元素含 bk_module_id）
    collectSelectionModules() {
      const moduleIds = []
      this.table.selection.forEach((row) => {
        ;(Array.isArray(row.module) ? row.module : []).forEach((m) => {
          if (m && m.bk_module_id != null) {
            moduleIds.push(m.bk_module_id)
          }
        })
      })
      return [...new Set(moduleIds)].map(mid => ({ bk_module_id: mid }))
    },

    /**
     * 跨业务转移入口：转移到其他业务（源业务 A → 目标业务 B）
     * 第一步：确认对话框（展示选中主机数；不实现主机池，invalidList 为空）
     */
    async handleAcrossBusinessTransfer() {
      const bkBizId = this.objId === 'biz'
        ? this.nodeData.bk_inst_id
        : (this.nodeData.bk_biz_id || 0)
      if (!bkBizId) {
        this.$bkMessage({ message: '无法确定业务，无法执行跨业务转移', theme: 'warning' })
        return
      }
      const hostIds = this.table.selection
        .map(h => h.bk_host_id || (h.host && h.host.bk_host_id))
        .filter(id => id != null)
      if (!hostIds.length) {
        this.$bkMessage({ message: '请先勾选需要转移的主机', theme: 'warning' })
        return
      }
      this.acrossBiz = { srcBizId: bkBizId, hostIds }
      this.acrossConfirm = {
        visible: true,
        count: hostIds.length,
        invalidList: []
      }
    },

    /**
     * 跨业务转移「确认」对话框点击下一步：打开目标业务 + 模块选择器
     */
    handleAcrossConfirmNext() {
      this.acrossConfirm.visible = false
      this.acrossSelector = {
        visible: true,
        business: { bk_biz_id: this.acrossBiz.srcBizId },
        confirmLoading: false
      }
    },

    /**
     * 跨业务转移「选择目标业务+模块」确认：提交后端
     */
    async handleAcrossSelectorConfirm(checked, targetBizId) {
      const moduleIds = (checked || [])
        .filter(node => node.data && node.data.bk_obj_id === 'module')
        .map(node => node.data.bk_inst_id)
      if (!moduleIds.length) {
        this.$bkMessage({ message: '请选择目标业务下的模块', theme: 'warning' })
        return
      }
      this.acrossSelector.confirmLoading = true
      try {
        await topoAPI.transferAcrossBiz({
          src_bk_biz_id: this.acrossBiz.srcBizId,
          dst_bk_biz_id: targetBizId,
          bk_host_id: this.acrossBiz.hostIds,
          module_id: moduleIds,
          bk_supplier_account: '0'
        })
        this.$bkMessage({
          message: `已转移 ${this.acrossBiz.hostIds.length} 台主机到业务 ${targetBizId} 的 ${moduleIds.length} 个模块`,
          theme: 'success'
        })
        this.acrossSelector.visible = false
        this.loadHostList()
      } catch (e) {
        console.error('[HostList] 跨业务转移失败:', e)
        this.$handleApiError(e)
      } finally {
        this.acrossSelector.confirmLoading = false
      }
    },

    /**
     * 转移确认（对话框 下一步/确定 触发）
     * Phase 2：调用后端写操作，修改 cc_ModuleHostConfig 绑定，成功后刷新列表。
     */
    async handleTransferConfirm(tab, checked) {
      const targetModuleIds = (checked || [])
        .filter(node => node.data && node.data.bk_obj_id === 'module')
        .map(node => node.data.bk_inst_id)
      if (!targetModuleIds.length) {
        this.$bkMessage({ message: '请选择目标模块', theme: 'warning' })
        return
      }
      const hostIds = this.table.selection
        .map(h => h.bk_host_id || (h.host && h.host.bk_host_id))
        .filter(id => id != null)
      if (!hostIds.length) {
        this.$bkMessage({ message: '未获取到选中主机', theme: 'warning' })
        return
      }

      this.transferDialog.confirmLoading = true
      try {
        const result = await topoAPI.transferModules({
          bk_biz_id: this.transferDialog.business.bk_biz_id,
          bk_host_id: hostIds,
          module_id: targetModuleIds,
          transfer_type: tab.moduleType,
          bk_supplier_account: '0'
        })
        this.$bkMessage({
          message: `已转移 ${hostIds.length} 台主机到 ${targetModuleIds.length} 个模块`,
          theme: 'success'
        })
        this.transferDialog.visible = false
        this.loadHostList()
        this.$emit('transfer-complete', {
          bizId: this.transferDialog.business.bk_biz_id,
          hostIds,
          moduleIds: targetModuleIds,
          transferType: tab.moduleType
        })
      } catch (e) {
        console.error('[HostList] 转移失败:', e)
        this.$handleApiError(e)
      } finally {
        this.transferDialog.confirmLoading = false
      }
    },

    /**
     * 转移取消
     */
    handleTransferCancel() {
      this.transferDialog.visible = false
      this.acrossConfirm.visible = false
      this.acrossSelector.visible = false
      this.transferDialog.confirmLoading = false
      this.acrossSelector.confirmLoading = false
    },

    /**
     * 新增主机
     */
    handleAddHost() {
      // 预留：新增主机弹窗
      console.log('新增主机到模块:', this.nodeData.bk_inst_id)
    },

    /**
     * 批量编辑：打开编辑主机抽屉
     * 通过 ref 调用 edit-multiple-host 组件内的 mixin 方法，
     * 由 mixin 负责加载属性分组、挂载表单、提交更新。
     */
    handleMultipleEdit() {
      this.$refs.editMultipleHost.handleMultipleEdit()
    },

    /**
     * 导出选中
     */
    handleExport() {
      // 预留：导出选中主机
      console.log('导出选中:', this.table.selection)
    },

    /**
     * 导出全部
     */
    handleBatchExport() {
      // 预留：导出全部主机
      console.log('导出全部:', this.table.pagination.count)
    },

    /**
     * 高级筛选 - 打开筛选侧边抽屉
     */
    handleSetFilters() {
      FilterForm.show()
    },

    /**
     * 刷新
     */
    handleRefresh() {
      this.loadHostList()
    }
  }
}
</script>

<style lang="scss" scoped>
.list-layout {
    overflow: hidden;
}

.filter-tag {
    padding: 0 20px;

    & ~ .host-table {
        margin-top: 0;
    }
}

.host-table {
    margin-top: 10px;
}

// 表头 (模型名) 后缀：复刻原项目 renderHeader 的
// style: { color: '#979BA5', marginLeft: '4px' }，灰色、左间距 4px
.header-model-name {
    color: #979BA5;
    margin-left: 4px;
    font-weight: normal;
}

.host-id-link {
  color: $primaryColor;
  cursor: pointer;

  &:hover {
    text-decoration: underline;
  }
}

.table-empty {
  padding: 40px 0;
}

.table-setting-btn {
  cursor: pointer;
  color: #63656e;
  font-size: 16px;

  &:hover {
    color: #3a84ff;
  }
}
</style>
