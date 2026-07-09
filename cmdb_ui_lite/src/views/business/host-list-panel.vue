<template>
  <div class="host-list-panel" v-bkloading="{ isLoading: loading, opacity: 1 }">
    <div class="panel-header">
      <span class="node-title">
        <span class="node-icon">{{ nodeIconText }}</span>
        <span class="node-name">{{ node.data.bk_inst_name }}</span>
      </span>
      <span class="node-path">{{ nodePath }}</span>
    </div>
    <div class="panel-body">
      <bk-table
        :data="hostList"
        :pagination="pagination"
        @page-change="handlePageChange"
        @page-limit-change="handlePageLimitChange">
        <bk-table-column prop="bk_host_id" label="主机ID" width="100"></bk-table-column>
        <bk-table-column prop="bk_host_name" label="主机名称" min-width="150"></bk-table-column>
        <bk-table-column prop="bk_host_innerip" label="内网IP" width="150"></bk-table-column>
        <bk-table-column prop="bk_host_outerip" label="外网IP" width="150"></bk-table-column>
        <bk-table-column prop="bk_cloud_id" label="云区域" width="100"></bk-table-column>
        <bk-table-column label="状态" width="100">
          <template #default="{ row }">
            <span :class="['status-tag', getStatus(row)]">{{ statusText(getStatus(row)) }}</span>
          </template>
        </bk-table-column>
      </bk-table>
    </div>
  </div>
</template>

<script>
import { topoAPI } from '@/api/topo'

export default {
  name: 'HostListPanel',
  props: {
    node: {
      type: Object,
      required: true
    },
    active: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      pagination: {
        current: 1,
        count: 0,
        limit: 10
      },
      hostList: [],
      loading: false
    }
  },
  computed: {
    nodeIconText() {
      return this.node.data.icon_text || this.node.data.bk_obj_name?.[0] || 'N'
    },
    nodePath() {
      // 从节点向上遍历获取路径
      let path = []
      let current = this.node
      while (current && current.data) {
        path.unshift(current.data.bk_inst_name)
        current = current.parent
      }
      return path.join(' / ')
    }
  },
  watch: {
    node: {
      deep: true,
      handler(node) {
        if (node && node.data) {
          this.pagination.current = 1
          this.loadHostList()
        }
      }
    },
    active(active) {
      if (active && this.node) {
        this.loadHostList()
      }
    }
  },
  methods: {
    async loadHostList() {
      this.loading = true
      try {
        const data = this.node.data
        const objId = data.bk_obj_id
        const params = {
          page: this.pagination.current,
          page_size: this.pagination.limit
        }
        let result
        if (objId === 'biz') {
          result = await topoAPI.getBizHostList(data.bk_inst_id, params)
        } else if (objId === 'set') {
          result = await topoAPI.getSetHostList(data.bk_inst_id, data.bk_biz_id, params)
        } else if (objId === 'module') {
          result = await topoAPI.getModuleHostList(data.bk_inst_id, params)
        } else {
          this.hostList = []
          this.pagination.count = 0
          return
        }
        this.hostList = result.data.info || []
        this.pagination.count = result.data.count || 0
      } catch (e) {
        console.error('加载主机列表失败:', e)
        this.hostList = []
        this.pagination.count = 0
      } finally {
        this.loading = false
      }
    },
    handlePageChange(page) {
      this.pagination.current = page
      this.loadHostList()
    },
    handlePageLimitChange(limit) {
      this.pagination.limit = limit
      this.pagination.current = 1
      this.loadHostList()
    },
    getStatus(row) {
      // 根据外网IP判断简单状态
      return row.bk_host_outerip ? 'running' : 'stopped'
    },
    statusText(status) {
      const map = {
        running: '运行中',
        stopped: '未配置'
      }
      return map[status] || status
    }
  }
}
</script>

<style lang="scss" scoped>
.host-list-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid $cmdbLayoutBorderColor;

  .node-title {
    display: flex;
    align-items: center;

    .node-icon {
      display: inline-flex;
      width: 24px;
      height: 24px;
      line-height: 24px;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      background-color: #c4c6cc;
      font-size: 12px;
      color: #fff;
      margin-right: 8px;
    }

    .node-name {
      font-size: 16px;
      font-weight: 500;
      color: $cmdbTextColor;
    }
  }

  .node-path {
    font-size: 12px;
    color: $grayColor;
  }
}

.panel-body {
  flex: 1;
  overflow: auto;
}

.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 12px;

  &.running {
    background-color: #e5f6ea;
    color: #14a568;
  }

  &.stopped {
    background-color: #feecec;
    color: #ea3636;
  }
}
</style>