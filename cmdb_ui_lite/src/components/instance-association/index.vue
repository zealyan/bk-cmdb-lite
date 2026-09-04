<template>
  <div class="instance-association" v-bkloading="{ isLoading: rootLoading }">
    <div class="options clearfix">
      <div class="fl">
        <bk-button theme="primary" class="options-button" @click="handleAddAssociation">
          新增关联
        </bk-button>
      </div>
      <div class="fr">
        <!-- 显示空列表：勾选后加载当前实例所属模型的「全部关联关系定义」，
             无关联实例数据的关系也以空 table（0 条）呈现。样式/组件与「全部展开」一致。
             该多选框需常驻可见（即便当前无任何关联数据），否则无关联时用户无法勾选。 -->
        <bk-checkbox
          :size="16"
          class="options-checkbox"
          :value="showEmptyList"
          @change="handleShowEmptyList">
          <span class="checkbox-label">显示空列表</span>
        </bk-checkbox>
        <bk-checkbox
          v-if="hasAssociations"
          :size="16"
          class="options-checkbox"
          :value="expandAll"
          @change="handleExpandAll">
          <span class="checkbox-label">全部展开</span>
        </bk-checkbox>
      </div>
    </div>

    <div class="association-list">
      <div v-if="!hasAssociations" class="association-empty">
        <span>暂无关联关系</span>
      </div>
      <div
        v-for="item in associationGroups"
        :key="item.key"
        class="association-group"
      >
        <div class="group-info clearfix" @click="toggleExpand(item)">
          <div class="info-title fl">
            <i class="icon bk-icon icon-right-shape"
              :class="{ 'is-open': item.expanded }"
            ></i>
            <span class="title-text">{{ item.relationTypeName }}</span>
            <span class="title-count">({{ item.total }})</span>
          </div>
          <div class="info-pagination fr" v-if="item.totalPages > 1" @click.stop>
            <span class="pagination-info">
              {{ getPaginationText(item) }}
            </span>
            <span class="pagination-toggle">
              <i class="pagination-icon bk-icon icon-cc-arrow-down left"
                :class="{ disabled: item.current <= 1 }"
                @click="togglePage(item, -1)"
              ></i>
              <i class="pagination-icon bk-icon icon-cc-arrow-down right"
                :class="{ disabled: item.current >= item.totalPages }"
                @click="togglePage(item, 1)"
              ></i>
            </span>
          </div>
        </div>
        <!-- 不设置固定 max-height：page size=10，让 10 行以自然高度展开，
             高度与父级 body 内容一致，避免 table-body 内部再出现虚拟滚动条
             （长内容由页面整体滚动承载，而非 table 内部滚动）。 -->
        <bk-table
          class="association-table"
          v-show="item.expanded"
          :data="item.displayInstances"
          :max-height="tableMaxHeight"
          v-bkloading="{ isLoading: tableBodyLoading && groupLoading[item.key] }"
        >
          <bk-table-column
            v-for="(column, colIndex) in item.columns"
            :key="column.bk_property_id"
            :prop="column.bk_property_id"
            :label="column.bk_property_name"
            :show-overflow-tooltip="true"
          >
            <template #default="{ row }">
              <span
                v-if="colIndex === 0"
                class="cell-value clickable"
                @click="handleRowClick(row, $event, column, item)"
              >{{ formatValue(row[column.bk_property_id], column, row) }}</span>
              <span v-else>{{ formatValue(row[column.bk_property_id], column, row) }}</span>
            </template>
          </bk-table-column>
          <bk-table-column label="操作" width="160">
            <template #default="{ row }">
              <bk-link theme="primary" @click.stop="handleRemoveAssociation(row, item)">
                取消关联
              </bk-link>
              <!-- 详情：新建窗口打开所关联实例的资源详情页（#/resource/instance/{objId}/{instId}） -->
              <bk-link
                theme="primary"
                class="row-detail-link"
                @click.stop="handleOpenDetails(row, item)">
                详情
              </bk-link>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </div>

    <association-create
      :show.sync="showCreateDialog"
      :obj-id="objId"
      :inst-id="instId"
      @created="handleAssociationCreated"
    />
  </div>
</template>

<script>
import AssociationCreate from './association-create.vue'
import associationAPI from '@/api/association'
import { modelAPI } from '@/api/client'
import showInstanceDetails from '@/components/instance/details/index.js'
import { formatPropertyValue } from '@/utils/property-value'
import { associationGroupKey } from '@/utils/instance-association'

export default {
  name: 'InstanceAssociation',
  components: {
    AssociationCreate
  },
  props: {
    objId: {
      type: String,
      required: true
    },
    instId: {
      type: [String, Number],
      required: true
    },
    associations: {
      type: Array,
      default: () => []
    },
    relations: {
      type: Array,
      default: () => []
    },
    // 是否将「展开分组 / 翻页」的数据加载 loading 收敛到 table body 内（而非罩住整个组件）。
    // true → 仅对应分组表格显示 loading，tab 内容区其余部分（如「新增关联」按钮、其它分组）不受影响；
    // false（默认）→ 维持原行为：整个关联组件统一显示一个 loading 遮罩。
    // 资源实例详情关联 tab 传 true；业务拓扑关联 tab 保持默认 false，互不影响（工程隔离）。
    tableBodyLoading: {
      type: Boolean,
      default: false
    }
  },
  created() {
    // 组件创建时，检查数据是否已准备好
    this.tryInit()
  },
  mounted() {
    // mounted 时使用 nextTick 确保数据已更新，然后检查
    this.$nextTick(() => {
      this.tryInit()
    })
    // 关联表格高度随视口/page size 动态计算，监听窗口变化重算（与实例列表页 table 逻辑一致）
    this.resizeHandler = () => this.calcTableMaxHeight()
    window.addEventListener('resize', this.resizeHandler)
    this.$nextTick(() => this.calcTableMaxHeight())
  },
  beforeDestroy() {
    if (this.resizeHandler) {
      window.removeEventListener('resize', this.resizeHandler)
    }
  },
  data() {
    return {
      pageSize: 10,
      // 关联表格 max-height：按 page size 动态计算（pageSize 行 + 表头），并以抽屉/内容区
      // 视口为上界（最高不超过视口、最低为 page size 行）。初始化为 462（=10×42+42，对齐上游）。
      tableMaxHeight: 462,
      groupStates: {},
      showCreateDialog: false,
      cachedProperties: {},
      // 每个分组的独立加载态（按 group.key 索引），用于 table body 级 loading
      groupLoading: {},
      // 每个分组的当前页实例数据缓存
      groupInstances: {},
      expandAll: false,
      // 「显示空列表」开关：true 时把当前模型的全部关联关系定义都渲染为分组，
      // 没有关联实例数据的分组显示空 table（0 条）
      showEmptyList: false,
      // 当前模型的全部关联关系定义（findObjectAssociation 源端+目标端合并，懒加载一次）
      modelAssocDefs: [],
      // 关联类型定义（findAssociationType），用于生成空分组标题的 src_des / dest_des
      assocTypes: [],
      // 关联定义是否已加载，避免重复请求
      assocDefsLoaded: false,
      // 记录上次展开状态用于判断变化
      prevExpanded: {},
      // 是否正在初始化中，防止 watch 重复触发
      _isInitializing: false
    }
  },
  computed: {
    hasAssociations() {
      return this.associationGroups.length > 0
    },
    // 根级 loading：仅当「未开启 table body 级 loading」时生效（即业务拓扑 tab 的旧行为），
    // 用于展开/翻页时罩住整个关联组件。资源实例详情 tab 开启 tableBodyLoading 后，
    // 根级 loading 恒为 false，loading 只出现在对应分组的 table body 内。
    rootLoading() {
      if (this.tableBodyLoading) return false
      return Object.keys(this.groupLoading).some(key => this.groupLoading[key])
    },
    associationGroups() {
      const groupedMap = new Map()

      this.associations.forEach((asst) => {
        const isSource = String(asst.bk_obj_id) === String(this.objId) && String(asst.bk_inst_id) === String(this.instId)
        const isTarget = String(asst.bk_asst_obj_id) === String(this.objId) && String(asst.bk_asst_inst_id) === String(this.instId)

        if (!isSource && !isTarget) return

        const relation = this.relations.find(r => r.bk_relation_type_id === asst.bk_relation_type_id)
        if (!relation) return

        let groupKey
        let relatedObjId
        let relationTypeName

        if (isSource) {
          relatedObjId = asst.bk_asst_obj_id
          const desc = relation.src_des || relation.bk_relation_type_name
          relationTypeName = `${desc}-${this.getModelDisplayName(relatedObjId)}`
        } else {
          relatedObjId = asst.bk_obj_id
          const desc = relation.dest_des || `被${this.getModelDisplayName(asst.bk_obj_id)}关联`
          relationTypeName = `${desc}-${this.getModelDisplayName(relatedObjId)}`
        }
        // 分组唯一性 = 关联定义(bk_obj_asst_id) + 指向(源/目标)，统一走共享工具
        // associationGroupKey（@/utils/instance-association.js），与 emptyGroupDefs /
        // initGroupStates 保持一致，避免 key 规则再次漂移。
        groupKey = associationGroupKey(isSource, asst.bk_obj_asst_id, relatedObjId)

        if (!groupedMap.has(groupKey)) {
          groupedMap.set(groupKey, {
            key: groupKey,
            relationTypeName,
            relatedObjId,
            instanceIds: [],
            isSource
          })
        }

        const group = groupedMap.get(groupKey)
        const targetInstId = isSource ? asst.bk_asst_inst_id : asst.bk_inst_id
        
        if (!group.instanceIds.includes(Number(targetInstId))) {
          group.instanceIds.push(Number(targetInstId))
        }
      })

      const result = []
      groupedMap.forEach((group) => {
        const state = this.groupStates[group.key]
        if (!state) return

        const total = group.instanceIds.length
        const totalPages = Math.ceil(total / this.pageSize)
        
        // 计算当前页的 instanceIds
        const start = (state.current - 1) * this.pageSize
        const currentPageIds = group.instanceIds.slice(start, start + this.pageSize)
        
        // 从缓存中获取当前页的实例数据
        const cacheKey = `${group.key}_${state.current}`
        const displayInstances = this.groupInstances[cacheKey] || []

        result.push({
          ...group,
          total,
          totalPages,
          current: state.current,
          expanded: state.expanded,
          currentPageIds,
          displayInstances,
          columns: this.getColumnsForModel(group.relatedObjId)
        })
      })

      // 「显示空列表」开启时：补齐当前模型「有定义但当前实例无关联数据」的关系分组，
      // 以空 table（total=0）呈现；已有数据的分组不受影响（上面已生成）。
      if (this.showEmptyList) {
        this.emptyGroupDefs.forEach((eg) => {
          if (groupedMap.has(eg.key)) return
          const state = this.groupStates[eg.key]
          if (!state) return
          result.push({
            ...eg,
            instanceIds: [],
            total: 0,
            totalPages: 0,
            current: state.current,
            expanded: state.expanded,
            currentPageIds: [],
            displayInstances: [],
            columns: this.getColumnsForModel(eg.relatedObjId)
          })
        })
      }

      return result
    },
    // 由「模型全部关联定义」推导出的分组骨架（key/标题/关联模型/方向），
    // 与 associationGroups 的 key 规则保持一致：当前实例为源 → to_<目标模型>，为目标 → from_<源模型>
    emptyGroupDefs() {
      const list = []
      const seen = new Set()
      this.modelAssocDefs.forEach((def) => {
        const srcObjId = def.bk_obj_id
        const dstObjId = def.target_obj_id || def.bk_asst_obj_id
        if (!srcObjId || !dstObjId) return

        const isSource = String(srcObjId) === String(this.objId)
        const isTarget = String(dstObjId) === String(this.objId)
        if (!isSource && !isTarget) return

        const relatedObjId = isSource ? dstObjId : srcObjId
        // 与 associationGroups / initGroupStates 统一走共享工具 associationGroupKey，
        // 保持三处 key 规则一致（关联定义 + 指向）。
        const key = associationGroupKey(isSource, def.bk_obj_asst_id, relatedObjId)
        if (seen.has(key)) return
        seen.add(key)

        const type = this.assocTypes.find(t => t.bk_asst_id === def.bk_asst_id)
        let desc
        if (isSource) {
          desc = (type && (type.src_des || type.bk_asst_name)) || def.bk_asst_name || def.bk_asst_id
        } else {
          desc = (type && (type.dest_des || type.bk_asst_name)) || `被${this.getModelDisplayName(srcObjId)}关联`
        }
        list.push({
          key,
          relationTypeName: `${desc}-${this.getModelDisplayName(relatedObjId)}`,
          relatedObjId,
          isSource
        })
      })
      return list
    }
  },
  watch: {
    // 监听 groupStates 变化，只在 expanded 从 false 变为 true 时触发 getData
    // 如果正在初始化中（_isInitializing=true），则不触发
    groupStates: {
      deep: true,
      handler(states) {
        if (!states) return
        
        Object.keys(states).forEach(key => {
          const state = states[key]
          const wasExpanded = this.prevExpanded[key] || false
          const isExpanded = state && state.expanded
          
          // 只在 expanded 从 false 变为 true 时触发（首次展开），且不在初始化中
          if (isExpanded && !wasExpanded && !this._isInitializing) {
            const group = this.associationGroups.find(g => g.key === key)
            if (group) {
              this.getData(group)
            }
          }
          
          // 更新 prevExpanded
          this.$set(this.prevExpanded, key, isExpanded)
        })
      }
    }
  },
  methods: {
    // 尝试初始化（在 created/mounted 中调用）
    tryInit() {
      // 检查数据是否准备好
      if (!this.associations || !this.associations.length) return
      if (!this.relations || !this.relations.length) return
      
      // 检查是否已经初始化过
      if (Object.keys(this.groupStates).length > 0) return
      
      this.doInit()
    },
    // 执行初始化
    doInit() {
      // 标记为正在初始化，防止 watch 重复触发
      this._isInitializing = true

      // 确保模型中文名已就绪：searchClassificationsObjects 不含主线模型(set/module/biz)，
      // 用 loadModels（/api/v1/models，返回全部模型含 bk_obj_name）补全，使关联标题正确显示中文名
      if (!this.$store.getters['objectModelClassify/getModelById']('set')) {
        this.$store.dispatch('objectModelClassify/loadModels').catch(() => {})
      }
      

      const keys = this.initGroupStates()
      if (!keys || keys.length === 0) {
        this._isInitializing = false
        return
      }
      
      // 清除 prevExpanded，重新计算
      this.prevExpanded = {}
      
      this.$nextTick(() => {
        const group = this.associationGroups.find(g => g.key === keys[0])
        if (group && group.expanded) {
          this.getData(group)
        }
        // 初始化完成后，重置标志
        this._isInitializing = false
      })
    },
    // 初始化 groupStates
    initGroupStates() {
      if (!this.associations || !this.associations.length) return []
      
      // 清除实例缓存，强制重新加载
      this.groupInstances = {}
      
      const groupedMap = new Map()
      this.associations.forEach((asst) => {
        const isSource = String(asst.bk_obj_id) === String(this.objId) && String(asst.bk_inst_id) === String(this.instId)
        const isTarget = String(asst.bk_asst_obj_id) === String(this.objId) && String(asst.bk_asst_inst_id) === String(this.instId)
        if (!isSource && !isTarget) return

        // 与 associationGroups / emptyGroupDefs 统一走共享工具 associationGroupKey，
        // 否则 groupStates（展开/分页）与分组 key 错位，分页与展开态会异常。
        const groupKey = associationGroupKey(
          isSource,
          asst.bk_obj_asst_id,
          isSource ? asst.bk_asst_obj_id : asst.bk_obj_id
        )
        
        if (!groupedMap.has(groupKey)) {
          groupedMap.set(groupKey, true)
        }
      })
      
      // 初始化 groupStates（第一个 group 默认展开）
      const keys = Array.from(groupedMap.keys())
      keys.forEach((key, index) => {
        // 每次都重置展开状态（第一个默认为展开，其他默认为合并）
        this.$set(this.groupStates, key, {
          expanded: index === 0, // 第一个 group 默认展开
          current: 1
        })
        this.$set(this.prevExpanded, key, false)
      })

      // 关联数据重载（新增/取消关联后）会重建 groupStates，若「显示空列表」仍开启，
      // 需同步补回空分组的 state，否则空 table 会在数据刷新后消失
      if (this.showEmptyList) {
        this.emptyGroupDefs.forEach((eg) => {
          if (!this.groupStates[eg.key]) {
            this.$set(this.groupStates, eg.key, { expanded: false, current: 1 })
            this.$set(this.prevExpanded, eg.key, false)
          }
        })
      }

      return keys
    },
    handleExpandAll(expandAll) {
      this.expandAll = expandAll
      Object.keys(this.groupStates).forEach(key => {
        this.groupStates[key].expanded = expandAll
      })
      this.$forceUpdate()
    },
    // 「显示空列表」切换：
    // true  → 懒加载当前模型的全部关联定义（源端+目标端），为「无数据」的关系补建分组状态，
    //         UI 上出现多个 0 条数据的空 table；
    // false → 回到默认：仅展示有关联实例数据的分组，无数据的关系不显示。
    async handleShowEmptyList(value) {
      this.showEmptyList = value
      if (!value) {
        // 关闭时清理空分组的展开状态，避免残留影响「全部展开」的全选语义
        this.emptyGroupDefs.forEach((eg) => {
          if (this.groupStates[eg.key] && !this.hasRealData(eg.key)) {
            this.$delete(this.groupStates, eg.key)
            this.$delete(this.prevExpanded, eg.key)
          }
        })
        return
      }

      if (!this.assocDefsLoaded) {
        await this.loadModelAssocDefs()
      }
      // 为补齐的空分组建立 state（默认合并，避免一次性展开过多空表格）
      this.emptyGroupDefs.forEach((eg) => {
        if (!this.groupStates[eg.key]) {
          this.$set(this.groupStates, eg.key, { expanded: false, current: 1 })
          this.$set(this.prevExpanded, eg.key, false)
        }
      })
    },
    // 判断某分组 key 是否存在真实关联数据（用于关闭空列表时保留有数据的分组状态）
    hasRealData(key) {
      return this.associations.some((asst) => {
        const isSource = String(asst.bk_obj_id) === String(this.objId) && String(asst.bk_inst_id) === String(this.instId)
        const isTarget = String(asst.bk_asst_obj_id) === String(this.objId) && String(asst.bk_asst_inst_id) === String(this.instId)
        if (!isSource && !isTarget) return false
        // 与 associationGroups 等保持一致，统一走共享工具 associationGroupKey，
        // 否则空分组「有数据后移除」的判断会对不上分组 key。
        const k = associationGroupKey(
          isSource,
          asst.bk_obj_asst_id,
          isSource ? asst.bk_asst_obj_id : asst.bk_obj_id
        )
        return k === key
      })
    },
    // 加载当前模型的全部关联定义 + 关联类型（用于空分组标题），仅首次勾选时请求
    async loadModelAssocDefs() {
      try {
        // 无任何关联数据时不会走 doInit，模型中文名可能尚未就绪，这里补齐，
        // 保证空分组标题显示「集群/交换机」等中文名而非 obj_id
        if (!this.$store.getters['objectModelClassify/getModelById']('set')) {
          this.$store.dispatch('objectModelClassify/loadModels').catch(() => {})
        }
        const [defsAsSource, defsAsTarget, types] = await Promise.all([
          associationAPI.findObjectAssociation({ bk_obj_id: this.objId }),
          associationAPI.findObjectAssociation({ bk_asst_obj_id: this.objId }),
          associationAPI.findAssociationType()
        ])
        // 主线关联（bk_asst_id='bk_mainline'）不参与通用关联列表的「空分组」渲染，
        // 对齐原项目规则（create-relation.vue / relation-detail.vue 均 filter 掉 bk_mainline，
        // 且 relation.vue 把 bk_mainline 与 ispre 并列为不可编辑项）。
        // 不过滤时，开启「显示空列表」会把 module→set 主线边渲染成「组成-集群」空分组。
        const isNonMainline = item => item && item.bk_asst_id !== 'bk_mainline'
        this.modelAssocDefs = [...(defsAsSource || []), ...(defsAsTarget || [])].filter(isNonMainline)
        this.assocTypes = types || []
        this.assocDefsLoaded = true
      } catch (e) {
        console.error('[InstanceAssociation] 加载模型关联定义失败:', e)
        this.modelAssocDefs = []
        this.assocTypes = []
      }
    },
    getModelDisplayName(objId) {
      // 优先从全局模型 store 取中文名（data 来自 listModels，含主线 biz/set/module 与自定义模型，bk_obj_name 为标准中文名）
      const model = this.$store.getters['objectModelClassify/getModelById'](objId)
      if (model && model.bk_obj_name) {
        return model.bk_obj_name
      }
      // 兜底：内置主线模型标准中文名（searchClassificationsObjects 不含 set/module/biz 时仍能正确显示）
      const BUILTIN_NAMES = {
        biz: '业务',
        set: '集群',
        module: '模块',
        host: '主机',
        bk_biz_set_obj: '业务集',
        bk_switch: '交换机',
        bk_slb: '负载均衡',
        bk_slb_server: '后端服务器',
        bk_slb_listener: '监听器'
      }
      return BUILTIN_NAMES[objId] || objId
    },
    // 获取模型的主键字段（内置模型使用专用字段，自定义模型用 bk_inst_id）
    getIdFieldByModel(objId) {
      const idFieldMap = {
        'host': 'bk_host_id',
        'biz': 'bk_biz_id',
        'set': 'bk_set_id',
        'module': 'bk_module_id',
        'bk_biz_set_obj': 'bk_biz_set_id'
      }
      return idFieldMap[objId] || 'bk_inst_id'
    },
    // 获取模型名称字段（内置模型使用专用字段，自定义模型用 bk_inst_name）
    getNameFieldByModel(objId) {
      const nameFieldMap = {
        'host': 'bk_host_name',
        'biz': 'bk_biz_name',
        'set': 'bk_set_name',
        'module': 'bk_module_name',
        'bk_biz_set_obj': 'bk_biz_set_name'
      }
      return nameFieldMap[objId] || 'bk_inst_name'
    },
    // 从行数据中提取实例ID（兼容内置模型专用字段）
    getInstanceIdFromRow(row, objId) {
      const idField = this.getIdFieldByModel(objId)
      return row[idField] !== undefined ? row[idField] : (row.bk_inst_id !== undefined ? row.bk_inst_id : row.id)
    },
    // 从行数据中提取实例名称（兼容内置模型专用字段）
    getInstanceNameFromRow(row, objId) {
      const nameField = this.getNameFieldByModel(objId)
      return row[nameField] || row.bk_inst_name || row.name || ''
    },
    getColumnsForModel(objId) {
      if (this.cachedProperties[objId] && this.cachedProperties[objId].length > 0) {
        return this.cachedProperties[objId]
      }

      return [{
        bk_property_id: 'id',
        bk_property_name: 'ID',
        bk_property_type: 'int',
        bk_property_index: 0
      }]
    },
    async getData(item) {
      this.$set(this.groupLoading, item.key, true)
      try {
        await Promise.all([
          this.getProperties(item.relatedObjId),
          this.getInstances(item)
        ])
      } catch (err) {
        console.warn(`加载 ${item.relatedObjId} 数据失败:`, err)
      } finally {
        this.$set(this.groupLoading, item.key, false)
        // 数据渲染后重算表格高度（行高可能随数据/主题变化），保证 page size 行完整可见
        this.$nextTick(() => this.calcTableMaxHeight())
      }
    },
    // 计算关联表格 max-height：按 page size 动态得出「pageSize 行 + 表头」的目标高度，
    // 并以抽屉/内容主区视口为上界（最高不超过视口、最低不低于 page size 行），对齐上游
    // bk-cmdb association-list-table 固定 462（=10×42+42）与 create 弹窗 $APP.height-X 的抽屉思路。
    calcTableMaxHeight() {
      // 防御：组件已销毁（$el 被 Vue 回收 / 退化为非 DOM 对象）或 $el 非标准元素时直接返回，
      // 避免 tab 切换 / 节点刷新导致 instance-association 被 v-if 卸载后，其异步 finally 中
      // 的 $nextTick(calcTableMaxHeight) 在卸载后才回调，此时 this.$el 失效并抛
      // "this.$el.querySelector is not a function"。
      if (this._isDestroyed || !this.$el || typeof this.$el.querySelectorAll !== 'function') return
      // 行高：优先测量实际渲染的首行，避免硬编码导致「恰好 page size 行差 1px 触发内部滚动」
      let rowHeight = 43
      const tables = this.$el.querySelectorAll('.association-table')
      for (const t of tables) {
        if (t.offsetParent === null) continue // 未展开（display:none）跳过
        const row = t.querySelector('.bk-table-body-wrapper tr')
        if (row) {
          const h = row.getBoundingClientRect().height
          if (h > 0) { rowHeight = h; break }
        }
      }
      const HEADER_HEIGHT = 42
      // 目标高度：恰好容纳 page size 行 + 表头；page size 变化时自动跟随
      const pageSizeHeight = this.pageSize * rowHeight + HEADER_HEIGHT
      // 视口上界：应用视口高度（抽屉/内容主区）减去顶部导航、面包屑、操作栏、分页等占用
      const viewport = (this.$APP && this.$APP.height) || window.innerHeight || 900
      const viewportCap = Math.max(200, viewport - 210)
      // 最高不超过视口、最低为 page size 行：max-height = min(视口上界, page size 行高)
      this.tableMaxHeight = Math.min(viewportCap, pageSizeHeight)
    },
    async getProperties(modelId) {
      if (this.cachedProperties[modelId]) {
        return
      }
      try {
        const attrResponse = await modelAPI.getModelAttributes(modelId)
        if (attrResponse && attrResponse.attributes) {
          // 纯内部字段过滤（保留名称字段参与默认列筛选，对齐原项目关联列表首列即实例名）
          const internalFields = [
            'id', 'bk_inst_id', 'bk_obj_id', 'bk_supplier_account',
            'create_time', 'last_time', 'bk_operate_time',
            'bk_host_id',
            'bk_biz_id', 'bk_set_id', 'bk_module_id', 'bk_biz_set_id'
          ]
          const all = attrResponse.attributes
          // 实例名称字段强制置首列（set→bk_set_name / module→bk_module_name / 通用→bk_inst_name ...）
          const nameField = this.getNameFieldByModel(modelId)
          const nameAttr = all.find(p => p.bk_property_id === nameField)
          // 其余默认列：排除隐藏字段(-1)、内部字段、名称字段，按 bk_property_index 升序取前5
          const restAttrs = all
            .filter(p => p.bk_property_index !== -1
              && !internalFields.includes(p.bk_property_id)
              && p.bk_property_id !== nameField)
            .sort((a, b) => a.bk_property_index - b.bk_property_index)
            .slice(0, 5)
          const columns = []
          if (nameAttr) {
            columns.push(nameAttr)
          }
          columns.push(...restAttrs)
          this.$set(this.cachedProperties, modelId, columns)
        }
      } catch (err) {
        console.warn(`加载 ${modelId} 属性定义失败:`, err)
      }
    },
    async getInstances(item) {
      // 使用当前页的 instanceIds 进行查询（后端分页）
      const currentPageIds = item.currentPageIds
      if (!currentPageIds || !currentPageIds.length) {
        return
      }
      
      try {
        const response = await modelAPI.getInstancesByIds(item.relatedObjId, currentPageIds)
        if (response && response.instances) {
          // 缓存当前页的实例数据
          const cacheKey = `${item.key}_${item.current}`
          this.$set(this.groupInstances, cacheKey, response.instances)
        }
      } catch (err) {
        console.warn(`加载 ${item.relatedObjId} 实例失败:`, err)
      }
    },
    toggleExpand(item) {
      const state = this.groupStates[item.key]
      if (state) {
        state.expanded = !state.expanded
      }
      this.$forceUpdate()
    },
    togglePage(item, step) {
      const newCurrent = item.current + step
      if (newCurrent < 1 || newCurrent > item.totalPages) {
        return
      }
      const state = this.groupStates[item.key]
      if (state) {
        state.current = newCurrent
      }
      // 使用 $nextTick 确保 computed 更新后再加载
      this.$nextTick(() => {
        const group = this.associationGroups.find(g => g.key === item.key)
        if (group && state && state.expanded) {
          // 翻页加载态收敛到该分组 table body（tableBodyLoading 开启时仅 table 内显示 loading）
          this.$set(this.groupLoading, item.key, true)
          this.getInstances(group).finally(() => {
            this.$set(this.groupLoading, item.key, false)
            this.$nextTick(() => this.calcTableMaxHeight())
          })
        }
      })
    },
    getPaginationText(item) {
      const total = item.total
      return '第' + item.current + '/' + item.totalPages + '页，共' + total + '条'
    },
    formatValue(value, column, row) {
      // 复用全局属性值格式化工具，统一枚举 / 多选枚举 / 列表等类型的「键 → 显示名」映射。
      // 旧逻辑用 column.option[value]（数组按数字下标取值）会错误返回对象并被 Vue 渲染为 JSON 文本，
      // 全局实现用 buildOptionMap 把 [{id,name}] 正确转为 {id:name} 并按 id 查 name，覆盖数组/字符串/对象三种来源。
      return formatPropertyValue(value, column)
    },
    handleAddAssociation() {
      this.showCreateDialog = true
    },
    handleAssociationCreated() {
      // 清空缓存，重新加载
      this.groupInstances = {}
      this.$emit('association-change')
    },
    handleRowClick(row, event, column, item) {
      const objId = item.relatedObjId
      const instId = this.getInstanceIdFromRow(row, objId)
      const modelName = this.getModelDisplayName(objId)
      const instanceName = this.getInstanceNameFromRow(row, objId) || ('ID: ' + instId)

      showInstanceDetails({
        bk_obj_id: objId,
        bk_inst_id: instId,
        title: modelName + '-' + instanceName
      })
    },
    async handleRemoveAssociation(row, item) {
      const objId = item.relatedObjId
      const instIdNum = Number(this.getInstanceIdFromRow(row, objId))

      const association = this.associations.find(asst => {
        const isSource = String(asst.bk_obj_id) === String(this.objId) &&
                         String(asst.bk_inst_id) === String(this.instId)
        const isTarget = String(asst.bk_asst_obj_id) === String(this.objId) &&
                        String(asst.bk_asst_inst_id) === String(this.instId)

        if (!isSource && !isTarget) return false

        const targetInstId = isSource ? asst.bk_asst_inst_id : asst.bk_inst_id

        return Number(targetInstId) === Number(instIdNum) &&
               (isSource ? asst.bk_asst_obj_id : asst.bk_obj_id) === item.relatedObjId
      })

      if (!association) {
        this.$bkMessage({ message: '未找到关联记录', theme: 'warning' })
        return
      }

      const instanceName = this.getInstanceNameFromRow(row, objId) || ('ID: ' + instIdNum)
      this.$bkInfo({
        title: '确认取消关联',
        content: '确定要取消与 ' + instanceName + ' 的关联吗？',
        confirmFn: async () => {
          try {
            await associationAPI.delete(this.objId, association.id)
            this.$bkMessage({ message: '取消关联成功', theme: 'success' })
            // 清空缓存，重新加载
            this.groupInstances = {}
            this.$emit('association-change')
          } catch (e) {
            this.$handleApiError(e)
          }
        }
      })
    },
    // 操作列「详情」：新建窗口打开所关联实例的资源详情页。
    // 路由构造与 MENU_RESOURCE_INSTANCE_DETAILS 一致：#/resource/instance/{objId}/{instId}
    // （objId 取分组关联目标模型 item.relatedObjId，instId 取行实例主键）。
    handleOpenDetails(row, item) {
      const objId = item.relatedObjId
      const instId = this.getInstanceIdFromRow(row, objId)
      if (!objId || instId === undefined || instId === null || instId === '') {
        this.$bkMessage({ message: '无法获取关联实例信息', theme: 'warning' })
        return
      }
      const { href } = this.$router.resolve({ path: `/resource/instance/${objId}/${instId}` })
      window.open(href, '_blank')
    }
  }
}
</script>

<style lang="scss" scoped>
.instance-association {
  height: 100%;
}

.options {
  padding: 15px 0;
  font-size: 0;

  .options-button {
    height: 32px;
    line-height: 30px;
    font-size: 14px;
  }

  .options-checkbox {
    margin-right: 0;
    line-height: 32px;

    .checkbox-label {
      padding-left: 4px;
      font-size: 14px;
    }

    /* 「显示空列表」与右侧「全部展开」并排时留出间距（两者样式保持一致） */
    & + .options-checkbox {
      margin-left: 20px;
    }
  }
}

.association-list {
  .association-empty {
    padding: 60px 20px;
    text-align: center;
    color: #909399;
    background: #fafafa;
    border-radius: 4px;
  }
}

.association-group {
  margin-bottom: 12px;
  border: 1px solid #e7e9ef;
  border-radius: 2px 2px 0 0;
  overflow: hidden;
  margin-top: 0;

  .group-info {
    height: 42px;
    padding: 0 20px;
    background-color: #DCDEE5;
    cursor: pointer;
    line-height: 42px;
    font-size: 14px;

    &:hover {
      background: #d5d7dd;
    }

    .info-title {
      float: left;
      display: flex;
      align-items: center;

      .icon-right-shape {
        display: inline-block;
        vertical-align: middle;
        transition: transform 0.2s linear;
        margin-right: 8px;
        color: #8b8d95;

        &.is-open {
          transform: rotate(90deg);
        }
      }

      .title-text {
        color: #000;
      }

      .title-count {
        color: #8b8d95;
      }
    }

    .info-pagination {
      float: right;
      display: flex;
      align-items: center;
      color: #8b8d95;

      .pagination-toggle {
        margin-left: 10px;
        display: flex;
        align-items: center;

        .pagination-icon {
          font-size: 14px;
          color: #979BA5;
          cursor: pointer;

          &.disabled {
            color: #C4C6CC;
            cursor: not-allowed;
          }

          &.left {
            transform: rotate(90deg);
          }

          &.right {
            transform: rotate(-90deg);
          }

          &:hover:not(.disabled) {
            color: #3a84ff;
          }
        }
      }
    }
  }

  .association-table {
    width: 100%;
    border: none;
    border-radius: 0;

    :deep(.empty-block) {
      width: 100% !important;
    }

    :deep(.bk-table) {
      border: none;
    }

    :deep(.bk-table-header-wrapper),
    :deep(.bk-table-body-wrapper) {
      table {
        table-layout: fixed;
      }
    }

    :deep(.bk-table-body) {
      tr {
        &:hover td {
          background-color: #f5f7fa;
        }
      }
    }
  }
}

.cell-value.clickable {
  cursor: pointer;
  color: #3a84ff;
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

/* 操作列「详情」链接与「取消关联」之间留出间距，避免文字拥挤 */
.row-detail-link {
  margin-left: 8px;
}

.clearfix::after {
  content: '';
  display: table;
  clear: both;
}

.fl {
  float: left;
}

.fr {
  float: right;
}
</style>