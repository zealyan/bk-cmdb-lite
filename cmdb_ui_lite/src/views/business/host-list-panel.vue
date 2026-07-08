<template>
  <div class="host-list-panel">
    <div class="panel-header">
      <span class="node-title">
        <span class="node-icon">{{ nodeIconText }}</span>
        <span class="node-name">{{ node.data.bk_inst_name }}</span>
      </span>
      <span class="node-path">{{ nodePath }}</span>
    </div>
    <div class="panel-body">
      <bk-table
        :data="mockHostList"
        :pagination="pagination"
        @page-change="handlePageChange"
        @page-limit-change="handlePageLimitChange">
        <bk-table-column prop="bk_host_id" label="主机ID" width="100"></bk-table-column>
        <bk-table-column prop="bk_host_name" label="主机名称" min-width="150"></bk-table-column>
        <bk-table-column prop="bk_host_innerip" label="内网IP" width="150"></bk-table-column>
        <bk-table-column prop="bk_host_outerip" label="外网IP" width="150"></bk-table-column>
        <bk-table-column prop="bk_os_name" label="操作系统" width="120"></bk-table-column>
        <bk-table-column prop="bk_cloud_id" label="云区域" width="100"></bk-table-column>
        <bk-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <span :class="['status-tag', row.status]">{{ statusText(row.status) }}</span>
          </template>
        </bk-table-column>
      </bk-table>
    </div>
  </div>
</template>

<script>
// 模拟主机数据
const generateMockHosts = (count, nodeId) => {
  const hosts = []
  const statusList = ['running', 'stopped', 'maintenance']
  const osList = ['CentOS 7.9', 'Ubuntu 20.04', 'Debian 11', 'Windows Server 2019', 'Rocky Linux 8']
  
  for (let i = 1; i <= count; i++) {
    hosts.push({
      bk_host_id: nodeId * 1000 + i,
      bk_host_name: `host-${nodeId}-${i}`,
      bk_host_innerip: `192.168.${Math.floor(nodeId / 10)}.${i}`,
      bk_host_outerip: nodeId % 2 === 0 ? `10.0.${Math.floor(nodeId / 10)}.${i}` : '',
      bk_os_name: osList[Math.floor(Math.random() * osList.length)],
      bk_cloud_id: 0,
      status: statusList[Math.floor(Math.random() * statusList.length)]
    })
  }
  return hosts
}

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
      mockHostList: []
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
      while (current) {
        path.unshift(current.data.bk_inst_name)
        current = current.parent
      }
      return path.join(' / ')
    },
    hostCount() {
      return this.node.data.host_count || 0
    }
  },
  watch: {
    node: {
      immediate: true,
      handler(node) {
        if (node) {
          this.loadHostList()
        }
      }
    }
  },
  methods: {
    loadHostList() {
      // 模拟加载主机列表
      const nodeId = this.node.data.bk_inst_id
      const hostCount = Math.min(this.hostCount, 50) // 模拟最多50条数据
      const allHosts = generateMockHosts(hostCount, nodeId)
      
      this.pagination.count = hostCount
      this.mockHostList = allHosts.slice(
        (this.pagination.current - 1) * this.pagination.limit,
        this.pagination.current * this.pagination.limit
      )
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
    statusText(status) {
      const map = {
        running: '运行中',
        stopped: '已停止',
        maintenance: '维护中'
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

  &.maintenance {
    background-color: #fff3e1;
    color: #ff9c02;
  }
}
</style>