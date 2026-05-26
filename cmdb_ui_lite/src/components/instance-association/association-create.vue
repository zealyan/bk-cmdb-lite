<template>
  <bk-sideslider
    :is-show.sync="sliderShow"
    :title="'新增关联'"
    :width="sliderWidth"
    @update:isShow="handleClose">
    <div slot="content" class="association-create-content">
      <div class="association-filter">
        <label class="filter-label">关联列表</label>
        <bk-select class="select-wrapper"
          v-model="selectedRelationType"
          placeholder="请选择关联类型"
          transfer
          @selected="handleSelectObj">
          <bk-option
            v-for="option in options"
            :key="option.bk_obj_asst_id"
            :id="option.bk_obj_asst_id"
            :name="option._label">
          </bk-option>
        </bk-select>
      </div>
      <div class="association-filter" v-if="currentOption.bk_obj_asst_id">
        <label class="filter-label">条件筛选</label>
        <div class="filter-group filter-group-property">
          <association-property-filter
            ref="filterComponent"
            :obj-id="currentAsstObj"
            :exclude-type="excludePropertyFilterTypes"
            @on-property-selected="handlePropertySelected"
            @on-operator-selected="handleOperatorSelected"
            @on-value-change="handleValueChange">
          </association-property-filter>
        </div>
        <bk-button theme="primary" class="btn-search" @click="search">搜索</bk-button>
      </div>
      <bk-table class="new-association-table"
        v-if="currentOption.bk_obj_asst_id"
        v-bkloading="{ isLoading: loading }"
        :key="tableKey"
        :data="displayInstances"
        :pagination="table.pagination"
        :max-height="tableMaxHeight"
        @page-change="setCurrentPage"
        @page-limit-change="setCurrentLimit">
        <bk-table-column type="selection" width="50"></bk-table-column>
        <bk-table-column
          v-for="column in table.header"
          :key="column.bk_property_id"
          :prop="column.bk_property_id"
          :label="column.bk_property_name">
          <template slot-scope="{ row }">
            {{ formatValue(row[column.bk_property_id], column) }}
          </template>
        </bk-table-column>
        <bk-table-column :label="'操作'" width="120">
          <template slot-scope="{ row }">
            <bk-link
              theme="primary"
              :disabled="isAssociated(row)"
              @click="updateAssociation(getInstanceId(row), 'new')"
              v-if="!isAssociated(row)">
              关联
            </bk-link>
            <bk-link
              theme="default"
              @click="updateAssociation(getInstanceId(row), 'remove')"
              v-else>
              取消关联
            </bk-link>
          </template>
        </bk-table-column>
        <div slot="empty">
          <div class="empty-text">暂无数据</div>
        </div>
      </bk-table>
    </div>
  </bk-sideslider>
</template>

<script>
import { modelAPI } from '@/api/client'
import associationAPI from '@/api/association'
import associationPropertyFilter from './association-property-filter.vue'
import modelIndex from '@/assets/api/index.json'

export default {
  name: 'AssociationCreate',
  components: {
    associationPropertyFilter
  },
  props: {
    show: {
      type: Boolean,
      default: false
    },
    objId: {
      type: String,
      required: true
    },
    instId: {
      type: [String, Number],
      required: true
    }
  },
  data() {
    return {
      sliderShow: false,
      models: modelIndex.models,
      associationType: [],
      associationObject: [],
      options: [],
      selectedRelationType: '',
      currentOption: {},
      currentAsstObj: '',
      existInstAssociation: [],
      tempData: [],
      hasChange: false,
      loading: false,
      filter: {
        id: '',
        operator: '$eq',
        value: ''
      },
      excludePropertyFilterTypes: ['inner_table', 'time', 'foreignkey'],
      displayColumns: [],
      allProperties: [], // 保存完整的属性列表
      allInstances: [],
      displayInstances: [],
      table: {
        header: [],
        pagination: {
          count: 0,
          current: 1,
          limit: 20
        }
      },
      tableKey: 0, // 用于强制表格重新渲染的 key
      useServerPagination: false,
    }
  },
  computed: {
    isSource() {
      return this.currentOption.bk_obj_id === this.objId
    },
    instanceIdKey() {
      const specialObj = {
        host: 'bk_host_id',
        biz: 'bk_biz_id',
        module: 'bk_module_id',
        set: 'bk_set_id'
      }
      if (specialObj[this.currentAsstObj]) {
        return specialObj[this.currentAsstObj]
      }
      return 'bk_inst_id'
    },
    sliderWidth() {
      return window.innerWidth < 640 ? '90%' : 640
    },
    tableMaxHeight() {
      const baseHeight = window.innerWidth < 640 ? 300 : 400
      return baseHeight
    }
  },
  watch: {
    show: {
      handler(val) {
        console.log('[AssociationCreate] show changed to:', val)
        this.sliderShow = val
        if (val) {
          console.log('[AssociationCreate] Calling initData(), objId:', this.objId)
          this.initData()
        }
      },
      immediate: true
    }
  },
  methods: {
    async initData() {
      console.log('[AssociationCreate] initData() started')
      console.log('[AssociationCreate] this.objId:', this.objId)
      console.log('[AssociationCreate] this.models:', this.models.length, 'models')
      
      try {
        await Promise.all([
          this.getAssociationType(),
          this.getObjAssociation()
        ])
        
        console.log('[AssociationCreate] After API calls:')
        console.log('[AssociationCreate]   associationType:', this.associationType.length, 'items')
        console.log('[AssociationCreate]   associationObject:', this.associationObject.length, 'items')
        
        this.setAssociationOptions()
        
        console.log('[AssociationCreate] After setAssociationOptions:')
        console.log('[AssociationCreate]   options:', this.options.length, 'items')
        console.log('[AssociationCreate]   options:', this.options)
      } catch (e) {
        console.error('[AssociationCreate] initData() error:', e)
      }
    },
    async getAssociationType() {
      try {
        console.log('[AssociationCreate] Calling findAssociationType API...')
        const data = await associationAPI.findAssociationType()
        console.log('[AssociationCreate] findAssociationType returned:', data.length, 'items')
        this.associationType = data
      } catch (e) {
        console.error('[AssociationCreate] getAssociationType error:', e)
        this.associationType = []
      }
    },
    async getObjAssociation() {
      try {
        console.log('[AssociationCreate] Calling findObjectAssociation API...')
        console.log('[AssociationCreate]   bk_obj_id condition:', this.objId)
        const [dataAsSource, dataAsTarget] = await Promise.all([
          associationAPI.findObjectAssociation({ bk_obj_id: this.objId }),
          associationAPI.findObjectAssociation({ bk_asst_obj_id: this.objId })
        ])
        console.log('[AssociationCreate] findObjectAssociation results:')
        console.log('[AssociationCreate]   As source:', dataAsSource?.length || 0, 'items')
        console.log('[AssociationCreate]   As target:', dataAsTarget?.length || 0, 'items')
        this.associationObject = [...(dataAsSource || []), ...(dataAsTarget || [])]
        console.log('[AssociationCreate]   Combined:', this.associationObject.length, 'items')
      } catch (e) {
        console.error('[AssociationCreate] getObjAssociation error:', e)
        this.associationObject = []
      }
    },
    setAssociationOptions() {
      console.log('[AssociationCreate] setAssociationOptions() called')
      console.log('[AssociationCreate]   this.associationObject:', this.associationObject)
      console.log('[AssociationCreate]   this.objId:', this.objId)
      
      if (!this.associationObject.length) {
        console.log('[AssociationCreate] No association objects, setting options to empty')
        this.options = []
        return
      }
      
      const options = this.associationObject.map((option) => {
        const srcObjId = option.bk_obj_id
        const dstObjId = option.target_obj_id
        
        const isSource = srcObjId === this.objId
        
        console.log('[AssociationCreate] Processing option:', option.bk_obj_asst_id, 'isSource:', isSource)
        
        const type = this.associationType.find(type => type.bk_asst_id === option.bk_asst_id)
        console.log('[AssociationCreate]   Found type:', type?.bk_asst_name)
        
        const model = this.models.find((model) => {
          if (isSource) {
            return model.bk_obj_id === dstObjId
          }
          return model.bk_obj_id === srcObjId
        })
        console.log('[AssociationCreate]   Found model:', model?.bk_obj_name)
        
        let labelPart1
        if (isSource) {
          if (type) {
            labelPart1 = type.src_des
          } else {
            labelPart1 = dstObjId
          }
        } else {
          if (type) {
            labelPart1 = type.dest_des
          } else {
            if (model) {
              labelPart1 = model.bk_obj_name
            } else {
              labelPart1 = srcObjId
            }
          }
        }
        let labelPart2
        if (model) {
          labelPart2 = model.bk_obj_name
        } else {
          if (isSource) {
            labelPart2 = dstObjId
          } else {
            labelPart2 = srcObjId
          }
        }
        const label = labelPart1 + "-" + labelPart2
        console.log('[AssociationCreate]   Generated label:', label)
        
        return {
          ...option,
          _label: label,
          _srcObjId: srcObjId,
          _dstObjId: dstObjId
        }
      })
      
      const uniqueLabels = [...new Set(options.map(option => option._label))]
      this.options = uniqueLabels.map(label => options.find(option => option._label === label))
      
      console.log('[AssociationCreate] Final options:', this.options.length, 'items')
      
      if (this.options.length > 0 && !this.selectedRelationType) {
        console.log('[AssociationCreate] Auto-selecting first option:', this.options[0].bk_obj_asst_id)
        this.selectedRelationType = this.options[0].bk_obj_asst_id
        this.$nextTick(() => {
          this.handleSelectObj(this.options[0].bk_obj_asst_id, this.options[0])
        })
      }
    },
    async handleSelectObj(asstId, option) {
      console.log('[AssociationCreate] handleSelectObj called with:', { asstId, option })
      
      // 1. 从 options 数组中找到完整的选项对象
      const fullOption = this.options.find(opt => opt.bk_obj_asst_id === asstId) || option
      
      if (!fullOption) {
        console.error('[AssociationCreate] fullOption is null/undefined')
        return
      }
      
      try {
        // 2. 先设置 currentOption，确保 v-if 条件成立
        this.currentOption = fullOption
        this.selectedRelationType = asstId
        
        // 3. 计算目标对象
        const srcObjId = fullOption._srcObjId || fullOption.bk_obj_id
        const dstObjId = fullOption._dstObjId || fullOption.target_obj_id
        const targetObj = srcObjId === this.objId ? dstObjId : srcObjId
        
        console.log('[AssociationCreate] Calculated srcObjId:', srcObjId, 'dstObjId:', dstObjId, 'targetObj:', targetObj)
        
        this.currentAsstObj = targetObj
        
        if (!this.currentAsstObj) {
          console.error('[AssociationCreate] currentAsstObj is empty, cannot load data')
          return
        }
        
        // 4. 重置状态
        this.table.pagination.current = 1
        this.table.pagination.count = 0
        this.table.list = []
        this.resetFilter()
        
        console.log('[AssociationCreate] Starting to load data...')
        this.loading = true
        
        // 5. 并行加载：表头 + 已存在关联
        await Promise.all([
          this.setTableHeader(),
          this.getExistInstAssociation()
        ])
        
        // 6. 最后加载实例列表（确保关联数据已加载）
        await this.getInstance()
        
        console.log('[AssociationCreate] Data load complete:', {
          tableHeaderLength: this.table.header.length,
          displayInstancesLength: this.displayInstances.length,
          existInstAssociationLength: this.existInstAssociation.length
        })
        
      } catch (e) {
        console.error('[AssociationCreate] handleSelectObj error:', e)
      } finally {
        this.loading = false
      }
    },
    async setTableHeader() {
      if (!this.currentAsstObj || this.currentAsstObj === '') {
        console.warn('[AssociationCreate] setTableHeader: currentAsstObj is empty, skipping')
        return
      }
      
      try {
        console.log('[AssociationCreate] setTableHeader: calling API for', this.currentAsstObj)
        const response = await modelAPI.getModelAttributes(this.currentAsstObj)
        const attrs = response.attributes || response || []
        console.log('[AssociationCreate] setTableHeader: got', attrs.length, 'attributes')
        this.displayColumns = attrs.slice(0, 5)
        this.allProperties = attrs // 保存完整的属性列表
        this.updateTableHeader() // 初始化表头
      } catch (e) {
        console.error('[AssociationCreate] setTableHeader error:', e)
        this.displayColumns = []
        this.allProperties = []
        this.table.header = []
      }
    },
    /**
     * 根据当前选择的属性更新表头
     * 规则：第一列 ID，第二列 实例名，第三列 当前选择的属性（如果选择的是实例名则不添加）
     */
    updateTableHeader() {
      const idKey = this.instanceIdKey
      const nameKey = this.getInstanceNameKey()
      const selectedPropertyId = this.filter.id
      
      const header = [
        { bk_property_id: idKey, bk_property_name: 'ID' },
        { bk_property_id: nameKey, bk_property_name: this.getInstanceNameLabel() }
      ]
      
      // 如果选择了属性且不是实例名，则添加到第三列
      if (selectedPropertyId && selectedPropertyId !== nameKey) {
        const selectedProperty = this.allProperties.find(
          prop => prop.bk_property_id === selectedPropertyId
        )
        if (selectedProperty) {
          header.push(selectedProperty)
        }
      }
      
      this.table.header = header
      
      // 1. 更新 tableKey 强制表格重新渲染
      this.tableKey++
      
      // 2. 强制刷新数据绑定，先清空再重新设置
      const tempInstances = [...this.displayInstances]
      this.displayInstances = []
      
      // 使用 nextTick 确保 DOM 更新后再恢复数据
      this.$nextTick(() => {
        this.displayInstances = tempInstances
        console.log('[AssociationCreate] updateTableHeader: header updated, table refreshed', this.table.header)
      })
    },
    getInstanceIdKey() {
      const specialObj = {
        host: 'bk_host_id',
        biz: 'bk_biz_id',
        module: 'bk_module_id',
        set: 'bk_set_id'
      }
      if (specialObj[this.currentAsstObj]) {
        return specialObj[this.currentAsstObj]
      }
      return 'bk_inst_id'
    },
    getInstanceNameKey() {
      const specialObj = {
        host: 'bk_host_innerip',
        biz: 'bk_biz_name',
        module: 'bk_module_name',
        set: 'bk_set_name'
      }
      if (specialObj[this.currentAsstObj]) {
        return specialObj[this.currentAsstObj]
      }
      return 'bk_inst_name'
    },
    getInstanceNameLabel() {
      const nameLabels = {
        bk_host_innerip: '内网IP',
        bk_biz_name: '业务名',
        bk_module_name: '模块名',
        bk_set_name: '集群名'
      }
      const nameKey = this.getInstanceNameKey()
      return nameLabels[nameKey] || '名称'
    },
    getInstanceId(row) {
      return row[this.instanceIdKey] || row.id || row.bk_inst_id
    },
    async getExistInstAssociation() {
      try {
        const option = this.currentOption
        const isSource = option.bk_obj_id === this.objId
        
        console.log('[AssociationCreate] getExistInstAssociation - Debug info:')
        console.log('  option.bk_obj_id:', option.bk_obj_id)
        console.log('  this.objId:', this.objId)
        console.log('  this.instId:', this.instId)
        console.log('  this.currentAsstObj:', this.currentAsstObj)
        console.log('  isSource:', isSource)
        console.log('  option.bk_obj_asst_id:', option.bk_obj_asst_id)
        console.log('  option.bk_asst_id:', option.bk_asst_id)
        
        // 按照原项目逻辑构建查询条件
        const condition = {
          bk_asst_id: option.bk_asst_id,
          bk_obj_asst_id: option.bk_obj_asst_id,
          bk_asst_obj_id: isSource ? this.currentAsstObj : this.objId
        }
        
        if (isSource) {
          condition.bk_inst_id = Number(this.instId)
        } else {
          condition.bk_asst_inst_id = Number(this.instId)
        }
        
        const queryParams = {
          bk_obj_id: isSource ? this.objId : undefined,
          condition: condition
        }
        
        if (!queryParams.bk_obj_id) {
          delete queryParams.bk_obj_id
        }
        
        console.log('[AssociationCreate] Final query params:', JSON.stringify(queryParams, null, 2))
        
        console.log('[AssociationCreate] Sending API request to /find/instassociation...')
        const result = await associationAPI.find(queryParams)
        console.log('[AssociationCreate] API response received:', result)
        console.log('[AssociationCreate] Response type:', typeof result)
        console.log('[AssociationCreate] Response is array:', Array.isArray(result))
        console.log('[AssociationCreate] Response has info:', result && result.info !== undefined)
        
        // 确保正确提取
        if (result && typeof result === 'object') {
          if (Array.isArray(result)) {
            this.existInstAssociation = result
          } else if (result.info !== undefined) {
            this.existInstAssociation = result.info
          } else {
            console.warn('[AssociationCreate] Response has no info field, setting empty array')
            this.existInstAssociation = []
          }
        } else {
          console.warn('[AssociationCreate] Response is not object, setting empty array')
          this.existInstAssociation = []
        }
        
        console.log('[AssociationCreate] existInstAssociation count:', this.existInstAssociation.length)
        console.log('[AssociationCreate] existInstAssociation full data:', this.existInstAssociation)
        
        // 验证查询结果中所有关联
        if (this.existInstAssociation.length > 0) {
          console.log('[AssociationCreate] All associations:')
          this.existInstAssociation.forEach((assoc, idx) => {
            console.log(`  [${idx}] bk_inst_id: ${assoc.bk_inst_id}, bk_asst_inst_id: ${assoc.bk_asst_inst_id}, type: ${typeof assoc.bk_asst_inst_id}`)
          })
        }
      } catch (e) {
        console.error('获取已存在关联失败', e)
        this.existInstAssociation = []
      }
    },
    isAssociated(inst) {
      const instId = this.getInstanceId(inst)
      const instIdNum = Number(instId)
      
      console.log('[AssociationCreate] isAssociated check:', {
        instId,
        instIdNum,
        isSource: this.isSource,
        existInstAssociationCount: this.existInstAssociation.length
      })
      
      if (this.existInstAssociation.length > 0) {
        console.log('[AssociationCreate] First association:', this.existInstAssociation[0])
      }
      
      const isAssoc = this.existInstAssociation.some((exist) => {
        if (this.isSource) {
          const targetInstId = Number(exist.bk_asst_inst_id)
          const match = targetInstId === instIdNum
          if (match) {
            console.log('[AssociationCreate] Match found in existInstAssociation!', {
              exist_bk_asst_inst_id: exist.bk_asst_inst_id,
              targetInstId,
              instIdNum
            })
          }
          return match
        } else {
          const sourceInstId = Number(exist.bk_inst_id)
          const match = sourceInstId === instIdNum
          if (match) {
            console.log('[AssociationCreate] Match found in existInstAssociation!', {
              exist_bk_inst_id: exist.bk_inst_id,
              sourceInstId,
              instIdNum
            })
          }
          return match
        }
      })
      
      const isInTempData = this.tempData.includes(instIdNum) || this.tempData.some(id => Number(id) === instIdNum)
      
      const result = isAssoc || isInTempData
      console.log('[AssociationCreate] isAssociated result:', {
        instId,
        isAssoc,
        isInTempData,
        tempData: this.tempData,
        finalResult: result
      })
      
      return result
    },
    handlePropertySelected(value, data) {
      this.filter.id = value
      // 选择属性后更新表头
      this.updateTableHeader()
    },
    handleOperatorSelected(value) {
      this.filter.operator = value
    },
    handleValueChange(value) {
      this.filter.value = value
    },
    resetFilter() {
      this.filter = {
        id: '',
        operator: '$eq',
        value: ''
      }
    },
    async getInstance() {
      if (!this.currentAsstObj || this.currentAsstObj === '') {
        console.warn('[AssociationCreate] getInstance: currentAsstObj is empty, skipping')
        return
      }
      
      try {
        this.loading = true
        const conditions = []
        
        if (this.filter.id && this.filter.value !== '') {
          let value = this.filter.value
          if (this.filter.operator === '$regex') {
            conditions.push({
              field: this.filter.id,
              operator: 'contains',
              value: value
            })
          } else if (this.filter.operator === '$eq') {
            conditions.push({
              field: this.filter.id,
              operator: 'equal',
              value: value
            })
          } else if (this.filter.operator === '$ne') {
            conditions.push({
              field: this.filter.id,
              operator: 'not_equal',
              value: value
            })
          } else if (this.filter.operator === '$in') {
            const values = value.split(',').map(v => v.trim()).filter(v => v)
            conditions.push({
              field: this.filter.id,
              operator: 'in',
              value: values
            })
          } else if (this.filter.operator === '$nin') {
            const values = value.split(',').map(v => v.trim()).filter(v => v)
            conditions.push({
              field: this.filter.id,
              operator: 'not_in',
              value: values
            })
          }
        }
        
        const hasFilter = conditions.length > 0
        
        // 智能分页策略：
        // 1. 如果有筛选条件，使用后端分页
        // 2. 如果没有筛选条件且当前显示第一页，先查询总数
        //    - 如果总数 <= 100，一次性加载所有数据，前端分页
        //    - 如果总数 > 100，启用后端分页
        // 3. 如果没有筛选条件但不是第一页，使用后端分页
        const isFirstPage = this.table.pagination.current === 1
        const pageSize = this.table.pagination.limit
        
        let params
        let useServerPagination = hasFilter || !isFirstPage || this.useServerPagination
        
        if (useServerPagination) {
          // 使用后端分页
          params = {
            page: this.table.pagination.current,
            page_size: pageSize,
            conditions: hasFilter ? {
              condition: 'AND',
              rules: conditions
            } : undefined
          }
          console.log('[AssociationCreate] Using server pagination, page:', params.page, 'pageSize:', params.page_size)
        } else {
          // 先查询总数
          params = {
            page: 1,
            page_size: 1,
            conditions: hasFilter ? {
              condition: 'AND',
              rules: conditions
            } : undefined
          }
        }
        
        const response = await modelAPI.searchInstances(this.currentAsstObj, params)
        console.log('[AssociationCreate] getInstance response:', response)
        
        const totalCount = response.total || response.count || 0
        
        if (useServerPagination) {
          // 后端分页
          const instances = response.instances || response.data || response.info || response || []
          this.allInstances = Array.isArray(instances) ? instances : []
          this.table.pagination.count = totalCount
          console.log('[AssociationCreate] Loaded', this.allInstances.length, 'instances (server pagination), total:', totalCount)
          this.displayInstances = this.allInstances
        } else {
          // 前端分页 - 检查总数决定策略
          if (totalCount <= 100) {
            // 数据量小，一次性加载所有数据
            console.log('[AssociationCreate] Total count:', totalCount, '<= 100, loading all data for client-side pagination')
            const allParams = {
              page: 1,
              page_size: 100,
              conditions: hasFilter ? {
                condition: 'AND',
                rules: conditions
              } : undefined
            }
            const allResponse = await modelAPI.searchInstances(this.currentAsstObj, allParams)
            const allInstances = allResponse.instances || allResponse.data || allResponse.info || allResponse || []
            this.allInstances = Array.isArray(allInstances) ? allInstances : []
            this.table.pagination.count = this.allInstances.length
            console.log('[AssociationCreate] Loaded all', this.allInstances.length, 'instances for client-side pagination')
            this.updateDisplayInstances()
          } else {
            // 数据量大，启用后端分页
            console.log('[AssociationCreate] Total count:', totalCount, '> 100, switching to server pagination')
            this.useServerPagination = true
            // 重新调用自己，这次会使用后端分页
            this.getInstance()
            return
          }
        }
      } catch (e) {
        console.error('获取实例列表失败', e)
        this.allInstances = []
        this.displayInstances = []
      } finally {
        this.loading = false
      }
    },
    updateDisplayInstances() {
      let filtered = this.allInstances
      
      this.table.pagination.count = filtered.length
      
      const start = (this.table.pagination.current - 1) * this.table.pagination.limit
      const end = start + this.table.pagination.limit
      this.displayInstances = filtered.slice(start, end)
    },
    search() {
      this.table.pagination.current = 1
      this.getInstance()
    },
    setCurrentPage(page) {
      this.table.pagination.current = page
      this.getInstance()
    },
    setCurrentLimit(limit) {
      this.table.pagination.limit = limit
      this.table.pagination.current = 1
      this.getInstance()
    },
    async updateAssociation(instId, updateType = 'new') {
      try {
        console.log('[AssociationCreate] ========== updateAssociation START ==========')
        console.log('[AssociationCreate] instId:', instId, 'updateType:', updateType)
        
        const instIdNum = Number(instId)
        
        if (updateType === 'new') {
          // 1. 创建关联
          console.log('[AssociationCreate] >>> Creating new association...')
          const result = await this.createAssociation(instId)
          console.log('[AssociationCreate] <<< createAssociation result:', result)
          
          // 2. 添加到临时数据（用于实时显示）
          this.tempData.push(instIdNum)
          console.log('[AssociationCreate] Added to tempData:', this.tempData)
          
          // 3. 显示成功提示
          this.$bkMessage({ message: '关联成功', theme: 'success' })
          
          // 4. 标记有变更
          this.hasChange = true
          
          // 5. 重新从后端加载关联列表（确保数据一致性）
          console.log('[AssociationCreate] Refreshing existInstAssociation from backend...')
          await this.getExistInstAssociation()
          console.log('[AssociationCreate] After refresh, existInstAssociation.length:', this.existInstAssociation.length)
          
        } else if (updateType === 'remove') {
          console.log('[AssociationCreate] >>> Removing association...')
          
          // 1. 找到要删除的关联记录
          const existInst = this.existInstAssociation.find(inst => {
            if (this.isSource) {
              return Number(inst.bk_asst_inst_id) === instIdNum
            }
            return Number(inst.bk_inst_id) === instIdNum
          })
          
          console.log('[AssociationCreate] Found association to delete:', existInst)
          
          if (existInst) {
            // 2. 删除关联
            console.log('[AssociationCreate] Deleting association ID:', existInst.id)
            await associationAPI.delete(this.objId, existInst.id)
            
            // 3. 从临时数据中移除
            this.tempData = this.tempData.filter(id => Number(id) !== instIdNum)
            console.log('[AssociationCreate] Removed from tempData, current tempData:', this.tempData)
            
            // 4. 显示成功提示
            this.$bkMessage({ message: '取消关联成功', theme: 'success' })
            
            // 5. 标记有变更
            this.hasChange = true
            
            // 6. 重新从后端加载关联列表
            console.log('[AssociationCreate] Refreshing existInstAssociation from backend...')
            await this.getExistInstAssociation()
            console.log('[AssociationCreate] After refresh, existInstAssociation.length:', this.existInstAssociation.length)
          } else {
            console.warn('[AssociationCreate] No existing association found')
            this.$bkMessage({ message: '未找到关联记录', theme: 'warning' })
          }
        }
        
        console.log('[AssociationCreate] ========== updateAssociation END ==========')
        
      } catch (e) {
        console.error('[AssociationCreate] updateAssociation error:', e)
        this.$bkMessage({ message: '操作失败: ' + (e.message || e), theme: 'error' })
        throw e
      }
    },
    async createAssociation(instId) {
      try {
        const isSource = this.currentOption.bk_obj_id === this.objId
        
        console.log('[AssociationCreate] ========== createAssociation ==========')
        console.log('[AssociationCreate] isSource:', isSource)
        console.log('[AssociationCreate] this.objId:', this.objId)
        console.log('[AssociationCreate] this.instId:', this.instId)
        console.log('[AssociationCreate] instId (target):', instId)
        console.log('[AssociationCreate] this.currentAsstObj:', this.currentAsstObj)
        console.log('[AssociationCreate] this.currentOption.bk_obj_asst_id:', this.currentOption.bk_obj_asst_id)
        console.log('[AssociationCreate] this.currentOption.bk_asst_id:', this.currentOption.bk_asst_id)
        
        const params = {
          bk_obj_id: isSource ? this.objId : this.currentAsstObj,
          bk_inst_id: isSource ? this.instId : instId,
          bk_asst_obj_id: isSource ? this.currentAsstObj : this.objId,
          bk_asst_inst_id: isSource ? instId : this.instId,
          bk_obj_asst_id: this.currentOption.bk_obj_asst_id,
          bk_relation_type_id: this.currentOption.bk_asst_id
        }
        
        console.log('[AssociationCreate] Final params:', JSON.stringify(params, null, 2))
        
        // 验证参数
        if (!params.bk_obj_id || !params.bk_asst_obj_id || !params.bk_obj_asst_id) {
          console.error('[AssociationCreate] ❌ Invalid params! Missing required fields')
          throw new Error('缺少必需参数')
        }
        
        console.log('[AssociationCreate] Sending request to create association...')
        console.log('[AssociationCreate] Source:', params.bk_obj_id, 'instance', params.bk_inst_id)
        console.log('[AssociationCreate] Target:', params.bk_asst_obj_id, 'instance', params.bk_asst_inst_id)
        
        const result = await associationAPI.create(params)
        console.log('[AssociationCreate] ✅ createAssociation result:', result)
        
        if (result && result.id) {
          console.log('[AssociationCreate] ✅ Created association ID:', result.id)
        } else if (result && result.info && result.info.id) {
          console.log('[AssociationCreate] ✅ Created association ID (from info):', result.info.id)
        } else {
          console.warn('[AssociationCreate] ⚠️ No ID returned in result:', result)
        }
        
        console.log('[AssociationCreate] ========== createAssociation END ==========')
        
        return result
      } catch (e) {
        console.error('[AssociationCreate] ❌ createAssociation error:', e)
        throw e
      }
    },
    handleClose() {
      this.sliderShow = false
      this.$emit('update:show', false)
      if (this.hasChange) {
        this.$emit('created')
      }
      this.resetData()
    },
    resetData() {
      this.selectedRelationType = ''
      this.currentOption = {}
      this.currentAsstObj = ''
      this.tempData = []
      this.hasChange = false
      this.useServerPagination = false
      this.resetFilter()
      this.allInstances = []
      this.displayInstances = []
      this.table = {
        header: [],
        pagination: {
          count: 0,
          current: 1,
          limit: 20
        }
      }
    },
    formatValue(value, column) {
      if (value === null || value === undefined || value === '') {
        return '-'
      }
      if (column.bk_property_type === 'enum' && column.option) {
        return column.option[value] || value
      }
      return String(value)
    }
  }
}
</script>

<style lang="scss" scoped>
.association-create-content {
  padding: 20px;
  box-sizing: border-box;

  .association-filter {
    margin-bottom: 20px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;

    .filter-label {
      width: auto;
      min-width: 80px;
      line-height: 32px;
      color: #63656e;
      font-weight: 500;
    }

    .select-wrapper {
      flex: 1;
      min-width: 200px;
    }

    .filter-group {
      flex: 1;
      min-width: 200px;
    }

    .btn-search {
      flex-shrink: 0;
      align-self: center;
    }
  }

  .new-association-table {
    margin-top: 20px;
  }
  
  .empty-text {
    color: #63656e;
    padding: 20px 0;
  }
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .association-create-content {
    padding: 16px;

    .association-filter {
      flex-direction: column;
      align-items: stretch;
      gap: 16px;

      .filter-label {
        min-width: auto;
        line-height: 1.5;
        margin-bottom: 4px;
      }

      .select-wrapper {
        width: 100%;
      }

      .filter-group {
        width: 100%;
        position: relative;
        z-index: 1;
      }

      .btn-search {
        width: 100%;
        margin-left: 0;
        align-self: stretch;
        position: relative;
        z-index: 10;
      }
    }
  }
}

@media screen and (max-width: 480px) {
  .association-create-content {
    padding: 12px;

    .association-filter {
      .filter-label {
        font-size: 14px;
      }
    }
  }
}
</style>
