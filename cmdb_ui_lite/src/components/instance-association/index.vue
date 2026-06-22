<template>
  <div class="instance-association" v-bkloading="{ isLoading: loading }">
    <div class="options clearfix">
      <div class="fl">
        <bk-button theme="primary" class="options-button" @click="handleAddAssociation">
          新增关联
        </bk-button>
      </div>
      <div class="fr" v-if="hasAssociations">
        <bk-checkbox
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
        <bk-table
          class="association-table"
          v-show="item.expanded"
          :data="item.displayInstances"
          :max-height="462"
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
          <bk-table-column label="操作" width="100">
            <template #default="{ row }">
              <bk-link theme="primary" @click.stop="handleRemoveAssociation(row, item)">
                取消关联
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
    }
  },
  created() {
    // 组件创建时，如果 associations 已有值，初始化 groupStates
    this.initGroupStates()
  },
  data() {
    return {
      pageSize: 10,
      groupStates: {},
      showCreateDialog: false,
      loading: false,
      cachedProperties: {},
      // 每个分组的当前页实例数据缓存
      groupInstances: {},
      expandAll: false,
      // 记录上次展开状态用于判断变化
      prevExpanded: {}
    }
  },
  computed: {
    hasAssociations() {
      return this.associationGroups.length > 0
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
          groupKey = `to_${asst.bk_asst_obj_id}`
          relatedObjId = asst.bk_asst_obj_id
          const desc = relation.src_des || relation.bk_relation_type_name
          relationTypeName = `${desc}-${this.getModelDisplayName(relatedObjId)}`
        } else {
          groupKey = `from_${asst.bk_obj_id}`
          relatedObjId = asst.bk_obj_id
          const desc = relation.dest_des || `被${this.getModelDisplayName(asst.bk_obj_id)}关联`
          relationTypeName = `${desc}-${this.getModelDisplayName(relatedObjId)}`
        }

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

      return result
    }
  },
  watch: {
    // 监听 associations 变化，初始化 groupStates 并触发数据加载
    associations: {
      immediate: true,
      handler(associations) {
        if (!associations || !associations.length) return
        
        // 初始化 groupStates
        const keys = this.initGroupStates()
        
        // 使用 nextTick 确保 associationGroups 更新后再触发数据加载
        this.$nextTick(() => {
          // 触发第一个分组的 getData
          if (keys.length > 0) {
            const group = this.associationGroups.find(g => g.key === keys[0])
            if (group && group.expanded) {
              this.getData(group)
            }
          }
        })
      }
    },
    // 监听 relations 变化，当 relations 加载完成后，重新初始化
    relations: {
      handler(relations) {
        if (!relations || !relations.length) return
        // 当 relations 可用时，确保 groupStates 正确初始化
        if (this.associations && this.associations.length > 0) {
          const keys = this.initGroupStates()
          this.$nextTick(() => {
            if (keys.length > 0) {
              const group = this.associationGroups.find(g => g.key === keys[0])
              if (group && group.expanded) {
                this.getData(group)
              }
            }
          })
        }
      }
    },
    // 监听 groupStates 变化，只在 expanded 从 false 变为 true 时触发 getData
    // 使用 prevExpanded 比较变化，避免 deep watch 中 oldStates 引用问题
    groupStates: {
      deep: true,
      handler(states) {
        if (!states) return
        Object.keys(states).forEach(key => {
          const state = states[key]
          const wasExpanded = this.prevExpanded[key] || false
          const isExpanded = state && state.expanded
          
          // 只在 expanded 从 false 变为 true 时触发（首次展开）
          if (isExpanded && !wasExpanded) {
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

        let groupKey
        if (isSource) {
          groupKey = `to_${asst.bk_asst_obj_id}`
        } else {
          groupKey = `from_${asst.bk_obj_id}`
        }
        
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
      
      return keys
    },
    handleExpandAll(expandAll) {
      this.expandAll = expandAll
      Object.keys(this.groupStates).forEach(key => {
        this.groupStates[key].expanded = expandAll
      })
      this.$forceUpdate()
    },
    getModelDisplayName(objId) {
      const modelNames = {
        'bk_slb': '负载均衡',
        'bk_slb_server': '后端服务器',
        'bk_slb_listener': '监听器',
        'bk_host': '主机',
        'biz': '业务'
      }
      return modelNames[objId] || objId
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
      this.loading = true
      try {
        await Promise.all([
          this.getProperties(item.relatedObjId),
          this.getInstances(item)
        ])
      } catch (err) {
        console.warn(`加载 ${item.relatedObjId} 数据失败:`, err)
      } finally {
        this.loading = false
      }
    },
    async getProperties(modelId) {
      if (this.cachedProperties[modelId]) {
        return
      }
      try {
        const attrResponse = await modelAPI.getModelAttributes(modelId)
        if (attrResponse && attrResponse.attributes) {
          const sortedAttrs = attrResponse.attributes
            .filter(p => p.bk_property_index !== -1 && !['id', 'bk_inst_id', 'bk_inst_name', 'bk_obj_id', 'bk_supplier_account', 'create_time', 'last_time', 'bk_operate_time'].includes(p.bk_property_id))
            .sort((a, b) => a.bk_property_index - b.bk_property_index)
            .slice(0, 5)
          this.$set(this.cachedProperties, modelId, sortedAttrs)
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
          this.getInstances(group)
        }
      })
    },
    getPaginationText(item) {
      const total = item.total
      return '第' + item.current + '/' + item.totalPages + '页，共' + total + '条'
    },
    formatValue(value, column, row) {
      if (value === null || value === undefined || value === '') {
        return '-'
      }
      if (column.bk_property_type === 'list' && Array.isArray(value)) {
        return value.join(', ')
      }
      if (column.bk_property_type === 'enum' && column.option) {
        return column.option[value] || value
      }
      if (Array.isArray(value)) {
        return value.map(v => (typeof v === 'object' && v !== null ? JSON.stringify(v) : v)).join(', ')
      }
      if (typeof value === 'object' && value !== null) {
        return JSON.stringify(value)
      }
      return String(value)
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
      const instId = row.bk_inst_id !== undefined ? row.bk_inst_id : row.id
      const objId = item.relatedObjId
      const modelName = this.getModelDisplayName(objId)
      const instanceName = row.bk_inst_name || row.name || 'ID: ' + instId

      showInstanceDetails({
        bk_obj_id: objId,
        bk_inst_id: instId,
        title: modelName + '-' + instanceName
      })
    },
    async handleRemoveAssociation(row, item) {
      const instIdNum = Number(row.bk_inst_id !== undefined ? row.bk_inst_id : row.id)

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

      this.$bkInfo({
        title: '确认取消关联',
        content: '确定要取消与 ' + (row.bk_inst_name || row.name || ('ID: ' + instIdNum)) + ' 的关联吗？',
        confirmFn: async () => {
          try {
            await associationAPI.delete(this.objId, association.id)
            this.$bkMessage({ message: '取消关联成功', theme: 'success' })
            // 清空缓存，重新加载
            this.groupInstances = {}
            this.$emit('association-change')
          } catch (e) {
            this.$bkMessage({ message: '取消关联失败: ' + (e.message || e), theme: 'error' })
          }
        }
      })
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