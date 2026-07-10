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
      @header-click="handleHeaderClick">

      <!-- 选择列 -->
      <bk-table-column type="selection" width="50" align="center" fixed></bk-table-column>

      <!-- 动态列：根据 tableHeader 渲染 -->
      <bk-table-column
        v-for="column in tableHeader"
        :key="column.bk_property_id"
        :prop="column.bk_property_id"
        :label="column.bk_property_name"
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
  </div>
</template>

<script>
import HostListOptions from './host-list-options.vue'
import HostFilterTag from '@/components/filters/filter-tag.vue'
import ColumnsConfig from '@/components/columns-config/columns-config.js'
import FilterForm from '@/components/filters/filter-form.js'
import FilterStore, { setupFilterStore } from '@/components/filters/store'
import tableMixin from '@/mixins/table'
import { topoAPI } from '@/api/topo'
import { modelAPI } from '@/api/client'
import { userCustom } from '@/api/client'

// 默认表头列定义（简化版，与原项目 host 属性对应）
const DEFAULT_TABLE_HEADER = [
  { bk_property_id: 'bk_host_id', bk_property_name: '主机ID', bk_property_type: 'int', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_host_name', bk_property_name: '主机名称', bk_property_type: 'singlechar', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_host_innerip', bk_property_name: '内网IP', bk_property_type: 'singlechar', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_host_outerip', bk_property_name: '外网IP', bk_property_type: 'singlechar', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_cloud_id', bk_property_name: '云区域', bk_property_type: 'int', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
  { bk_property_id: 'bk_os_type', bk_property_name: '操作系统类型', bk_property_type: 'singlechar', bk_obj_id: 'host', bk_issystem: false, bk_isapi: false },
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
    HostFilterTag
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
      loading: false,
      allProperties: [],
      table: {
        data: [],
        selection: [],
        sort: 'bk_host_id',
        pagination: {
          count: 0,
          current: 1,
          limit: 10,
          'limit-list': [10, 50, 100, 500]
        }
      },
      tableHeader: DEFAULT_TABLE_HEADER,
      customColumns: [],
      columnsConfig: {
        show: false,
        selected: [],
        disabledColumns: ['bk_host_id', 'bk_host_name']
      },
      searchKeyword: '',
      filtersTagHeight: 0,
      lastNodeId: null
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
    }
  },
  watch: {
    node: {
      deep: false,
      immediate: true,
      handler(node) {
        if (node && node.data) {
          const nodeId = node.id
          // 同一节点不重复加载
          if (nodeId === this.lastNodeId) return
          this.lastNodeId = nodeId
          this.table.pagination.current = 1
          this.loadHostAttributes()
          this.loadHostList()
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
    this.initFilterStore()
  },
  mounted() {
    this.disabledTableSettingDefaultBehavior()
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
  },
  methods: {
    /**
     * 初始化 FilterStore
     */
    async initFilterStore() {
      const bizId = this.node?.data?.bk_biz_id || this.$route.params.bizId || 1
      await setupFilterStore({
        bk_biz_id: bizId,
        modelIds: ['host', 'module', 'set', 'biz'],
        searchHandler: () => {
          this.table.pagination.current = 1
          this.loadHostList()
        },
        modelPropertyMap: {
          host: this.allProperties.length ? this.allProperties : DEFAULT_TABLE_HEADER
        }
      })
    },

    /**
     * 加载主机模型属性列表
     */
    async loadHostAttributes() {
      try {
        const result = await modelAPI.getModelAttributes('host')
        const attrs = result.data?.attributes || result.attributes || result.data || result || []
        // 过滤掉 bk_isapi 为 true 的属性
        const filteredAttrs = Array.isArray(attrs) ? attrs.filter(p => !p.bk_isapi) : []
        if (filteredAttrs.length) {
          this.allProperties = filteredAttrs
        } else {
          // 内置模型 host 无属性配置时，使用默认属性列表
          this.allProperties = DEFAULT_TABLE_HEADER
        }
      } catch (e) {
        console.error('加载主机属性失败:', e)
        this.allProperties = DEFAULT_TABLE_HEADER
      }
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
        // 默认列：固定列 + 默认显示的列
        const defaultIds = ['bk_host_id', 'bk_host_name', 'bk_host_innerip', 'bk_host_outerip', 'bk_cloud_id']
        headerProps = defaultIds
          .map(id => this.allProperties.find(p => p.bk_property_id === id))
          .filter(Boolean)
      }

      // 确保固定列在最前面
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
          this.table.data = []
          this.table.pagination.count = 0
          return
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

            const existing = payload.condition.find(c => c.bk_obj_id === modelId)
            if (existing) {
              existing.condition.push({
                field: fieldId,
                operator: cond.operator || '$eq',
                value: val
              })
            } else {
              payload.condition.push({
                bk_obj_id: modelId,
                fields: [],
                condition: [{
                  field: fieldId,
                  operator: cond.operator || '$eq',
                  value: val
                }]
              })
            }
          })
        }

        // 添加 IP 筛选条件
        if (filterIP && filterIP.text) {
          const ipList = filterIP.text.split('\n').filter(ip => ip.trim())
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

        // 调用新的 searchHosts 接口
        const result = await topoAPI.searchHosts(payload)

        // 兼容后端返回的数据结构
        const resData = result.data || result
        this.table.data = resData.info || []
        this.table.pagination.count = resData.count || 0
      } catch (e) {
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
      // host 类型直接取属性，其他类型从子对象取
      const modelData = objId === 'host' ? row : (row[objId] || row)
      let value = modelData[propId]

      // 云区域ID特殊处理
      if (propId === 'bk_cloud_id' && value !== undefined && value !== null) {
        return value === 0 ? '默认云区域' : `云区域${value}`
      }

      // 空值处理
      if (value === undefined || value === null || value === '') {
        return '--'
      }
      return value
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
     * 获取列排序属性
     */
    getColumnSortable(column) {
      return ['int', 'long', 'float', 'date', 'time'].includes(column.bk_property_type) ? 'custom' : false
    },

    /**
     * 分页变更
     */
    handlePageChange(current = 1) {
      this.table.pagination.current = current
      this.loadHostList()
    },

    /**
     * 每页条数变更
     */
    handleLimitChange(limit) {
      this.table.pagination.limit = limit
      this.table.pagination.current = 1
      this.loadHostList()
    },

    /**
     * 排序变更
     */
    handleSortChange(sort) {
      this.table.sort = sort.prop ? `${sort.order === 'descending' ? '-' : ''}${sort.prop}` : 'bk_host_id'
      this.loadHostList()
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
      if (column.bk_obj_id !== 'host' || column.bk_property_id !== 'bk_host_id') return
      // 预留：跳转主机详情
      console.log('跳转主机详情:', row.host?.bk_host_id || row.bk_host_id)
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
     * 转移主机
     */
    handleTransfer(type) {
      // 预留：转移主机弹窗
      console.log('转移主机:', type, this.table.selection)
    },

    /**
     * 新增主机
     */
    handleAddHost() {
      // 预留：新增主机弹窗
      console.log('新增主机到模块:', this.nodeData.bk_inst_id)
    },

    /**
     * 批量编辑
     */
    handleMultipleEdit() {
      // 预留：批量编辑弹窗
      console.log('批量编辑:', this.table.selection)
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
