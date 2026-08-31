<template>
  <div class="models-layout general-model-layout">
    <div class="models-options clearfix">
      <div class="options-button clearfix fl">
        <bk-button theme="primary" :disabled="isSetOrModule" v-bk-tooltips.top-start="'集群/模块请在业务拓扑中创建'" @click="handleCreate">新建</bk-button>
        <bk-button class="models-button" theme="default" :disabled="isSetOrModule" v-bk-tooltips.top-start="'集群/模块不支持复制'" @click="handleCopySelected">复制</bk-button>
        <!-- <bk-button class="models-button" theme="default" @click="handleImport">导入</bk-button> -->
        <!-- <bk-button class="models-button" theme="default" @click="handleExport">导出</bk-button> -->
        <bk-button class="models-button" theme="default" @click="handleBatchEdit">批量更新</bk-button>
        <bk-button class="models-button button-delete" theme="default" @click="handleBatchDelete">删除</bk-button>
      </div>
      <div class="options-button fr ml10">
        <span :class="['icon-button', 'option-filter', { active: hasCondition }]" @click="handleAdvancedFilter">
          <i class="bk-icon icon-cc-funnel"></i>
        </span>
        <span class="icon-button ml5" @click="handleRefresh">
          <i class="bk-icon icon-cc-refresh"></i>
        </span>
        <span class="icon-button ml5" @click="columnsConfig.show = true">
          <i class="bk-icon icon-cc-setting"></i>
        </span>
      </div>
      <div class="options-filter clearfix fr">
        <div class="filter-selector">
          <bk-select
            v-model="filter.field"
            searchable
            :clearable="false"
            @change="handleFieldChange">
            <bk-option
              v-for="property in searchableProperties"
              :key="property.bk_property_id"
              :id="property.bk_property_id"
              :name="property.bk_property_name">
            </bk-option>
          </bk-select>
        </div>
        <div class="filter-value">
          <div v-if="filter.field && filter.field !== ''" class="search-input-wrapper">
            <div v-if="isEnumField || isBoolField || isListField || isEnumMultiField" class="enum-select-wrapper" :class="{ 'is-open': enumDropdownVisible }" @click.stop>
              <div class="enum-input-container">
                <input
                  type="text"
                  class="search-input enum-multi-input"
                  :value="filter.values.join(', ')"
                  :placeholder="filterPlaceholder"
                  readonly
                  @click.stop="toggleEnumDropdown">
                <i :class="['bk-icon', 'icon-angle-down', 'bk-select-angle', { 'icon-flip': enumDropdownVisible }]" @click.stop="toggleEnumDropdown"></i>
              </div>
              <div class="enum-dropdown" @click.stop>
                <div class="bk-select-search-wrapper" v-if="enumOptions.length > 3">
                  <input
                    type="text"
                    class="bk-select-search-input"
                    v-model="enumSearchQuery"
                    placeholder="搜索..."
                    @click.stop>
                </div>
                <div class="bk-select-options">
                  <label
                    v-for="option in filteredEnumOptions"
                    :key="option.id"
                    class="bk-select-option"
                    :class="{ 'is-selected': filter.values.includes(option.id) }">
                    <input
                      type="checkbox"
                      :value="option.id"
                      :checked="filter.values.includes(option.id)"
                      @click="handleEnumCheckbox(option.id, $event)">
                    <span class="bk-select-option-name">{{ option.name }}</span>
                    <i class="bk-icon bk-select-check icon-check" v-if="filter.values.includes(option.id)"></i>
                  </label>
                </div>
              </div>
            </div>
            <template v-else-if="isDateField">
              <cmdb-search-date
                class="search-date-picker"
                v-model="filter.values"
                :property="filterProperty"
                :placeholder="filterPlaceholder"
                @change="handleSearch">
              </cmdb-search-date>
            </template>
            <template v-else-if="isTimeField">
              <cmdb-search-time
                class="search-time-picker"
                v-model="filter.values"
                :property="filterProperty"
                :placeholder="filterPlaceholder"
                @change="handleSearch">
              </cmdb-search-time>
            </template>
            <template v-else>
              <input
                type="text"
                class="search-input"
                v-model="filter.value"
                :placeholder="filterPlaceholder"
                @keyup.enter="handleSearch">
            </template>
          </div>
          <span v-else class="filter-placeholder">请先选择字段</span>
        </div>
        <div class="filter-exact" v-if="allowFuzzyQuery">
          <bk-checkbox
            size="small"
            v-model="filter.fuzzyQuery">
            模糊
          </bk-checkbox>
        </div>
      </div>
    </div>

    <filter-tag
      ref="filterTagRef"
      v-if="hasFilterCondition"
      class="filter-tag-wrapper"
      :filter-tags="filterTags"
      @remove="handleRemoveFilterTag"
      @clear-all="handleClearAllFilterTags">
    </filter-tag>

    <general-model-filter
      ref="generalModelFilterRef"
      :show.sync="advancedFilter.show"
      :properties="allProperties"
      :loaded-data="table.list"
      :condition-map="advancedFilterConditions"
      @search="handleAdvancedFilterSearch"
      @reset="handleAdvancedFilterReset">
    </general-model-filter>

    <div class="models-table-wrapper">
      <bk-table
        ref="tableRef"
        class="models-table"
        v-bkloading="{ isLoading: table.loading }"
        :data="table.list"
        :pagination="table.pagination"
        :max-height="tableContentHeight"
        :sort="tableSort"
        :selected-data.sync="selectedIds"
        :row-key="row => row[instanceIdField]"
        @selection-change="handleSelectionChange"
        @page-change="handlePageChange"
        @page-limit-change="handleLimitChange"
        @sort-change="handleSortChange">
          <bk-table-column type="selection" width="60" align="center" fixed></bk-table-column>
          <bk-table-column
            v-for="column in table.header"
            :key="column.id"
            :prop="column.id"
            :label="column.name"
            :sortable="getColumnSortable(column.id)"
            :show-overflow-tooltip="true">
            <template v-if="column.id === instanceIdField" #default="{ row }">
              <span class="cell-id-link" @click="handleViewDetails(row)">
                {{ row[column.id] }}
              </span>
            </template>
            <template v-else #default="{ row }">
              {{ formatCellValue(row[column.id], column) }}
            </template>
          </bk-table-column>
          <bk-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <bk-button :text="true" theme="danger" @click="handleDeleteSingle(row)">删除</bk-button>
            </template>
          </bk-table-column>
        </bk-table>
    </div>

    <bk-sideslider
      transfer
      :is-show.sync="columnsConfig.show"
      :title="'列表显示属性配置'"
      :width="sidesliderWidth"
      :quick-close="true"
      @hidden="handleSidesliderHidden">
      <template #content>
        <columns-config
          v-if="columnsConfig.show"
          :properties="allProperties"
          :selected="columnsConfig.selected"
          :disabled-columns="disabledColumns"
          :max="20"
          @on-apply="handleApplyColumns"
          @on-cancel="handleCancelColumns"
          @on-reset="handleResetColumns">
        </columns-config>
      </template>
    </bk-sideslider>

    <!-- 新增实例弹窗 -->
    <bk-sideslider
      transfer
      :is-show.sync="createDialogVisible"
      :title="'新增实例'"
      :width="createSidesliderWidth"
      :fullscreen="createSidesliderFullscreen"
      :quick-close="true"
      :before-close="handleCreateDialogBeforeClose"
      @hidden="handleCreateDialogClose">
      <template #content>
        <div class="create-form-wrapper">
          <cmdb-form
            ref="cmdbFormRef"
            :properties="allProperties"
            :property-groups="propertyGroups"
            :values="createForm"
            :type="'create'"
            :model-id="objId"
            :show-options="true"
            :submitting="createFormLoading"
            :is-mobile="isMobileDevice"
            submit-text="提交"
            @update:values="createForm = $event"
            @submit="handleCreateSubmit"
            @cancel="handleCreateDialogClose">
          </cmdb-form>
        </div>
      </template>
    </bk-sideslider>

    <!-- 批量更新弹窗 -->
    <bk-sideslider
      transfer
      :is-show.sync="batchUpdateDialogVisible"
      :title="'批量更新'"
      :width="createSidesliderWidth"
      :fullscreen="createSidesliderFullscreen"
      :quick-close="true"
      :before-close="handleBatchUpdateDialogBeforeClose"
      @hidden="handleBatchUpdateDialogClose">
      <template #content>
        <div class="batch-update-form-wrapper">
          <div class="batch-update-info" v-if="selectedIds.length > 0">
            <i class="bk-icon icon-info-circle"></i>
            已选择 <strong>{{ selectedIds.length }}</strong> 个实例进行更新
            <span v-if="hiddenUniqueProperties.length > 0" class="hidden-properties">
              （已隐藏 <strong>{{ hiddenUniqueProperties.join('、') }}</strong>，原因：添加了唯一校验规则）
            </span>
          </div>
          <form-multiple
            ref="formMultipleRef"
            :properties="allProperties"
            :property-groups="propertyGroups"
            :show-options="true"
            :submitting="batchUpdateFormLoading"
            :model-id="objId"
            submit-text="更新"
            @submit="handleBatchUpdateSubmit"
            @cancel="handleBatchUpdateDialogClose"
            @unique-properties-changed="handleUniquePropertiesChanged">
          </form-multiple>
        </div>
      </template>
    </bk-sideslider>
  </div>
</template>

<script>
// 全局模糊搜索状态：持久化到 localStorage，跨模型 / 会话 / 标签页保持一致
const FUZZY_STORAGE_KEY = 'bk_cmdb_fuzzy_query'

function getInitialFuzzyQuery() {
  try {
    const stored = window.localStorage.getItem(FUZZY_STORAGE_KEY)
    // 未设置时默认勾选（true）
    if (stored === null || stored === undefined) return true
    return stored === 'true'
  } catch (e) {
    return true
  }
}

function saveFuzzyQuery(val) {
  try {
    window.localStorage.setItem(FUZZY_STORAGE_KEY, val ? 'true' : 'false')
  } catch (e) {
    // 忽略隐私模式 / 写入失败
  }
}
import ColumnsConfig from '@/components/columns-config/index.vue'
import FilterTag from '@/components/filter-tag/index.vue'
import FilterTagItem from '@/components/filter-tag/filter-tag-item.vue'
import GeneralModelFilter from '@/components/filter/general-model-filter.vue'
import FormMultiple from '@/components/ui/form/form-multiple.vue'
import CmdbForm from '@/components/ui/form/form.vue'
import DateSearch from '@/components/search/date.vue'
import TimeSearch from '@/components/search/time.vue'
import { modelAPI, userCustom, cancelRequest, isCancelError, freezeList } from '@/api/client'
import routerQuery from '@/utils/router-query'
import QS from 'qs'
import throttle from 'lodash/throttle'
import isEqual from 'lodash/isEqual'
import { buildSearchParams } from '@/utils/query-builder'
import { formatPropertyValue } from '@/utils/property-value'
import { MENU_INDEX, MENU_RESOURCE_INSTANCE_DETAILS, MENU_RESOURCE_MANAGEMENT, MENU_RESOURCE_HOST_DETAILS } from '@/dictionary/menu-symbol'
import AppMixin from '@/mixins/app'

export default {
  name: 'GeneralModel',
  mixins: [AppMixin],
  components: {
    ColumnsConfig,
    FilterTag,
    FilterTagItem,
    GeneralModelFilter,
    FormMultiple,
    'cmdb-form': CmdbForm,
    'cmdb-search-date': DateSearch,
    'cmdb-search-time': TimeSearch
  },
  data() {
    return {
      filter: {
        field: '',
        value: '',
        values: [],
        fuzzyQuery: getInitialFuzzyQuery()
      },
      enumDropdownVisible: false,
      enumSearchQuery: '',
      // 不再硬编码默认模型；缺失 objId 时由 resolveObjId 按数据（模型列表首个）动态定位
      objId: '',
      modelData: null,
      allProperties: [],
      propertyGroups: [],
      defaultColumns: [],
      // 与原项目保持一致: customColumns 是从存储加载的自定义列配置（存储状态）
      // columnsConfig.selected 是 UI 状态（抽屉中已勾选的属性），由 setTableHeader 同步更新
      // 参考: /workspace/bk-cmdb/src/ui/src/views/general-model/index.vue customColumns computed
      customColumns: [],
      selectedIds: [],
      selectedRows: [],
      hiddenUniqueProperties: [],
      createDialogVisible: false,
      createForm: {},
      createFormInitial: {},
      createFormRules: {},
      createFormLoading: false,
      batchUpdateDialogVisible: false,
      batchUpdateFormLoading: false,
      table: {
        list: [],
        header: [],
        sort: '',
        pagination: {
          count: 0,
          current: 1,
          limit: 10,
          show: true,
          'limit-list': [10, 20, 50, 100, 500]
        },
        loading: false,
        displayFields: []
      },
      filterTags: [],
      advancedFilterConditions: null,
      currentSearchParams: null,
      advancedFilter: {
        show: false,
        conditions: [],
        condition: {
          field: '',
          operator: '$eq',
          value: ''
        }
      },
      columnsConfig: {
        show: false,
        selected: []
      },
      isUrlUpdateTriggered: false,
      searchTimeout: null,
      filterTagHeight: 0,
      tableMaxHeight: 600,
      MENU_RESOURCE_INSTANCE_DETAILS,
      MENU_RESOURCE_HOST_DETAILS,
      MENU_RESOURCE_MANAGEMENT
    }
  },
  computed: {
    modelName() {
      if (this.modelData && this.modelData.bk_obj_name) {
        return this.modelData.bk_obj_name
      }
      return this.objId
    },
    // 内置模型主键字段映射（与后端 BUILTIN_ID_FIELD_MAP 保持一致）
    instanceIdField() {
      const idFieldMap = {
        'host': 'bk_host_id',
        'biz': 'bk_biz_id',
        'set': 'bk_set_id',
        'module': 'bk_module_id',
        'bk_biz_set_obj': 'bk_biz_set_id'
      }
      return idFieldMap[this.objId] || 'bk_inst_id'
    },
    // 内置模型名称字段映射
    instanceNameField() {
      const nameFieldMap = {
        'host': 'bk_host_name',
        'biz': 'bk_biz_name',
        'set': 'bk_set_name',
        'module': 'bk_module_name',
        'bk_biz_set_obj': 'bk_biz_set_name'
      }
      return nameFieldMap[this.objId] || 'bk_inst_name'
    },
    // 禁用列：内置模型的 ID/名称字段为系统固定字段，不可移除
    disabledColumns() {
      return [this.instanceIdField, this.instanceNameField]
    },
    // 资源目录实例列表视图中,主线拓扑模型(set/module)不允许从通用入口新建/复制,
    // 避免脱离业务归属形成孤儿节点(应走业务拓扑页建立)。
    isSetOrModule() {
      return ['set', 'module'].includes(this.objId)
    },
    searchableProperties() {
      // 与原项目保持一致: 排除 bk_isapi=true 的系统字段(如 id、bk_inst_id、bk_obj_id)
      // 参考: /workspace/bk-cmdb/src/ui/src/components/model-instance/property.vue
      return this.allProperties.filter(property => !property.bk_isapi && property.bk_property_id !== 'id')
    },
    filterProperty() {
      if (!this.filter.field || !this.allProperties.length) return null
      return this.allProperties.find(property => property.bk_property_id === this.filter.field)
    },
    filterPlaceholder() {
      if (this.filterProperty) {
        const propertyType = this.filterProperty.bk_property_type
        const selectTypes = ['list', 'enum', 'timezone', 'organization', 'date', 'time', 'bool']
        if (selectTypes.includes(propertyType)) {
          return `请选择${this.filterProperty.bk_property_name}`
        }
        return `请输入${this.filterProperty.bk_property_name}`
      }
      return '请选择搜索字段'
    },
    allowFuzzyQuery() {
      const property = this.filterProperty
      if (!property) return false
      const propertyType = property.bk_property_type
      if (!propertyType) return false
      const supportedTypes = [
        'singlechar', 'longchar', 'enum', 'int', 'bool', 'time', 'date', 'float', 'list'
      ]
      return supportedTypes.includes(propertyType)
    },
    isEnumField() {
      const property = this.filterProperty
      if (!property) return false
      return property.bk_property_type === 'enum'
    },
    isListField() {
      const property = this.filterProperty
      if (!property) return false
      return property.bk_property_type === 'list'
    },
    isBoolField() {
      const property = this.filterProperty
      if (!property) return false
      return property.bk_property_type === 'bool'
    },
    isEnumMultiField() {
      const property = this.filterProperty
      if (!property) return false
      return property.bk_property_type === 'enummulti'
    },
    isDateField() {
      const property = this.filterProperty
      if (!property) return false
      return property.bk_property_type === 'date'
    },
    isTimeField() {
      const property = this.filterProperty
      if (!property) return false
      return property.bk_property_type === 'time'
    },
    enumOptions() {
      const property = this.filterProperty
      if (!property) return []

      if (property.bk_property_type === 'bool') {
        return [
          { id: 'true', name: 'true' },
          { id: 'false', name: 'false' }
        ]
      }

      const option = property.option
      if (option && Array.isArray(option)) {
        if (option.length > 0 && option[0] && typeof option[0] === 'object' && option[0].id !== undefined) {
          return option.map(opt => ({
            id: opt.id,
            name: opt.name
          }))
        } else {
          return option.map(opt => ({
            id: opt,
            name: opt
          }))
        }
      }

      return []
    },
    filteredEnumOptions() {
      if (!this.enumSearchQuery) {
        return this.enumOptions
      }
      const query = this.enumSearchQuery.toLowerCase()
      return this.enumOptions.filter(opt => opt.name.toLowerCase().includes(query))
    },
    tableContentHeight() {
      return Math.max(200, this.$APP.height - (this.filterTagHeight || 0) - 190)
    },
    hasFilterCondition() {
      return this.visibleFilterTags.length > 0
    },
    hasCondition() {
      return this.filterTagHeight !== 0
    },
    sidesliderWidth() {
      const screenWidth = window.innerWidth
      if (screenWidth >= 768) {
        return 600
      } else if (screenWidth >= 480) {
        return Math.floor(screenWidth * 0.8)
      }
      return Math.floor(screenWidth * 0.95)
    },
    tableSort() {
      if (!this.table.sort) {
        return undefined
      }
      return {
        prop: this.table.sort.startsWith('-') ? this.table.sort.substring(1) : this.table.sort,
        order: this.table.sort.startsWith('-') ? 'descending' : 'ascending'
      }
    },
    visibleFilterTags() {
      return this.filterTags.filter(tag => {
        const value = tag.value
        if (Array.isArray(value)) {
          return value.length > 0
        }
        return value !== null && value !== undefined && String(value).trim().length > 0
      })
    },
    hasFilterCondition() {
      return this.visibleFilterTags.length > 0
    },
    hasCondition() {
      return this.visibleFilterTags.length > 0
    },
    isMobileDevice() {
      return window.innerWidth < 768
    },
    dialogWidth() {
      const screenWidth = window.innerWidth
      if (screenWidth >= 1200) {
        return '800px'
      } else if (screenWidth >= 768) {
        return '700px'
      } else if (screenWidth >= 480) {
        return Math.floor(screenWidth * 0.9) + 'px'
      } else {
        return Math.floor(screenWidth * 0.95) + 'px'
      }
    },
    createSidesliderWidth() {
      const width = window.innerWidth
      if (width < 480) return '100%'
      if (width < 768) return Math.floor(width * 0.9) + 'px'
      return 600
    },
    createSidesliderFullscreen() {
      return window.innerWidth < 480
    }
  },
  created() {
    // 面包屑活跃守卫：本视图的 updateBreadcrumbs 可能在异步加载完成后才执行，
    // 若期间路由已切换到其它视图（组件销毁），必须拦截写入，避免旧标题串扰新视图。
    this._breadcrumbGuard = true
    this.resolveObjId()
    this.updateBreadcrumbs()

    this.stopRouteQueryWatch = routerQuery.watch('*', (query, oldQuery) => {
      console.log('[Index.watch] URL变化被触发', { query, oldQuery })

      const isFromDetails = this.prevInstanceId && !this.$route.params.instanceId
      console.log('[Index.watch] isFromDetails:', isFromDetails, 'prevInstanceId:', this.prevInstanceId)

      if (isFromDetails) {
        console.log('[Index.watch] 从详情页返回，优先恢复状态')
        this.restoreStateFromUrl()
        // restoreStateFromUrl已经处理了filterTags，不需要再调用updateFilterTagsFromQuery
        
        // 如果有高级筛选条件，使用高级筛选参数加载数据
        if (this.advancedFilterConditions) {
          const rawConditions = []
          Object.keys(this.advancedFilterConditions).forEach(field => {
            const cond = this.advancedFilterConditions[field]
            rawConditions.push({
              field,
              operator: cond.operator,
              value: cond.value
            })
          })
          const searchParams = this.buildAdvancedSearchParams(rawConditions)
          console.log('[Index.watch] 从详情页返回，使用高级筛选参数:', searchParams)
          this.loadModelData(searchParams)
        } else {
          this.loadModelData()
        }
        return
      }

      if (this.isUrlUpdateTriggered) {
        console.log('[Index.watch] isUrlUpdateTriggered为true，跳过处理')
        this.isUrlUpdateTriggered = false
        return
      }

      const hasQuery = query && Object.keys(query).length > 0
      const hadQuery = oldQuery && Object.keys(oldQuery).length > 0

      console.log('[Index.watch] hasQuery:', hasQuery, 'hadQuery:', hadQuery)

      if (hasQuery && hadQuery) {
        const pageChanged = query.page !== oldQuery.page
        const limitChanged = query.limit !== oldQuery.limit
        const fieldChanged = query.field !== oldQuery.field
        const filterChanged = query.filter !== oldQuery.filter
        const fuzzyChanged = query.fuzzy !== oldQuery.fuzzy
        const sortChanged = query.sort !== oldQuery.sort
        const filter_advChanged = query.filter_adv !== oldQuery.filter_adv
        const sChanged = query.s !== oldQuery.s

        console.log('[Index.watch] 变化检测:', { pageChanged, limitChanged, fieldChanged, filterChanged, fuzzyChanged, sortChanged, filter_advChanged, sChanged })

        if (pageChanged || limitChanged) {
          this.table.pagination.current = parseInt(query.page || 1, 10)
          this.table.pagination.limit = parseInt(query.limit || 10, 10)
        }
        if (fieldChanged || filterChanged || fuzzyChanged || sortChanged || filter_advChanged || sChanged) {
          console.log('[Index.watch] 搜索条件变化，执行restoreStateFromUrl')
          this.restoreStateFromUrl()
          // restoreStateFromUrl已经处理了filterTags，不需要再调用updateFilterTagsFromQuery
          // 只有在没有filter_adv的简单搜索情况下才需要调用
          if (!filter_advChanged && !sChanged) {
            this.updateFilterTagsFromQuery()
          }
        }

        if (pageChanged || limitChanged || fieldChanged || filterChanged || fuzzyChanged || sortChanged || filter_advChanged || sChanged) {
          console.log('[Index.watch] 执行loadModelData')
          
          // 如果有高级筛选条件，使用高级筛选参数加载数据
          if (this.advancedFilterConditions) {
            const rawConditions = []
            Object.keys(this.advancedFilterConditions).forEach(field => {
              const cond = this.advancedFilterConditions[field]
              rawConditions.push({
                field,
                operator: cond.operator,
                value: cond.value
              })
            })
            const searchParams = this.buildAdvancedSearchParams(rawConditions)
            console.log('[Index.watch] 使用高级筛选参数:', searchParams)
            this.loadModelData(searchParams)
          } else {
            this.loadModelData()
          }
        }
      }
    }, { throttle: 300 })
  },
  mounted() {
    console.log('[Index.mounted] 组件挂载')
    console.log('[Index.mounted] 当前URL:', window.location.href)
    console.log('[Index.mounted] Route query:', JSON.stringify(this.$route.query))
    this.restoreStateFromUrl()
    console.log('[Index.mounted] restoreStateFromUrl 后 filter.value:', this.filter.value, 'fuzzy:', this.filter.fuzzyQuery)
    this.$nextTick(() => {
      this.updateFilterTagHeight()
      // 初次挂载时同步计算表格高度, 避免等待 setTimeout 300ms
      this.calculateTableHeight()
    })

    // 监听窗口尺寸变化, 重新计算表格高度, 保持分页在 window 可视范围内
    this.resizeHandler = () => {
      this.calculateTableHeight()
      this.updateFilterTagHeight()
    }
    window.addEventListener('resize', this.resizeHandler)

    this.clickOutsideHandler = (event) => {
      const wrapper = document.querySelector('.enum-select-wrapper')
      if (wrapper && !wrapper.contains(event.target)) {
        this.enumDropdownVisible = false
      }
    }
    document.addEventListener('click', this.clickOutsideHandler)

    setTimeout(() => {
      // 如果有高级筛选条件，构建 searchParams 并传递给 loadModelData
      if (this.advancedFilterConditions) {
        const rawConditions = []
        Object.keys(this.advancedFilterConditions).forEach(field => {
          const cond = this.advancedFilterConditions[field]
          rawConditions.push({
            field,
            operator: cond.operator,
            value: cond.value
          })
        })
        
        // 构建高级筛选的 searchParams
        const searchParams = this.buildAdvancedSearchParams(rawConditions)
        console.log('[Index.mounted] 从URL恢复高级筛选参数:', searchParams)
        this.loadModelData(searchParams)
      } else {
        this.loadModelData()
      }
    }, 0)
  },
  beforeDestroy() {
    // 组件销毁：解除面包屑活跃守卫，阻止异步回调继续写入全局面包屑
    this._breadcrumbGuard = false
    if (this.stopRouteQueryWatch) {
      this.stopRouteQueryWatch()
    }
    if (this.clickOutsideHandler) {
      document.removeEventListener('click', this.clickOutsideHandler)
    }
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout)
    }
    if (this.resizeHandler) {
      window.removeEventListener('resize', this.resizeHandler)
    }
    // 取消进行中的列表请求，释放大列表数据引用，避免组件销毁后陈旧 500+ 行响应挂载/驻留（GC）
    cancelRequest('inst-list')
  },
  watch: {
    filterTags: {
      handler() {
        this.$nextTick(() => this.updateFilterTagHeight())
      }
    },
    filterTagHeight: {
      handler() {
        this.$nextTick(() => this.calculateTableHeight())
      }
    },
    'filter.values': {
      handler(newValues, oldValues) {
        console.log('[Index.watch.filter.values] 变化:', { old: oldValues, new: newValues })
        if (newValues && newValues.length > 0) {
          this.filter.value = newValues.join(',')
        }
      }
    },
    'filter.fuzzyQuery'(val) {
      // 全局模糊状态：任意变化（勾选/取消/URL 同步）均写回 localStorage
      saveFuzzyQuery(val)
    },
    '$route.params.objId': {
      handler(newObjId) {
        if (newObjId) {
          if (newObjId !== this.objId) {
            this.objId = newObjId
            this.updateBreadcrumbs()
            this.restoreStateFromUrl()
            this.loadModelData()
          }
        } else {
          // 路由未携带 objId：提示错误并返回首页，避免硬编码兜底
          this.resolveObjId()
        }
      }
    },
    '$route.params.instanceId': {
      handler(newInstanceId, oldInstanceId) {
        console.log('[Index.watch.instanceId] 实例ID变化:', { new: newInstanceId, old: oldInstanceId })
        if (!newInstanceId && oldInstanceId) {
          console.log('[Index.watch.instanceId] 从详情页返回，执行restoreStateFromUrl')
          this.hasRestoredFromUrl = false
          this.restoreStateFromUrl()
          // restoreStateFromUrl已经处理了filterTags，不需要再调用updateFilterTagsFromQuery
          this.hasRestoredFromUrl = true
          // 如果有高级筛选条件，使用高级筛选参数加载数据
          if (this.advancedFilterConditions) {
            const rawConditions = []
            Object.keys(this.advancedFilterConditions).forEach(field => {
              const cond = this.advancedFilterConditions[field]
              rawConditions.push({
                field,
                operator: cond.operator,
                value: cond.value
              })
            })
            const searchParams = this.buildAdvancedSearchParams(rawConditions)
            console.log('[Index.watch.instanceId] 从详情页返回，使用高级筛选参数:', searchParams)
            this.loadModelData(searchParams)
          } else {
            this.loadModelData()
          }
        }
        this.prevInstanceId = newInstanceId
      }
    },
    allProperties: {
      handler(newProperties) {
        console.log('[Index.watch.allProperties] 属性加载完成，检查是否需要恢复 filterTags')
        if (newProperties && newProperties.length > 0) {
          const query = this.$route.query
          
          // 如果有高级筛选条件，且filterTags为空，重新恢复filterTags
          if (query.filter_adv && this.filterTags.length === 0) {
            console.log('[Index.watch.allProperties] 检测到filter_adv且filterTags为空，重新恢复状态')
            this.restoreStateFromUrl()
            
            // 重新恢复状态后，使用高级筛选参数加载数据
            if (this.advancedFilterConditions && Object.keys(this.advancedFilterConditions).length > 0) {
              const rawConditions = []
              Object.keys(this.advancedFilterConditions).forEach(field => {
                const cond = this.advancedFilterConditions[field]
                rawConditions.push({
                  field,
                  operator: cond.operator,
                  value: cond.value
                })
              })
              const searchParams = this.buildAdvancedSearchParams(rawConditions)
              console.log('[Index.watch.allProperties] 使用高级筛选参数:', searchParams)
              this.loadModelData(searchParams)
            }
          } else if (newProperties && newProperties.length > 0 && !this.hasRestoredFromUrl) {
            // 简单搜索场景
            if (query && Object.keys(query).length > 0) {
              if (query.field) {
                const validField = newProperties.find(p => p.bk_property_id === query.field)
                if (validField) {
                  this.filter.field = query.field
                  if (query.filter !== undefined && query.filter !== null) {
                    this.filter.value = String(query.filter)
                  }
                }
              }
              // 仅当 URL 显式给出 fuzzy 取值时覆盖；缺失/空串保留默认（已勾选）
              if (query.fuzzy === 'true' || query.fuzzy === '1') {
                this.filter.fuzzyQuery = true
              } else if (query.fuzzy === 'false' || query.fuzzy === '0') {
                this.filter.fuzzyQuery = false
              }
              this.hasRestoredFromUrl = true
              this.updateFilterTagsFromQuery()
            } else if (!this.filter.field) {
              const firstField = newProperties.find(p => p.bk_property_id !== 'id')
              if (firstField) {
                this.filter.field = firstField.bk_property_id
              }
            }
          } else if (newProperties && newProperties.length > 0 && !this.filter.field) {
            const firstField = newProperties.find(p => p.bk_property_id !== 'id')
            if (firstField) {
              this.filter.field = firstField.bk_property_id
            }
          }
        }
      }
    }
  },
  methods: {
    /**
     * 创建合成的 bk_inst_id 属性（前端注入）
     * 与原项目 createIdProperty 保持一致:
     * 参考: /workspace/bk-cmdb/src/ui/src/service/property/property.js#L17-L40
     *
     * 后端 for_web 过滤了 bk_isapi=true 的字段（包括 bk_inst_id），
     * 前端通过此方法注入合成的 bk_inst_id 属性，用于:
     * 1. 在表头第一位显示"实例ID"列（bk_property_index: -1，优先级最高）
     * 2. 作为 disabledColumns 中的固定字段，不可移除、不可拖动
     * 3. 支持点击跳转到实例详情
     */
    createIdProperty(objId) {
      const idFieldMap = {
        'host': 'bk_host_id',
        'biz': 'bk_biz_id',
        'set': 'bk_set_id',
        'module': 'bk_module_id',
        'bk_biz_set_obj': 'bk_biz_set_id'
      }
      const idField = idFieldMap[objId] || 'bk_inst_id'
      const nameMap = {
        'host': '主机ID',
        'biz': '业务ID',
        'set': '集群ID',
        'module': '模块ID',
        'bk_biz_set_obj': '业务集ID'
      }
      const name = nameMap[objId] || '实例ID'
      return {
        id: Date.now(),
        bk_obj_id: objId,
        bk_property_id: idField,
        bk_property_name: name,
        bk_property_index: -1,
        bk_property_type: 'int',
        isonly: true,
        ispre: true,
        bk_isapi: true,
        bk_issystem: true,
        isreadonly: true,
        editable: false,
        bk_property_group: null,
        _is_inject_: true
      }
    },
    // 模型 ID 解析：
    // - 路由已携带 objId：直接使用（无硬编码兜底）
    // - 路由缺失 objId：提示 UI 错误并返回首页 index（不异步拉取后端数据、不跳首个模型）
    resolveObjId() {
      // 优先取路由参数 objId；内置模型专属资源路由（如 /resource/host）在 meta 中显式声明 objId，
      // 作为其路由语义（非缺省兜底），保证收藏项在该路由下精确命中。
      const paramObjId = this.$route.params.objId || this.$route.meta?.objId
      if (paramObjId) {
        this.objId = paramObjId
        return
      }
      this.$bkMessage({
        message: '未指定模型（objId），无法打开实例列表，已返回首页',
        theme: 'error'
      })
      this.$router.replace({ name: MENU_INDEX })
    },
    updateBreadcrumbs() {
      this.$nextTick(() => {
        // 竞态守卫：本视图可能已在异步加载期间被路由替换（组件销毁），
        // 或当前路由已切换到其它模型实例。此时若仍写入自定义面包屑，
        // 会把旧视图标题串扰到新视图（如业务拓扑页显示"负载均衡"）。
        if (!this._breadcrumbGuard) {
          return
        }
        const routeObjId = this.$route.params.objId || this.$route.meta.objId
        if (routeObjId && routeObjId !== this.objId) {
          return
        }
        this.$store.commit('setCustomBreadcrumbs', {
          enable: true,
          title: this.modelName,
          backward: () => {
            this.$router.push({
              name: this.MENU_RESOURCE_MANAGEMENT
            })
          }
        })
      })
    },
    updateFilterTagHeight() {
      setTimeout(() => {
        const filterTagRef = this.$refs?.filterTagRef
        const el = filterTagRef?.$el || filterTagRef
        if (el && el.getBoundingClientRect) {
          const style = getComputedStyle(el)
          const marginTop = parseFloat(style.marginTop) || 0
          const marginBottom = parseFloat(style.marginBottom) || 0
          this.filterTagHeight = el.getBoundingClientRect().height + marginTop + marginBottom
        } else {
          this.filterTagHeight = 0
        }
      }, 300)
    },
    calculateTableHeight() {
      // 通过 DOM 直接获取 .main-scroller 实际可用高度, 这样不受视口变化影响
      // main-scroller 高度 = main-layout 高度 = views-layout 高度 - 面包屑(53)
      // 减去内容区上方的: general-model-layout padding-top(15) + options(32) + margin(14) = 61
      // 减去内容区下方的: buffer(12) + pagination(63) = 75
      const mainScroller = document.querySelector('.main-scroller')
      if (mainScroller) {
        const scrollerHeight = mainScroller.getBoundingClientRect().height
        const newHeight = Math.max(200, scrollerHeight - 15 - 32 - 14 - 12 - 63 - (this.filterTagHeight || 0))
        console.log('[calculateTableHeight] mainScroller.height:', scrollerHeight, 'filterTagHeight:', this.filterTagHeight, 'newHeight:', newHeight, 'oldHeight:', this.tableMaxHeight)
        this.tableMaxHeight = newHeight
      } else {
        // fallback: 使用 $APP.height 推算
        const contentHeight = (this.$APP?.height || window.innerHeight) - 52 - 53
        this.tableMaxHeight = Math.max(200, contentHeight - (this.filterTagHeight || 0) - 15 - 32 - 14 - 12 - 63)
      }
    },
    async loadModelData(searchParams = null) {
      this.table.loading = true
      try {
        const query = this.$route.query
        const currentField = query.field || this.filter.field
        const currentValue = query.filter !== undefined ? String(query.filter) : this.filter.value
        // 仅当 URL 显式给出 fuzzy 取值时使用；缺失/空串保留当前/默认值（已勾选）
        const currentFuzzy = (query.fuzzy === 'true' || query.fuzzy === '1') ? true
          : (query.fuzzy === 'false' || query.fuzzy === '0') ? false
          : this.filter.fuzzyQuery
        const currentSort = query.sort || this.table.sort
        const currentPage = query.page ? parseInt(query.page, 10) : this.table.pagination.current
        const currentLimit = query.limit ? parseInt(query.limit, 10) : this.table.pagination.limit

        // 输出完整的 URL 字符串
        const fullUrl = window.location.href
        console.log('[Index.loadModelData] 完整URL:', fullUrl)
        console.log('[Index.loadModelData] 开始加载')
        console.log('[Index.loadModelData] URL query:', query)
        console.log('[Index.loadModelData] 搜索参数:', {
          field: currentField,
          value: currentValue,
          fuzzy: currentFuzzy,
          sort: currentSort,
          page: currentPage,
          limit: currentLimit,
          advancedFilter: searchParams
        })

        const attrResult = await modelAPI.getModelAttributes(this.objId)

        // 与原项目保持一致: 后端 for_web 过滤了 bk_isapi=true 的字段（如 bk_inst_id），
        // 前端通过 createIdProperty 注入合成的 bk_inst_id 属性，用于在表头第一位显示"ID"列
        // 参考: /workspace/bk-cmdb/src/ui/src/service/property/property.js createIdProperty
        // 参考: /workspace/bk-cmdb/src/ui/src/store/modules/api/object-model-property.js searchObjectAttribute
        const rawAttributes = attrResult.attributes || []
        const alreadyInject = rawAttributes.some(property => property._is_inject_)
        if (!alreadyInject) {
          rawAttributes.unshift(this.createIdProperty(this.objId))
        }
        this.allProperties = rawAttributes
        this.defaultColumns = attrResult.default_columns || []
        console.log('[Persistence] Loaded model attributes, objId:', this.objId, 'defaultColumns:', this.defaultColumns, 'allProperties count:', this.allProperties.length)

        // 拉取分组定义，供 cmdb-form 使用权威 bk_group_name 渲染分组标题
        try {
          const groupsResult = await modelAPI.getModelPropertyGroups(this.objId)
          this.propertyGroups = (groupsResult && groupsResult.groups) || []
        } catch (e) {
          console.log('[Index.loadModelData] 获取分组失败:', e)
          this.propertyGroups = []
        }

        try {
          const modelResult = await modelAPI.getModel(this.objId)
          if (modelResult && modelResult.model && modelResult.model.bk_obj_name) {
            this.modelData = modelResult.model
            this.updateBreadcrumbs()
          }
        } catch (e) {
          console.log('[Index.loadModelData] 获取模型详情失败:', e)
        }

        // Load saved columns config
        // 与原项目保持一致: 存储数据加载到 customColumns（存储状态）
        // columnsConfig.selected（UI 状态）由 setTableHeader 同步更新
        try {
          console.log('[Persistence] Calling getModelCustomColumns for objId:', this.objId)
          const savedColumns = await userCustom.getModelCustomColumns(this.objId)
          console.log('[Persistence] getModelCustomColumns result:', savedColumns)
          if (savedColumns && savedColumns.columns && savedColumns.columns.length > 0) {
            this.customColumns = savedColumns.columns
            console.log('[Persistence] Set customColumns to:', this.customColumns)
          } else {
            // 没有有效配置时，重置为空数组，使用默认规则
            this.customColumns = []
            console.log('[Persistence] Reset customColumns to empty array')
          }
        } catch (e) {
          console.log('[Persistence] No saved columns config found or error:', e)
          this.customColumns = []
        }

        // 与原项目保持一致: 使用 searchableProperties 的过滤逻辑，排除 bk_isapi=true 和 id 字段
        const validField = this.searchableProperties.find(p => p.bk_property_id === currentField)
        if (!validField && this.searchableProperties.length > 0) {
          const firstField = this.searchableProperties[0]
          if (firstField) {
            this.filter.field = firstField.bk_property_id
          }
        }

        // 只有在非多选场景下才设置 filter.value，避免与 filter.values 冲突
        if (!(this.isEnumField || this.isBoolField || this.isEnumMultiField) || this.filter.values.length === 0) {
          this.filter.value = currentValue
        }
        this.filter.fuzzyQuery = currentFuzzy
        this.table.sort = currentSort
        this.table.pagination.current = currentPage
        this.table.pagination.limit = currentLimit

        console.log('[Index.loadModelData] 调用搜索API，搜索值:', this.filter.value, '多选:', this.filter.values)

        let instResult

        // 如果有高级筛选参数，使用新的API调用方式
        if (searchParams) {
          console.log('[Index.loadModelData] 使用高级筛选参数:', searchParams)
          
          instResult = await modelAPI.searchInstances(this.objId, {
            ...searchParams
          }, { requestId: 'inst-list', cancelPrevious: true })
        } else {
          // 否则使用原有的简单搜索方式
          const isMultiSelectEnum = this.isEnumField || this.isBoolField || this.isEnumMultiField
          const isDateTimeField = this.isDateField || this.isTimeField
          const searchValues = (isMultiSelectEnum || isDateTimeField) && this.filter.values.length > 0
            ? this.filter.values
            : (this.filter.value ? [this.filter.value] : [])

          let searchParams = {
            page: this.table.pagination.current,
            page_size: this.table.pagination.limit,
            search_field: this.filter.field || undefined,
            fuzzy: this.filter.fuzzyQuery,
            sort: this.table.sort || undefined
          }

          if (isDateTimeField && searchValues.length > 0) {
            // 日期时间范围搜索
            searchParams.search_start = searchValues[0]
            if (searchValues.length > 1) {
              searchParams.search_end = searchValues[1]
            }
          } else if (searchValues.length > 0) {
            searchParams.search_value = searchValues[0]
            if (searchValues.length > 1) {
              searchParams.search_values = searchValues.join(',')
            }
          }

          instResult = await modelAPI.searchInstances(this.objId, searchParams,
            { requestId: 'inst-list', cancelPrevious: true })
        }

        console.log('[Index.loadModelData] API返回结果:', {
          count: instResult.instances?.length || 0,
          total: instResult.total
        })

        this.setTableHeader()
        this.updateTableSortState()

        // 冻结大列表数据，跳过 Vue 对每行每列的深度响应式代理：
        // 与上游 relation/create.vue 对 originalList 使用 Object.freeze 的意图一致，
        // 避免 500+ 行 × 上百列在初始化/重载时产生大量响应式 getter 与内存开销（DOM 替换/GC 更快）。
        this.table.list = freezeList(instResult.instances || [])
        this.table.pagination.count = instResult.total || 0

        // 复刻原项目 bk-cmdb（general-model/index.vue getTableData）：
        // 当后端返回 count > 0 但当前页 info 为空时，回退到「当前页 - 1」重新加载，
        // 而非停留在空页。典型场景：末页（如 page=7）仅剩的 1 条被删除后，该页被删空、
        // 但总记录仍 > 0，若不做处理表格会显示「暂无数据」且翻页组件因 current 越界而丢失。
        // 原项目用 RouterQuery.set({ page: current - 1 }) 触发 watch 重新拉取上一页数据。
        // lite 这里改为「同步内联递归重载」：直接递减 current 并就地重新请求上一页，
        // 同时同步 URL。这样避免依赖 watch 异步链（watch 读取 current 的时序可能仍读到
        // 旧值 7，导致用空页参数再请求一次、陷入延迟级联回退）。
        // 注意：回到的是「上一页」(current-1)，既不是首页(1)也不是末页，这是删除后
        // 剩余数据最自然的落点（上一页恰好承载被删空页之前的最后若干条）。
        if (this.table.pagination.count && this.table.list.length === 0 && this.table.pagination.current > 1) {
          this.table.pagination.current -= 1
          routerQuery.set({ page: this.table.pagination.current, _t: Date.now() })
          // 用更新后的页码内联重新加载上一页（递归，但最终页有数据时自然收敛）
          return this.loadModelData(searchParams)
        }

        console.log('[Index.loadModelData] 加载完成，当前列表行数:', this.table.list.length)

      } catch (error) {
        // 请求被取消（翻页/筛选重载时的 cancelPrevious）属预期行为，静默忽略，不弹错误
        if (isCancelError(error)) {
          console.log('[Index.loadModelData] 请求已取消（被新请求取代）')
          return
        }
        console.error('[ERROR] 加载数据失败:', error)
        this.$handleApiError(error)
      } finally {
        this.table.loading = false
      }
    },
    /**
     * 与原项目 tools.js 保持一致的表头生成逻辑
     * 参考: /workspace/bk-cmdb/src/ui/src/utils/tools.js#L269-L332
     * - getPropertyPriority(property): 基于 bk_property_index，isonly，isrequired 计算优先级，越小越靠前
     * - getDefaultHeaderProperties(properties): 按优先级排序取前6个（不过滤）
     * - getCustomHeaderProperties(properties, customColumns): 按自定义列ID查找属性（简单映射，不过滤）
     * - getHeaderProperties(properties, customColumns, fixedPropertyIds): 始终将固定字段前置
     */
    getPropertyPriority(property) {
      let priority = property.bk_property_index ?? 0
      if (property.isonly) {
        priority = priority - 1
      }
      if (property.isrequired) {
        priority = priority - 1
      }
      return priority
    },
    getDefaultHeaderProperties(properties) {
      // 与原项目一致: 不过滤系统字段，按优先级排序取前6个
      return [...properties]
        .sort((A, B) => this.getPropertyPriority(A) - this.getPropertyPriority(B))
        .slice(0, 6)
    },
    getCustomHeaderProperties(properties, customColumns) {
      // 与原项目一致: 简单映射，不过滤任何字段
      const columnProperties = []
      customColumns.forEach((propertyId) => {
        const columnProperty = properties.find(property => property.bk_property_id === propertyId)
        if (columnProperty) {
          columnProperties.push(columnProperty)
        }
      })
      return columnProperties
    },
    getHeaderProperties(properties, customColumns, fixedPropertyIds = []) {
      // 与原项目一致: 始终将固定字段前置
      let headerProperties
      if (customColumns && customColumns.length) {
        headerProperties = this.getCustomHeaderProperties(properties, customColumns)
      } else {
        headerProperties = this.getDefaultHeaderProperties(properties)
      }
      if (fixedPropertyIds.length) {
        headerProperties = headerProperties.filter(property => !fixedPropertyIds.includes(property.bk_property_id))
        const fixedProperties = []
        fixedPropertyIds.forEach((id) => {
          const property = properties.find(property => property.bk_property_id === id)
          if (property) {
            fixedProperties.push(property)
          }
        })
        return [...fixedProperties, ...headerProperties]
      }
      return headerProperties
    },
    setTableHeader() {
      console.log('[Debug] setTableHeader start')
      console.log('[Debug] allProperties:', this.allProperties?.length)
      console.log('[Debug] customColumns:', this.customColumns)
      console.log('[Debug] disabledColumns:', this.disabledColumns)

      // 与原项目保持一致: 从存储状态 customColumns 读取，不从 UI 状态 columnsConfig.selected 读取
      // 参考: /workspace/bk-cmdb/src/ui/src/views/general-model/index.vue#L654-L667
      const customColumns = this.customColumns || []
      const fixedPropertyIds = this.disabledColumns || []

      // 调用与原项目一致的 getHeaderProperties 函数
      // - 有自定义列时: 按自定义列顺序生成（固定字段始终前置）
      // - 无自定义列时: 按默认优先级生成前6个（固定字段始终前置）
      const headerProperties = this.getHeaderProperties(
        this.allProperties,
        customColumns,
        fixedPropertyIds
      )

      console.log('[Debug] headerProperties:', headerProperties.length)

      // 与原项目保持一致: 数组长度不变时需要先清空再赋值，否则表头无法实时更新
      // 参考: /workspace/bk-cmdb/src/ui/src/views/general-model/index.vue updateTableHeader 方法
      // 原项目注释: "数组length在没有变化时候，需要先清空数组在赋值。否则表头无法实时更新"
      const newHeader = headerProperties.map(property => ({
        id: property.bk_property_id,
        name: property.bk_property_name,
        property
      }))
      this.table.header = []
      this.$nextTick(() => {
        this.table.header = newHeader
      })

      // 与原项目保持一致: 始终同步 columnsConfig.selected 为当前表头属性
      // 这样抽屉打开时显示的已选属性与表格列保持一致
      this.columnsConfig.selected = headerProperties.map(property => property.bk_property_id)

      console.log('[Debug] table.header will be updated via $nextTick, count:', newHeader.length)
      console.log('[Debug] columnsConfig.selected synced to:', this.columnsConfig.selected)
    },
    formatCellValue(value, column) {
      // column.property 为完整属性定义（含 bk_property_type 与 option），
      // 未取到时回退到 column 本身，保证枚举/多选/列表等类型按 option 映射为显示名。
      // 统一复用全站 property-value.js 的 formatPropertyValue，避免通用模型列表与
      // 资源/关联/业务拓扑列表在属性格式化上实现漂移。
      const property = (column && column.property) || column
      if (value === null || value === undefined || value === '') {
        return '-'
      }
      return formatPropertyValue(value, property)
    },
    handleFieldChange() {
      // 只清空当前输入框的值，保留之前的搜索条件
      // 条件清空将在提交查询时（handleSearch）触发
      this.filter.value = ''
      this.filter.values = []
    },
    handleEnumSelect(event) {
      const selected = event.target.selectedOptions
      const values = Array.from(selected).map(opt => opt.value)
      this.filter.values = values
      if (values.length > 0) {
        this.filter.value = values.join(',')
        this.handleSearch()
      }
    },
    toggleEnumDropdown() {
      this.enumDropdownVisible = !this.enumDropdownVisible
    },
    handleEnumOptionChange() {
      if (this.filter.values.length > 0) {
        this.filter.value = this.filter.values.join(',')
      } else {
        this.filter.value = ''
      }
      this.handleSearch()
    },
    handleEnumCheckbox(optionId, event) {
      console.log('[handleEnumCheckbox]', { optionId, checked: event.target.checked, currentValues: this.filter.values })
      
      // 使用 $set 确保 Vue 能正确追踪数组变化
      if (event.target.checked) {
        if (!this.filter.values.includes(optionId)) {
          this.$set(this.filter.values, this.filter.values.length, optionId)
        }
      } else {
        const index = this.filter.values.indexOf(optionId)
        if (index > -1) {
          this.filter.values.splice(index, 1)
        }
      }
      
      console.log('[handleEnumCheckbox] after change:', this.filter.values)
      this.filter.value = this.filter.values.join(',')
      
      // 延迟搜索，让用户可以快速多选多个选项
      if (this.searchTimeout) {
        clearTimeout(this.searchTimeout)
      }
      this.searchTimeout = setTimeout(() => {
        this.handleSearch()
      }, 300)
    },
    handleEnumSelectSingle(selected) {
      this.filter.value = selected
      this.filter.values = selected ? [selected] : []
      this.handleSearch()
    },
    handleEnumClear() {
      this.filter.values = []
      this.filter.value = ''
      this.handleSearch()
    },
    restoreStateFromUrl() {
      console.log('[restoreStateFromUrl] 开始恢复状态')
      
      // 获取 Vue Router hash 路由中的参数 — 唯一数据源
      const routeQuery = this.$route.query
      
      // 只使用路由查询（window.location.search 可能含有 query-builder 遗留的双重编码值，忽略之）
      const query = { ...routeQuery }
      
      console.log('[restoreStateFromUrl] 合并后的URL query:', query)

      if (query.page) {
        this.table.pagination.current = parseInt(query.page, 10) || 1
      }
      if (query.limit) {
        this.table.pagination.limit = parseInt(query.limit, 10) || 10
      }
      if (query.field) {
        this.filter.field = query.field
      }
      if (query.filter !== undefined && query.filter !== null && query.filter !== '') {
        this.filter.value = String(query.filter)
      } else {
        this.filter.value = ''
      }
      // 仅当 URL 显式给出 fuzzy 取值时覆盖；缺失/空串保留默认（已勾选）
      if (query.fuzzy === 'true' || query.fuzzy === '1') {
        this.filter.fuzzyQuery = true
      } else if (query.fuzzy === 'false' || query.fuzzy === '0') {
        this.filter.fuzzyQuery = false
      }
      if (query.sort) {
        this.table.sort = query.sort
      }

      // 从filter_adv参数中恢复高级筛选条件，保持与原bk-cmdb项目一致
      if (query.filter_adv) {
        try {
          const advQuery = QS.parse(query.filter_adv)
          console.log('[restoreStateFromUrl] 解析filter_adv:', advQuery)
          
          if (advQuery && Object.keys(advQuery).length > 0) {
            const rawConditions = []
            const conditionMap = {}
            
            Object.keys(advQuery).forEach((key) => {
              const [id, operator] = key.split('.')
              const value = advQuery[key]
              
              if (id && operator) {
                // 将值转换为数组（如果是逗号分隔的字符串）
                let processedValue = value
                if (typeof processedValue === 'string' && processedValue.includes(',')) {
                  processedValue = processedValue.split(',')
                }
                
                rawConditions.push({
                  field: id,
                  operator: `$${operator}`,
                  value: processedValue
                })
                conditionMap[id] = {
                  operator: `$${operator}`,
                  value: processedValue
                }
              }
            })
            
            // 如果是快速搜索模式，且有快速搜索条件，将其添加到 conditionMap 中
            if (query.s === 'fast' && query.field && query.filter) {
              const property = this.allProperties.find(p => p.bk_property_id === query.field)
              if (property) {
                const propType = property.bk_property_type
                const isEnum = propType === 'enum'
                const isBool = propType === 'bool'
                const isList = propType === 'list'
                const isDate = propType === 'date'
                const isTime = propType === 'time'
                const isDateTime = isDate || isTime
                const isEnumOrListOrBool = isEnum || isList || isBool

                let operator = query.operator || '$eq'
                let value = query.filter

                if (!query.operator) {
                  if (isDateTime || isEnumOrListOrBool) {
                    operator = '$in'
                    value = value.split(',').map(v => v.trim()).filter(v => v)
                  } else {
                    const isFuzzy = query.fuzzy === 'true' || query.fuzzy === '1'
                    operator = isFuzzy ? '$regex' : '$eq'
                  }
                }

                conditionMap[query.field] = {
                  operator,
                  value
                }
              }
            }

            // 只有当 conditionMap 非空时才设置 advancedFilterConditions
            if (Object.keys(conditionMap).length > 0) {
              this.advancedFilterConditions = conditionMap
            } else {
              this.advancedFilterConditions = null
            }
            
            // 恢复 filterTags - 基于 conditionMap
            const tags = []
            Object.keys(conditionMap).forEach(id => {
              const { operator, value } = conditionMap[id]
              const property = this.allProperties.find(p => p.bk_property_id === id)
              if (property && value !== null && value !== undefined) {
                if (Array.isArray(value) ? value.length > 0 : String(value).trim().length > 0) {
                  tags.push({
                    id: id,
                    property: property,
                    propertyName: property.bk_property_name || id,
                    operator: operator,
                    value: value
                  })
                }
              }
            })
            this.filterTags = tags
            
            console.log('[restoreStateFromUrl] 高级筛选条件已恢复，filterTags:', this.filterTags)
          } else {
            // advQuery 为空
            this.advancedFilterConditions = null
          }
        } catch (e) {
          console.error('[restoreStateFromUrl] 解析filter_adv失败:', e)
          this.advancedFilterConditions = null
          // 解析失败时，才使用简单搜索条件更新filterTags
          this.updateFilterTagsFromQuery()
        }
      } else {
        // 没有高级筛选条件时，检查是否有快速搜索条件
        if (query.s === 'fast' && query.field && query.filter) {
          // 有快速搜索条件，构建高级筛选条件
          const property = this.allProperties.find(p => p.bk_property_id === query.field)
          if (property) {
            const propType = property.bk_property_type
            const isEnum = propType === 'enum'
            const isBool = propType === 'bool'
            const isList = propType === 'list'
            const isDate = propType === 'date'
            const isTime = propType === 'time'
            const isDateTime = isDate || isTime
            const isEnumOrListOrBool = isEnum || isList || isBool

            let operator = query.operator || '$eq'
            let value = query.filter

            if (!query.operator) {
              if (isDateTime || isEnumOrListOrBool) {
                operator = '$in'
                value = value.split(',').map(v => v.trim()).filter(v => v)
              } else {
                const isFuzzy = query.fuzzy === 'true' || query.fuzzy === '1'
                operator = isFuzzy ? '$regex' : '$eq'
              }
            }

            const conditionMap = {
              [query.field]: {
                operator,
                value
              }
            }

            this.advancedFilterConditions = conditionMap

            // 更新 filterTags
            const tags = []
            Object.keys(conditionMap).forEach(id => {
              const { operator, value } = conditionMap[id]
              const property = this.allProperties.find(p => p.bk_property_id === id)
              if (property && value !== null && value !== undefined) {
                if (Array.isArray(value) ? value.length > 0 : String(value).trim().length > 0) {
                  tags.push({
                    id: id,
                    property: property,
                    propertyName: property.bk_property_name || id,
                    operator: operator,
                    value: value
                  })
                }
              }
            })
            this.filterTags = tags
          } else {
            this.advancedFilterConditions = null
            this.updateFilterTagsFromQuery()
          }
        } else {
          this.advancedFilterConditions = null
          this.updateFilterTagsFromQuery()
        }
      }

      console.log('[restoreStateFromUrl] 恢复后的状态:', {
        field: this.filter.field,
        value: this.filter.value,
        fuzzyQuery: this.filter.fuzzyQuery,
        page: this.table.pagination.current,
        sort: this.table.sort,
        hasAdvancedFilter: !!this.advancedFilterConditions,
        filterTagsCount: this.filterTags.length
      })
      
      // 标记URL已同步，防止watch重复触发
      this.isUrlUpdateTriggered = true
    },
    syncStateToUrl(options = {}) {
      const { keepSort = true, resetPage = false, filter_adv, s, operator } = options
      const query = {}

      if (!resetPage) {
        // 在 URL 中始终包含 page 参数
        query.page = this.table.pagination.current
      }
      query.limit = this.table.pagination.limit

      // 如果是高级筛选模式，不要添加快速搜索的参数
      if (s !== 'adv') {
        if (this.filter.field) {
          query.field = this.filter.field
        }
        if (this.filter.value) {
          query.filter = this.filter.value
        }
        if (this.filter.fuzzyQuery !== false) {
          query.fuzzy = this.filter.fuzzyQuery ? '1' : '0'
        }
        // 添加operator参数
        if (operator) {
          query.operator = operator
        }
      }

      if (keepSort && this.table.sort) {
        query.sort = this.table.sort
      }

      // 保持与原bk-cmdb项目一致的URL参数
      // 优先使用传入的filter_adv和s，如果没有则检查当前状态
      if (filter_adv !== undefined) {
        // 只有当filter_adv不为空字符串时才设置该参数
        if (filter_adv) {
          query.filter_adv = filter_adv
        }
      } else if (this.advancedFilterConditions && Object.keys(this.advancedFilterConditions).length > 0) {
        // 如果没有显式传入，但有当前高级筛选条件，则从当前状态重新构建
        try {
          const tempQuery = {}
          Object.keys(this.advancedFilterConditions).forEach(field => {
            const cond = this.advancedFilterConditions[field]
            // 格式必须与 handleAdvancedFilterSearch 中保存的格式一致: {field}.{operator_without_$}
            const key = `${field}.${cond.operator.replace('$', '')}`
            let value = cond.value
            
            if (Array.isArray(value)) {
              // 如果是数组，用逗号分隔
              tempQuery[key] = value.join(',')
            } else if (value !== null && value !== undefined) {
              tempQuery[key] = value
            }
          })
          if (Object.keys(tempQuery).length > 0) {
            query.filter_adv = QS.stringify(tempQuery, { encode: false })
          }
        } catch (e) {
          console.error('[syncStateToUrl] 构建filter_adv失败:', e)
        }
      }
      
      if (s !== undefined) {
        query.s = s
      } else if (this.advancedFilterConditions && Object.keys(this.advancedFilterConditions).length > 0) {
        // 如果没有显式传入，但有高级筛选条件，则设置s为'adv'
        query.s = 'adv'
      }

      // 使用 replaceQuery 完整替换 query（而非 setAll 的合并），
      // 确保被省略的参数（如清除筛选时的 filter_adv/s）被真正移除，不会因合并残留
      this.isUrlUpdateTriggered = true
      routerQuery.replaceQuery(query)
    },
    handleSearch() {
      this.table.pagination.current = 1
      this.currentSearchParams = null
      
      let operator = '$eq'
      
      // 构建快速搜索条件并同步到高级筛选
      if (this.filter.field && (this.filter.value || (this.filter.values && this.filter.values.length > 0))) {
        const property = this.allProperties.find(p => p.bk_property_id === this.filter.field)
        if (property) {
          const propType = property.bk_property_type
          const isEnum = propType === 'enum'
          const isBool = propType === 'bool'
          const isList = propType === 'list'
          const isDate = propType === 'date'
          const isTime = propType === 'time'
          const isDateTime = isDate || isTime
          const isEnumOrListOrBool = isEnum || isList || isBool
          
          let value = ''
          
          if (isDateTime) {
            // 日期和时间类型使用 $in 操作符，与 cmdb-search-date 组件的数组格式匹配
            operator = '$in'
            value = this.filter.values && this.filter.values.length > 0 
              ? [...this.filter.values] 
              : (this.filter.value ? [this.filter.value] : [])
          } else if (isEnumOrListOrBool) {
            // 枚举、布尔、列表使用 $in 操作符
            operator = '$in'
            value = this.filter.values && this.filter.values.length > 0 
              ? [...this.filter.values] 
              : (this.filter.value ? [this.filter.value] : [])
          } else {
            // 其他类型根据模糊查询设置使用 $regex 或 $eq
            operator = this.filter.fuzzyQuery ? '$regex' : '$eq'
            value = this.filter.value
          }
          
          // 构建高级筛选条件 - 同一字段替换，不同字段追加
          const newConditions = { ...this.advancedFilterConditions } || {}
          newConditions[this.filter.field] = {
            operator,
            value
          }
          this.advancedFilterConditions = Object.keys(newConditions).length > 0 ? newConditions : null
          
          console.log('[handleSearch] 快速搜索同步到高级筛选:', {
            field: this.filter.field,
            propertyName: property.bk_property_name,
            propType,
            operator,
            value,
            allConditions: this.advancedFilterConditions
          })
        } else {
          // 如果找不到对应的属性，只清除当前字段的条件
          console.warn('[handleSearch] 未找到对应的属性:', this.filter.field)
          if (this.advancedFilterConditions) {
            delete this.advancedFilterConditions[this.filter.field]
            // 如果没有其他条件了，则设为 null
            if (Object.keys(this.advancedFilterConditions).length === 0) {
              this.advancedFilterConditions = null
            }
          }
        }
      } else {
        // 没有搜索值时，只清除当前字段的条件
        if (this.advancedFilterConditions && this.filter.field) {
          delete this.advancedFilterConditions[this.filter.field]
          if (Object.keys(this.advancedFilterConditions).length === 0) {
            this.advancedFilterConditions = null
          }
        }
      }
      
      this.updateFilterTags()
      
      // 按高级筛选数据提交查询：先组合 URL，再查询
      let filter_advParam = undefined
      if (this.advancedFilterConditions && Object.keys(this.advancedFilterConditions).length > 0) {
        // 构建 filter_adv
        try {
          const tempQuery = {}
          Object.keys(this.advancedFilterConditions).forEach(field => {
            const cond = this.advancedFilterConditions[field]
            const key = `${field}.${cond.operator.replace('$', '')}`
            let value = cond.value
            if (Array.isArray(value)) {
              tempQuery[key] = value.join(',')
            } else if (value !== null && value !== undefined) {
              tempQuery[key] = value
            }
          })
          if (Object.keys(tempQuery).length > 0) {
            filter_advParam = QS.stringify(tempQuery, { encode: false })
          }
        } catch (e) {
          console.error('[handleSearch] 构建filter_adv失败:', e)
        }
        
        // 更新 filterTags - 基于组合后的高级筛选条件
        const tags = []
        Object.keys(this.advancedFilterConditions).forEach(id => {
          const { operator, value } = this.advancedFilterConditions[id]
          const property = this.allProperties.find(p => p.bk_property_id === id)
          if (property && value !== null && value !== undefined) {
            const hasValue = Array.isArray(value) ? value.length > 0 : String(value).trim().length > 0
            if (hasValue) {
              tags.push({
                id: id,
                property: property,
                propertyName: property.bk_property_name || id,
                operator: operator,
                value: value
              })
            }
          }
        })
        this.filterTags = tags
        
        // 构建搜索参数并查询（与高级筛选一致）
        const rawConditions = []
        Object.keys(this.advancedFilterConditions).forEach(field => {
          const cond = this.advancedFilterConditions[field]
          rawConditions.push({
            field,
            operator: cond.operator,
            value: cond.value
          })
        })
        const searchParams = this.buildAdvancedSearchParams(rawConditions)
        
        // 同步 URL，使用高级筛选模式（s=adv）
        this.syncStateToUrl({ resetPage: true, filter_adv: filter_advParam, s: 'adv' })
        
        this.currentSearchParams = searchParams
        this.isUrlUpdateTriggered = true
        this.loadModelData(searchParams)
      } else {
        // 如果没有条件，直接查询
        this.syncStateToUrl({ resetPage: true, s: 'fast', operator })
        this.isUrlUpdateTriggered = true
        this.loadModelData()
      }
    },
    handleRefresh() {
      this.isUrlUpdateTriggered = true
      routerQuery.refresh()
      this.loadModelData()
      this.$bkMessage({ message: '刷新成功', theme: 'success' })
    },
    handleAdvancedFilter() {
      this.advancedFilter.show = true
    },
    handleAdvancedFilterSearch(searchResult) {
      console.log('[handleAdvancedFilterSearch] 高级筛选条件:', searchResult)
      
      const { conditionMap, transformedCondition, searchParams, rawConditions } = searchResult

      this.advancedFilterConditions = conditionMap
      this.currentSearchParams = searchParams
      
      console.log('[handleAdvancedFilterSearch] rawConditions:', rawConditions)
      console.log('[handleAdvancedFilterSearch] conditionMap:', conditionMap)
      console.log('[handleAdvancedFilterSearch] allProperties:', this.allProperties)
      
      // 构建 filterTags - 基于 conditionMap 而不是 rawConditions
      const tags = []
      Object.keys(conditionMap).forEach(id => {
        const { operator, value } = conditionMap[id]
        const property = this.allProperties.find(p => p.bk_property_id === id)
        if (property && value !== null && value !== undefined) {
          const hasValue = Array.isArray(value) ? value.length > 0 : String(value).trim().length > 0
          if (hasValue) {
            tags.push({
              id: id,
              property: property,
              propertyName: property.bk_property_name || id,
              operator: operator,
              value: value
            })
          }
        }
      })
      this.filterTags = tags
      
      console.log('[handleAdvancedFilterSearch] filterTags:', this.filterTags)

      this.table.pagination.current = 1
      
      // 按照原bk-cmdb项目格式，保存到filter_adv参数中
      const advQuery = {}
      Object.keys(conditionMap).forEach((id) => {
        const { operator, value } = conditionMap[id]
        const key = `${id}.${operator.replace('$', '')}`
        if (String(value).length) {
          advQuery[key] = Array.isArray(value) ? value.join(',') : value
        }
      })
      
      this.syncStateToUrl({ 
        resetPage: true, 
        filter_adv: QS.stringify(advQuery, { encode: false }),
        s: 'adv'
      })
      
      this.loadModelData(searchParams)
    },
    handleAdvancedFilterReset() {
      this.table.pagination.current = 1
      this.currentSearchParams = null
      this.advancedFilterConditions = null
      this.filterTags = []
      // 清除快速搜索输入框
      this.filter.value = ''
      this.filter.values = []
      this.isUrlUpdateTriggered = true
      // 清除URL中的filter_adv和s参数，保持与原项目一致
      const query = {
        page: 1,
        limit: this.table.pagination.limit
      }
      routerQuery.setAll(query)
      this.loadModelData()
    },
    // handleImport() {
    //   this.$bkMessage({ message: '导入功能开发中', theme: 'info' })
    // },
    // handleExport() {
    //   this.$bkMessage({ message: '导出功能开发中', theme: 'info' })
    // },
    handleBatchEdit() {
      if (this.selectedIds.length === 0) {
        this.$bkMessage({ message: '请先选择要更新的实例', theme: 'warning' })
        return
      }
      this.batchUpdateDialogVisible = true
    },
    handleBatchUpdateSubmit(data) {
      this.doBatchUpdate(data)
    },
    async doBatchUpdate(data) {
      this.batchUpdateFormLoading = true
      try {
        const result = await modelAPI.batchUpdateInstancesWithSameData(this.objId, this.selectedIds, data)
        if (result) {
          this.$bkMessage({ message: `成功更新 ${this.selectedIds.length} 个实例`, theme: 'success' })
          this.handleBatchUpdateDialogClose()
          this.selectedIds = []
          await this.loadModelData(this.currentSearchParams)
        } else {
          this.$bkMessage({ message: '未获取到更新结果', theme: 'error' })
        }
      } catch (error) {
        console.error('Batch update error:', error)
        this.$handleApiError(error)
      } finally {
        this.batchUpdateFormLoading = false
      }
    },
    handleBatchUpdateDialogBeforeClose() {
      const formRef = this.$refs.formMultipleRef
      if (formRef && formRef.hasChange) {
        return new Promise((resolve) => {
          this.$bkInfo({
            title: '确认退出？',
            subTitle: '当前批量更新有未保存的修改，是否确认退出？',
            confirmFn: () => {
              resolve(true)
            },
            cancelFn: () => {
              resolve(false)
            }
          })
        })
      }
      return true
    },
    handleBatchUpdateDialogClose() {
      this.batchUpdateDialogVisible = false
      this.hiddenUniqueProperties = []
      if (this.$refs.formMultipleRef) {
        this.$refs.formMultipleRef.reset()
      }
    },
    handleUniquePropertiesChanged(properties) {
      this.hiddenUniqueProperties = properties || []
    },
    handleSelectionChange(selection) {
      this.selectedIds = selection.map(row => row[this.instanceIdField])
      this.selectedRows = selection
    },
    handleDeleteSingle(row) {
      this.handleDelete([row[this.instanceIdField]])
    },
    handleBatchDelete() {
      if (this.selectedIds.length === 0) {
        this.$bkMessage({ message: '请先选择要删除的实例', theme: 'warning' })
        return
      }
      this.handleDelete(this.selectedIds)
    },
    handleDelete(ids) {
      this.table.loading = true
      
      // 先检查关联实例数量
      modelAPI.checkInstanceAssociations(this.objId, ids)
        .then(associationData => {
          const { total_associations, source_associations, target_associations } = associationData
          
          let subTitle = `您确定要删除选中的 ${ids.length} 个实例吗？此操作不可撤销。`
          
          if (total_associations > 0) {
            subTitle += `\n\n⚠️ 检测到 ${total_associations} 条关联关系将同时被删除：`
            if (source_associations > 0) {
              subTitle += `\n- ${source_associations} 条作为源的关联`
            }
            if (target_associations > 0) {
              subTitle += `\n- ${target_associations} 条作为目标的关联`
            }
          }
          
          this.$bkInfo({
            title: '确认删除',
            subTitle: subTitle,
            confirmFn: async () => {
              try {
                this.table.loading = true
                await modelAPI.deleteInstances(this.objId, ids)
                this.$bkMessage({ message: `成功删除 ${ids.length} 个实例，同时删除 ${total_associations} 条关联关系`, theme: 'success' })
                this.selectedIds = []
                await this.loadModelData(this.currentSearchParams)
              } catch (error) {
                console.error('Delete error:', error)
                this.$handleApiError(error)
              } finally {
                this.table.loading = false
              }
            },
            cancelFn: () => {
              console.log('用户取消删除')
              this.table.loading = false
            }
          })
        })
        .catch(error => {
          console.error('Check associations error:', error)
          this.$handleApiError(error)
          this.table.loading = false
        })
    },
    buildAdvancedSearchParams(rawConditions) {
      // 从 rawConditions 构建 conditionMap
      const conditionMap = {}
      
      rawConditions.forEach(cond => {
        const { field, operator, value } = cond
        
        // 获取属性信息
        const property = this.allProperties.find(p => p.bk_property_id === field)
        const isEnumOrList = property && ['enum', 'list'].includes(property.bk_property_type)
        const isDateTime = property && ['date', 'time'].includes(property.bk_property_type)
        
        // 处理值
        let processedValue = value
        if (isEnumOrList || isDateTime) {
          // 枚举、列表、日期时间类型，值应该是数组
          if (Array.isArray(value)) {
            processedValue = value
          } else if (value !== null && value !== undefined && String(value).trim().length > 0) {
            processedValue = [value]
          }
        } else if (value !== null && value !== undefined && String(value).trim().length > 0) {
          // 其他类型
          if (this.isInOperator(operator) && !isEnumOrList) {
            processedValue = String(value).split(/[\n,，]/).map(v => v.trim()).filter(v => v.length > 0)
          } else if (this.isRangeOperator(operator)) {
            processedValue = String(value).split(/[\n,，]/).map(v => v.trim()).filter(v => v.length > 0)
          }
        }
        
        if (processedValue !== null && processedValue !== undefined && 
            !(typeof processedValue === 'string' && processedValue.length === 0) &&
            !(Array.isArray(processedValue) && processedValue.length === 0)) {
          conditionMap[field] = {
            operator,
            value: processedValue
          }
        }
      })
      
      // 使用 buildSearchParams 构建最终的 searchParams
      return buildSearchParams(conditionMap, this.allProperties, {
        page: this.table.pagination.current,
        pageSize: this.table.pagination.limit,
        sort: this.table.sort || '-id'
      })
    },
    isInOperator(operator) {
      return operator === '$in' || operator === '$nin'
    },
    isRangeOperator(operator) {
      return operator === '$range' || operator === '$gte' || operator === '$lte'
    },
    handleCreate() {
      if (this.isSetOrModule) {
        this.$bkMessage({ message: '集群/模块请在业务拓扑中创建，不支持在资源目录新建', theme: 'warning' })
        return
      }
      console.log('[DEBUG] handleCreate called - 新建按钮被点击')
      console.log('[DEBUG] 当前对象ID:', this.objId)
      console.log('[DEBUG] 当前属性数量:', this.allProperties.length)
      console.log('[DEBUG] 属性列表:', this.allProperties.map(p => ({ id: p.bk_property_id, name: p.bk_property_name, type: p.bk_property_type })))
      this.handleCreateInstance()
    },
    handleCreateInstance() {
      console.log('[DEBUG] handleCreateInstance - 开始打开新建弹窗')
      const formData = {}

      // 初始化表单默认值
      this.allProperties.forEach(attr => {
        const propType = attr.bk_property_type

        // bool 类型的默认值存储在 option 中（与原项目保持一致）
        if (propType === 'bool') {
          const option = attr.option
          let defaultVal = false
          if (typeof option === 'boolean') {
            defaultVal = option
          } else if (typeof option === 'string') {
            defaultVal = option.toLowerCase() === 'true'
          } else if (typeof option === 'number') {
            defaultVal = Boolean(option)
          }
          formData[attr.bk_property_id] = defaultVal
          return
        }

        // 其他类型优先使用 default，为默认值
        if (attr.default !== null && attr.default !== undefined) {
          formData[attr.bk_property_id] = attr.default
        }
      })

      this.createForm = formData
      this.createFormInitial = JSON.parse(JSON.stringify(formData))
      this.createDialogVisible = true
    },
    // 复制选中行（仅支持单行）：从表格选中项复制为新建副本。
    // - 必须恰好选中 1 行，多选/零选均给出提示；
    // - 剔除 bk_isapi=true 的系统字段（id / bk_inst_id / bk_obj_id 等）与只读字段；
    // - 名称字段（bk_inst_name 或内置模型的 bk_*_name）自动加「_副本」后缀，
    //   避免与源实例的 bk_inst_name 唯一约束冲突；
    // - 其余唯一约束字段（如 bk_server_ip + bk_server_port 组合键）原样带入，
    //   由用户在弹窗内手动调整，并异步拉取 unique 键集合做提示。
    handleCopySelected() {
      if (this.isSetOrModule) {
        this.$bkMessage({ message: '集群/模块不支持在资源目录复制', theme: 'warning' })
        return
      }
      if (this.selectedRows.length === 0) {
        this.$bkMessage({ message: '请先勾选要复制的实例（仅支持单行）', theme: 'warning' })
        return
      }
      if (this.selectedRows.length > 1) {
        this.$bkMessage({ message: '复制仅支持单行，请只勾选 1 个实例', theme: 'warning' })
        return
      }
      const row = this.selectedRows[0]
      console.log('[DEBUG] handleCopySelected - 复制行:', row[this.instanceIdField])
      const editableProps = this.searchableProperties
      const nameField = this.instanceNameField
      const formData = {}

      editableProps.forEach(attr => {
        const pid = attr.bk_property_id
        // 跳过实例主键
        if (pid === this.instanceIdField) return
        const val = row[pid]
        if (val === undefined || val === null) return
        formData[pid] = val
      })

      // 名称字段加副本后缀，防止撞 bk_inst_name 唯一约束
      if (formData[nameField] !== undefined && formData[nameField] !== null && formData[nameField] !== '') {
        const suffix = '_副本'
        formData[nameField] = String(formData[nameField]).endsWith(suffix)
          ? formData[nameField] + suffix
          : formData[nameField] + suffix
      }

      this.createForm = formData
      this.createFormInitial = JSON.parse(JSON.stringify(formData))
      this.createDialogVisible = true

      // 异步提示受唯一约束影响的字段，引导用户调整组合键
      this.fetchCopyUniqueHint()
    },
    async fetchCopyUniqueHint() {
      try {
        const result = await modelAPI.searchObjectUnique(this.objId)
        const info = (result && result.info) || []
        if (!info.length) return
        const uniquePropIds = []
        info.forEach(constraint => {
          ;(constraint.keys || []).forEach(key => {
            if (key.key_kind === 'property' && key.key_id) {
              const prop = this.allProperties.find(p => p.id === key.key_id)
              if (prop) uniquePropIds.push(prop.bk_property_id)
            }
          })
        })
        const names = uniquePropIds
          .map(pid => (this.allProperties.find(p => p.bk_property_id === pid) || {}).bk_property_name || pid)
          .filter(Boolean)
        if (names.length) {
          this.$bkMessage({
            message: `已复制为副本，以下字段受唯一约束请勿重复：${names.join('、')}`,
            theme: 'warning',
            extCls: 'copy-unique-hint'
          })
        }
      } catch (e) {
        // 提示失败不影响复制主流程
      }
    },
    handleCreateDialogBeforeClose() {
      const changed = !isEqual(this.createForm, this.createFormInitial)
      if (changed) {
        return new Promise((resolve) => {
          this.$bkInfo({
            title: '确认退出？',
            subTitle: '当前新增实例有未保存的修改，是否确认退出？',
            confirmFn: () => {
              resolve(true)
            },
            cancelFn: () => {
              resolve(false)
            }
          })
        })
      }
      return true
    },
    handleCreateDialogClose() {
      this.createDialogVisible = false
      this.createForm = {}
      this.createFormInitial = {}
    },
    handleCreateSubmit(formData) {
      console.log('[DEBUG] handleCreateSubmit - 提交表单数据:', formData)
      this.doCreateInstance(formData)
    },
    async doCreateInstance(formData) {
      this.createFormLoading = true
      try {
        const result = await modelAPI.createInstance(this.objId, formData)
        
        if (result) {
          this.$bkMessage({ message: '实例创建成功', theme: 'success' })
          this.handleCreateDialogClose()
          // 刷新列表
          await this.loadModelData(this.currentSearchParams)
        } else {
          this.$bkMessage({ message: '未获取到创建结果', theme: 'error' })
        }
      } catch (error) {
        console.error('Create instance error:', error)
        this.$handleApiError(error)
      } finally {
        this.createFormLoading = false
      }
    },
    parseOptions(option) {
      if (!option) return []
      if (Array.isArray(option)) return option
      try {
        const parsed = JSON.parse(option)
        return Array.isArray(parsed) ? parsed : []
      } catch {
        return []
      }
    },
    handleViewDetails(instance) {
      // 进入详情页前，确保URL中包含当前的高级筛选条件
      const query = this.$route.query
      let filterAdv = null
      
      // 优先使用URL中的filter_adv，否则从advancedFilterConditions构建
      if (query.filter_adv) {
        filterAdv = query.filter_adv
      } else if (this.advancedFilterConditions && Object.keys(this.advancedFilterConditions).length > 0) {
        filterAdv = QS.stringify(
          Object.keys(this.advancedFilterConditions).reduce((acc, id) => {
            const { operator, value } = this.advancedFilterConditions[id]
            const key = `${id}.${operator.replace('$', '')}`
            if (String(value).length) {
              acc[key] = Array.isArray(value) ? value.join(',') : value
            }
            return acc
          }, {}), { encode: false }
        )
      }
      
      const s = query.s || 'adv'
      
      this.syncStateToUrl({
        filter_adv: filterAdv,
        s: filterAdv ? s : undefined
      })
      const instanceId = instance[this.instanceIdField]
      this.prevInstanceId = instanceId
      // 内置 host 模型使用专门的主机详情页，其他模型使用通用实例详情页
      if (this.objId === 'host') {
        this.$router.push({
          name: MENU_RESOURCE_HOST_DETAILS,
          params: { id: instanceId }
        })
      } else {
        this.$router.push({
          name: MENU_RESOURCE_INSTANCE_DETAILS,
          params: { objId: this.objId, instId: instanceId }
        })
      }
    },
    handlePageChange(page) {
      this.table.pagination.current = page
      this.syncStateToUrl({ keepSort: false })
      this.isUrlUpdateTriggered = true
      
      // 如果有当前搜索参数，更新页码并使用（使用当前分页限制）
      if (this.currentSearchParams) {
        const newParams = {
          ...this.currentSearchParams,
          page,
          page_size: this.table.pagination.limit
        }
        this.loadModelData(newParams)
      } else {
        this.loadModelData()
      }
    },
    handleLimitChange(limit) {
      this.table.pagination.limit = limit
      this.table.pagination.current = 1
      this.syncStateToUrl({ keepSort: false, resetPage: true })
      this.isUrlUpdateTriggered = true
      
      // 如果有当前搜索参数，更新限制和页码并使用
      if (this.currentSearchParams) {
        const newParams = { ...this.currentSearchParams, page: 1, page_size: limit }
        this.loadModelData(newParams)
      } else {
        this.loadModelData()
      }
    },
    handleSortChange(sort) {
      if (!sort.order) {
        this.table.sort = ''
      } else if (sort.order === 'descending') {
        this.table.sort = `-${sort.prop}`
      } else {
        this.table.sort = sort.prop
      }
      this.table.pagination.current = 1
      this.syncStateToUrl({ resetPage: true })
      this.isUrlUpdateTriggered = true
      
      // 如果有高级筛选条件，使用高级筛选参数加载数据
      if (this.advancedFilterConditions && Object.keys(this.advancedFilterConditions).length > 0) {
        const rawConditions = []
        Object.keys(this.advancedFilterConditions).forEach(field => {
          const cond = this.advancedFilterConditions[field]
          rawConditions.push({
            field,
            operator: cond.operator,
            value: cond.value
          })
        })
        const searchParams = this.buildAdvancedSearchParams(rawConditions)
        console.log('[handleSortChange] 使用高级筛选参数:', searchParams)
        this.loadModelData(searchParams)
      } else {
        this.loadModelData()
      }
    },
    updateTableSortState() {
      if (!this.table.sort) {
        return
      }
      const isDesc = this.table.sort.startsWith('-')
      const prop = isDesc ? this.table.sort.substring(1) : this.table.sort
      const orderClass = isDesc ? 'descending' : 'ascending'

      this.$nextTick(() => {
        this.$nextTick(() => {
          const allThs = document.querySelectorAll('.models-table th.is-sortable')
          if (allThs.length === 0) {
            return
          }

          allThs.forEach(th => {
            th.classList.remove('ascending', 'descending')
          })

          let targetLabel = prop
          if (this.table.header && this.table.header.length > 0) {
            const col = this.table.header.find(c => c.id === prop)
            if (col) {
              targetLabel = col.name
            }
          }

          let targetTh = null
          for (let i = 0; i < allThs.length; i++) {
            const th = allThs[i]
            const labelEl = th.querySelector('.bk-table-header-label')
            if (labelEl && labelEl.textContent.trim() === targetLabel.trim()) {
              targetTh = th
              break
            }
          }

          if (targetTh) {
            targetTh.classList.add(orderClass)
          }
        })
      })
    },
    updateFilterTags() {
      const property = this.allProperties.find(p => p.bk_property_id === this.filter.field)
      if (!property) return

      // 互斥原则：清空所有旧标签，只保留当前字段的标签
      this.filterTags = []

      if (this.filter.values && this.filter.values.length > 0) {
        const tagData = {
          id: property.bk_property_id,
          propertyName: property.bk_property_name,
          operator: (this.isEnumField || this.isBoolField || this.isEnumMultiField) ? '$in' : ((this.isDateField || this.isTimeField) ? '$range' : (this.filter.fuzzyQuery ? '$regex' : '$eq')),
          value: [...this.filter.values],
          values: [...this.filter.values],
          property
        }
        this.filterTags.push(tagData)
      } else if (this.filter.value) {
        const tagData = {
          id: property.bk_property_id,
          propertyName: property.bk_property_name,
          operator: this.filter.fuzzyQuery ? '$regex' : '$eq',
          value: this.filter.value,
          property
        }
        this.filterTags.push(tagData)
      }
    },
    updateFilterTagsFromQuery() {
      // 如果有高级筛选条件，不要更新filterTags（避免把高级筛选标签清空）
      if (this.advancedFilterConditions && Object.keys(this.advancedFilterConditions).length > 0) {
        console.log('[updateFilterTagsFromQuery] 有高级筛选条件，跳过更新filterTags')
        return
      }

      const query = this.$route.query
      this.filterTags = []
      if (query.field && query.filter) {
        const property = this.allProperties.find(p => p.bk_property_id === query.field)
        if (property) {
          this.filterTags.push({
            id: property.bk_property_id,
            propertyName: property.bk_property_name,
            operator: query.fuzzy === 'true' || query.fuzzy === '1' ? '$regex' : '$eq',
            value: String(query.filter),
            property
          })
        }
      }
    },
    handleRemoveFilterTag(tag) {
      const tagIndex = this.filterTags.findIndex(t => t.id === tag.id)
      if (tagIndex >= 0) {
        this.filterTags.splice(tagIndex, 1)
      }
      // 如果移除的tag与快速搜索字段相同，清除快速搜索
      if (tag.id === this.filter.field) {
        this.filter.value = ''
        this.filter.values = []
      }
      this.table.pagination.current = 1
      this.currentSearchParams = null
      
      // 修复：同步更新 advancedFilterConditions，只删除被点击的标签对应的条件
      if (this.filterTags.length === 0) {
        // 如果没有剩余标签，清除所有高级筛选条件
        this.advancedFilterConditions = null
      } else {
        // 如果还有剩余标签，只保留剩余标签对应的条件
        const newConditions = {}
        this.filterTags.forEach(t => {
          const cond = this.advancedFilterConditions ? this.advancedFilterConditions[t.id] : null
          if (cond) {
            newConditions[t.id] = cond
          }
        })
        this.advancedFilterConditions = Object.keys(newConditions).length > 0 ? newConditions : null
      }
      
      // conditionMap 的变化会被子组件自动监听，不需要手动调用子组件方法
      
      this.syncStateToUrl({ resetPage: true })
      
      // 如果有剩余的高级筛选条件，使用高级筛选参数加载数据
      if (this.advancedFilterConditions && Object.keys(this.advancedFilterConditions).length > 0) {
        const rawConditions = []
        Object.keys(this.advancedFilterConditions).forEach(field => {
          const cond = this.advancedFilterConditions[field]
          rawConditions.push({
            field,
            operator: cond.operator,
            value: cond.value
          })
        })
        const searchParams = this.buildAdvancedSearchParams(rawConditions)
        console.log('[handleRemoveFilterTag] 使用剩余高级筛选参数:', searchParams)
        this.loadModelData(searchParams)
      } else {
        this.loadModelData()
      }
    },
    handleClearAllFilterTags() {
      this.filterTags = []
      // 清除快速搜索输入框
      this.filter.value = ''
      this.filter.values = []
      this.table.pagination.current = 1
      this.currentSearchParams = null
      this.advancedFilterConditions = null
      
      // conditionMap 的变化会被子组件自动监听，不需要手动调用子组件方法
      
      this.syncStateToUrl({ resetPage: true })
      this.loadModelData()
    },
    getColumnSortable(columnId) {
      // 参考原项目实现: 除了 INNER_TABLE 类型外，其他类型都可以排序
      // 原项目 isPropertySortable 函数:
      //   - 对于 host 模型: 排除 FOREIGNKEY, TOPOLOGY, INNER_TABLE
      //   - 对于其他模型: 只排除 INNER_TABLE
      const property = this.allProperties.find(p => p.bk_property_id === columnId)
      if (!property) return false
      
      // INNER_TABLE 类型不支持排序
      const notSortableTypes = ['innertable']
      return !notSortableTypes.includes(property.bk_property_type)
    },
    async handleApplyColumns(properties) {
      console.log('[Persistence] handleApplyColumns called, properties:', properties)
      // 与原项目保持一致: 更新存储状态 customColumns，UI 状态由 setTableHeader 同步
      this.customColumns = properties.map(p => p.bk_property_id)
      console.log('[Persistence] customColumns updated to:', this.customColumns)
      this.columnsConfig.show = false
      this.setTableHeader()
      console.log('[Persistence] setTableHeader called after apply')

      // Save to both API and Vuex store for sharing
      try {
        console.log('[Persistence] Calling saveModelCustomColumns for objId:', this.objId, 'columns:', this.customColumns)
        const saveResult = await userCustom.saveModelCustomColumns(this.objId, this.customColumns)
        console.log('[Persistence] saveModelCustomColumns result:', saveResult)

        // Sync to Vuex store for sharing with association list
        const configKey = `${this.objId}_custom_table_columns`
        this.$store.dispatch('saveUsercustom', { [configKey]: this.customColumns })
        console.log('[Persistence] Synced to Vuex store:', configKey)
      } catch (e) {
        console.error('[Persistence] Failed to save columns config:', e)
      }
      this.$bkMessage({ message: '配置已应用', theme: 'success' })
    },
    handleCancelColumns() {
      console.log('[Persistence] handleCancelColumns called')
      this.columnsConfig.show = false
    },
    async handleResetColumns() {
      console.log('[Persistence] handleResetColumns called')
      // 与原项目保持一致: 清空存储状态 customColumns（保存空数组到存储）
      // setTableHeader 会基于空的 customColumns 生成默认列（含固定字段 bk_inst_id、bk_inst_name）
      // 并同步更新 columnsConfig.selected，使抽屉再次打开时显示默认已选属性
      this.customColumns = []
      this.columnsConfig.show = false
      this.setTableHeader()
      console.log('[Persistence] setTableHeader called after reset')

      // 清空存储中的自定义列配置
      try {
        console.log('[Persistence] Clearing custom columns for objId:', this.objId)
        const saveResult = await userCustom.saveModelCustomColumns(this.objId, [])
        console.log('[Persistence] saveModelCustomColumns (clear) result:', saveResult)

        // Sync to Vuex store for sharing with association list
        const configKey = `${this.objId}_custom_table_columns`
        this.$store.dispatch('saveUsercustom', { [configKey]: [] })
        console.log('[Persistence] Synced empty config to Vuex store:', configKey)
      } catch (e) {
        console.error('[Persistence] Failed to clear columns config:', e)
      }
      this.$bkMessage({ message: '已还原默认配置', theme: 'success' })
    },
    handleSidesliderHidden() {
      this.columnsConfig.show = false
    },
    goBackToResource() {
      console.log('[Persistence] goBackToResource called, navigating to /resource')
      this.$router.push({ name: MENU_RESOURCE_MANAGEMENT })
    }
  }
}
</script>

<style lang="scss">
.general-model-layout {
  padding: 15px 20px 0;
}

.models-table-wrapper {
  margin-top: 14px;
}

.filter-tag-wrapper + .models-table-wrapper {
  margin-top: 0;
}

.general-model-layout .models-table {
  margin-top: 0 !important;
}

.models-options {
  .options-button {
    display: inline-block;
    position: relative;
    &:hover {
      z-index: 1;
    }
  }

  .models-button {
    margin-left: 10px;
    &:first-child {
      margin-left: 0;
    }
  }

  .icon-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    line-height: 30px;
    padding: 0;
    font-size: 0;
    cursor: pointer;
    border-radius: 2px;
    border: 1px solid #c4c6cc;
    background: #fff;
    transition: all 0.2s;
    vertical-align: middle;

    &:hover {
      border-color: #3a84ff;
      color: #3a84ff;
    }

    i {
      font-size: 14px;
    }
  }

  .option-filter {
    &:hover,
    &.active {
      border-color: #3a84ff;
      color: #3a84ff;
    }
  }

  .ml5 {
    margin-left: 5px;
  }

  .ml10 {
    margin-left: 10px;
  }

  .fl {
    float: left;
  }

  .fr {
    float: right;
  }
}

.options-filter {
  position: relative;
  margin-right: 5px;
  display: flex;
  align-items: flex-start;
  width: 430px;

  .filter-selector {
    width: 120px;
    border-radius: 2px 0 0 2px;
    margin-right: -1px;

    .bk-select {
      width: 100%;
      height: 32px;
      min-height: 32px;
      box-sizing: border-box;

      .bk-select-name {
        font-size: 12px;
      }
    }
  }

  .filter-value {
    flex: 1;
    width: 320px;
    border-radius: 0 2px 2px 0;

    .bk-form-input {
      line-height: 32px;
    }

    .search-input-wrapper {
      display: flex;
      align-items: center;
      width: 100%;

      .search-input {
        flex: 1;
        height: 32px;
        padding: 0 10px;
        border: 1px solid #c4c6cc;
        border-radius: 2px;
        font-size: 12px;
        outline: none;
        min-width: 0;
        box-sizing: border-box;
        line-height: 32px;

        &:focus {
          border-color: #3a84ff;
        }
      }

      .enum-select-wrapper {
        flex: 1;
        position: relative;
        min-width: 0;

        .enum-input-container {
          position: relative;
          width: 100%;

          .enum-multi-input {
            width: 100%;
            height: 32px;
            padding: 0 32px 0 10px;
            border: 1px solid #c4c6cc;
            border-radius: 2px;
            font-size: 12px;
            outline: none;
            cursor: pointer;
            background: #fff;
            text-align: left;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            box-sizing: border-box;
            line-height: 32px;

            &:focus,
            &:hover {
              border-color: #3a84ff;
            }
          }

          .bk-select-angle {
            position: absolute;
            right: 8px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 14px;
            line-height: 1;
            color: #979ba5;
            cursor: pointer;
            pointer-events: auto;
            transition: transform 0.2s ease;

            &.icon-flip {
              transform: translateY(-50%) rotate(180deg);
              color: #3a84ff;
            }
          }
        }

        .enum-dropdown {
          position: absolute;
          top: calc(100% + 4px);
          left: 0;
          right: 0;
          min-width: 200px;
          max-width: 400px;
          background: #fff;
          border: 1px solid #dcdee5;
          border-radius: 2px;
          box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
          z-index: 1000;
          max-height: 280px;
          overflow-y: auto;
          padding: 0;
          opacity: 0;
          visibility: hidden;
          transform: translateY(-10px);
          transition: opacity 0.2s ease, transform 0.2s ease, visibility 0.2s ease;

          &::before {
            content: '';
            position: absolute;
            top: -6px;
            left: 16px;
            width: 10px;
            height: 10px;
            background: #fff;
            border-left: 1px solid #dcdee5;
            border-top: 1px solid #dcdee5;
            transform: rotate(45deg);
          }

          .bk-select-search-wrapper {
            padding: 8px;
            border-bottom: 1px solid #f0f1f5;

            .bk-select-search-input {
              width: 100%;
              height: 32px;
              padding: 0 10px;
              border: 1px solid #c4c6cc;
              border-radius: 2px;
              font-size: 14px;
              outline: none;
              box-sizing: border-box;
              line-height: 32px;

              &:focus {
                border-color: #3a84ff;
              }
            }
          }

          .bk-select-options {
            padding: 6px 0;
          }

          .bk-select-option {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            cursor: pointer;
            font-size: 14px;
            color: #63656e;
            transition: background-color 0.15s;

            &:hover {
              background: #f0f1f5;
            }

            &.is-selected {
              color: #3a84ff;
              background: #f0f1f5;
            }

            input[type="checkbox"] {
              width: 16px;
              height: 16px;
              margin-right: 8px;
              cursor: pointer;
              accent-color: #3a84ff;
            }

            .bk-select-option-name {
              flex: 1;
            }

            .bk-select-check {
              margin-left: auto;
              color: #3a84ff;
              font-size: 14px;
            }
          }
        }

        &.is-open {
          .enum-input-container {
            .enum-multi-input {
              border-color: #3a84ff;
            }
          }

          .enum-dropdown {
            opacity: 1;
            visibility: visible;
            transform: translateY(0);
          }
        }
      }
    }
  }

  .filter-exact {
    display: inline-flex;
    align-items: center;
    padding: 0 5px;
    height: 32px;
    border: 1px solid #c4c6cc;
    border-radius: 0 2px 2px 0;
    border-left: none;
    flex-shrink: 0;
    white-space: nowrap;
    background: #fff;
    box-sizing: border-box;
  }

  @media screen and (max-width: 768px) {
    max-width: 100%;
    width: 100% !important;
    margin-right: 0;
    margin-top: 10px;

    .filter-selector {
      width: 100px;
    }

    .filter-value {
      .search-input-wrapper {
        .enum-select-wrapper {
          .enum-dropdown {
            max-width: 100%;
            left: 0;
            right: 0;
          }
        }
      }
    }
  }

  @media screen and (max-width: 480px) {
    flex-wrap: wrap;
    gap: 8px;

    .filter-selector {
      flex: 1 1 calc(50% - 4px);
      min-width: unset;
      width: auto;

      .bk-select {
        width: 100%;
      }
    }

    .filter-value {
      flex: 1 1 calc(50% - 4px);
      min-width: unset;

      .search-input-wrapper {
        flex-direction: column;

        .search-input,
        .enum-select-wrapper .enum-multi-input {
          width: 100%;
          border-radius: 2px;
          border-right: 1px solid #c4c6cc;
        }

        .enum-select-wrapper {
          width: 100%;

          .enum-dropdown {
            position: fixed;
            top: auto;
            bottom: 0;
            left: 0;
            right: 0;
            max-width: 100%;
            max-height: 60vh;
            border-radius: 12px 12px 0 0;
            transform: translateY(100%);
            transition: transform 0.3s ease;
            z-index: 9999;

            &::before {
              display: none;
            }
          }

          &.is-open .enum-dropdown {
            transform: translateY(0);
          }
        }
      }
    }

    .filter-exact {
      flex: 1 1 100%;
      justify-content: center;
      border-radius: 2px;
      border-left: 1px solid #c4c6cc;
      margin-top: 4px;
    }
  }
}

.bk-table-pagination-wrapper {
  background: #fff;
  border-top: 1px solid #eaeaea;
  padding: 15px 20px;
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  font-size: 0;
  background: #fff;
  border: 1px solid #c4c6cc;
  border-radius: 2px;
  cursor: pointer;
  vertical-align: middle;
  transition: all 0.2s;

  .bk-icon {
    font-size: 14px;
    line-height: 1;
    color: #63656e;
  }

  &:hover {
    border-color: #3a84ff;
    .bk-icon {
      color: #3a84ff;
    }
  }
}

.filter-placeholder {
  display: flex;
  align-items: center;
  padding: 0 10px;
  height: 32px;
  color: #999;
  font-size: 14px;
  background: #fff;
  border: 1px solid #c4c6cc;
  border-radius: 0 2px 2px 0;
  border-left: none;
  box-sizing: border-box;
}

.clearfix::after {
  content: '';
  display: table;
  clear: both;
}

.filter-tag-wrapper {
  margin-top: 10px;
}

@media screen and (max-width: 768px) {
  .mobile-dialog-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 2000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    box-sizing: border-box;
    
    .mobile-dialog {
      background: #fff;
      border-radius: 8px;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
      
      .mobile-dialog-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 15px 20px;
        border-bottom: 1px solid #e6e6e6;
        
        .mobile-dialog-title {
          font-size: 16px;
          font-weight: 500;
          color: #303133;
        }
        
        .mobile-dialog-close {
          font-size: 24px;
          color: #909399;
          cursor: pointer;
          line-height: 1;
          
          &:hover {
            color: #303133;
          }
        }
      }
      
      .mobile-dialog-content {
        flex: 1;
        padding: 20px;
        overflow-y: auto;
        
        .bk-form {
          .bk-form-item {
            margin-bottom: 15px;
            
            .bk-form-label {
              width: 100px;
              padding-right: 10px;
              font-size: 14px;
            }
            
            .bk-form-content {
              margin-left: 100px;
            }
          }
        }
      }
      
      .mobile-dialog-footer {
        display: flex;
        justify-content: flex-end;
        gap: 10px;
        padding: 15px 20px;
        border-top: 1px solid #e6e6e6;
      }
    }
  }
}

@media screen and (max-width: 480px) {
  .mobile-dialog-overlay {
    padding: 10px;
    
    .mobile-dialog {
      width: 100%;
      max-height: 95vh;
      border-radius: 4px;
      
      .mobile-dialog-header {
        padding: 12px 15px;
        
        .mobile-dialog-title {
          font-size: 15px;
        }
        
        .mobile-dialog-close {
          font-size: 20px;
        }
      }
      
      .mobile-dialog-content {
        padding: 15px;
        
        .bk-form {
          .bk-form-item {
            margin-bottom: 12px;
            
            .bk-form-label {
              width: 80px;
              font-size: 13px;
            }
            
            .bk-form-content {
              margin-left: 80px;
              
              .bk-form-input,
              .bk-select,
              .bk-textarea {
                width: 100%;
              }
            }
          }
        }
      }
      
      .mobile-dialog-footer {
        padding: 12px 15px;
        
        .bk-button {
          min-width: 70px;
          height: 30px;
          line-height: 30px;
          font-size: 13px;
        }
      }
    }
  }
}

@media screen and (min-width: 769px) {
  .mobile-dialog-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 2000;
    display: flex;
    align-items: center;
    justify-content: center;
    
    .mobile-dialog {
      background: #fff;
      border-radius: 8px;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
      
      .mobile-dialog-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 15px 20px;
        border-bottom: 1px solid #e6e6e6;
        
        .mobile-dialog-title {
          font-size: 16px;
          font-weight: 500;
          color: #303133;
        }
        
        .mobile-dialog-close {
          font-size: 24px;
          color: #909399;
          cursor: pointer;
          line-height: 1;
          
          &:hover {
            color: #303133;
          }
        }
      }
      
      .mobile-dialog-content {
        flex: 1;
        padding: 20px;
        overflow-y: auto;
      }
      
      .mobile-dialog-footer {
        display: flex;
        justify-content: flex-end;
        gap: 10px;
        padding: 15px 20px;
        border-top: 1px solid #e6e6e6;
      }
    }
  }
}

.batch-update-form-wrapper {
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.batch-update-info {
  padding: 16px 24px;
  background: #f0f9ff;
  border-bottom: 1px solid #dcdee5;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #63656e;

  i {
    font-size: 16px;
    color: #3a84ff;
  }

  strong {
    color: #303133;
    font-weight: 500;
  }

  .hidden-properties {
    color: #f56c6c;
    font-size: 13px;
  }
}

@media screen and (max-width: 768px) {
  .batch-update-info {
    padding: 12px 16px;
  }
}

// 表格实例ID列样式 - 蓝色可点击链接，与其他列一样溢出隐藏
.cell-id-link {
  color: #3a84ff;
  cursor: pointer;

  &:hover {
    text-decoration: underline;
  }
}

// 复制副本唯一约束提示横幅：长文本自动换行，避免超出视口被截断
// （$bkMessage 渲染在 body 悬浮层，故用非 scoped 全局样式 + extCls 精准定位）
.bk-message.copy-unique-hint {
  max-width: min(90vw, 640px);
  align-items: flex-start;

  .bk-message-content {
    white-space: normal;
    word-break: break-word;
    overflow-wrap: anywhere;
    line-height: 20px;
  }
}
</style>
