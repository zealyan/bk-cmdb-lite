<template>
  <div class="cmdb-page">
    <div class="page-header">
      <h2>主机列表</h2>
      <div class="header-actions">
        <bk-button theme="default" @click="handleRefresh">刷新</bk-button>
        <bk-button theme="primary" @click="handleAdd">新增主机</bk-button>
      </div>
    </div>

    <bk-box>
      <div class="search-bar">
        <bk-input
          v-model="searchKeyword"
          placeholder="搜索主机IP或名称..."
          :right-icon="'bk-icon icon-search'"
          style="width: 300px;"
          @change="handleSearch"
        />
      </div>

      <bk-table
        :data="filteredHosts"
        :pagination="paginationConfig"
        @page-change="handlePageChange"
        @page-limit-change="handleLimitChange"
      >
        <bk-table-column label="主机ID" prop="id" width="100">
          <template #default="{ row }">
            <bk-button
              :text="true"
              :primary="true"
              @click="handleView(row)">
              {{ row.id }}
            </bk-button>
          </template>
        </bk-table-column>
        <bk-table-column label="内网IP" prop="inner_ip" />
        <bk-table-column label="外网IP" prop="outer_ip">
          <template #default="{ row }">
            {{ row.outer_ip || '-' }}
          </template>
        </bk-table-column>
        <bk-table-column label="管控区域" prop="cloud_area" />
        <bk-table-column label="主机名称" prop="host_name" />
        <bk-table-column label="云服务商" prop="cloud_vendor" />
        <bk-table-column label="状态" prop="status">
          <template #default="{ row }">
            <span :class="['status-badge', `status-${row.status}`]">
              {{ row.status === 'running' ? '运行中' : '已关机' }}
            </span>
          </template>
        </bk-table-column>
        <bk-table-column label="操作" width="100">
          <template #default="{ row }">
            <bk-button :text="true" @click="handleView(row)">查看</bk-button>
          </template>
        </bk-table-column>
      </bk-table>
    </bk-box>
  </div>
</template>

<script>
export default {
  name: 'ResourceHost',
  data () {
    return {
      searchKeyword: '',
      hosts: [
        {
          id: 1,
          inner_ip: '192.168.1.101',
          outer_ip: '10.0.0.101',
          cloud_area: '北京一区',
          host_name: 'web-server-01',
          cloud_vendor: '腾讯云',
          status: 'running'
        },
        {
          id: 2,
          inner_ip: '192.168.1.102',
          outer_ip: '10.0.0.102',
          cloud_area: '北京一区',
          host_name: 'web-server-02',
          cloud_vendor: '腾讯云',
          status: 'running'
        },
        {
          id: 3,
          inner_ip: '192.168.1.103',
          outer_ip: '',
          cloud_area: '上海一区',
          host_name: 'db-server-01',
          cloud_vendor: '阿里云',
          status: 'stopped'
        },
        {
          id: 4,
          inner_ip: '192.168.1.104',
          outer_ip: '10.0.0.104',
          cloud_area: '上海一区',
          host_name: 'cache-server-01',
          cloud_vendor: '阿里云',
          status: 'running'
        },
        {
          id: 5,
          inner_ip: '192.168.1.105',
          outer_ip: '10.0.0.105',
          cloud_area: '广州一区',
          host_name: 'app-server-01',
          cloud_vendor: '华为云',
          status: 'running'
        }
      ],
      paginationConfig: {
        count: 5,
        limit: 10,
        current: 1
      }
    }
  },
  computed: {
    filteredHosts () {
      if (!this.searchKeyword) return this.hosts
      const keyword = this.searchKeyword.toLowerCase()
      return this.hosts.filter(host =>
        host.inner_ip.includes(keyword) ||
        host.host_name.toLowerCase().includes(keyword)
      )
    }
  },
  methods: {
    handleSearch (value) {
      this.searchKeyword = value
      this.paginationConfig.current = 1
    },
    handleRefresh () {
      this.$bkMessage({
        message: '刷新成功',
        theme: 'success'
      })
    },
    handleAdd () {
      this.$bkInfo({
        title: '新增主机',
        content: '新增主机功能开发中...'
      })
    },
    handleView (host) {
      this.$router.push({
        name: 'ResourceHostDetails',
        params: {
          id: host.id
        }
      })
    },
    handlePageChange (page) {
      this.paginationConfig.current = page
    },
    handleLimitChange (limit) {
      this.paginationConfig.limit = limit
    }
  }
}
</script>

<style lang="scss" scoped>
.cmdb-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  h2 {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }

  .header-actions {
    display: flex;
    gap: 8px;
  }
}

.search-bar {
  margin-bottom: 16px;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;

  &.status-running {
    background: #e6f7e6;
    color: #52c41a;
  }

  &.status-stopped {
    background: #f5f5f5;
    color: #909399;
  }
}
</style>
