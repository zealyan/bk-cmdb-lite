<template>
  <div class="model-details-page">
    <div class="details-layout">
      <bk-tab :active.sync="activeTab" type="unborder-card" class="details-tab">
      <bk-tab-panel name="property" label="属性">
          <div class="info-card">
            <div class="property-groups">
              <div v-for="group in effectivePropertyGroups" :key="group.bk_group_id" class="property-group">
                <cmdb-collapse
                  :label="group.bk_group_name"
                  :collapse.sync="groupState[group.bk_group_id]">
                  <div class="info-grid">
                    <div
                      v-for="property in getPropertiesByGroup(group.bk_group_id)"
                      :key="property.bk_property_id"
                      class="info-item"
                      :class="{ 'full-width': isFullWidthProperty(property) }">
                      <span class="property-label" v-bk-overflow-tips="{ boundary: 'viewport' }">{{ property.bk_property_name }}</span>
                      <span class="property-colon">：</span>
                      <span class="property-value-wrap">
                        <template v-if="property.bk_property_id === 'id'">
                          <bk-button :text="true" @click="viewInstance">{{ instanceData[property.bk_property_id] }}</bk-button>
                        </template>
                        <template v-else>
                          <editable-property
                            :property="property"
                            :value="instanceData[property.bk_property_id]"
                            :editable="property.editable !== false && !property.bk_isapi"
                            :editing-property-id="editingPropertyId"
                            @start-edit="editingPropertyId = $event"
                            @end-edit="editingPropertyId = null"
                            @confirm="handlePropertyConfirm">
                          </editable-property>
                        </template>
                      </span>
                    </div>
                  </div>
                </cmdb-collapse>
              </div>
            </div>
          </div>
        </bk-tab-panel>

        <bk-tab-panel name="association" label="关联">
          <div v-bkloading="{ isLoading: associationLoading }">
            <div v-if="!isDataReady" class="empty-state">
              <span>数据加载中...</span>
            </div>
            <instance-association
              v-else
              ref="associationComponent"
              :key="associationKey"
              :obj-id="objId"
              :inst-id="instId"
              :associations="allAssociations"
              :relations="modelRelations"
              @association-change="handleAssociationChange">
            </instance-association>
          </div>
        </bk-tab-panel>
      </bk-tab>
    </div>
  </div>
</template>

<script>
import InstanceAssociation from '@/components/instance-association/index.vue'
import EditableProperty from '@/components/property/editable-property.vue'
import CmdbCollapse from '@/components/ui/collapse/CmdbCollapse.vue'
import { modelAPI } from '@/api/client'
import bkSlbRelations from '@/assets/api/models/relations/instance.json'
import { MENU_RESOURCE_INSTANCE, MENU_RESOURCE_MANAGEMENT } from '@/dictionary/menu-symbol'

export default {
  name: 'ModelDetails',
  components: {
    InstanceAssociation,
    EditableProperty,
    CmdbCollapse
  },
  data() {
    return {
      activeTab: 'property',
      objId: '',
      instId: null,
      instanceData: {},
      modelData: null,
      apiAssociations: [],
      apiRelations: [],
      apiAttributes: {},
      propertyGroups: [],
      isDataReady: false,
      associationLoading: false,
      editingPropertyId: null,
      associationKey: 0,
      groupState: {},
      MENU_RESOURCE_INSTANCE,
      MENU_RESOURCE_MANAGEMENT
    }
  },
  computed: {
    properties () {
      return this.apiAttributes[this.objId]?.info || []
    },
    modelRelations () {
      return this.apiRelations || bkSlbRelations.relations || []
    },
    modelAssociations () {
      return this.apiAssociations || []
    },
    allAssociations () {
      return this.modelAssociations
    },
    displayProperties () {
      return this.properties.filter(p =>
        p.bk_property_index !== -1 &&
        p.bk_property_id !== 'id' &&
        !p.bk_isapi
      ).sort((a, b) => a.bk_property_index - b.bk_property_index)
    },
    dynamicPropertyGroups () {
      const groups = {}
      let orderIndex = 0
      this.displayProperties.forEach(prop => {
        const groupId = prop.bk_property_group || 'default'
        if (!groups[groupId]) {
          groups[groupId] = {
            bk_group_id: groupId,
            bk_group_name: groupId,
            bk_group_index: orderIndex
          }
          orderIndex += 1
        }
      })
      return Object.values(groups).sort((a, b) => a.bk_group_index - b.bk_group_index)
    },
    effectivePropertyGroups () {
      if (this.propertyGroups && this.propertyGroups.length > 0) {
        return this.propertyGroups.sort((a, b) => {
          const indexA = a.bk_group_index ?? 99
          const indexB = b.bk_group_index ?? 99
          return indexA - indexB
        })
      }
      if (this.dynamicPropertyGroups && this.dynamicPropertyGroups.length > 0) {
        return this.dynamicPropertyGroups
      }
      return []
    },
    modelName () {
      if (this.modelData && this.modelData.bk_obj_name) {
        return this.modelData.bk_obj_name
      }
      return this.objId
    },
    instanceName () {
      if (this.instanceData.bk_inst_name) {
        return this.instanceData.bk_inst_name
      }
      const nameField = this.instanceData.bk_cloud_name ? 'bk_cloud_name' : 'name'
      return this.instanceData[nameField] || `ID: ${this.instId}`
    }
  },
  watch: {
    activeTab (newTab) {
      if (newTab === 'association') {
        if (!this.isDataReady) {
          this.associationLoading = true
        }
        this.loadAssociationData()
      }
    },
    effectivePropertyGroups: {
      immediate: true,
      handler () {
        this.initGroupState()
      }
    }
  },
  created () {
    this.objId = this.$route.params.objId
    this.instId = parseInt(this.$route.params.instId, 10)
    this.loadInstanceData()
  },
  methods: {
    initGroupState () {
      this.effectivePropertyGroups.forEach(group => {
        this.$set(this.groupState, group.bk_group_id, group.is_collapse)
      })
    },
    getPropertiesByGroup (groupId) {
      const props = this.properties.filter(p => {
        if (p.bk_property_id === 'id') return false
        if (p.bk_isapi) return false
        const propGroup = p.bk_property_group || 'default'
        return propGroup === groupId && p.bk_property_index !== -1
      }).sort((a, b) => a.bk_property_index - b.bk_property_index)

      return props
    },

    // 对应原项目 cmdb-details 中 .property-item.innertable 的整行通栏判定：
    // 仅 INNER_TABLE 类型字段占满整行；longchar 在原项目中是普通两栏项（不整行），
    // 其值由 2 行截断 + 悬停 tips 处理，避免整行通栏导致与原项目观感不符
    isFullWidthProperty (property) {
      return property.bk_property_type === 'INNER_TABLE'
    },

    async loadInstanceData () {
      this.associationLoading = true
      try {
        if (!this.objId || !this.instId) {
          return
        }
        
        const response = await modelAPI.getInstance(this.objId, this.instId)
        
        if (response && response.instance) {
          this.instanceData = response.instance
          
          const instName = this.instanceName
          this.$store.dispatch('setCurrentInstance', {
            name: instName,
            objId: this.objId,
            instId: this.instId
          })
        }
        
        try {
          const groupsResponse = await modelAPI.getModelPropertyGroups(this.objId)
          if (groupsResponse && groupsResponse.groups) {
            this.propertyGroups = groupsResponse.groups
          }
        } catch (err) {
          this.propertyGroups = [{
            id: 1,
            bk_group_id: 'default',
            bk_group_name: '基础信息',
            bk_group_index: 1,
            bk_isdefault: true
          }]
        }
        
        const attrResponse = await modelAPI.getModelAttributes(this.objId)
        if (attrResponse && attrResponse.attributes) {
          const sortedAttrs = attrResponse.attributes
            .filter(p => p.bk_property_index !== -1)
            .sort((a, b) => a.bk_property_index - b.bk_property_index)
          this.$set(this.apiAttributes, this.objId, { info: sortedAttrs })
        }
        
        try {
          const modelResponse = await modelAPI.getModel(this.objId)
          if (modelResponse && modelResponse.model) {
            this.modelData = modelResponse.model
          }
        } catch (err) {
          console.error('加载模型详情失败:', err)
        }
        
        this.isDataReady = true
        
        this.$nextTick(() => {
          this.updateBreadcrumbs()
        })
        
      } catch (error) {
        console.error('加载实例数据失败:', error)
      } finally {
        this.associationLoading = false
      }
    },
    async loadAssociationData () {
      this.associationLoading = true
      try {
        if (!this.objId || !this.instId) {
          return
        }
        
        // 先加载数据
        this.isDataReady = false
        this.apiAssociations = []
        this.apiRelations = []
        
        const assocResponse = await modelAPI.getInstanceAssociations(this.instId)
        if (assocResponse && assocResponse.associations) {
          this.apiAssociations = assocResponse.associations
        }
        
        const relationsResponse = await modelAPI.listRelations()
        if (relationsResponse && relationsResponse.relations) {
          this.apiRelations = relationsResponse.relations
        }
        
        // 数据加载完成后，强制子组件重新创建
        this.associationKey++
        this.isDataReady = true
        
      } catch (error) {
        console.error('加载关联数据失败:', error)
      } finally {
        this.associationLoading = false
      }
    },
    goBack () {
      this.$router.go(-1)
    },
    goToResource () {
      this.$router.push({ name: MENU_RESOURCE_MANAGEMENT })
    },
    goToInstanceList () {
      this.$router.push({
        name: MENU_RESOURCE_INSTANCE,
        params: { objId: this.objId }
      })
    },
    updateBreadcrumbs () {
      const objId = this.objId
      const title = `${this.modelName} ${this.instanceName ? '【' + this.instanceName + '】' : ''}`
      this.$nextTick(() => {
        this.$store.commit('setCustomBreadcrumbs', {
          enable: true,
          title: title,
          backward: () => {
            this.$router.go(-1)
          }
        })
      })
    },
    viewInstance () {
    },
    handleAssociationChange () {
      this.loadAssociationData()
    },
    async handlePropertyConfirm ({ property, value, changed }) {
      if (!changed) {
        // 值没有变化，关闭编辑态
        this.editingPropertyId = null
        return
      }

      try {
        const updateData = {
          [property.bk_property_id]: value
        }
        
        await modelAPI.updateInstance(this.objId, this.instId, updateData)
        
        this.$bkMessage({
          message: '属性更新成功',
          theme: 'success'
        })
        
        this.$set(this.instanceData, property.bk_property_id, value)
        // 保存成功，关闭编辑态
        this.editingPropertyId = null
      } catch (error) {
        console.error('更新属性失败:', error)
        let errorMsg = error.message || '未知错误'
        this.$bkMessage({
          message: errorMsg,
          theme: 'error'
        })
        // 保存失败，保持编辑态打开，让用户可以继续编辑
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.model-details-page {
  background: #f5f7fa;
  min-height: 100vh;
  box-sizing: border-box;
}

.details-layout {
  overflow: visible;
  min-height: 100vh;
  box-sizing: border-box;
  background-color: #fff;

  .details-tab {
    min-height: 400px;
    background-color: transparent;

    // 属性/关联 tab 栏：在 .main-scroller 滚动时吸顶，
    // 效果与顶部面包屑一致（不随虚拟滚动条下滑而移出视口）
    :deep(.bk-tab-header) {
      position: sticky;
      top: 0;
      z-index: 10;
      padding: 0 20px;
      height: 58px;
      background-color: #fff !important;
      background-image: none !important;
      border-bottom: 1px solid #dcdee5;

      .bk-tab-label-list {
        height: 58px;

        .bk-tab-label-item {
          line-height: 58px;
          min-width: auto;

          &.active {
            background-color: transparent;
          }
        }
      }
    }

    :deep(.bk-tab-section) {
      padding: 0 20px;
      padding-bottom: 10px;
      background-color: transparent;
    }
  }
}

.info-card {
  padding: 20px;
  background-color: #fff;
}

.property-groups {
  .property-group {
    margin-bottom: 24px;

    &:last-child {
      margin-bottom: 0;
    }
  }
}

.info-grid {
  // 与原项目 cmdb-details 的 .property-list 保持一致：
  // 严格两栏，每项 width:50% 且上限 max-width:400px（float 布局的等价写法）。
  // 列宽 min 0 可被窄容器压缩，max 400px 与原始「50% 且封顶 400px」观感一致。
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 400px));
  // 行距 12px 与原项目 .property-item 的 margin: 12px 0 0 一致；
  // 列距 40px 复刻上游 / 主机详情两栏的横向留白（上游 .property-value 右侧
  // padding:0 15px 0 0 + 主机详情 name 左缩进 36px），避免左右栏紧贴。
  gap: 12px 40px;
}

.info-item {
  display: flex;
  align-items: flex-start;
  // 不允许换行，否则超长属性值会把值区挤到下一行，截断失效
  flex-wrap: nowrap;
  // 栅格子项默认 min-width:auto，会被内容撑破 1fr，导致整行溢出
  min-width: 0;

  .property-label {
    // 与原项目 cmdb-details 一致：属性名定宽右对齐，过长时自身也截断
    flex: none;
    width: 140px;
    text-align: right;
    font-size: 14px;
    color: #63656e;
    line-height: 20px;
    padding-top: 6px;
    @include ellipsis;
  }

  .property-colon {
    flex: none;
    font-size: 14px;
    color: #63656e;
    margin: 0 4px;
    line-height: 20px;
    padding-top: 6px;
  }

  .property-value-wrap {
    font-size: 14px;
    color: #313238;
    min-width: 0;
    flex: 1;
    overflow: hidden;
    line-height: 20px;
    padding-top: 6px;
  }

  // INNER_TABLE 类型字段整行通栏，对应原项目 .property-item.innertable 的
  // width:100%; max-width:unset。longchar 不整行（按原项目为普通两栏项）
  &.full-width {
    grid-column: 1 / -1;
    padding-right: 0;

    .property-value-wrap {
      max-width: 1200px;
    }
  }
}

.empty-state {
  padding: 60px 20px;
  text-align: center;
  color: #909399;
  background: #fafafa;
  border-radius: 4px;
}
</style>
