<template>
  <div class="tree-layout">
    <bk-input
      class="tree-search"
      clearable
      right-icon="bk-icon icon-search"
      placeholder="请输入关键词"
      v-model.trim="filterKeyword"
      @input="handleFilter">
    </bk-input>
    <div v-bkloading="{ isLoading: loading, opacity: 1 }" class="tree-loading-wrapper">
      <bk-big-tree
        ref="tree"
        class="topology-tree"
        :height="treeHeight"
        :node-height="36"
        :options="{
          idKey: getNodeId,
          nameKey: 'bk_inst_name',
          childrenKey: 'child'
        }"
        :data="treeData"
        :is-node-fold="isNodeFold"
        @select-change="handleSelectChange"
        @expand-change="handleExpandChange">
        <template #default="{ node, data }">
          <topology-tree-node
            :node="node"
            :data="data"
            :node-count-type="nodeCountType">
          </topology-tree-node>
        </template>
      </bk-big-tree>
      <div v-if="errorMsg" class="tree-error">
        <bk-exception type="500" scene="part">
          <div>{{ errorMsg }}</div>
          <bk-button theme="primary" @click="reload" size="small" class="mt10">重试</bk-button>
        </bk-exception>
      </div>
      <div v-else-if="!loading && treeData.length === 0" class="tree-empty">
        <bk-exception type="empty" scene="part">
          <div>暂无业务数据</div>
        </bk-exception>
      </div>
    </div>
  </div>
</template>

<script>
import TopologyTreeNode from './topology-tree-node.vue'
import { topoAPI } from '@/api/topo'

// 模型元信息（节点显示用）
const MODEL_INFO = {
  biz: { bk_obj_name: '业务', icon_text: '业' },
  set: { bk_obj_name: '集群', icon_text: '集' },
  module: { bk_obj_name: '模块', icon_text: '模' }
}

export default {
  name: 'TopologyTree',
  components: {
    TopologyTreeNode
  },
  props: {
    active: {
      type: String,
      default: 'hostList'
    }
  },
  data() {
    return {
      filterKeyword: '',
      nodeCountType: 'host_count',
      treeHeight: 600,
      treeData: [],
      loading: false,
      errorMsg: '',
      loadedNodes: new Set(),
      loadingNodes: new Set()
    }
  },
  watch: {
    active: {
      immediate: true,
      handler(value) {
        const map = {
          hostList: 'host_count',
          serviceInstance: 'service_instance_count',
          nodeInfo: 'host_count'
        }
        if (Object.keys(map).includes(value)) {
          this.nodeCountType = map[value]
        }
      }
    }
  },
  async mounted() {
    this.updateTreeHeight()
    window.addEventListener('resize', this.updateTreeHeight)
    await this.loadRootNodes()
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.updateTreeHeight)
  },
  methods: {
    // 加载根节点（业务级）
    async loadRootNodes() {
      this.loading = true
      this.errorMsg = ''
      try {
        const res = await topoAPI.getBizList()
        const bizList = (res.data || []).filter(biz => bk_obj_name_filter(biz))

        // 转换为树节点数据
        this.treeData = bizList.map(biz => {
          const info = MODEL_INFO.biz
          return {
            ...biz,
            ...info,
            bk_obj_id: 'biz',
            bk_inst_id: biz.bk_biz_id,
            bk_inst_name: biz.bk_biz_name,
            host_count: null, // 异步统计
            is_lazy: true, // 标记需要懒加载
            child: []
          }
        })

        // 默认展开第一个业务并加载下一级
        if (this.treeData.length > 0) {
          this.$nextTick(() => {
            this.setDefaultState()
          })
        }

        // 异步加载业务级统计
        this.loadBizStatistics()
      } catch (e) {
        console.error('加载业务列表失败:', e)
        this.errorMsg = '加载业务列表失败'
        this.treeData = []
      } finally {
        this.loading = false
      }
    },

    // 异步加载业务级统计
    async loadBizStatistics() {
      const promises = this.treeData.map(async (biz) => {
        try {
          const res = await topoAPI.getNodeCount('biz', biz.bk_inst_id)
          biz.host_count = res.data.count
        } catch (e) {
          console.error(`加载业务 ${biz.bk_inst_id} 统计失败:`, e)
          biz.host_count = 0
        }
      })
      await Promise.all(promises)
    },

    // 设置默认状态：展开第一个业务
    setDefaultState() {
      if (this.$refs.tree && this.$refs.tree.nodes && this.$refs.tree.nodes.length > 0) {
        const firstNode = this.$refs.tree.nodes[0]
        if (firstNode) {
          this.$refs.tree.setExpanded(firstNode.id, { emitEvent: false })
        }
      }
    },

    // 节点是否折叠（懒加载占位）
    isNodeFold(node) {
      const data = node.data || {}
      // 业务级、set 级别都有子节点需要懒加载
      if ((data.bk_obj_id === 'biz' || data.bk_obj_id === 'set') && data.is_lazy) {
        return !node.expanded
      }
      return false
    },

    // 生成节点ID
    getNodeId(data) {
      return `${data.bk_obj_id}-${data.bk_inst_id}`
    },

    // 处理搜索过滤
    handleFilter() {
      if (this.filterKeyword) {
        this.$refs.tree.filter(this.filterKeyword)
      } else {
        this.$refs.tree.filter('')
      }
    },

    // 处理节点选择
    handleSelectChange(node) {
      this.$emit('node-select', node)
    },

    // 处理节点展开 - 懒加载子节点
    async handleExpandChange(node) {
      if (!node || !node.data) return
      const data = node.data
      const nodeKey = `${data.bk_obj_id}-${data.bk_inst_id}`

      // 已加载过或不需要懒加载
      if (this.loadedNodes.has(nodeKey) || !data.is_lazy) {
        // 异步加载统计（如果还没有）
        if (data.host_count === null || data.host_count === undefined) {
          this.loadNodeStatistics(data)
        }
        return
      }

      // 标记为加载中
      this.loadingNodes.add(nodeKey)
      this.$set(data, 'loading', true)

      try {
        if (data.bk_obj_id === 'biz') {
          await this.loadBizChildren(data)
        } else if (data.bk_obj_id === 'set') {
          await this.loadSetChildren(data)
        }
        this.loadedNodes.add(nodeKey)
      } catch (e) {
        console.error(`加载 ${nodeKey} 子节点失败:`, e)
        this.$bkNotify({
          title: '加载失败',
          message: `加载子节点失败: ${e.message || e}`,
          theme: 'error'
        })
      } finally {
        this.loadingNodes.delete(nodeKey)
        this.$set(data, 'loading', false)
      }
    },

    // 加载业务的子节点（set）
    async loadBizChildren(bizNode) {
      const res = await topoAPI.getBizSetList(bizNode.bk_inst_id)
      const setList = res.data || []

      bizNode.child = setList.map(set => {
        const info = MODEL_INFO.set
        return {
          ...set,
          ...info,
          bk_obj_id: 'set',
          bk_inst_id: set.bk_set_id,
          bk_inst_name: set.bk_set_name,
          bk_biz_id: bizNode.bk_inst_id,
          host_count: set.host_count || 0,
          is_lazy: true,
          is_loaded: true, // 业务级加载的 set 已有 host_count
          child: []
        }
      })

      // 触发视图更新
      this.treeData = [...this.treeData]
    },

    // 加载 set 的子节点（module）
    async loadSetChildren(setNode) {
      const res = await topoAPI.getSetModuleList(setNode.bk_inst_id, setNode.bk_biz_id)
      const moduleList = res.data || []

      setNode.child = moduleList.map(mod => {
        const info = MODEL_INFO.module
        return {
          ...mod,
          ...info,
          bk_obj_id: 'module',
          bk_inst_id: mod.bk_module_id,
          bk_inst_name: mod.bk_module_name,
          bk_set_id: setNode.bk_inst_id,
          bk_biz_id: setNode.bk_biz_id,
          host_count: mod.host_count || 0,
          is_lazy: false, // module 是叶子节点
          child: []
        }
      })

      this.treeData = [...this.treeData]
    },

    // 异步加载节点统计
    async loadNodeStatistics(data) {
      try {
        const params = { bk_biz_id: data.bk_biz_id }
        const res = await topoAPI.getNodeCount(data.bk_obj_id, data.bk_inst_id, params)
        data.host_count = res.data.count
      } catch (e) {
        console.error(`加载 ${data.bk_obj_id}-${data.bk_inst_id} 统计失败:`, e)
      }
    },

    // 重新加载
    async reload() {
      this.loadedNodes.clear()
      this.loadingNodes.clear()
      this.treeData = []
      await this.loadRootNodes()
    },

    // 更新树高度
    updateTreeHeight() {
      const container = this.$el.parentElement
      if (container) {
        this.treeHeight = container.clientHeight - 60
      }
    },

    // 获取当前选中的节点
    getSelectedNode() {
      return this.$refs.tree?.selectedNode
    }
  }
}

// 过滤掉资源池业务（default=1）
function bk_obj_name_filter(biz) {
  return biz.default !== 1
}
</script>

<style lang="scss" scoped>
.tree-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.tree-search {
  display: block;
  width: auto;
  margin: 0 20px;
  flex-shrink: 0;
}

.tree-loading-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.topology-tree {
  flex: 1;
  padding: 10px 0;
  margin-right: 2px;
  overflow: auto;

  &::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  &::-webkit-scrollbar-thumb {
    border-radius: 20px;
    background: rgba(165, 165, 165, 0.3);
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  ::v-deep .bk-big-tree-node {
    &:not(.has-link-line) {
      height: 36px;
      line-height: 36px;

      &.is-selected {
        .node-folder-icon {
          color: #3a84ff;
        }
      }

      .node-options {
        padding-left: 10px;
      }
    }

    &.has-link-line.is-leaf {
      padding-left: 6px;
    }

    &:hover {
      background-color: #F0F1F5;
    }
  }

  ::v-deep .bk-scroll-home {
    .bk-min-nav-slide.bk-nav-show {
      width: 6px;
      background-color: #dcdee5;
      border-radius: 3px;
    }
  }
}

.tree-error,
.tree-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 20px;

  .mt10 {
    margin-top: 10px;
  }
}
</style>