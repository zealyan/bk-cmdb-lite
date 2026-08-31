<template>
  <div class="node-association-layout" v-bkloading="{ isLoading: loading }">
    <div v-if="!node" class="empty-state">
      <div class="placeholder-text">请选择拓扑节点</div>
      <div class="placeholder-desc">点击左侧拓扑树节点查看关联</div>
    </div>
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
    </div>
    <!-- 委托通用关联组件渲染；写入操作（新增关联/取消关联）由该组件内置支持。
         :key 强制在节点切换/数据刷新时重建组件：instance-association 仅在 created/mounted
         调 tryInit()，不监听 associations/relations 变化，故必须靠 key 变化触发重新初始化，
         否则在关联 tab 内点击 set/module/任意节点时数据不会刷新（沿用旧实例）。

         @association-change：instance-association 在完成「新增/取消关联」写操作成功后会 emit
         该事件。此处挂 loadData() 重新拉取 API 并自增 associationKey 强制重建子组件，
         实现写后联动刷新（UI + API 数据同步）。
         —— 注意：该监听仅存在于业务拓扑关联 tab（本文件，位于 src/views/business-topology/
            children/ 目录），与资源实例详情关联 tab（src/views/general-model/details.vue
            的 handleAssociationChange）相互独立，互不影响，满足工程隔离要求。 -->
    <instance-association
      v-else-if="isDataReady"
      :key="associationKey"
      :obj-id="objId"
      :inst-id="instId"
      :associations="associations"
      :relations="relations"
      :table-body-loading="true"
      @association-change="loadData">
    </instance-association>
  </div>
</template>

<script>
import InstanceAssociation from '@/components/instance-association/index.vue'
import { modelAPI } from '@/api/client'

export default {
  name: 'NodeAssociation',
  components: {
    InstanceAssociation
  },
  props: {
    // 与 node-info.vue 完全一致：只吃 node 一个 prop，由本组件自行取数
    node: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      loading: false,
      error: null,
      associations: [],
      relations: [],
      isDataReady: false,
      // 每次取数后自增，作为 instance-association 的 :key，强制重建以刷新分组
      associationKey: 0
    }
  },
  computed: {
    objId() {
      return this.node?.data?.bk_obj_id
    },
    // bk_inst_id 为数字，instance-association 的 instId 接受 String|Number，无需转换
    instId() {
      return this.node?.data?.bk_inst_id
    }
  },
  watch: {
    node: {
      immediate: true,
      handler(node) {
        if (node && node.data && node.data.bk_obj_id && node.data.bk_inst_id !== undefined) {
          this.loadData()
        } else {
          this.reset()
        }
      }
    }
  },
  methods: {
    reset() {
      this.associations = []
      this.relations = []
      this.isDataReady = false
      this.error = null
    },
    async loadData() {
      // 与 general-model/details.vue 一致：并行拉取实例关联 + 关系定义
      this.loading = true
      this.error = null
      // 先置为未就绪：卸载旧 instance-association 实例，避免复用导致数据不刷新
      this.isDataReady = false
      try {
        const [assocResponse, relationsResponse] = await Promise.all([
          modelAPI.getInstanceAssociations(this.instId),
          modelAPI.listRelations()
        ])
        this.associations = (assocResponse && assocResponse.associations) || []
        this.relations = (relationsResponse && relationsResponse.relations) || []
        // 关键：自增 key + 置就绪，强制 instance-association 以新数据重新初始化
        this.associationKey++
        this.isDataReady = true
      } catch (err) {
        console.error('加载节点关联数据失败:', err)
        this.error = '关联数据加载失败，请稍后重试'
        this.associations = []
        this.relations = []
        this.isDataReady = false
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.node-association-layout {
  height: 100%;
  padding: 0;
  box-sizing: border-box;
  overflow: auto;

  .empty-state,
  .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #979ba5;
  }

  .placeholder-text {
    font-size: 14px;
    margin-bottom: 8px;
  }

  .placeholder-desc {
    font-size: 12px;
    color: #c4c6cc;
  }

  .error-state {
    color: #ea3636;
  }
}
</style>
