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
              :obj-id="objId"
              :inst-id="instId"
              :associations="allAssociations"
              :relations="modelRelations"
              :instances-map="instancesMap"
              :properties-map="propertiesMap"
              @view-instance="handleViewAssociatedInstance"
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

const modelAttributesMap = {}

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
      apiInstances: {},
      apiAttributes: {},
      propertyGroups: [], // 属性分组数据
      isDataReady: false,
      associationLoading: false,
      editingPropertyId: null // 当前正在编辑的属性ID
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
    instancesMap () {
      const map = { ...this.apiInstances }
      return map
    },
    propertiesMap () {
      const map = { ...this.apiAttributes }
      return map
    },
    displayProperties () {
      // 与原项目保持一致: 排除 bk_isapi=true 的系统字段
      // 参考: /workspace/bk-cmdb/src/ui/src/components/model-instance/property.vue
      return this.properties.filter(p =>
        p.bk_property_index !== -1 &&
        p.bk_property_id !== 'id' &&
        !p.bk_isapi
      ).sort((a, b) => a.bk_property_index - b.bk_property_index)
    },
    // 从属性数据动态生成分组（仅作为回退方案）
    // 与原项目一致：名称直接使用 groupId，索引根据在属性列表中出现的顺序
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
      // 过滤掉空分组并排序
      return Object.values(groups).sort((a, b) => a.bk_group_index - b.bk_group_index)
    },
    // 实际使用的分组：优先使用后端返回的分组数据（已按 bk_group_index 排序）
    // 后端 cc_PropertyGroup 表有 bk_group_index 字段控制排序
    // 只有后端没有返回分组时才使用动态生成的分组
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
    },
    hasAssociations () {
      const associations = this.allAssociations || []
      const hasSourceData = associations.some(asst =>
        String(asst.bk_obj_id) === String(this.objId) &&
        String(asst.bk_inst_id) === String(this.instId)
      )
      const hasTargetData = associations.some(asst =>
        String(asst.bk_asst_obj_id) === String(this.objId) &&
        String(asst.bk_asst_inst_id) === String(this.instId)
      )
      return (hasSourceData || hasTargetData) && this.modelRelations.length > 0
    }
  },
  watch: {
    activeTab (newTab) {
      if (newTab === 'association' && !this.isDataReady) {
        this.associationLoading = true
      }
    }
  },
  created () {
    this.objId = this.$route.params.objId
    this.instId = parseInt(this.$route.params.instId, 10)
    this.loadInstanceData()
  },
  methods: {
    // 获取指定分组的属性
    getPropertiesByGroup (groupId) {
      const props = this.properties.filter(p => {
        // 不显示 id 字段
        if (p.bk_property_id === 'id') return false
        // 不显示 bk_isapi=true 的系统字段
        if (p.bk_isapi) return false
        // 检查分组，默认为 'default'
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
        
        // 加载属性分组
        try {
          const groupsResponse = await modelAPI.getModelPropertyGroups(this.objId)
          if (groupsResponse && groupsResponse.groups) {
            this.propertyGroups = groupsResponse.groups
          }
        } catch (err) {
          console.warn('加载属性分组失败:', err)
          // 如果没有分组，创建默认分组
          this.propertyGroups = [{
            id: 1,
            bk_group_id: 'default',
            bk_group_name: '默认',
            bk_group_index: 0,
            bk_isdefault: true
          }]
        }
        
        const assocResponse = await modelAPI.getInstanceAssociations(this.instId)
        if (assocResponse && assocResponse.associations) {
          this.apiAssociations = assocResponse.associations
        }
        
        const relationsResponse = await modelAPI.listRelations()
        if (relationsResponse && relationsResponse.relations) {
          this.apiRelations = relationsResponse.relations
        }
        
        const relatedModelIds = new Set()
        relatedModelIds.add(this.objId)
        
        this.apiAssociations.forEach(asst => {
          if (String(asst.bk_obj_id) === String(this.objId) && String(asst.bk_inst_id) === String(this.instId)) {
            relatedModelIds.add(asst.bk_asst_obj_id)
          }
          if (String(asst.bk_asst_obj_id) === String(this.objId) && String(asst.bk_asst_inst_id) === String(this.instId)) {
            relatedModelIds.add(asst.bk_obj_id)
          }
        })
        
        for (const modelId of relatedModelIds) {
          try {
            const attrResponse = await modelAPI.getModelAttributes(modelId)
            if (attrResponse && attrResponse.attributes) {
              const sortedAttrs = attrResponse.attributes
                .filter(p => p.bk_property_index !== -1)
                .sort((a, b) => a.bk_property_index - b.bk_property_index)
              this.$set(this.apiAttributes, modelId, { info: sortedAttrs })
            }
          } catch (err) {
            console.warn(`加载 ${modelId} 属性定义失败:`, err)
          }
        }
        
        for (const modelId of relatedModelIds) {
          try {
            const instancesResponse = await modelAPI.listInstances(modelId, { page: 1, page_size: 100 })
            if (instancesResponse && instancesResponse.instances) {
              this.$set(this.apiInstances, modelId, instancesResponse.instances)
            }
          } catch (err) {
            console.warn(`加载 ${modelId} 实例失败:`, err)
          }
        }
        
        this.isDataReady = true
        
      } catch (error) {
        console.error('加载实例数据失败:', error)
      } finally {
        this.associationLoading = false
      }
    },
    goBack () {
      this.$router.go(-1)
    },
    goToResource () {
      this.$router.push({ name: 'Resource' })
    },
    goToInstanceList () {
      this.$router.push({
        name: 'GeneralModel',
        params: { objId: this.objId }
      })
    },
    viewInstance () {
      // ID 列不需要跳转
    },
    handleViewAssociatedInstance ({ objId, instId }) {
      this.$router.push({
        name: 'GeneralModelDetails',
        params: { objId, instId }
      })
    },
    handleAssociationChange () {
      this.loadInstanceData()
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
  min-height: 100%;
}

.details-layout {
  overflow: hidden;

  .details-tab {
    min-height: 400px;

    :deep(.bk-tab-header) {
      padding: 0 20px;
      height: 58px;
      background-image: linear-gradient(transparent 57px, #dcdee5 0);

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
    }
  }
}

.info-card {
  padding: 20px;
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
