<template>
  <div class="model-details-page">
    <div class="details-layout">
      <bk-tab :active.sync="activeTab" type="unborder-card" class="details-tab">
      <bk-tab-panel name="property" label="属性">
          <div class="info-card">
            <div class="property-groups">
              <div v-for="group in effectivePropertyGroups" :key="group.bk_group_id" class="property-group">
                <h3 class="group-title">{{ group.bk_group_name }}</h3>
                <div class="info-grid">
                  <div
                    v-for="property in getPropertiesByGroup(group.bk_group_id)"
                    :key="property.bk_property_id"
                    class="info-item">
                    <span class="property-label">{{ property.bk_property_name }}</span>
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
import { modelAPI } from '@/api/client'
import modelIndex from '@/assets/api/index.json'
import bkSlbRelations from '@/assets/api/models/relations/instance.json'
import { MENU_RESOURCE_INSTANCE, MENU_RESOURCE_MANAGEMENT } from '@/dictionary/menu-symbol'

export default {
  name: 'ModelDetails',
  components: {
    InstanceAssociation,
    EditableProperty
  },
  data() {
    return {
      activeTab: 'property',
      objId: '',
      instId: null,
      instanceData: {},
      modelIndex: modelIndex.models,
      apiAssociations: [],
      apiRelations: [],
      apiAttributes: {},
      propertyGroups: [],
      isDataReady: false,
      associationLoading: false,
      editingPropertyId: null,
      associationKey: 0,
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
      const model = this.modelIndex.find(m => m.bk_obj_id === this.objId)
      return model?.bk_obj_name || this.objId
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
    }
  },
  created () {
    this.objId = this.$route.params.objId
    this.instId = parseInt(this.$route.params.instId, 10)
    this.loadInstanceData()
  },
  methods: {
    getPropertiesByGroup (groupId) {
      const props = this.properties.filter(p => {
        if (p.bk_property_id === 'id') return false
        if (p.bk_isapi) return false
        const propGroup = p.bk_property_group || 'default'
        return propGroup === groupId && p.bk_property_index !== -1
      }).sort((a, b) => a.bk_property_index - b.bk_property_index)
      
      return props
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
            bk_group_name: '默认',
            bk_group_index: 0,
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
            this.$router.push({
              name: MENU_RESOURCE_INSTANCE,
              params: { objId }
            })
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
      } catch (error) {
        console.error('更新属性失败:', error)
        this.$bkMessage({
          message: '属性更新失败: ' + (error.message || '未知错误'),
          theme: 'error'
        })
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
  overflow: hidden;
  min-height: 100vh;
  box-sizing: border-box;
  background-color: #fff;

  .details-tab {
    min-height: 400px;
    background-color: transparent;

    :deep(.bk-tab-header) {
      padding: 0 20px;
      height: 58px;
      background-color: transparent !important;
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

    .group-title {
      font-size: 16px;
      font-weight: 600;
      color: #313238;
      margin: 0 0 16px 0;
      padding-bottom: 8px;
      border-bottom: 1px solid #e8eaec;
    }
  }
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.info-item {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;

  .property-label {
    font-size: 14px;
    color: #63656e;
    white-space: nowrap;
    line-height: 20px;
    padding-top: 6px;
  }

  .property-colon {
    font-size: 14px;
    color: #63656e;
    margin: 0 4px;
    line-height: 20px;
    padding-top: 6px;
  }

  .property-value-wrap {
    font-size: 14px;
    color: #313238;
    word-break: break-all;
    min-width: 0;
    flex: 1;
    line-height: 20px;
    padding-top: 6px;
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
