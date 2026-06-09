<template>
  <div class="instance-association" v-bkloading="{ isLoading: loading }">
    <div class="options clearfix">
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
            <span class="title-count">({{ item.total })</span>
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
            v-for="column in item.columns"
            :key="column.bk_property_id"
            :prop="column.bk_property_id"
            :label="column.bk_property_name"
            :show-overflow-tooltip="true"
          >
            <template #default="{ row }">
              <span class="cell-value">{{ formatValue(row[column.bk_property_id], column, row) }}</span>
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

    <!-- 关联实例详情抽屉
    -->
    <bk-sideslider
      :is-show.sync="showDetailsSlider"
      :title="detailsTitle"
      :width="800
      transfer
      @update:isShow="handleCloseDetails"
    >
      <div slot="content" class="details-content" v-bkloading="{ isLoading: detailsLoading }">
        <div v-if="!detailsLoading" :key="detailsInstance.bk_inst_id">
          <!-- 基础信息
          -->
          <div class="detail-section">
            <div class="detail-title">基础信息</div>
            <ul class="property-list clearfix">
              <li class="property-item fl">
              <span class="property-name">实例ID</span>
              <span class="property-value">{{ detailsInstance.id }}</span>
            </li>
            <li class="property-item fl">
              <span class="property-name">蓝鲸ID</span>
              <span class="property-value">{{ detailsInstance.bk_inst_id }}</span>
            </li>
            <li class="property-item fl">
              <span class="property-name">实例名称</span>
              <span class="property-value">{{ detailsInstance.bk_inst_name }}</span>
            </li>
            <li class="property-item fl">
              <span class="property-name">所属模型</span>
              <span class="property-value">{{ getModelDisplayName(detailsObjId) }}</span>
            </li>
          </div>

          <!-- 自定义属性
          -->
          <div class="detail-section" v-if="detailColumns.length">
            <div class="detail-title">详细信息</div>
            <ul class="property-list clearfix">
              <li class="property-item fl" v-for="column in detailColumns" :key="column.bk_property_id">
                <span class="property-name">{{ column.bk_property_name }}</span>
                <span class="property-value">
                  {{ formatValue(detailsInstance[column.bk_property_id], column, detailsInstance) }}
                </span>
              </li>
            </ul>
          </div>
        </div>
        <div v-else-if="!detailsLoading" class="details-empty">
          正在加载实例详情...
        </div>
        <div v-else class="details-empty">
          未找到实例信息
        </div>
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import AssociationCreate from './association-create.vue'
import associationAPI from '@/api/association'
import instanceAPI from '@/api/instance'

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
  data() {
    return {
      pageSize: 10,
      groupStates: {},
      showCreateDialog: false,
      loading: false,
      cachedProperties: {},
      // 抽屉相关
      showDetailsSlider: false,
      detailsLoading: false,
      detailsTitle: '',
      detailsObjId: '',
      detailsInstance: {},
      detailColumns: []
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
          relationTypeName = relation.bk_relation_type_name || relation.bk_obj_asst_name || asst.bk_asst_obj_id
        } else {
          groupKey = `from_${asst.bk_obj_id}`
          relatedObjId = asst.bk_obj_id
          relationTypeName = `被${this.getModelDisplayName(asst.bk_obj_id)}关联`
        }

        if (!groupedMap.has(groupKey)) {
          groupedMap.set(groupKey, {
            key: groupKey,
            relationTypeName,
            relatedObjId,
            allInstances: [],
            columns: this.getColumnsForModel(relatedObjId)
          })
        }

        const group = groupedMap.get(groupKey)
        const targetInstId = isSource ? asst.bk_asst_inst_id : asst.bk_inst_id
        const instances = this.instancesMap[relatedObjId] || []

        const instance = instances.find(inst => {
          const instMatch = inst.bk_inst_id !== undefined ? inst.bk_inst_id : inst.id
          return Number(instMatch) === Number(targetInstId)
        })

        if (instance) {
          const existingId = instance.bk_inst_id !== undefined ? instance.bk_inst_id : instance.id
          if (!group.allInstances.find(i => {
            const iId = i.bk_inst_id !== undefined ? i.bk_inst_id : i.id
            return Number(iId) === Number(existingId)
          })) {
            group.allInstances.push(instance)
          }
        }
      })

      const result = []
      groupedMap.forEach((group) => {
        if (group.allInstances.length === 0) return

        const total = group.allInstances.length
        const totalPages = Math.ceil(total / this.pageSize)

        if (!this.groupStates[group.key]) {
          this.$set(this.groupStates, group.key, {
            expanded: true,
            current: 1
          })
        }

        const state = this.groupStates[group.key]
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

      const propsObj = this.propertiesMap[objId]
      const propsArray = (propsObj && propsObj.info) ? propsObj.info : (Array.isArray(propsObj) ? propsObj : [])

      let orderedColumns = []

      if (propsArray.length > 0) {
        orderedColumns = propsArray
          .filter(p => p.bk_property_index !== -1 && !['id', 'bk_inst_id', 'bk_inst_name', 'bk_obj_id', 'bk_supplier_account', 'create_time', 'last_time', 'bk_operate_time'].includes(p.bk_property_id))
          .sort((a, b) => a.bk_property_index - b.bk_property_index)
          .slice(0, 5)
      } else {
        orderedColumns = [{
          bk_property_id: 'bk_inst_name',
          bk_property_name: '实例名称',
          bk_property_type: 'string',
          bk_property_index: 0
        }]
      }

      this.cachedProperties[objId] = orderedColumns
      return orderedColumns
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
      this.$forceUpdate()
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
      this.$emit('association-change')
    },
    async handleRowClick(row, event, column, item) {
      // 使用 bk_inst_id 作为标准实例ID（与原项目一致
      const instId = row.bk_inst_id !== undefined ? row.bk_inst_id : row.id
      const objId = item.relatedObjId

      const displayName = row.bk_inst_name || row.name || 'ID: ' + instId
      this.detailsTitle = this.getModelDisplayName(objId) + ' - ' + displayName
      this.detailsObjId = objId
      this.showDetailsSlider = true
      this.detailsLoading = true
      this.detailsInstance = {}

      try {
        const instance = await instanceAPI.getInstanceDetails(objId, instId)
        if (instance) {
          this.detailsInstance = instance
          this.detailColumns = this.getColumnsForModel(objId)
        } else {
          this.detailsInstance = row
          this.detailColumns = item.columns
        }
      } catch (e) {
        console.error('加载实例详情失败:', e)
        this.detailsInstance = row
        this.detailColumns = item.columns
      } finally {
        this.detailsLoading = false
      }
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
            this.$emit('association-change')
          } catch (e) {
            console.error('取消关联失败:', e)
            this.$bkMessage({ message: '取消关联失败: ' + (e.message || e), theme: 'error' })
          }
        }
      })
    },
    handleCloseDetails(val) {
      this.showDetailsSlider = val
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

/* ========== 实例详情抽屉样式
  */
.details-content {
  padding: 20px;
  min-height: 100%;
}

.detail-section {
  margin-bottom: 20px;
}

.detail-title {
  font-size: 14px;
  font-weight: bold;
  color: #333;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e7e9ef;
}

.property-list {
  padding: 0;
  margin: 0;
}

.property-item {
  list-style: none;
  width: 50%;
  margin: 8px 0;
  font-size: 14px;
  line-height: 24px;
  display: flex;
  float: left;
  box-sizing: border-box;

  .property-name {
    position: relative;
    flex: none;
    width: 120px;
    padding: 0 16px 0 0;
    color: #63656e;
    text-align: right;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;

    &::after {
      content: ':';
      position: absolute;
      right: 10px;
    }
  }

  .property-value {
    max-width: calc(100% - 120px - 24px);
    color: #313238;
    word-break: break-all;
  }
}

.cell-value {
  color: #3a84ff;
}

.details-empty {
  padding: 80px 20px;
  text-align: center;
  color: #909399;
}
</style>
