<template>
  <bk-sideslider
    transfer
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
        <bk-select class="select-wrapper status-select"
          v-model="relationStatusFilter"
          :clearable="false"
          transfer
          @selected="handleStatusFilterChange">
          <bk-option
            v-for="item in relationStatusOptions"
            :key="item.value"
            :id="item.value"
            :name="item.label">
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
        @page-limit-change="setCurrentLimit"
        @sort-change="handleSortChange">
        <bk-table-column type="selection" width="50"></bk-table-column>
        <bk-table-column
          v-for="column in table.header"
          :key="column.bk_property_id"
          :prop="column.bk_property_id"
          :label="column.bk_property_name"
          :sortable="column.sortable ? 'custom' : false">
          <template slot-scope="{ row }">
            {{ formatValue(row[column.bk_property_id], column) }}
          </template>
        </bk-table-column>
        <bk-table-column :label="'操作'" width="120">
          <template slot-scope="{ row }">
            <bk-link
              theme="primary"
              :disabled="rowActionType(row) === 'remove'"
              @click="beforeUpdate($event, getInstanceId(row), 'new')"
              v-if="rowActionType(row) === 'new'">
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
      <div class="confirm-tips" ref="confirmTips" v-show="confirm.id">
        <p class="tips-content">更新确认</p>
        <div class="tips-option">
          <bk-button class="tips-button" theme="primary" @click="confirmUpdate">确认</bk-button>
          <bk-button class="tips-button" theme="default" @click="cancelUpdate">取消</bk-button>
        </div>
      </div>
    </div>
  </bk-sideslider>
</template>

<script>
import { modelAPI, freezeList, cancelRequest, isCancelError } from '@/api/client'
import associationAPI from '@/api/association'
import associationPropertyFilter from './association-property-filter.vue'
import { formatPropertyValue } from '@/utils/property-value'

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
      models: [],
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
      // 新增关联弹框：关联状态筛选（全部/已关联/未关联），默认全部（行为同现状）
      relationStatusFilter: 'all',
      relationStatusOptions: [
        { value: 'all', label: '全部关联' },
        { value: 'associated', label: '已关联' },
        { value: 'not_associated', label: '未关联' }
      ],
      // 后端候选查询返回的已关联实例ID集合（用于操作列判定，替代纯前端 isAssociated）
      associatedIds: [],
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
          limit: 20,
          'limit-list': [10, 20, 50, 100, 500]
        }
      },
      tableKey: 0, // 用于强制表格重新渲染的 key
      // 关联创建弹框 table max-height：按 page size 动态计算（limit 行 + 表头），并以抽屉/内容区
      // 视口为上界（最高不超过视口、最低为 page size 行）。初始化为 400（与原固定值一致），
      // 真实值由 calcTableMaxHeight() 在数据重载后计算。
      tableMaxHeight: 400,
      // 新增关联弹框 table 排序状态：UI 列点击触发、API 联动排序。
      // sortField 为空表示不排序（后端按 id 默认序）；order 取值 'asc' | 'desc'。
      sortField: '',
      sortOrder: '',
      useServerPagination: false,
      confirm: {
        instance: null,
        id: null
      }
    }
  },
  computed: {
    isSource() {
      return this.currentOption.bk_obj_id === this.objId
    },
    multiple() {
      return this.currentOption.mapping !== '1:1'
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
  mounted() {
    // 关联创建弹框 table 高度随视口/page size 动态计算（与关联列表 table 逻辑一致）
    this.resizeHandler = () => this.calcTableMaxHeight()
    window.addEventListener('resize', this.resizeHandler)
    this.$nextTick(() => this.calcTableMaxHeight())
  },
  beforeDestroy() {
    // 解绑窗口缩放监听
    if (this.resizeHandler) {
      window.removeEventListener('resize', this.resizeHandler)
    }
    // 组件销毁时取消进行中的列表请求，释放大列表数据引用（GC）
    cancelRequest('assoc-list')
  },
  methods: {
    async initData() {
      console.log('[AssociationCreate] initData() started')
      console.log('[AssociationCreate] this.objId:', this.objId)
      
      try {
        await Promise.all([
          this.getAssociationType(),
          this.getObjAssociation(),
          this.loadModels()
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
        // 主线关联（bk_asst_id='bk_mainline'）由拓扑主线机制维护，不能出现在通用
        // 「新增关联」的选择项里 —— 对齐原项目规则：
        //   bk-cmdb/src/ui/src/views/model-topology/children/create-relation.vue
        //       }).filter(relation => relation.id !== 'bk_mainline')
        //   bk-cmdb/src/ui/src/views/model-manage/children/model-details/relation-detail.vue
        //       return this.relationList.filter(relation => relation.id !== 'bk_mainline')
        // 不过滤时，module→set 的主线边会被拼成「组成-集群」这类误导性选项
        // （src_des='组成' + set 的模型名='集群'）。
        const isNonMainline = item => item && item.bk_asst_id !== 'bk_mainline'
        this.associationObject = [...(dataAsSource || []), ...(dataAsTarget || [])].filter(isNonMainline)
        console.log('[AssociationCreate]   Combined:', this.associationObject.length, 'items')
      } catch (e) {
        console.error('[AssociationCreate] getObjAssociation error:', e)
        this.associationObject = []
      }
    },
    async loadModels() {
      try {
        const response = await modelAPI.listModels()
        if (response && response.models) {
          this.models = response.models
        }
      } catch (e) {
        console.error('[AssociationCreate] loadModels error:', e)
        this.models = []
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
          if (type && type.src_des) {
            labelPart1 = type.src_des
          } else if (type && type.bk_asst_name) {
            labelPart1 = type.bk_asst_name
          } else {
            labelPart1 = dstObjId
          }
        } else {
          if (type && type.dest_des) {
            labelPart1 = type.dest_des
          } else if (type && type.bk_asst_name) {
            labelPart1 = type.bk_asst_name
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
        // 切换关联类型时列已变化，清空上一轮的排序/状态筛选状态
        this.sortField = ''
        this.sortOrder = ''
        this.relationStatusFilter = 'all'
        this.associatedIds = []
        
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
        { bk_property_id: idKey, bk_property_name: 'ID', sortable: false },
        { bk_property_id: nameKey, bk_property_name: this.getInstanceNameLabel(), sortable: true }
      ]
      
      // 如果选择了属性且不是实例名，则添加到第三列（属性列同样支持排序）
      if (selectedPropertyId && selectedPropertyId !== nameKey) {
        const selectedProperty = this.allProperties.find(
          prop => prop.bk_property_id === selectedPropertyId
        )
        if (selectedProperty) {
          // 必须携带 bk_property_type 与 option，否则 formatPropertyValue 无法将枚举/列表类型
          // 的存储值（key）映射为显示名（name）。此前仅复制了 id/name/sortable，导致「模块类型」
          // 等枚举列直接渲染原始 key（如 "1"）而非「普通」。
          header.push({
            bk_property_id: selectedProperty.bk_property_id,
            bk_property_name: selectedProperty.bk_property_name,
            bk_property_type: selectedProperty.bk_property_type,
            option: selectedProperty.option,
            sortable: true
          })
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
        
        // 关键：当当前实例是目标端时，需要从源模型的分表查询
        // 与原项目逻辑一致：bk_obj_id 始终指向关联的源模型
        const queryParams = {
          bk_obj_id: isSource ? this.objId : option.bk_obj_id,
          condition: condition
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
    // 根据当前关联状态筛选，决定某行的操作类型（仅用于操作列渲染）：
    //  - 'new'     → 显示「关联」按钮
    //  - 'remove'  → 显示「取消关联」按钮
    // 全部关联(all)：沿用现有 isAssociated 判定（兼容临时关联/取消的 tempData 状态）；
    // 已关联(associated)：恒为取消；
    // 未关联(not_associated)：恒为关联。
    rowActionType(inst) {
      if (this.relationStatusFilter === 'associated') return 'remove'
      if (this.relationStatusFilter === 'not_associated') return 'new'
      // 全部：优先用后端候选查询返回的 associatedIds 判定，回退到原有 existInstAssociation 逻辑
      const instId = this.getInstanceId(inst)
      if (this.associatedIds.length > 0) {
        return this.associatedIds.map(String).includes(String(instId)) ? 'remove' : 'new'
      }
      return this.isAssociated(inst) ? 'remove' : 'new'
    },
    // 关联状态筛选下拉切换：重置到首页并重新拉取候选数据（联动 table）
    handleStatusFilterChange() {
      this.table.pagination.current = 1
      this.getInstance()
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
          } else if (this.filter.operator === '$gt') {
            conditions.push({
              field: this.filter.id,
              operator: 'greater_than',
              value: value
            })
          } else if (this.filter.operator === '$gte') {
            conditions.push({
              field: this.filter.id,
              operator: 'greater_or_equal',
              value: value
            })
          } else if (this.filter.operator === '$lt') {
            conditions.push({
              field: this.filter.id,
              operator: 'less_than',
              value: value
            })
          } else if (this.filter.operator === '$lte') {
            conditions.push({
              field: this.filter.id,
              operator: 'less_or_equal',
              value: value
            })
          }
        }
        
        const hasFilter = conditions.length > 0
        
        // 关联候选查询统一走后端 candidates 接口（支持 全部/已关联/未关联 筛选 + 条件 + 排序 + 分页 组合查询）。
        // 后端按 LIMIT/OFFSET 返回当前页实例 + total，前端直接进入「后端分页」展示，无需前端二次切片。
        const pageSize = this.table.pagination.limit
        const params = {
          obj_id: this.objId,
          inst_id: this.instId,
          asst_obj_id: this.currentAsstObj,
          bk_obj_asst_id: this.currentOption.bk_obj_asst_id,
          filter: this.relationStatusFilter,
          page: this.table.pagination.current,
          page_size: pageSize,
          conditions: hasFilter ? {
            condition: 'AND',
            rules: conditions
          } : undefined
        }
        // 联动排序：UI 触发的排序列/方向传给后端（后端 search_candidates 已支持 sort/order）
        if (this.sortField) {
          params.sort = this.sortField
          params.order = this.sortOrder || 'asc'
        }
        console.log('[AssociationCreate] candidates params:', params)

        const response = await associationAPI.searchCandidates(params,
          { requestId: 'assoc-list', cancelPrevious: true })
        console.log('[AssociationCreate] getInstance response:', response)

        const data = response.data || response
        const instances = data.instances || []
        const totalCount = data.total || 0
        // 已关联实例ID集合（用于操作列判定，替代纯前端 isAssociated 依赖 existInstAssociation）
        this.associatedIds = Array.isArray(data.associated_ids) ? data.associated_ids : []

        // 冻结大列表数据，跳过 Vue 对每行每列的深度响应式代理（与上游/实例列表一致，
        // 避免关联弹框内 >500 行数据在初始化/重载时产生大量响应式 getter 与内存开销）。
        // 关联列表为纯展示场景，行对象无需运行时写回，冻结安全。
        this.allInstances = freezeList(Array.isArray(instances) ? instances : [])
        this.table.pagination.count = totalCount
        console.log('[AssociationCreate] Loaded', this.allInstances.length, 'candidates (filter=', this.relationStatusFilter, '), total:', totalCount)
        this.displayInstances = this.allInstances
      } catch (e) {
        // 请求被取消（筛选/翻页/切换关联类型时的 cancelPrevious）属预期行为，静默忽略，
        // 不弹错误、不清空数据：由取代它的新请求负责重新填充 displayInstances（卸载/替换/GC 更干净）
        if (isCancelError(e)) {
          console.log('[AssociationCreate] 请求已取消（被新请求取代）')
          return
        }
        console.error('获取实例列表失败', e)
        this.allInstances = []
        this.displayInstances = []
      } finally {
        this.loading = false
        // 数据重载（含 page size 调整/翻页/搜索/切换关联类型）后，按当前页大小重算 table 高度
        this.$nextTick(() => this.calcTableMaxHeight())
      }
    },
    updateDisplayInstances() {
      let filtered = this.allInstances
      // 前端分页场景（≤100 全量加载）：按 UI 触发的排序列本地排序后再切片
      if (this.sortField) {
        filtered = this.sortInstances(filtered, this.sortField, this.sortOrder)
      }

      this.table.pagination.count = filtered.length

      const start = (this.table.pagination.current - 1) * this.table.pagination.limit
      const end = start + this.table.pagination.limit
      this.displayInstances = filtered.slice(start, end)
    },
    // 对实例数组按指定字段排序（用于前端分页的本地排序）。与后端 ORDER BY 语义对齐：
    // 数字字段按数值比大小，其余按字符串（中文 localeCompare）；空值恒排末尾。
    sortInstances(list, field, order) {
      const dir = order === 'desc' ? -1 : 1
      return [...list].sort((a, b) => {
        const va = a[field]
        const vb = b[field]
        const aEmpty = va === null || va === undefined || va === ''
        const bEmpty = vb === null || vb === undefined || vb === ''
        if (aEmpty && bEmpty) return 0
        if (aEmpty) return 1  // 空值恒排末尾
        if (bEmpty) return -1
        const na = Number(va)
        const nb = Number(vb)
        const bothNum = !Number.isNaN(na) && !Number.isNaN(nb) && va !== '' && vb !== ''
        if (bothNum) {
          return (na - nb) * dir
        }
        return String(va).localeCompare(String(vb), 'zh-CN') * dir
      })
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
    // 列排序触发（bk-table @sort-change 回调参数为 { column, prop, order }，
    // order 取值 'ascending' | 'descending' | null）。prop 为空或 order 为 null 表示取消排序，
    // 回到后端默认按 id 排序。排序后重置到首页并重新拉取数据（后端排序 / 前端分页本地排序）。
    handleSortChange({ prop, order }) {
      if (!prop || order === null) {
        this.sortField = ''
        this.sortOrder = ''
      } else {
        this.sortField = prop
        this.sortOrder = order === 'descending' ? 'desc' : 'asc'
      }
      this.table.pagination.current = 1
      this.getInstance()
    },
    async updateAssociation(instId, updateType = 'new') {
      try {
        const instIdNum = Number(instId)
        
        if (updateType === 'new') {
          await this.createAssociation(instId)
          this.tempData.push(instIdNum)
          this.$bkMessage({ message: '关联成功', theme: 'success' })
          this.hasChange = true
          await this.getExistInstAssociation()
          // 操作成功后重载候选列表：操作列随关联状态翻转（关联 -> 取消关联），
          // 并兼容当前 条件筛选 / 排序 / 分页 / 关联状态 上下文（getInstance 复用现有状态）
          await this.getInstance()
          
        } else if (updateType === 'remove') {
          const existInst = this.existInstAssociation.find(inst => {
            if (this.isSource) {
              return Number(inst.bk_asst_inst_id) === instIdNum
            }
            return Number(inst.bk_inst_id) === instIdNum
          })
          
          if (existInst) {
            await associationAPI.delete(this.objId, existInst.id)
            this.tempData = this.tempData.filter(id => Number(id) !== instIdNum)
            this.$bkMessage({ message: '取消关联成功', theme: 'success' })
            this.hasChange = true
            await this.getExistInstAssociation()
            // 重载候选列表：操作列翻转（取消关联 -> 关联）；not_associated 视图下该行会移出当前页
            await this.getInstance()
          } else {
            this.$bkMessage({ message: '未找到关联记录', theme: 'warning' })
          }
        } else if (updateType === 'update') {
          const oldInst = this.existInstAssociation[0]
          
          if (oldInst) {
            await associationAPI.delete(this.objId, oldInst.id)
          }
          
          this.tempData = []
          this.hasChange = true
          await this.createAssociation(instId)
          this.tempData = [instIdNum]
          this.$bkMessage({ message: '关联成功', theme: 'success' })
          await this.getExistInstAssociation()
          // 重载候选列表：替换关联后操作列/筛选视图同步刷新
          await this.getInstance()
        }
        
      } catch (e) {
        console.log(e)
        this.$handleApiError(e)
      } finally {
        this.getExistInstAssociation()
      }
    },
    async createAssociation(instId) {
      const isSource = this.currentOption.bk_obj_id === this.objId
      
      const params = {
        bk_obj_id: isSource ? this.objId : this.currentAsstObj,
        bk_inst_id: isSource ? this.instId : instId,
        bk_asst_obj_id: isSource ? this.currentAsstObj : this.objId,
        bk_asst_inst_id: isSource ? instId : this.instId,
        bk_obj_asst_id: this.currentOption.bk_obj_asst_id,
        bk_relation_type_id: this.currentOption.bk_asst_id
      }
      
      return await associationAPI.create(params)
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
      // 关闭弹框时取消进行中的列表请求，释放大列表数据引用，避免弹框隐藏后
      // 陈旧 500+ 行响应继续挂载/驻留（避免无谓的响应式重建与 GC 压力）
      cancelRequest('assoc-list')
      this.selectedRelationType = ''
      this.currentOption = {}
      this.currentAsstObj = ''
      this.tempData = []
      this.hasChange = false
      this.useServerPagination = false
      this.sortField = ''
      this.sortOrder = ''
      this.relationStatusFilter = 'all'
      this.associatedIds = []
      this.resetFilter()
      this.allInstances = []
      this.displayInstances = []
      this.table = {
        header: [],
        pagination: {
          count: 0,
          current: 1,
          limit: 20,
          'limit-list': [10, 20, 50, 100, 500]
        }
      }
    },
    beforeUpdate(event, instId, updateType = 'new') {
      if (this.multiple || !this.existInstAssociation.length) {
        this.updateAssociation(instId, updateType)
      } else {
        this.confirm.id = instId
        this.confirm.instance = this.$bkPopover(event.target, {
          content: this.$refs.confirmTips,
          theme: 'light',
          zIndex: 9999,
          width: 230,
          trigger: 'click',
          boundary: 'window',
          arrow: true,
          interactive: true,
          onHidden: () => {
            this.confirm.instance && this.confirm.instance.destroy()
            this.confirm.instance = null
          }
        })
        this.$nextTick(() => {
          this.confirm.instance.show()
        })
      }
    },
    confirmUpdate() {
      this.updateAssociation(this.confirm.id, 'update')
      this.cancelUpdate()
    },
    cancelUpdate() {
      this.confirm.instance && this.confirm.instance.hide()
    },
    formatValue(value, column) {
      if (value === null || value === undefined || value === '') {
        return '-'
      }
      // 复用全站 property-value.js 的 formatPropertyValue：枚举/多选/列表按 option 映射为显示名，
      // 避免直接用 column.option[value]（数组被当数字下标）导致返回对象并被渲染成 JSON 文本。
      return formatPropertyValue(value, column)
    },
    // 计算关联创建弹框 table 的 max-height：按 page size 动态得出「limit 行 + 表头」的目标高度，
    // 并以抽屉/内容主区视口为上界（最高不超过视口、最低不低于 page size 行），对齐上游
    // bk-cmdb association-list-table 固定 462（=10×42+42）与 create 弹窗 $APP.height-X 的抽屉思路，
    // 与关联列表组件 calcTableMaxHeight 逻辑保持一致。
    calcTableMaxHeight() {
      // 防御：关联创建弹框以 v-if 挂载/卸载，关闭弹框后其内部异步加载的 finally 仍可能
      // 触发 $nextTick(calcTableMaxHeight)；此时 this.$el 已失效（被销毁 / 退化为非 DOM
      // 对象），若不守卫会抛 "this.$el.querySelector is not a function"。
      if (this._isDestroyed || !this.$el || typeof this.$el.querySelector !== 'function') return
      // 行高：优先测量实际渲染的首行，避免硬编码导致「恰好 page size 行差 1px 触发内部滚动」
      let rowHeight = 43
      const tableEl = this.$el.querySelector('.new-association-table')
      if (tableEl) {
        const row = tableEl.querySelector('.bk-table-body-wrapper tr')
        if (row) {
          const h = row.getBoundingClientRect().height
          if (h > 0) { rowHeight = h }
        }
      }
      const HEADER_HEIGHT = 43
      // 目标高度：恰好容纳当前页 size 行 + 表头；page size 变化时自动跟随
      const limit = this.table.pagination.limit || 20
      const pageSizeHeight = limit * rowHeight + HEADER_HEIGHT
      // 视口上界：应用视口高度（抽屉/内容主区）减去顶部导航、面包屑、操作栏、分页等占用
      const viewport = (this.$APP && this.$APP.height) || window.innerHeight || 900
      const viewportCap = Math.max(200, viewport - 210)
      // 最高不超过视口、最低为 page size 行：max-height = min(视口上界, page size 行高)
      this.tableMaxHeight = Math.min(viewportCap, pageSizeHeight)
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

    /* 新增的「全部关联/已关联/未关联」状态筛选下拉：固定宽度 120px */
    .status-select {
      flex: 0 0 120px;
      width: 120px;
      min-width: 120px;
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

  .confirm-tips {
    padding: 9px;
    .tips-content {
      color: #313238;
      line-height: 20px;
    }
    .tips-option {
      margin: 12px 0 0 0;
      text-align: right;
      .tips-button {
        height: 26px;
        line-height: 24px;
        padding: 0 16px;
        min-width: 56px;
        font-size: 12px;
      }
    }
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

      /* 竖屏移动端：状态筛选下拉与关联类型下拉保持一致的盒子高度/对齐，
         清除桌面端遗留的 flex 收缩与固定宽度，避免 column 布局下被拉伸变形 */
      .status-select {
        flex: none;
        width: 100%;
        min-width: 0;
        align-self: stretch;
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
