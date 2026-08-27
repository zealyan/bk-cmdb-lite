<template>
  <div class="details-layout">
    <div v-bkloading="{ isLoading: loading }" style="height: 100%;">
      <div class="info" v-if="hostInfo.host">
        <div class="info-basic">
          <i :class="['info-icon', hostIcon]"></i>
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
              <span class="topology-path">{{ item.path }}</span>
              <i class="topology-module-link bk-icon icon-cc-share"
                title="跳转到所属模块"
                @click="handleModuleLink(item)"></i>
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
            <div
              v-for="group in effectivePropertyGroups"
              :key="group.bk_group_id"
              class="property-group"
              v-show="getPropertiesByGroup(group.bk_group_id).length">
              <cmdb-collapse
                :label="group.bk_group_name"
                :collapse.sync="groupState[group.bk_group_id]">
                <ul class="property-list">
                  <li v-for="property in getPropertiesByGroup(group.bk_group_id)" :key="property.bk_property_id" :class="['property-item', property.bk_property_type]">
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
              </cmdb-collapse>
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
import CmdbCollapse from '@/components/ui/collapse/CmdbCollapse.vue'
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
    EditableProperty,
    CmdbCollapse
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
      groupState: {},
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
      // 分组显示名对齐上游 bk-cmdb（admin_server/common/definitions.go）
      const groupNameMap = {
        default: '基础信息',
        auto: '自动发现信息（需要安装agent）',
        role: '角色',
        proc_port: '监听信息'
      }
      const groups = {}
      let orderIndex = 0
      this.displayProperties.forEach(prop => {
        // 复刻原项目 bk-cmdb (src/ui/src/mixins/form.js $groupedProperties):
        // 兼容旧数据，把 bk_property_group === 'none' 的属性归入默认分组，
        // 避免该分组在无对应定义时整组属性消失。
        const groupId = prop.bk_property_group === 'none'
          ? 'default'
          : (prop.bk_property_group || 'default')
        if (!groups[groupId]) {
          groups[groupId] = {
            bk_group_id: groupId,
            bk_group_name: groupNameMap[groupId] || groupId,
            bk_group_index: orderIndex
          }
          orderIndex += 1
        }
      })
      return Object.values(groups).sort((a, b) => a.bk_group_index - b.bk_group_index)
    },
    effectivePropertyGroups () {
      const apiGroups = (this.propertyGroups && this.propertyGroups.length > 0)
        ? this.propertyGroups
        : []
      const dynamicGroups = this.dynamicPropertyGroups || []

      // 复刻原项目: 以接口分组为主，但用属性实际所属分组(dynamic)做并集补全，
      // 防止接口漏返回某分组(如后端分组表未登记)时整组属性消失。
      const merged = {}
      apiGroups.forEach(g => {
        merged[g.bk_group_id] = { ...g, bk_group_index: g.bk_group_index ?? 99, bk_group_name: g.bk_group_name || g.bk_group_id }
      })
      // 属性反推的分组(未出现在接口中)追加进来，index 置后保证排在已知分组之后
      dynamicGroups.forEach(g => {
        if (!merged[g.bk_group_id]) {
          merged[g.bk_group_id] = { ...g, bk_group_index: g.bk_group_index ?? 99 }
        }
      })
      const result = Object.values(merged).sort((a, b) => (a.bk_group_index ?? 99) - (b.bk_group_index ?? 99))
      return result
    },
    hostIcon() {
      // 引用 host 模型描述中预设的图标（bk_obj_icon），如 "icon-cc-host"；
      // 模型未配置 icon 时回退到通用桌面图标。
      return (this.modelData && this.modelData.bk_obj_icon) || 'icon-desktop'
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
            // 优先使用后端返回的通用主线路径 module.topo_path（含自定义层
            // appsys/appsubsys 等），保持 biz→...→set→module 完整层级链。
            // 向后兼容：旧数据/旧后端无 topo_path 时回退到 biz/set/module 三层。
            const chain = (module.topo_path && module.topo_path.length)
              ? module.topo_path
              : [
                { bk_obj_id: 'biz', bk_inst_id: biz.bk_biz_id, bk_inst_name: biz.bk_biz_name },
                { bk_obj_id: 'set', bk_inst_id: set.bk_set_id, bk_inst_name: set.bk_set_name },
                { bk_obj_id: 'module', bk_inst_id: module.bk_module_id, bk_inst_name: module.bk_module_name }
              ]
            paths.push({
              id: module.bk_module_id,
              path: chain.map(n => n.bk_inst_name).join(' / '),
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
    },
    // 分组数据加载完成后重置折叠状态；默认折叠由分组的 is_collapse 决定，
    // 与上游 cmdb-details (mixins/form.js) 行为一致。
    effectivePropertyGroups () {
      this.initGroupState()
    }
  },
  created () {
    // 面包屑活跃守卫：本视图的 updateBreadcrumbs 在异步加载完成后执行，
    // 若期间路由已切换到其它视图（组件销毁），必须拦截写入，避免旧标题串扰新视图。
    this._breadcrumbGuard = true
    this.instId = parseInt(this.$route.params.id, 10)
    this.bizId = parseInt(this.$route.params.bizId, 10) || null
    this.loadHostData()
  },
  beforeDestroy () {
    // 组件销毁：解除守卫，阻止异步回调继续写入全局面包屑
    this._breadcrumbGuard = false
  },
  methods: {
    // 初始化各分组折叠状态：默认展开/折叠由后端分组的 is_collapse 决定。
    // 对应上游 bk-cmdb 中 form.js 对 groupState 的初始化逻辑。
    initGroupState () {
      const state = {}
      this.effectivePropertyGroups.forEach(group => {
        state[group.bk_group_id] = !!group.is_collapse
      })
      this.groupState = state
    },

    getPropertiesByGroup (groupId) {
      const props = this.properties.filter(p => {
        if (p.bk_property_id === 'id') return false
        if (p.bk_isapi) return false
        // 复刻原项目 bk-cmdb: bk_property_group === 'none' 的属性归入默认分组
        const propGroup = p.bk_property_group === 'none'
          ? 'default'
          : (p.bk_property_group || 'default')
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

        await this.loadTopologyData()

        // 数据加载完毕，按分组的 is_collapse 初始化折叠状态
        this.initGroupState()
        
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
        if (res) {
          this.topologyData = res || []
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
        this.$handleApiError(error)
      }
    },

    updateBreadcrumbs () {
      const title = `主机详情【${this.hostIp}】`
      this.$nextTick(() => {
        // 竞态守卫：本视图可能已在异步加载期间被路由替换（组件销毁），
        // 此时若仍写入自定义面包屑，会把旧标题串扰到新视图。
        if (!this._breadcrumbGuard) {
          return
        }
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

        // bizId 必须以字符串形式回传：路由 params 从 URL 解析时恒为字符串，
        // 若这里回传数字会造成 params 类型漂移（'2' -> 2），被业务拓扑页的
        // bizId watch 误判为业务切换而重建拓扑树。
        this.$router.replace({
          name: MENU_BUSINESS_TOPOLOGY,
          params: { bizId: String(this.bizId) },
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

    handleModuleLink(item) {
      // 对齐原项目 bk-cmdb（components/host-topo-path/host-topo-path.vue）：
      // 「所属拓扑」路径为整行文本（biz / set / module 用「 / 」连接），
      // 仅 module 一个「分享」图标可点击，点击在【新窗口】打开业务拓扑并
      // 定位展开到该 module（node=module-{id}）。多级 node（biz/set/自定义层）
      // 不作为独立链接 —— 原项目即为单链接行为，本组件此前将每段都做成独立
      // 可点链接，不符合原项目规范，本次恢复为「仅 module 链接」。
      // 业务入口 bizId 来自路由参数；资源入口无该参数，但 topologyList 已按
      // biz/set/module 构建好 item.bizId，点击定位只依赖 item.bizId，故不依赖
      // 当前路由是否有 bizId 守卫，只要 item.bizId 存在即可跳转。
      if (!item || !item.bizId) return
      const to = {
        name: MENU_BUSINESS_TOPOLOGY,
        params: { bizId: String(item.bizId) },
        query: { node: `module-${item.moduleId}` }
      }
      const { href } = this.$router.resolve(to)
      window.open(href, '_blank')
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
  // 对齐 #/business/2/index/host/11：业务拓扑的 host 详情由 .host-detail-subview
  // 浮层(background-color:#fff)承载白底。#/resource/host/11 同样复用本组件，但其
  // 父容器 dynamicRouterView 的 .main-views/.main-scroller 无白底，会落在全局灰底
  // (#f5f7fa) 上。此处给共享组件根节点补白底，使两种入口的 details-tab(unborder-card)
  // 背景一致，且不依赖父容器是否有白底。
  background-color: #fff;
}

.info {
  max-height: 450px;
  padding: 11px 0 2px 24px;
  background: rgba(235, 244, 255, .6);
  border-bottom: 1px solid #dcdee5;
  // 复刻上游 bk-cmdb（host-details/index.vue）：滚动条用项目标准 @include scrollbar-y
  // （8px / thumb #dcdee5 / radius 20px / hover #979BA5），与上游及 Lite 其余组件保持一致，
  // 不再手写 6px/#d9d9d9/3px 的非标准值。
  @include scrollbar-y;
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
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          color: #63656e;
        }

        // 仅 module 一个「分享」图标可点击，对齐原项目 host-topo-path.vue：
        // 路径整行文本不可点，多级 node（biz/set/自定义层）均不作为链接。
        .topology-module-link {
          display: none;
          vertical-align: middle;
          margin-left: 5px;
          font-size: 12px;
          color: #3a84ff;
          cursor: pointer;

          &:hover {
            opacity: .75;
          }
        }

        // 悬停整行时显示 module 链接图标（与原项目 .cmdb-host-topo-path:hover 行为一致）
        &:hover .topology-module-link {
          display: inline-block;
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
    // 复刻上游 bk-cmdb（host-details/index.vue .bk-tab-section）：竖向滚动容器使用
    // 项目标准 @include scrollbar-y（8px / thumb #dcdee5 / radius 20px / hover #979BA5），
    // 与上游及 Lite 其余组件保持一致；位置修正见上一任务（滚动改由全宽 .bk-tab-section 承载）。
    @include scrollbar-y;
  }
}

.property {
  // 滚动由外层 .bk-tab-section（全宽）承载，使垂直滚动条紧贴页面右边缘；
  // 本容器仅做内容居中与最大宽度限制，自身不再作为滚动容器，避免滚动条错误地
  // 出现在 1200px 居中盒子的右边缘（距视口右约 330px）而非视口右边缘。
  max-width: 1200px;
  margin: 0 auto;
}

.property-group {
  // 与上游 cmdb-details 的 .property-group 保持一致的分组间距
  padding: 7px 0 10px 0;

  &:first-child {
    padding: 28px 0 10px 0;
  }
}

.property-list {
  // 复刻上游 bk-cmdb host-details/children/property.vue (528-608)：
  // flex-wrap + 每项 flex:0 0 50% => 恒定两栏；name 行高 32px、value 用 normal 行高，
  // 并以 margin-top:6px 抵消基线差，使 name/value 文字垂直居中对齐（与原项目一致）
  margin: 24px 0 0 0;
  padding: 0 20px;
  color: #63656e;
  display: flex;
  flex-wrap: wrap;

  .property-item {
    flex: 0 0 50%;
    max-width: 50%;
    padding-bottom: 8px;
    margin: 0;
    font-size: 14px;
    display: flex;

    // 内部表格字段（inner table）占满整行，与上游 .property-item.innertable 一致
    &.innertable {
      flex: 0 0 100%;
      max-width: 100%;

      .property-value {
        flex: 1;
        min-width: 0;
        max-width: none;
      }
    }

    .property-name {
      // 复刻上游：定宽 160px、右对齐、左缩进 36px 对齐分组标题、过长截断
      position: relative;
      flex: none;
      width: 160px;
      padding: 0 16px 0 36px;
      color: #63656e;
      text-align: right;
      line-height: 32px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;

      &:after {
        // 与上游一致：使用全角冒号并贴右对齐
        content: "：";
        position: absolute;
        right: 2px;
      }
    }

    .property-value {
      // 复刻上游 property.vue：
      // 1) margin-top:6px 抵消 name(line-height:32px) 与 value(normal 行高) 的基线差 => 垂直对齐
      // 2) line-height:normal + word-break:break-all 与上游 value-default-theme 一致
      flex: 1;
      min-width: 0;
      // 原项目 .property-value 自身 max-width = calc(100% - 160px - 60px)，
      // 留出 60px 给右侧的编辑/复制图标（与值平级）。
      // lite 中图标位于 editable-property 内部，但外层 wrapper 仍应占满整段值区，
      // 由内部 .property-value + .property-actions 共同分配，故只减去 name 宽度。
      max-width: calc(100% - 160px);
      margin: 6px 0 0 4px;
      line-height: normal;
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
</style>