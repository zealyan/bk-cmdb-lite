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
        <div class="filter-value">
          <div v-if="filter.field && filter.field !== ''" class="search-input-wrapper">
            <div v-if="isEnumField || isBoolField" class="enum-select-wrapper" :class="{ 'is-open': enumDropdownVisible }" @click.stop>
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
      v-if="hasFilterCondition"
      class="filter-tag-wrapper"
      :filter-tags="filterTags"
      @remove="handleRemoveFilterTag"
      @clear-all="handleClearAllFilterTags">
    </filter-tag>

    <general-model-filter
      :show.sync="advancedFilter.show"
      :properties="allProperties"
      :loaded-data="table.list"
      @search="handleAdvancedFilterSearch"
      @reset="handleAdvancedFilterReset">
    </general-model-filter>

    <bk-table
      ref="tableRef"
      class="models-table"
      v-bkloading="{ isLoading: table.loading }"
      :data="table.list"
      :pagination="table.pagination"
      :sort="tableSort"
      :selected-data.sync="selectedIds"
      :row-key="row => row.id"
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
        <template v-if="column.id === 'id'" #default="{ row }">
          <bk-button :text="true" :primary="true" @click="handleViewDetails(row)">
            {{ row[column.id] }}
          </bk-button>
        </template>
        <template v-else #default="{ row }">
          {{ formatCellValue(row[column.id], column) }}
        </template>
      </bk-table-column>
      <bk-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <bk-button :text="true" @click="handleViewDetails(row)">查看</bk-button>
          <bk-button :text="true" theme="danger" @click="handleDeleteSingle(row)">删除</bk-button>
        </template>
      </bk-table-column>
    </bk-table>

    <bk-sideslider
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
          :disabled-columns="columnsConfig.disabledColumns"
          :max="20"
          @on-apply="handleApplyColumns"
          @on-cancel="handleCancelColumns"
          @on-reset="handleResetColumns">
        </columns-config>
      </template>
    </bk-sideslider>

    <!-- 新增实例弹窗 -->
    <bk-sideslider
      :is-show.sync="createDialogVisible"
      :title="'新增实例'"
      :width="createSidesliderWidth"
      :fullscreen="createSidesliderFullscreen"
      :quick-close="true"
      @hidden="handleCreateDialogClose">
      <template #content>
        <div class="create-form-wrapper">
          <cmdb-form
            ref="cmdbFormRef"
            :properties="allProperties"
            :values="createForm"
            :type="'create'"
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
import modelIndex from '@/assets/api/index.json'
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
        return value !== null && value !== undefined && !!String(value).length
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
    this.objId = this.$route.params.objId || 'bk_switch'

    this.stopRouteQueryWatch = routerQuery.watch('*', (query, oldQuery) => {
      console.log('[Index.watch] URL变化被触发', { query, oldQuery })

      const isFromDetails = this.prevInstanceId && !this.$route.params.instanceId
      console.log('[Index.watch] isFromDetails:', isFromDetails, 'prevInstanceId:', this.prevInstanceId)

      if (isFromDetails) {
        console.log('[Index.watch] 从详情页返回，优先恢复状态')
        this.restoreStateFromUrl()
        this.updateFilterTagsFromQuery()
        
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
          console.log('[Index.watch] 搜索条件变化，执行restoreStateFromUrl和updateFilterTagsFromQuery')
          this.restoreStateFromUrl()
          this.updateFilterTagsFromQuery()
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
        console.log('[Index.watch.instanceId] 实例ID变化:', { new: newInstanceId, old: oldInstanceId })
        if (!newInstanceId && oldInstanceId) {
          console.log('[Index.watch.instanceId] 从详情页返回，执行restoreStateFromUrl和updateFilterTagsFromQuery')
          this.hasRestoredFromUrl = false
          this.restoreStateFromUrl()
          this.updateFilterTagsFromQuery()
          this.hasRestoredFromUrl = true
          this.loadModelData()
        }
        this.prevInstanceId = newInstanceId
      }
    },
    allProperties: {
      handler(newProperties) {
        if (newProperties && newProperties.length > 0 && !this.hasRestoredFromUrl) {
          const query = this.$route.query
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
            if (query.fuzzy !== undefined) {
              this.filter.fuzzyQuery = query.fuzzy === 'true' || query.fuzzy === '1'
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
  },
  methods: {
    async loadModelData(searchParams = null) {
      this.table.loading = true
      try {
        const query = this.$route.query
        const currentField = query.field || this.filter.field
        const currentValue = query.filter !== undefined ? String(query.filter) : this.filter.value
        const currentFuzzy = query.fuzzy !== undefined ? (query.fuzzy === 'true' || query.fuzzy === '1') : this.filter.fuzzyQuery
        const currentSort = query.sort || this.table.sort
        const currentPage = query.page ? parseInt(query.page, 10) : this.table.pagination.current
        const currentLimit = query.limit ? parseInt(query.limit, 10) : this.table.pagination.limit

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

        this.allProperties = attrResult.attributes || []
        this.defaultColumns = attrResult.default_columns || []
        console.log('[Persistence] Loaded model attributes, objId:', this.objId, 'defaultColumns:', this.defaultColumns)

        // Load saved columns config
        try {
          console.log('[Persistence] Calling getModelCustomColumns for objId:', this.objId)
          const savedColumns = await userCustom.getModelCustomColumns(this.objId)
          console.log('[Persistence] getModelCustomColumns result:', savedColumns)
          if (savedColumns && savedColumns.columns && savedColumns.columns.length > 0) {
            this.columnsConfig.selected = savedColumns.columns
            console.log('[Persistence] Set columnsConfig.selected to:', this.columnsConfig.selected)
          } else {
            // 没有有效配置时，重置为空数组，使用默认规则
            this.columnsConfig.selected = []
            console.log('[Persistence] Reset columnsConfig.selected to empty array')
          }
        } catch (e) {
          console.log('[Persistence] No saved columns config found or error:', e)
          this.columnsConfig.selected = []
        }

        const validField = this.allProperties.find(p => p.bk_property_id === currentField)
        if (!validField && this.allProperties.length > 0) {
          const firstField = this.allProperties.find(p => p.bk_property_id !== 'id')
          if (firstField) {
            this.filter.field = firstField.bk_property_id
          }
        }

        // 只有在非多选场景下才设置 filter.value，避免与 filter.values 冲突
        if (!(this.isEnumField || this.isBoolField) || this.filter.values.length === 0) {
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
          })
        } else {
          // 否则使用原有的简单搜索方式
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
      
      // 检查是否有有效的用户配置
      if (this.columnsConfig.selected && Array.isArray(this.columnsConfig.selected) && this.columnsConfig.selected.length > 0) {
        selectedIds = this.columnsConfig.selected
        console.log('[Debug] Use user config:', selectedIds)
      } else {
        console.log('[Debug] Use default config')
      }

      if (!selectedIds) {
        // 从属性中获取排序后的默认列
        selectedIds = this.allProperties
          .filter(p => p.bk_property_index >= 0)
          .sort((a, b) => a.bk_property_index - b.bk_property_index)
          .slice(0, maxDefaultColumns)
          .map(p => p.bk_property_id)

        // 确保 id 始终在第一位
        selectedIds = ['id', ...selectedIds.filter(id => id !== 'id')]
        console.log('[Debug] Default selectedIds:', selectedIds)
      } else if (!selectedIds.includes('id')) {
        // 确保 id 在自定义配置中
        selectedIds = ['id', ...selectedIds]
      }

      const selectedProperties = this.allProperties
        .filter(p => selectedIds.includes(p.bk_property_id))
        .sort((a, b) => {
          // 强制 id 在第一位
          if (a.bk_property_id === 'id') return -1
          if (b.bk_property_id === 'id') return 1
          // 其他按 selectedIds 顺序排列
          const indexA = selectedIds.indexOf(a.bk_property_id)
          const indexB = selectedIds.indexOf(b.bk_property_id)
          return indexA - indexB
        })

      console.log('[Debug] selectedProperties:', selectedProperties.length)
      
      this.table.header = selectedProperties.map(property => ({
        id: property.bk_property_id,
        name: property.bk_property_name,
        property
      }))
      
      console.log('[Debug] table.header:', this.table.header.length)
    },
    formatCellValue(value, column) {
      if (value === null || value === undefined || value === '') {
        return '-'
      }
      return String(value)
    },
    handleFieldChange() {
      this.filter.value = ''
      this.filter.values = []
      this.filter.fuzzyQuery = false
    },
    handleEnumSelect(event) {
      const selected = event.target.selectedOptions
      const values = Array.from(selected).map(opt => opt.value)
      this.filter.values = values
      if (values.length > 0) {
        this.filter.value = values.join(',')
        this.table.pagination.current = 1
        this.updateFilterTags()
        this.syncStateToUrl({ resetPage: true })
        this.isUrlUpdateTriggered = true
        this.loadModelData()
      }
    },
    toggleEnumDropdown() {
      this.enumDropdownVisible = !this.enumDropdownVisible
    },
    handleEnumOptionChange() {
      if (this.filter.values.length > 0) {
        this.filter.value = this.filter.values.join(',')
        this.table.pagination.current = 1
        this.updateFilterTags()
        this.syncStateToUrl({ resetPage: true })
        this.isUrlUpdateTriggered = true
        this.loadModelData()
      } else {
        this.filter.value = ''
        this.table.pagination.current = 1
        this.syncStateToUrl({ resetPage: true })
        this.isUrlUpdateTriggered = true
        this.loadModelData()
      }
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
      this.table.pagination.current = 1
      this.updateFilterTags()
      this.syncStateToUrl({ resetPage: true })
      this.isUrlUpdateTriggered = true
      
      // 延迟搜索，让用户可以快速多选多个选项
      if (this.searchTimeout) {
        clearTimeout(this.searchTimeout)
      }
      this.searchTimeout = setTimeout(() => {
        this.loadModelData()
      }, 300)
    },
    handleEnumSelectSingle(selected) {
      this.filter.value = selected
      this.filter.values = selected ? [selected] : []
      this.table.pagination.current = 1
      this.updateFilterTags()
      this.syncStateToUrl({ resetPage: true })
      this.isUrlUpdateTriggered = true
      this.loadModelData()
    },
    handleEnumClear() {
      this.filter.values = []
      this.filter.value = ''
      this.table.pagination.current = 1
      this.syncStateToUrl({ resetPage: true })
      this.isUrlUpdateTriggered = true
      this.loadModelData()
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
            
            this.advancedFilterConditions = conditionMap
            
            // 恢复 filterTags
            this.filterTags = rawConditions.map(c => {
              const property = this.allProperties.find(p => p.bk_property_id === c.field)
              return {
                id: c.field,
                property: property || {},
                propertyName: property?.bk_property_name || c.field,
                operator: c.operator,
                value: c.value
              }
            })
            
            console.log('[restoreStateFromUrl] 高级筛选条件已恢复，filterTags:', this.filterTags)
          }
        } catch (e) {
          console.error('[restoreStateFromUrl] 解析filter_adv失败:', e)
          this.advancedFilterConditions = null
          this.filterTags = []
        }
      } else {
        this.advancedFilterConditions = null
      }

      this.updateFilterTagsFromQuery()

      console.log('[restoreStateFromUrl] 恢复后的状态:', {
        field: this.filter.field,
        value: this.filter.value,
        fuzzyQuery: this.filter.fuzzyQuery,
        page: this.table.pagination.current,
        sort: this.table.sort,
        hasAdvancedFilter: !!this.advancedFilterConditions
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

      // 保持与原bk-cmdb项目一致的URL参数
      if (filter_adv !== undefined) {
        query.filter_adv = filter_adv
      }
      if (s !== undefined) {
        query.s = s
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
    handleAdvancedFilterSearch(searchResult) {
      console.log('[handleAdvancedFilterSearch] 高级筛选条件:', searchResult)
      
      const { conditionMap, transformedCondition, searchParams, rawConditions } = searchResult

      this.advancedFilterConditions = conditionMap
      this.currentSearchParams = searchParams
      
      if (rawConditions && rawConditions.length > 0) {
        this.filterTags = rawConditions.map(c => {
          const property = this.allProperties.find(p => p.bk_property_id === c.field)
          return {
            id: c.field,
            property: property || {},
            propertyName: property?.bk_property_name || c.field,
            operator: c.operator,
            value: c.value
          }
        })
      } else {
        this.filterTags = []
      }

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
      this.filter.fuzzyQuery = false
      this.isUrlUpdateTriggered = true
      // 清除URL中的filter_adv和s参数，保持与原项目一致
      const query = {
        page: 1,
        limit: this.table.pagination.limit,
        filter_adv: '',
        s: ''
      }
      routerQuery.setAll(query)
      this.loadModelData()
    },
    handleImport() {
      this.$bkMessage({ message: '导入功能开发中', theme: 'info' })
    },
    handleExport() {
      this.$bkMessage({ message: '导出功能开发中', theme: 'info' })
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
        this.$bkMessage({ message: '更新失败，请稍后重试', theme: 'error' })
      } finally {
        this.batchUpdateFormLoading = false
      }
    },
    handleBatchUpdateDialogClose() {
      this.batchUpdateDialogVisible = false
      if (this.$refs.formMultipleRef) {
        this.$refs.formMultipleRef.reset()
      }
    },
    handleSelectionChange(selection) {
      this.selectedIds = selection.map(row => row.id)
    },
    handleDeleteSingle(row) {
      this.handleDelete([row.id])
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
      
      // 初始化表单默认值
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
          // 刷新列表
          await this.loadModelData(this.currentSearchParams)
        } else {
          this.$bkMessage({ message: result.message || '创建失败', theme: 'error' })
        }
      } catch (error) {
        console.error('Create instance error:', error)
        let errorMsg = '创建失败，请稍后重试'
        
        if (error.response && error.response.status === 400) {
          const errorData = error.response.data
          if (errorData && errorData.detail && errorData.detail.errors) {
            errorMsg = errorData.detail.errors.join('; ')
          } else if (errorData && errorData.detail) {
            errorMsg = errorData.detail
          }
        }
        
        this.$bkMessage({ message: errorMsg, theme: 'error' })
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
      this.syncStateToUrl()
      this.prevInstanceId = instance.id
      this.$router.push({
        name: 'ResourceInstanceDetails',
        params: { objId: this.objId, instId: instance.id }
      })
    },
    handlePageChange(page) {
      this.table.pagination.current = page
      this.syncStateToUrl({ keepSort: false, resetPage: true })
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
      this.loadModelData()
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

      const existingIndex = this.filterTags.findIndex(tag => tag.id === this.filter.field)

      if (this.filter.values && this.filter.values.length > 0) {
        const tagData = {
          id: property.bk_property_id,
          propertyName: property.bk_property_name,
          operator: (this.isEnumField || this.isBoolField) ? '$in' : ((this.isDateField || this.isTimeField) ? '$range' : (this.filter.fuzzyQuery ? '$regex' : '$eq')),
          value: [...this.filter.values],
          values: [...this.filter.values],
          property
        }
        if (existingIndex >= 0) {
          this.filterTags.splice(existingIndex, 1, tagData)
        } else {
          this.filterTags.push(tagData)
        }
      } else if (this.filter.value) {
        const tagData = {
          id: property.bk_property_id,
          propertyName: property.bk_property_name,
          operator: this.filter.fuzzyQuery ? '$regex' : '$eq',
          value: this.filter.value,
          property
        }
        if (existingIndex >= 0) {
          this.filterTags.splice(existingIndex, 1, tagData)
        } else {
          this.filterTags.push(tagData)
        }
      } else if (existingIndex >= 0) {
        this.filterTags.splice(existingIndex, 1)
      }
    },
    updateFilterTagsFromQuery() {
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
        this.filter.fuzzyQuery = false
      }
      this.table.pagination.current = 1
      this.currentSearchParams = null
      this.advancedFilterConditions = null
      this.syncStateToUrl({ resetPage: true })
      this.loadModelData()
    },
    handleClearAllFilterTags() {
      this.filterTags = []
      // 清除快速搜索输入框
      this.filter.value = ''
      this.filter.values = []
      this.filter.fuzzyQuery = false
      this.table.pagination.current = 1
      this.currentSearchParams = null
      this.advancedFilterConditions = null
      this.syncStateToUrl({ resetPage: true })
      this.loadModelData()
    },
    getColumnSortable(columnId) {
      const sortableTypes = ['int', 'float', 'date', 'time', 'enum', 'singlechar', 'longchar']
      const property = this.allProperties.find(p => p.bk_property_id === columnId)
      if (!property) return false
      return sortableTypes.includes(property.bk_property_type)
    },
    async handleApplyColumns(properties) {
      console.log('[Persistence] handleApplyColumns called, properties:', properties)
      this.columnsConfig.selected = properties.map(p => p.bk_property_id)
      console.log('[Persistence] columnsConfig.selected updated to:', this.columnsConfig.selected)
      this.columnsConfig.show = false
      this.setTableHeader()
      console.log('[Persistence] setTableHeader called after apply')
      
      // Save to both API and Vuex store for sharing
      try {
        console.log('[Persistence] Calling saveModelCustomColumns for objId:', this.objId, 'columns:', this.columnsConfig.selected)
        const saveResult = await userCustom.saveModelCustomColumns(this.objId, this.columnsConfig.selected)
        console.log('[Persistence] saveModelCustomColumns result:', saveResult)
        
        // Sync to Vuex store for sharing with association list
        const configKey = `${this.objId}_custom_table_columns`
        this.$store.dispatch('saveUsercustom', { [configKey]: this.columnsConfig.selected })
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
      console.log('[Persistence] handleResetColumns called, defaultColumns:', this.defaultColumns)
      this.columnsConfig.selected = [...this.defaultColumns]
      console.log('[Persistence] columnsConfig.selected reset to:', this.columnsConfig.selected)
      this.columnsConfig.show = false
      this.setTableHeader()
      console.log('[Persistence] setTableHeader called after reset')
      
      // Save to both API and Vuex store for sharing
      try {
        console.log('[Persistence] Calling saveModelCustomColumns (reset) for objId:', this.objId, 'columns:', this.columnsConfig.selected)
        const saveResult = await userCustom.saveModelCustomColumns(this.objId, this.columnsConfig.selected)
        console.log('[Persistence] saveModelCustomColumns (reset) result:', saveResult)
        
        // Sync to Vuex store for sharing with association list
        const configKey = `${this.objId}_custom_table_columns`
        this.$store.dispatch('saveUsercustom', { [configKey]: this.columnsConfig.selected })
        console.log('[Persistence] Synced reset to Vuex store:', configKey)
      } catch (e) {
        console.error('[Persistence] Failed to save columns config (reset):', e)
      }
      this.$bkMessage({ message: '已还原默认配置', theme: 'success' })
    },
    handleSidesliderHidden() {
      this.columnsConfig.show = false
    },
    goBackToResource() {
      console.log('[Persistence] goBackToResource called, navigating to /resource')
      this.$router.push({ name: 'Resource' })
    }
  }
}
</script>

<style lang="scss">
.general-model-layout {
  padding: 15px 20px 0;
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

    :deep(.bk-select) {
      height: 32px;
      min-height: 32px;
      box-sizing: border-box;
      
      .bk-select-name {
        font-size: 12px;
        height: 30px;
        line-height: 30px;
      }

      .bk-select-trigger {
        height: 32px;
        min-height: 32px;
        box-sizing: border-box;

        .bk-select-name {
          height: 30px;
          line-height: 30px;
        }
      }
    }
  }

  .filter-value {
    flex: 1;
    width: 320px;
    border-radius: 0 2px 2px 0;

    :deep(.bk-form-input) {
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
        font-size: 14px;
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
            border-radius: 0;
            font-size: 14px;
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

      :deep(.bk-select) {
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

.models-table {
  margin-top: 14px;
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

.filter-tag-wrapper ~ .models-table {
  margin-top: 0;
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
}

@media screen and (max-width: 768px) {
  .batch-update-info {
    padding: 12px 16px;
  }
}
</style>
