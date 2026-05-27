<template>
  <div class="instance-association" v-bkloading="{ isLoading: loading }">
    <div class="association-options">
      <div class="fl">
        <bk-button theme="primary" class="options-button" @click="handleAddAssociation">
          新增关联
        </bk-button>
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
          @row-click="(row, event, column) => handleRowClick(row, event, column, item)"
        >
          <bk-table-column
            v-for="(column, index) in item.columns"
            :key="column.bk_property_id"
            :prop="column.bk_property_id"
            :label="column.bk_property_name"
            :class-name="index === 0 ? 'is-highlight' : ''"
            :width="column.width || ''"
          >
            <template #default="{ row }">
              {{ formatValue(row[column.bk_property_id], column) }}
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
    },
    instancesMap: {
      type: Object,
      default: () => {}
    },
    propertiesMap: {
      type: Object,
      default: () => {}
    }
  },
  data () {
    return {
      pageSize: 10,
      groupStates: {},
      showCreateDialog: false,
      loading: false,
      loadedProperties: {} // 按需加载的属性缓存
    }
  },
  watch: {
    // 监听 propertiesMap 变化，重新构建列缓存
    propertiesMap: {
      handler(newMap) {
        console.log('[InstanceAssociation] propertiesMap 变化:', Object.keys(newMap))
        this.loading = true
        // 清空缓存，强制重新构建列
        this.loadedProperties = {}
        this.$nextTick(() => {
          this.loading = false
        })
      },
      deep: true
    },
    // 监听关联数据变化，重新构建分组
    associations: {
      handler() {
        console.log('[InstanceAssociation] associations 变化')
        this.loading = true
        // 清空分组状态
        this.groupStates = {}
        this.$nextTick(() => {
          this.loading = false
        })
      },
      deep: true
    }
  },
  computed: {
    hasAssociations () {
      return this.associationGroups.length > 0
    },
    associationGroups () {
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
          relationTypeName = relation.bk_relation_type_name
        } else {
          groupKey = `from_${asst.bk_obj_id}`
          relatedObjId = asst.bk_obj_id
          relationTypeName = `被${this.getModelDisplayName(asst.bk_obj_id)}关联`
        }
        
        if (!groupedMap.has(groupKey)) {
          const columns = this.getColumnsForModel(relatedObjId)
          
          groupedMap.set(groupKey, {
            key: groupKey,
            relationTypeName,
            relatedObjId,
            allInstances: [],
            columns: columns
          })
        }
        
        const group = groupedMap.get(groupKey)
        const targetInstId = isSource ? asst.bk_asst_inst_id : asst.bk_inst_id
        const instances = this.instancesMap[relatedObjId] || []
        
        const instance = instances.find(inst => inst.id === targetInstId)
        
        if (instance && !group.allInstances.find(i => i.id === instance.id)) {
          group.allInstances.push(instance)
        }
      })
      
      const result = []
      groupedMap.forEach((group, key) => {
        if (group.allInstances.length === 0) return
        
        const total = group.allInstances.length
        const totalPages = Math.ceil(total / this.pageSize)
        
        if (!this.groupStates[key]) {
          this.$set(this.groupStates, key, {
            expanded: true,
            current: 1
          })
        }
        
        const state = this.groupStates[key]
        const start = (state.current - 1) * this.pageSize
        const displayInstances = group.allInstances.slice(start, start + this.pageSize)
        
        result.push({
          ...group,
          total,
          totalPages,
          current: state.current,
          expanded: state.expanded,
          displayInstances
        })
      })
      
      return result
    }
  },
  methods: {
    getModelDisplayName (objId) {
      const modelNames = {
        'bk_slb': '负载均衡',
        'bk_slb_server': '后端服务器',
        'bk_slb_listener': '监听器'
      }
      return modelNames[objId] || objId
    },
    getColumnsForModel (objId) {
      console.log(`[InstanceAssociation] getColumnsForModel(${objId}) 被调用`)
      
      // 如果已经加载过，直接返回缓存
      if (this.loadedProperties[objId] && this.loadedProperties[objId].length > 0) {
        console.log(`[InstanceAssociation] ${objId} 使用已缓存的列配置`)
        return this.loadedProperties[objId]
      }
      
      // 检查是否有自定义列配置
      const customColumns = this.$store.getters.getCustomColumns(objId)
      
      console.log(`[InstanceAssociation] 获取 ${objId} 的列配置:`, {
        objId,
        customColumns,
        propertiesMapKeys: Object.keys(this.propertiesMap),
        hasPropertiesMap: !!this.propertiesMap[objId]
      })
      
      // 从 propertiesMap 获取属性
      const propsObj = this.propertiesMap[objId]
      const propsArray = (propsObj && propsObj.info) ? propsObj.info : (Array.isArray(propsObj) ? propsObj : [])
      
      console.log(`[InstanceAssociation] ${objId} 找到 ${propsArray.length} 个属性`)
      
      let orderedColumns = []
      
      if (customColumns.length > 0) {
        // 使用自定义列配置
        orderedColumns = customColumns
          .map(propId => propsArray.find(p => p.bk_property_id === propId))
          .filter(Boolean)
          .slice(0, 6)
        
        console.log(`[InstanceAssociation] ${objId} 使用自定义列:`, orderedColumns.map(c => c.bk_property_id))
      } else if (propsArray.length > 0) {
        // 使用默认列（按 bk_property_index 排序）
        orderedColumns = propsArray
          .filter(p => p.bk_property_index !== -1)
          .sort((a, b) => a.bk_property_index - b.bk_property_index)
          .slice(0, 6)
        
        console.log(`[InstanceAssociation] ${objId} 使用默认列:`, orderedColumns.map(c => c.bk_property_id))
      } else {
        // 如果没有任何属性，创建一个默认的 ID 列
        console.warn(`[InstanceAssociation] ${objId} 没有找到任何属性，使用默认列`)
        orderedColumns = [{
          bk_property_id: 'id',
          bk_property_name: 'ID',
          bk_property_type: 'int',
          bk_property_index: 0
        }]
      }
      
      // 缓存结果
      this.loadedProperties[objId] = orderedColumns
      
      console.log(`[InstanceAssociation] ${objId} 最终列:`, orderedColumns.map(c => `${c.bk_property_id}(${c.bk_property_name})`))
      
      return orderedColumns
    },
    toggleExpand (item) {
      const state = this.groupStates[item.key]
      if (state) {
        state.expanded = !state.expanded
      }
      this.$forceUpdate()
    },
    togglePage (item, step) {
      const newCurrent = item.current + step
      if (newCurrent < 1 || newCurrent > item.totalPages) {
        return
      }
      const state = this.groupStates[item.key]
      if (state) {
        state.current = newCurrent
      }
      this.$forceUpdate()
    },
    getPaginationText (item) {
      const current = item.current
      const total = item.total
      return `第${current}页，共${total}条`
    },
    formatValue (value, column) {
      if (value === null || value === undefined || value === '') {
        return '-'
      }
      if (column.bk_property_type === 'enum' && column.option) {
        return column.option[value] || value
      }
      return String(value)
    },
    handleAddAssociation () {
      this.showCreateDialog = true
    },
    handleAssociationCreated () {
      this.$emit('association-change')
    },
    handleRowClick (row, event, column, item) {
      const columnIndex = item.columns.findIndex(col => col.bk_property_id === column.property)
      
      if (columnIndex !== 0) {
        return
      }

      const modelName = this.getModelDisplayName(item.relatedObjId)
      const instanceName = row.bk_inst_name || row.name || `ID: ${row.id}`
      
      showInstanceDetails({
        bk_obj_id: item.relatedObjId,
        bk_inst_id: row.id,
        title: `${modelName}-${instanceName}`
      })
    },
    async handleRemoveAssociation (row, item) {
      try {
        const instIdNum = Number(row.id)
        
        const association = this.associations.find(asst => {
          const isSource = String(asst.bk_obj_id) === String(this.objId) &&
                           String(asst.bk_inst_id) === String(this.instId)
          const isTarget = String(asst.bk_asst_obj_id) === String(this.objId) &&
                          String(asst.bk_asst_inst_id) === String(this.instId)
          
          if (!isSource && !isTarget) return false
          
          const targetInstId = isSource ? asst.bk_asst_inst_id : asst.bk_inst_id
          const targetObjId = isSource ? asst.bk_asst_obj_id : asst.bk_obj_id
          
          return String(targetInstId) === String(instIdNum) &&
                 targetObjId === item.relatedObjId
        })

        if (!association) {
          this.$bkMessage({ message: '未找到关联记录', theme: 'warning' })
          return
        }

        this.$bkInfo({
          title: '确认取消关联',
          content: `确定要取消与 ${row.bk_inst_name || row.name || `ID: ${instIdNum}`} 的关联吗？`,
          confirmLoading: true,
          confirmFn: async () => {
            try {
              await associationAPI.delete(this.objId, association.id)
              this.$bkMessage({ message: '取消关联成功', theme: 'success' })
              this.$emit('association-change')
            } catch (e) {
              console.error('取消关联失败:', e)
              this.$bkMessage({ message: '取消关联失败: ' + (e.message || e), theme: 'error' })
              throw e
            }
          }
        })

      } catch (e) {
        console.error('取消关联失败:', e)
        this.$bkMessage({ message: '取消关联失败: ' + (e.message || e), theme: 'error' })
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.instance-association {
  height: 100%;
}

.association-options {
  padding: 12px 20px;
  font-size: 0;
  background: #fff;
  border-bottom: 1px solid #e7e9ef;

  .options-button {
    height: 32px;
    line-height: 30px;
    font-size: 14px;
  }
}

.association-list {
  padding-top: 0;

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

    :deep(.is-highlight) {
      color: #3a84ff;
    }

    :deep(.bk-table-body) {
      tr {
        cursor: pointer;
        &:hover td {
          background-color: #f5f7fa;
        }
      }
    }
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
