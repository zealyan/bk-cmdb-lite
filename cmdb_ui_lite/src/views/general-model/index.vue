<template>
  <div class="models-layout general-model-layout">
    <div class="models-options clearfix">
      <div class="options-button clearfix fl">
        <bk-button theme="primary" @click="handleCreate">新建</bk-button>
        <bk-button class="models-button" theme="default" @click="handleImport">导入</bk-button>
        <bk-button class="models-button" theme="default" @click="handleExport">导出</bk-button>
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
        <div class="filter-input" v-if="!isEnumField && !isBoolField && !isDateField && !isTimeField">
          <bk-input
            v-model="filter.value"
            :placeholder="filterPlaceholder"
            right-icon="bk-icon icon-search"
            @enter="handleSearch"
            @clear="handleClear">
          </bk-input>
        </div>
        <div class="filter-input enum-select-wrapper" v-else-if="isEnumField || isBoolField">
          <bk-input
            v-model="enumSearchQuery"
            :placeholder="filterPlaceholder"
            @enter="handleSearch">
          </bk-input>
          <div class="enum-dropdown" v-if="enumDropdownVisible">
            <div class="enum-option" v-for="opt in filteredEnumOptions" :key="opt.id" @click="handleEnumSelect(opt)">
              {{ opt.name }}
            </div>
          </div>
        </div>
        <div class="filter-input" v-else-if="isDateField">
          <bk-date-picker
            v-model="filter.values"
            :placeholder="filterPlaceholder"
            type="daterange"
            @change="handleDateChange">
          </bk-date-picker>
        </div>
        <div class="filter-input" v-else-if="isTimeField">
          <cmdb-search-time
            v-model="filter.values"
            :property="filterProperty"
            @change="handleTimeChange">
          </cmdb-search-time>
        </div>
        <bk-button class="filter-button" theme="primary" @click="handleSearch">搜索</bk-button>
      </div>
    </div>

    <filter-tag
      v-if="visibleFilterTags.length > 0"
      :tags="visibleFilterTags"
      :show-icon="false"
      @remove="handleRemoveFilterTag"
      @clear-all="handleClearAllFilterTags">
    </filter-tag>

    <general-model-filter
      :show.sync="advancedFilter.show"
      :properties="allProperties"
      :loaded-data="table.list"
      :page-size="table.pagination.limit"
      @search="handleAdvancedFilterSearch"
      @reset="handleAdvancedFilterReset">
    </general-model-filter>

    <bk-table
      ref="tableRef"
      class="models-table"
      v-bkloading="{ isLoading: table.loading }"
      :data="table.list"
      :pagination="table.pagination"
      :max-height="620"
      @page-change="handlePageChange"
      @page-limit-change="handlePageLimitChange"
      @select-all="handleSelectAll"
      @row-click="handleRowClick"
      @sort-change="handleSortChange">
      <bk-table-column type="selection" width="60" fixed="left" :selectable="() => true"></bk-table-column>
      <bk-table-column v-for="column in table.header" :key="column.bk_property_id" :label="column.bk_property_name" :prop="column.bk_property_id" :width="column.width || 150" sortable="custom">
        <template slot-scope="{ row }">
          <span v-if="column.bk_property_type === 'bool'">{{ row[column.bk_property_id] ? '是' : '否' }}</span>
          <span v-else-if="column.bk_property_type === 'enum'">
            <span class="enum-tag" v-for="(val, idx) in (row[column.bk_property_id] || '').split(',')" :key="idx">{{ val }}</span>
          </span>
          <span v-else>{{ row[column.bk_property_id] }}</span>
        </template>
      </bk-table-column>
    </bk-table>

    <bk-sideslider
      :is-show.sync="createDialogVisible"
      :title="'新建 ' + modelName"
      :width="createSidesliderWidth"
      :fullscreen="createSidesliderFullscreen"
      :quick-close="true"
      @hidden="handleCreateDialogClose">
      <template #content>
        <cmdb-form
          ref="createFormRef"
          :properties="allProperties"
          :object-id="objId"
          :is-edit-mode="false"
          @cancel="handleCreateDialogClose"
          @submit="handleCreateSubmit">
        </cmdb-form>
      </template>
    </bk-sideslider>

    <bk-sideslider
      :is-show.sync="batchUpdateDialogVisible"
      :title="'批量更新'"
      :width="createSidesliderWidth"
      :fullscreen="createSidesliderFullscreen"
      :quick-close="true"
      @hidden="handleBatchUpdateDialogClose">
      <template #content>
        <div class="batch-update-form-wrapper">
          <div class="batch-update-info" v-if="selectedIds.length > 0">
            <i class="bk-icon icon-info-circle"></i>
            已选择 <strong>{{ selectedIds.length }}</strong> 个实例进行更新
          </div>
          <form-multiple
            ref="formMultipleRef"
            :properties="allProperties"
            :show-options="true"
            :submitting="batchUpdateFormLoading"
            submit-text="更新"
            @submit="handleBatchUpdateSubmit"
            @cancel="handleBatchUpdateDialogClose">
          </form-multiple>
        </div>
      </template>
    </bk-sideslider>
  </div>
</template>

<script>
import ColumnsConfig from '@/components/columns-config/index.vue'
import FilterTag from '@/components/filter-tag/index.vue'
import FilterTagItem from '@/components/filter-tag/filter-tag-item.vue'
import GeneralModelFilter from '@/components/filter/general-model-filter.vue'
import FormMultiple from '@/components/ui/form/form-multiple.vue'
import DateSearch from '@/components/search/date.vue'
import TimeSearch from '@/components/search/time.vue'
import apiData from '@/assets/api/index.json'
import { modelAPI, userCustom } from '@/api/client'
import routerQuery from '@/utils/router-query'
import QS from 'qs'
import { buildSearchParams } from '@/utils/query-builder'

export default {
  name: 'GeneralModel',
  components: {
    ColumnsConfig,
    FilterTag,
    FilterTagItem,
    GeneralModelFilter,
    FormMultiple,
    'cmdb-search-date': DateSearch,
    'cmdb-search-time': TimeSearch
  },
  data() {
    return {
      filter: {
        field: '',
        value: '',
        values: [],
        fuzzyQuery: true
      },
      enumDropdownVisible: false,
      enumSearchQuery: '',
      objId: 'bk_switch',
      modelData: null,
      allProperties: [],
      defaultColumns: [],
      selectedIds: [],
      createDialogVisible: false,
      createForm: {},
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
          show: true
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
        selected: [],
        disabledColumns: ['id']
      },
      isUrlUpdateTriggered: false,
      searchTimeout: null
    }
  },
  computed: {
    modelName() {
      const model = this.modelIndex.find(m => m.bk_obj_id === this.objId)
      return model ? model.bk_obj_name : this.objId
    },
    searchableProperties() {
      return this.allProperties.filter(property => property.bk_property_id !== 'id')
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
        'singlechar', 'longchar', 'shortchar', 'text', 'string',
        'enum', 'int', 'bool', 'time', 'date', 'float', 'list', 'map'
      ]
      return supportedTypes.includes(propertyType)
    },
    isEnumField() {
      const property = this.filterProperty
      if (!property) return false
      return property.bk_property_type === 'enum'
    },
    isBoolField() {
      const property = this.filterProperty
      if (!property) return false
      return property.bk_property_type === 'bool'
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

      const option = property.option || property.bk_property_option
      if (option && Array.isArray(option)) {
        return option.map(opt => ({ id: opt, name: opt }))
      }

      return []
    },
    filteredEnumOptions() {
      if (!this.enumSearchQuery) {
        return this.enumOptions
      }
      const query = this.enumSearchQuery.toLowerCase()
      return this.enumOptions.filter(opt => 
        opt.name.toLowerCase().includes(query)
      )
    },
    sidesliderWidth() {
      const screenWidth = window.innerWidth
      if (screenWidth >= 768) {
        return 600
      } else if (screenWidth >= 480) {
        return Math.floor(screenWidth * 0.8)
      } else {
        return Math.floor(screenWidth * 0.95)
      }
    },
    /**
     * 将内部排序格式转换为 bk-table 组件所需的格式
     * 内部格式: 'name' (升序) 或 '-name' (降序)
     * 组件格式: { prop: 'name', order: 'ascending' | 'descending' }
     */
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
    },
    modelIndex() {
      return apiData.models || []
    }
  },
  created() {
    this.objId = this.$route.params.objId || 'bk_switch'

    this.stopRouteQueryWatch = routerQuery.watch('*', (query, oldQuery) => {
      console.log('[Index.watch] URL变化被触发', { query, oldQuery })

      const isFromDetails = this.prevInstanceId && !this.$route.params.instanceId
      console.log('[Index.watch] isFromDetails:', isFromDetails, 'prevInstanceId:', this.prevInstanceId)

      if (isFromDetails) {
        console.log('[Index.watch] 从详情页返回，优先恢复状态')
        this.restoreStateFromUrl()
        
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
        return
      }

      const fieldChanged = query.field !== oldQuery.field
      const filterChanged = query.filter !== oldQuery.filter
      const fuzzyChanged = query.fuzzy !== oldQuery.fuzzy
      const filter_advChanged = query.filter_adv !== oldQuery.filter_adv
      const sChanged = query.s !== oldQuery.s
      const sortChanged = query.sort !== oldQuery.sort
      const pageChanged = query.page !== oldQuery.page
      const limitChanged = query.limit !== oldQuery.limit

      if (fieldChanged || filterChanged || fuzzyChanged || filter_advChanged || sChanged || sortChanged || pageChanged || limitChanged) {
        console.log('[Index.watch] 搜索条件变化，执行restoreStateFromUrl')
        this.restoreStateFromUrl()
        
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
    }, { throttle: 100 })
  },
  mounted() {
    console.log('[Index.mounted] 组件挂载')
    console.log('[Index.mounted] 当前URL:', window.location.href)
    console.log('[Index.mounted] Route query:', JSON.stringify(this.$route.query))
    this.restoreStateFromUrl()
    console.log('[Index.mounted] restoreStateFromUrl 后 filter.value:', this.filter.value, 'fuzzy:', this.filter.fuzzyQuery)

    this.clickOutsideHandler = (event) => {
      const wrapper = document.querySelector('.enum-select-wrapper')
      if (wrapper && !wrapper.contains(event.target)) {
        this.enumDropdownVisible = false
      }
    }
    document.addEventListener('click', this.clickOutsideHandler)

    setTimeout(() => {
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
        console.log('[Index.mounted] 从URL恢复高级筛选参数:', searchParams)
        this.loadModelData(searchParams)
      } else {
        this.loadModelData()
      }
    }, 0)
  },
  beforeDestroy() {
    if (this.stopRouteQueryWatch) {
      this.stopRouteQueryWatch()
    }
    if (this.clickOutsideHandler) {
      document.removeEventListener('click', this.clickOutsideHandler)
    }
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout)
    }
  },
  watch: {
    'filter.values': {
      handler(newValues, oldValues) {
        console.log('[Index.watch.filter.values] 变化:', { old: oldValues, new: newValues })
        if (newValues && newValues.length > 0) {
          this.filter.value = newValues.join(',')
        }
      }
    },
    '$route.params.objId': {
      handler(newObjId) {
        if (newObjId !== this.objId) {
          this.objId = newObjId || 'bk_switch'
          this.restoreStateFromUrl()
          this.loadModelData()
        }
      }
    },
    '$route.params.instanceId': {
      handler(newInstanceId, oldInstanceId) {
        console.log('[Index.watch.instanceId] 变化:', { old: oldInstanceId, new: newInstanceId })
        const isEnterDetails = !oldInstanceId && newInstanceId
        const isLeaveDetails = oldInstanceId && !newInstanceId
        
        if (isEnterDetails) {
          this.prevInstanceId = oldInstanceId
        }
        
        if (isLeaveDetails) {
          console.log('[Index.watch.instanceId] 从详情页返回，延迟恢复状态')
          this.$nextTick(() => {
            this.restoreStateFromUrl()
            
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
          })
        }
      }
    },
    allProperties: {
      handler(newProperties) {
        console.log('[Index.watch.allProperties] 属性加载完成，检查是否需要恢复 filterTags')
        if (newProperties && newProperties.length > 0) {
          const query = this.$route.query
          
          if (query.filter_adv && this.filterTags.length === 0) {
            console.log('[Index.watch.allProperties] 检测到filter_adv且filterTags为空，重新恢复状态')
            this.restoreStateFromUrl()
            
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
            this.hasRestoredFromUrl = true
          }
        }
      }
    },
    'table.pagination.current': {
      handler(newPage) {
        console.log('[Index.watch.pagination.current] 页码变化:', newPage)
        if (!this.isUrlUpdateTriggered) {
          this.syncStateToUrl({ resetPage: false })
        }
        this.isUrlUpdateTriggered = false
      }
    }
  },
  methods: {
    async loadModelData(searchParams) {
      console.log('[Index.loadModelData] 开始加载数据')
      this.table.loading = true

      try {
        const currentValue = this.filter.value
        const currentFuzzy = this.filter.fuzzyQuery
        const currentSort = this.table.sort
        const currentPage = this.table.pagination.current
        const currentLimit = this.table.pagination.limit

        if (!this.filter.field && this.allProperties.length > 0) {
          const firstField = this.allProperties.find(p => p.bk_property_id !== 'id')
          if (firstField) {
            this.filter.field = firstField.bk_property_id
          }
        }

        if (!(this.isEnumField || this.isBoolField) || this.filter.values.length === 0) {
          this.filter.value = currentValue
        }
        this.filter.fuzzyQuery = currentFuzzy
        this.table.sort = currentSort
        this.table.pagination.current = currentPage
        this.table.pagination.limit = currentLimit

        console.log('[Index.loadModelData] 调用搜索API，搜索值:', this.filter.value, '多选:', this.filter.values)

        let instResult

        if (searchParams) {
          console.log('[Index.loadModelData] 使用高级筛选参数:', searchParams)
          
          instResult = await modelAPI.searchInstances(this.objId, {
            ...searchParams
          })
        } else {
          const isMultiSelectEnum = this.isEnumField || this.isBoolField
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

          instResult = await modelAPI.searchInstances(this.objId, searchParams)
        }

        console.log('[Index.loadModelData] API返回结果:', {
          count: instResult.instances?.length || 0,
          total: instResult.total
        })

        this.setTableHeader()
        this.updateTableSortState()

        this.table.list = instResult.instances || []
        this.table.pagination.count = instResult.total || 0

        console.log('[Index.loadModelData] 加载完成，当前列表行数:', this.table.list.length)

      } catch (error) {
        console.error('[ERROR] 加载数据失败:', error)
        this.$bkMessage({ message: '加载数据失败', theme: 'error' })
      } finally {
        this.table.loading = false
      }
    },
    setTableHeader() {
      console.log('[Debug] setTableHeader start')
      console.log('[Debug] allProperties:', this.allProperties?.length)
      console.log('[Debug] columnsConfig.selected:', this.columnsConfig.selected)
      
      const maxDefaultColumns = 8
      let selectedIds = null
      
      if (this.columnsConfig.selected && Array.isArray(this.columnsConfig.selected) && this.columnsConfig.selected.length > 0) {
        selectedIds = this.columnsConfig.selected
        console.log('[Debug] Use user config:', selectedIds)
      } else {
        console.log('[Debug] Use default config')
      }

      if (!selectedIds) {
        selectedIds = this.allProperties
          .filter(p => p.bk_property_index >= 0)
          .sort((a, b) => a.bk_property_index - b.bk_property_index)
          .slice(0, maxDefaultColumns)
          .map(p => p.bk_property_id)

        selectedIds = ['id', ...selectedIds.filter(id => id !== 'id')]
        console.log('[Debug] Default selectedIds:', selectedIds)
      }

      const selected = this.allProperties.filter(p => selectedIds.includes(p.bk_property_id))
      console.log('[Debug] selectedProperties:', selected.length)

      selected.sort((a, b) => {
        const indexA = selectedIds.indexOf(a.bk_property_id)
        const indexB = selectedIds.indexOf(b.bk_property_id)
        return indexA - indexB
      })

      this.table.header = selected
      console.log('[Debug] table.header:', this.table.header.length)
    },
    async handleFieldChange(field) {
      console.log('[DEBUG] handleFieldChange:', field)
      this.filter.value = ''
      this.filter.values = []
      this.enumSearchQuery = ''
    },
    handleSearch() {
      this.table.pagination.current = 1
      this.currentSearchParams = null
      this.advancedFilterConditions = null
      this.updateFilterTags()
      this.syncStateToUrl({ resetPage: true })
      this.isUrlUpdateTriggered = true
      this.loadModelData()
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
    handleAdvancedFilterSearch(payload) {
      console.log('[DEBUG] handleAdvancedFilterSearch:', payload)
      const { conditionMap, rawConditions } = payload
      
      this.table.pagination.current = 1
      this.advancedFilterConditions = conditionMap
      this.filterTags = []
      
      Object.keys(conditionMap).forEach(id => {
        const { operator, value } = conditionMap[id]
        const property = this.allProperties.find(p => p.bk_property_id === id)
        if (property) {
          this.filterTags.push({
            id: id,
            propertyName: property.bk_property_name || id,
            operator: operator,
            value: value,
            property: property
          })
        }
      })
      
      const searchParams = this.buildAdvancedSearchParams(rawConditions)
      console.log('[DEBUG] handleAdvancedFilterSearch searchParams:', searchParams)
      
      this.syncStateToUrl({
        filter_adv: routerQuery.get('filter_adv'),
        s: 'adv',
        resetPage: true
      })
      this.isUrlUpdateTriggered = true
      
      this.loadModelData(searchParams)
    },
    handleAdvancedFilterReset() {
      console.log('[DEBUG] handleAdvancedFilterReset')
      this.table.pagination.current = 1
      this.advancedFilterConditions = null
      this.filterTags = []
      this.syncStateToUrl({ resetPage: true })
      this.isUrlUpdateTriggered = true
      this.loadModelData()
    },
    handlePageChange(page) {
      console.log('[DEBUG] handlePageChange:', page)
      this.table.pagination.current = page
      this.syncStateToUrl({ resetPage: false })
      this.isUrlUpdateTriggered = true
      
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
        this.loadModelData(searchParams)
      } else {
        this.loadModelData()
      }
    },
    handlePageLimitChange(limit) {
      console.log('[DEBUG] handlePageLimitChange:', limit)
      this.table.pagination.current = 1
      this.table.pagination.limit = limit
      this.syncStateToUrl({ resetPage: true })
      this.isUrlUpdateTriggered = true
      
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
        this.loadModelData(searchParams)
      } else {
        this.loadModelData()
      }
    },
    handleClear() {
      this.filter.value = ''
      this.filter.values = []
      this.filter.fuzzyQuery = true
    },
    handleEnumSelect(opt) {
      console.log('[DEBUG] handleEnumSelect:', opt)
      if (!this.filter.values.includes(opt.id)) {
        this.filter.values.push(opt.id)
        this.filter.value = this.filter.values.join(',')
      }
      this.enumSearchQuery = ''
      this.enumDropdownVisible = false
    },
    handleDateChange(dates) {
      console.log('[DEBUG] handleDateChange:', dates)
      if (dates && dates.length === 2) {
        this.filter.values = dates
        this.filter.value = dates.join(',')
      }
    },
    handleTimeChange(values) {
      console.log('[DEBUG] handleTimeChange:', values)
      if (values && values.length > 0) {
        this.filter.values = values
        this.filter.value = values.join(',')
      }
    },
    handleSelectAll(selection) {
      this.selectedIds = selection.map(item => item.id)
    },
    handleRowClick({ row }) {
      this.$router.push({
        name: 'generalModelDetail',
        params: {
          objId: this.objId,
          instanceId: row.id
        }
      })
    },
    updateFilterTags() {
      if (this.filter.field && this.filter.value) {
        const property = this.allProperties.find(p => p.bk_property_id === this.filter.field)
        if (property) {
          this.filterTags = [{
            id: this.filter.field,
            propertyName: property.bk_property_name,
            operator: this.filter.fuzzyQuery ? '$regex' : '$eq',
            value: this.filter.value,
            property: property
          }]
        }
      } else {
        this.filterTags = []
      }
    },
    updateFilterTagsFromQuery() {
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
      console.log('[DEBUG] handleRemoveFilterTag:', tag)
      if (tag.operator && tag.operator !== '$eq' && tag.operator !== '$regex') {
        const property = tag.property
        if (property) {
          const opType = this.getOperatorType(property.bk_property_type)
          tag.value = this.getDefaultValue(opType)
        }
        return
      }
      
      if (this.advancedFilterConditions && this.advancedFilterConditions[tag.id]) {
        delete this.advancedFilterConditions[tag.id]
        
        if (Object.keys(this.advancedFilterConditions).length === 0) {
          this.advancedFilterConditions = null
          this.filterTags = []
          this.syncStateToUrl({ resetPage: true })
          this.isUrlUpdateTriggered = true
          this.loadModelData()
        } else {
          this.filterTags = this.filterTags.filter(t => t.id !== tag.id)
          const rawConditions = Object.keys(this.advancedFilterConditions).map(id => ({
            field: id,
            ...this.advancedFilterConditions[id]
          }))
          const searchParams = this.buildAdvancedSearchParams(rawConditions)
          this.syncStateToUrl({
            filter_adv: routerQuery.get('filter_adv'),
            s: 'adv',
            resetPage: true
          })
          this.isUrlUpdateTriggered = true
          this.loadModelData(searchParams)
        }
      } else {
        this.filter.field = ''
        this.filter.value = ''
        this.filterTags = []
        this.syncStateToUrl({ resetPage: true })
        this.isUrlUpdateTriggered = true
        this.loadModelData()
      }
    },
    handleClearAllFilterTags() {
      console.log('[DEBUG] handleClearAllFilterTags')
      this.advancedFilterConditions = null
      this.filterTags = []
      this.filter.field = ''
      this.filter.value = ''
      this.filter.values = []
      this.syncStateToUrl({ resetPage: true })
      this.isUrlUpdateTriggered = true
      this.loadModelData()
    },
    getOperatorType(propertyType) {
      if (propertyType === 'enum' || propertyType === 'list') return 'multiple'
      if (propertyType === 'bool') return 'boolean'
      if (propertyType === 'int' || propertyType === 'float') return 'range'
      return 'single'
    },
    getDefaultValue(opType) {
      switch (opType) {
        case 'multiple': return []
        case 'boolean': return null
        case 'range': return { start: '', end: '' }
        default: return ''
      }
    },
    restoreStateFromUrl() {
      console.log('[restoreStateFromUrl] 开始恢复状态')
      const query = this.$route.query
      console.log('[restoreStateFromUrl] URL query:', query)

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
      if (query.fuzzy !== undefined) {
        this.filter.fuzzyQuery = query.fuzzy === 'true' || query.fuzzy === '1'
      }
      if (query.sort) {
        this.table.sort = query.sort
      }

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
            
            if (Object.keys(conditionMap).length > 0) {
              this.advancedFilterConditions = conditionMap
            } else {
              this.advancedFilterConditions = null
            }
            
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
            this.advancedFilterConditions = null
          }
        } catch (e) {
          console.error('[restoreStateFromUrl] 解析filter_adv失败:', e)
          this.advancedFilterConditions = null
          this.updateFilterTagsFromQuery()
        }
      } else {
        this.advancedFilterConditions = null
        this.updateFilterTagsFromQuery()
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
    },
    syncStateToUrl(options = {}) {
      const { keepSort = true, resetPage = false, filter_adv, s } = options
      const query = {}

      if (!resetPage) {
        query.page = this.table.pagination.current
      }
      query.limit = this.table.pagination.limit

      if (this.filter.field) {
        query.field = this.filter.field
      }
      if (this.filter.value) {
        query.filter = this.filter.value
      }
      if (this.filter.fuzzyQuery !== false) {
        query.fuzzy = this.filter.fuzzyQuery ? '1' : '0'
      }
      if (keepSort && this.table.sort) {
        query.sort = this.table.sort
      }

      if (filter_adv !== undefined) {
        query.filter_adv = filter_adv
      } else if (this.advancedFilterConditions && Object.keys(this.advancedFilterConditions).length > 0) {
        try {
          const tempQuery = {}
          Object.keys(this.advancedFilterConditions).forEach(field => {
            const cond = this.advancedFilterConditions[field]
            const key = `${field}${cond.operator}`
            let value = cond.value
            
            if (Array.isArray(value)) {
              tempQuery[key] = value.join(',')
            } else if (value !== null && value !== undefined) {
              tempQuery[key] = value
            }
          })
          query.filter_adv = QS.stringify(tempQuery, { encode: false })
        } catch (e) {
          console.error('[syncStateToUrl] 构建filter_adv失败:', e)
        }
      }
      
      if (s !== undefined) {
        query.s = s
      } else if (this.advancedFilterConditions && Object.keys(this.advancedFilterConditions).length > 0) {
        query.s = 'adv'
      }

      this.isUrlUpdateTriggered = true
      routerQuery.setAll(query)
    },
    handleSearch() {
      this.table.pagination.current = 1
      this.currentSearchParams = null
      this.advancedFilterConditions = null
      this.updateFilterTags()
      this.syncStateToUrl({ resetPage: true })
      this.isUrlUpdateTriggered = true
      this.loadModelData()
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
    handleBatchDelete() {
      if (this.selectedIds.length === 0) {
        this.$bkMessage({ message: '请先选择要删除的实例', theme: 'warning' })
        return
      }
      
      const ids = this.selectedIds
      const total = ids.length
      
      modelAPI.getInstanceAssociations(this.objId, ids)
        .then(result => {
          let total_associations = 0
          if (result && result.associations) {
            total_associations = result.associations.length
          }
          
          const subTitle = total_associations > 0
            ? `将同时删除 ${total_associations} 条关联关系`
            : ''
          
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
                this.$bkMessage({ message: '删除失败，请稍后重试', theme: 'error' })
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
          this.$bkMessage({ message: '检查关联关系失败，请稍后重试', theme: 'error' })
          this.table.loading = false
        })
    },
    buildAdvancedSearchParams(rawConditions) {
      const conditionMap = {}
      
      rawConditions.forEach(cond => {
        const { field, operator, value } = cond
        
        const property = this.allProperties.find(p => p.bk_property_id === field)
        const isEnumOrList = property && ['enum', 'list'].includes(property.bk_property_type)
        const isDateTime = property && ['date', 'time'].includes(property.bk_property_type)
        
        let processedValue = value
        if (isEnumOrList || isDateTime) {
          if (Array.isArray(value)) {
            processedValue = value
          } else if (value !== null && value !== undefined && String(value).trim().length > 0) {
            processedValue = [value]
          }
        } else if (value !== null && value !== undefined && String(value).trim().length > 0) {
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
      console.log('[DEBUG] handleCreate called - 新建按钮被点击')
      console.log('[DEBUG] 当前对象ID:', this.objId)
      console.log('[DEBUG] 当前属性数量:', this.allProperties.length)
      console.log('[DEBUG] 属性列表:', this.allProperties.map(p => ({ id: p.bk_property_id, name: p.bk_property_name, type: p.bk_property_type })))
      this.handleCreateInstance()
    },
    handleCreateInstance() {
      console.log('[DEBUG] handleCreateInstance - 开始打开新建弹窗')
      this.createForm = {}
      this.createDialogVisible = true
      
      this.allProperties.forEach(attr => {
        if (attr.default !== null && attr.default !== undefined) {
          this.$set(this.createForm, attr.bk_property_id, attr.default)
        }
      })
    },
    handleCreateDialogClose() {
      this.createDialogVisible = false
      this.createForm = {}
    },
    handleCreateSubmit(formData) {
      console.log('[DEBUG] handleCreateSubmit - 提交表单数据:', formData)
      this.doCreateInstance(formData)
    },
    async doCreateInstance(formData) {
      this.createFormLoading = true
      try {
        const result = await modelAPI.createInstance(this.objId, formData)
        
        if (result.success) {
          this.$bkMessage({ message: '实例创建成功', theme: 'success' })
          this.handleCreateDialogClose()
          await this.loadModelData(this.currentSearchParams)
        } else {
          this.$bkMessage({ message: result.message || '创建失败', theme: 'error' })
        }
      } catch (error) {
        console.error('Create instance error:', error)
        this.$bkMessage({ message: '创建失败', theme: 'error' })
      } finally {
        this.createFormLoading = false
      }
    },
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
        if (result.success) {
          this.$bkMessage({ message: `成功更新 ${this.selectedIds.length} 个实例`, theme: 'success' })
          this.handleBatchUpdateDialogClose()
          this.selectedIds = []
          await this.loadModelData(this.currentSearchParams)
        } else {
          this.$bkMessage({ message: result.message || '更新失败', theme: 'error' })
        }
      } catch (error) {
        console.error('Batch update error:', error)
        this.$bkMessage({ message: '更新失败', theme: 'error' })
      } finally {
        this.batchUpdateFormLoading = false
      }
    },
    handleBatchUpdateDialogClose() {
      this.batchUpdateDialogVisible = false
    },
    handleImport() {
      this.$bkMessage({ message: '导入功能开发中', theme: 'info' })
    },
    handleExport() {
      this.$bkMessage({ message: '导出功能开发中', theme: 'info' })
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

          const targetTh = Array.from(allThs).find(th => {
            const propName = th.getAttribute('data-prop')
            return propName === prop
          })

          if (targetTh) {
            const sortIcon = targetTh.querySelector('.caret-wrapper')
            if (sortIcon) {
              sortIcon.classList.remove('ascending', 'descending')
              sortIcon.classList.add(orderClass)
            }
          }
        })
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.general-model-layout {
  padding: 20px;
  .models-options {
    margin-bottom: 16px;
    .options-button {
      .models-button {
        margin-left: 8px;
      }
      .button-delete {
        color: #ff4949;
      }
    }
    .options-filter {
      display: flex;
      align-items: center;
      gap: 8px;
      .filter-selector {
        width: 150px;
      }
      .filter-input {
        width: 200px;
      }
      .filter-button {
        margin-left: 4px;
      }
    }
  }
  .enum-select-wrapper {
    position: relative;
    .enum-dropdown {
      position: absolute;
      top: 100%;
      left: 0;
      width: 100%;
      max-height: 200px;
      overflow-y: auto;
      background: #fff;
      border: 1px solid #dcdee5;
      border-radius: 2px;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
      z-index: 100;
      .enum-option {
        padding: 8px 12px;
        cursor: pointer;
        &:hover {
          background: #eaf3ff;
        }
      }
    }
  }
  .models-table {
    margin-top: 16px;
    .enum-tag {
      display: inline-block;
      padding: 2px 8px;
      margin: 2px;
      background: #eaf3ff;
      border-radius: 2px;
      font-size: 12px;
    }
  }
}
</style>
