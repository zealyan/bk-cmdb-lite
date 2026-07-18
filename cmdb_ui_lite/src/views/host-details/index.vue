<template>
  <div class="details-layout">
    <div v-bkloading="{ isLoading: loading }" style="height: 100%;">
      <div class="info" v-if="hostInfo.host">
        <div class="info-basic">
          <i :class="['info-icon', 'icon-desktop']"></i>
          <span class="info-ip">{{ hostIp }}</span>
          <span class="info-area" v-if="cloudArea">{{ cloudArea }}</span>
        </div>
        <div class="info-topology" v-if="isBusinessHost || topologyList.length > 0">
          <div class="topology-label">
            <span>所属拓扑</span>
            <span v-pre style="padding: 0 5px;">:</span>
          </div>
          <ul class="topology-list"
            :class="{ 'is-single-column': isSingleColumn }"
            :style="getListStyle(topologyList)">
            <li :class="['topology-item']"
              v-for="(item, index) in topologyList"
              :key="index">
              <span class="topology-path" v-bk-overflow-tips @click="handlePathClick(item)">{{ item.path }}</span>
            </li>
          </ul>
          <a class="action-btn view-all"
            href="javascript:void(0)"
            v-if="showMore"
            @click="viewAll">
            更多
            <i class="bk-icon icon-angle-down" :class="{ 'is-all-show': showAll }"></i>
          </a>
        </div>
      </div>

      <bk-tab class="details-tab" v-if="!loading"
        type="unborder-card"
        :active.sync="activeTab">
        <bk-tab-panel name="property" label="主机属性">
          <div class="property">
            <div v-for="group in effectivePropertyGroups" :key="group.bk_group_id" class="group">
              <h2 class="group-name">{{ group.bk_group_name }}</h2>
              <ul class="property-list">
                <li v-for="property in getPropertiesByGroup(group.bk_group_id)" :key="property.bk_property_id" class="property-item">
                  <span class="property-name">{{ property.bk_property_name }}</span>
                  <span class="property-value">
                    <editable-property
                      :property="property"
                      :value="hostInfo.host[property.bk_property_id]"
                      :editable="property.editable !== false && !property.bk_isapi"
                      :editing-property-id="editingPropertyId"
                      @start-edit="editingPropertyId = $event"
                      @end-edit="editingPropertyId = null"
                      @confirm="handlePropertyConfirm">
                    </editable-property>
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </bk-tab-panel>

        <bk-tab-panel name="association" label="关联">
          <div v-bkloading="{ isLoading: associationLoading }">
            <div v-if="!isAssociationReady" class="empty-state">
              <span>数据加载中...</span>
            </div>
            <instance-association
              v-else
              ref="associationComponent"
              :key="associationKey"
              :obj-id="'host'"
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
import {
  MENU_BUSINESS_TOPOLOGY,
  MENU_BUSINESS_HOST_DETAILS,
  MENU_RESOURCE_HOST_DETAILS,
  MENU_RESOURCE_MANAGEMENT
} from '@/dictionary/menu-symbol'

export default {
  name: 'HostDetails',
  components: {
    InstanceAssociation,
    EditableProperty
  },
  data() {
    return {
      activeTab: 'property',
      objId: 'host',
      instId: null,
      bizId: null,
      hostInfo: {
        host: null,
        biz: [],
        module: [],
        set: []
      },
      modelData: null,
      apiAssociations: [],
      apiRelations: [],
      apiAttributes: {},
      propertyGroups: [],
      loading: true,
      associationLoading: false,
      editingPropertyId: null,
      associationKey: 0,
      isAssociationReady: false,
      topologyData: [],
      topologyLoading: false,
      showAll: false,
      displayType: 'double',
      MENU_BUSINESS_TOPOLOGY,
      MENU_BUSINESS_HOST_DETAILS,
      MENU_RESOURCE_HOST_DETAILS,
      MENU_RESOURCE_MANAGEMENT
    }
  },
  computed: {
    isBusinessHost() {
      return this.bizId && this.bizId > 0
    },
    properties () {
      return this.apiAttributes[this.objId]?.info || []
    },
    modelRelations () {
      return this.apiRelations || []
    },
    allAssociations () {
      return this.apiAssociations || []
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
            bk_group_name: groupId === 'default' ? '默认' : groupId,
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
    hostIp() {
      const host = this.hostInfo.host || {}
      if (host.bk_host_innerip) {
        const hostList = host.bk_host_innerip.split(',')
        return hostList.length > 1 ? `${hostList[0]}...` : hostList[0]
      }
      if (host.bk_host_outerip) {
        const hostList = host.bk_host_outerip.split(',')
        return hostList.length > 1 ? `${hostList[0]}...` : hostList[0]
      }
      return ''
    },
    cloudArea() {
      const host = this.hostInfo.host || {}
      const cloudId = host.bk_cloud_id
      if (!cloudId && cloudId !== 0) return ''
      return `管控区域：${cloudId}`
    },
    hostDisplayName() {
      const host = this.hostInfo.host || {}
      if (host.bk_host_name) return host.bk_host_name
      if (host.bk_inst_name) return host.bk_inst_name
      return `主机 ${this.instId}`
    },
    isSingleColumn() {
      return this.displayType === 'single'
    },
    topologyList() {
      const paths = []
      this.topologyData.forEach(biz => {
        biz.sets.forEach(set => {
          set.modules.forEach(module => {
            paths.push({
              id: module.bk_module_id,
              path: `${biz.bk_biz_name} / ${set.bk_set_name} / ${module.bk_module_name}`,
              bizId: biz.bk_biz_id,
              setId: set.bk_set_id,
              moduleId: module.bk_module_id
            })
          })
        })
      })
      return paths.sort((a, b) => a.path.localeCompare(b.path, 'zh-Hans-CN'))
    },
    showMore() {
      if (this.isSingleColumn) {
        return this.topologyList.length > 1
      }
      return this.topologyList.length > 2
    }
  },
  watch: {
    activeTab (newTab) {
      if (newTab === 'association') {
        this.loadAssociationData()
      }
    }
  },
  created () {
    this.instId = parseInt(this.$route.params.id, 10)
    this.bizId = parseInt(this.$route.params.bizId, 10) || null
    this.loadHostData()
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

    async loadHostData () {
      this.loading = true
      try {
        if (!this.instId) return

        const response = await modelAPI.getInstance(this.objId, this.instId)
        
        if (response && response.instance) {
          this.hostInfo.host = response.instance
          this.updateBreadcrumbs()
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
        
        try {
          const modelResponse = await modelAPI.getModel(this.objId)
          if (modelResponse && modelResponse.model) {
            this.modelData = modelResponse.model
          }
        } catch (err) {
          console.error('加载模型详情失败:', err)
        }

        await this.loadTopologyData()
        
      } catch (error) {
        console.error('加载主机数据失败:', error)
      } finally {
        this.loading = false
      }
    },

    async loadAssociationData () {
      this.associationLoading = true
      try {
        if (!this.instId) return

        this.isAssociationReady = false
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
        
        this.associationKey++
        this.isAssociationReady = true
        
      } catch (error) {
        console.error('加载关联数据失败:', error)
      } finally {
        this.associationLoading = false
      }
    },

    async loadTopologyData() {
      this.topologyLoading = true
      try {
        if (!this.instId) {
          this.topologyData = []
          return
        }

        const res = await modelAPI.getHostTopology(this.instId, this.bizId)
        if (res && res.data) {
          this.topologyData = res.data || []
          if (this.topologyData.length > 0) {
            this.hostInfo.biz = this.topologyData.map(biz => ({
              bk_biz_id: biz.bk_biz_id,
              bk_biz_name: biz.bk_biz_name
            }))
            const modules = []
            const sets = []
            this.topologyData.forEach(biz => {
              biz.sets.forEach(set => {
                sets.push({
                  bk_set_id: set.bk_set_id,
                  bk_set_name: set.bk_set_name,
                  bk_biz_id: biz.bk_biz_id
                })
                set.modules.forEach(module => {
                  modules.push({
                    bk_module_id: module.bk_module_id,
                    bk_module_name: module.bk_module_name,
                    bk_set_id: set.bk_set_id,
                    bk_biz_id: biz.bk_biz_id
                  })
                })
              })
            })
            this.hostInfo.module = modules
            this.hostInfo.set = sets
          }
        } else {
          this.topologyData = []
        }
      } catch (err) {
        console.error('加载主机拓扑失败:', err)
        this.topologyData = []
      } finally {
        this.topologyLoading = false
      }
    },

    handleAssociationChange () {
      this.loadAssociationData()
    },

    async handlePropertyConfirm ({ property, value, changed }) {
      if (!changed) {
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
        
        this.$set(this.hostInfo.host, property.bk_property_id, value)
        this.editingPropertyId = null
      } catch (error) {
        console.error('更新属性失败:', error)
        let errorMsg = error.message || '未知错误'
        if (error.response && error.response.data) {
          const errorData = error.response.data
          if (errorData.bk_error_msg) {
            errorMsg = errorData.bk_error_msg
          } else if (errorData.detail) {
            errorMsg = errorData.detail
          }
        }
        this.$bkMessage({
          message: errorMsg,
          theme: 'error'
        })
      }
    },

    updateBreadcrumbs () {
      const title = `主机详情【${this.hostIp}】`
      this.$nextTick(() => {
        this.$store.commit('setCustomBreadcrumbs', {
          enable: true,
          title: title,
          backward: () => {
            this.handleBack()
          }
        })
      })
    },

    handleBack() {
      console.log('[host-details] handleBack called', {
        query: this.$route.query,
        _f: this.$route.query._f,
        page: this.$route.query.page,
        node: this.$route.query.node,
        isBusinessHost: this.isBusinessHost,
        bizId: this.bizId
      })

      if (this.isBusinessHost) {
        const page = this.$route.query._f ? parseInt(this.$route.query._f, 10) : (this.$route.query.page ? parseInt(this.$route.query.page, 10) : 1)
        const node = this.$route.query.node || `biz-${this.bizId}`

        // 返回列表时把 filter / ip 一并带回，保证高级筛选条件（条件状态 / tag UI / 后端结果）不丢失
        const query = {
          page: page,
          node: node,
          _t: Date.now()
        }
        if (this.$route.query.filter) query.filter = this.$route.query.filter
        if (this.$route.query.ip) query.ip = this.$route.query.ip

        // 复刻原项目：返回业务拓扑时把拓扑树的关系词/关键词 keyword 一并带回，
        // 否则返回后 topology-tree 挂载时从 URL 取不到 keyword，已输入的搜索词即丢失。
        // 对齐 host-list.handleValueClick 将 keyword 带入详情的逻辑，形成往返闭环。
        if (this.$route.query.keyword) query.keyword = this.$route.query.keyword

        console.log('[host-details] navigating back with', { page, node, filter: this.$route.query.filter, ip: this.$route.query.ip })

        this.$router.replace({
          name: MENU_BUSINESS_TOPOLOGY,
          params: { bizId: this.bizId },
          query
        })
      } else {
        // 资源目录入口：优先返回上一页，无历史时回退到资源目录
        if (window.history.length > 1) {
          this.$router.back()
        } else {
          this.$router.push({ name: MENU_RESOURCE_MANAGEMENT })
        }
      }
    },

    handlePathClick(item) {
      if (this.isBusinessHost) {
        this.$router.push({
          name: MENU_BUSINESS_TOPOLOGY,
          params: { bizId: item.bizId }
        })
      }
    },

    viewAll() {
      this.showAll = !this.showAll
    },

    getListStyle(items) {
      const itemHeight = 21
      const itemMargin = 9
      const length = this.isSingleColumn ? items.length : Math.ceil(items.length / 2)
      return {
        height: `${(this.showAll ? length : 1) * (itemHeight + itemMargin)}px`
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.details-layout {
  overflow: hidden;
  height: 100%;
}

.info {
  max-height: 450px;
  padding: 11px 0 2px 24px;
  background: rgba(235, 244, 255, .6);
  border-bottom: 1px solid #dcdee5;
  overflow-y: auto;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: #d9d9d9;
    border-radius: 3px;
  }
}

.info-basic {
  font-size: 0;

  .info-icon {
    display: inline-block;
    width: 38px;
    height: 38px;
    margin: 0 11px 0 0;
    border: 1px solid #dde4eb;
    border-radius: 50%;
    background-color: #fff;
    vertical-align: middle;
    line-height: 38px;
    text-align: center;
    font-size: 18px;
    color: #3a84ff;
  }

  .info-ip {
    display: inline-block;
    vertical-align: middle;
    line-height: 38px;
    font-size: 16px;
    font-weight: bold;
    color: #333948;
  }

  .info-area {
    display: inline-block;
    vertical-align: middle;
    height: 18px;
    margin-left: 10px;
    padding: 0 5px;
    line-height: 16px;
    font-size: 12px;
    color: #979ba5;
    border: 1px solid #c4c6cc;
    border-radius: 2px;
    background-color: #fff;
  }
}

.info-topology {
  line-height: 19px;
  display: flex;
  margin-top: 8px;
  position: relative;

  .topology-label {
    display: flex;
    align-items: center;
    align-self: baseline;
    padding: 0 0 0 50px;
    font-size: 14px;
    font-weight: bold;
    line-height: 20px;
    color: #333948;
  }

  .topology-list {
    flex: 1;
    display: flex;
    flex-wrap: wrap;
    overflow: hidden;
    color: #63656e;
    max-width: 700px;
    margin: 0;
    padding: 0;

    &.is-single-column {
      flex-direction: column;
      flex-wrap: nowrap;

      .topology-item {
        flex: none;
        width: 100%;
      }
    }

    .topology-item {
      flex: 0 1 50%;
      width: 50%;
      height: 20px;
      font-size: 0;
      margin: 0 0 9px 0;
      padding: 0 15px 0 0;
      line-height: 20px;
      list-style: none;

      .topology-path {
        display: inline-block;
        vertical-align: middle;
        font-size: 14px;
        max-width: calc(100% - 30px);
        cursor: pointer;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;

        &:hover {
          color: #3a84ff;
        }
      }
    }
  }

  .action-btn {
    display: inline-block;
    font-size: 12px;
    cursor: pointer;
    color: #3a84ff;

    &.view-all {
      margin-left: 10px;
    }

    i {
      margin-left: 2px;
      transition: transform 0.3s;
    }

    &.is-all-show i {
      transform: rotate(180deg);
    }
  }
}

.details-tab {
  height: calc(100% - 81px) !important;
  min-height: 400px;

  :deep(.bk-tab-header) {
    padding: 0;
    margin: 0 20px;
  }

  :deep(.bk-tab-section) {
    padding-bottom: 10px;
    overflow-y: auto;

    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-track {
      background: transparent;
    }

    &::-webkit-scrollbar-thumb {
      background: #d9d9d9;
      border-radius: 3px;
    }
  }
}

.property {
  height: 100%;
  overflow: auto;
}

.group {
  margin: 22px 0 0 0;

  .group-name {
    line-height: 21px;
    font-size: 16px;
    font-weight: normal;
    color: #333948;
    margin: 0;
    padding-left: 24px;
    position: relative;

    &::before {
      content: '';
      display: inline-block;
      vertical-align: -2px;
      width: 4px;
      height: 14px;
      margin-right: 9px;
      margin-left: -24px;
      position: absolute;
      left: 20px;
      background-color: #dcdee5;
    }
  }
}

.property-list {
  margin: 24px 0 0 0;
  color: #63656e;
  display: flex;
  flex-wrap: wrap;
  padding: 0 20px;

  .property-item {
    flex: 0 0 50%;
    max-width: 50%;
    padding-bottom: 8px;
    display: flex;

    .property-name {
      position: relative;
      width: 160px;
      line-height: 32px;
      padding: 0 16px 0 36px;
      font-size: 14px;
      color: #63656e;
      text-align: right;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;

      &::after {
        position: absolute;
        right: 2px;
        content: '：';
      }
    }

    .property-value {
      margin: 6px 0 0 4px;
      max-width: calc(100% - 160px - 60px);
      font-size: 14px;
      color: #313237;
      word-break: break-all;
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

@media (min-width: 1600px) {
  .property-list {
    .property-item {
      .property-name {
        width: 260px;
      }

      .property-value {
        max-width: calc(100% - 260px - 60px);
      }
    }
  }
}
</style>