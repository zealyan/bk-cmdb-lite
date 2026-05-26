<template>
  <div class="cmdb-page">
    <div class="page-header">
      <div class="breadcrumb">
        <router-link to="/resource">资源</router-link>
        <span class="separator">/</span>
        <router-link to="/resource/host">主机</router-link>
        <span class="separator">/</span>
        <span>{{ host?.host_name || hostId }}</span>
      </div>
      <h2>{{ host?.host_name || '主机详情' }}</h2>
    </div>

    <div class="detail-container" v-if="host">
      <bk-box>
        <div class="detail-card">
          <h3>基本信息</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>主机ID</label>
              <span>{{ host.id }}</span>
            </div>
            <div class="detail-item">
              <label>主机名称</label>
              <span>{{ host.host_name }}</span>
            </div>
            <div class="detail-item">
              <label>内网IP</label>
              <span>{{ host.inner_ip }}</span>
            </div>
            <div class="detail-item">
              <label>外网IP</label>
              <span>{{ host.outer_ip || '-' }}</span>
            </div>
            <div class="detail-item">
              <label>管控区域</label>
              <span>{{ host.cloud_area }}</span>
            </div>
            <div class="detail-item">
              <label>云服务商</label>
              <span>{{ host.cloud_vendor }}</span>
            </div>
            <div class="detail-item">
              <label>操作系统</label>
              <span>{{ host.os_type }}</span>
            </div>
            <div class="detail-item">
              <label>状态</label>
              <span :class="['status-badge', `status-${host.status}`]">
                {{ host.status === 'running' ? '运行中' : '已关机' }}
              </span>
            </div>
          </div>
        </div>
      </bk-box>

      <bk-box>
        <div class="detail-card">
          <h3>硬件信息</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>CPU</label>
              <span>{{ host.cpu }}</span>
            </div>
            <div class="detail-item">
              <label>内存</label>
              <span>{{ host.memory }}</span>
            </div>
            <div class="detail-item">
              <label>磁盘</label>
              <span>{{ host.disk }}</span>
            </div>
            <div class="detail-item">
              <label>主机标识</label>
              <span>{{ host.bk_host_innerip }}</span>
            </div>
          </div>
        </div>
      </bk-box>

      <bk-box>
        <div class="detail-card">
          <h3>业务信息</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>所属业务</label>
              <span>{{ host.biz_name }}</span>
            </div>
            <div class="detail-item">
              <label>所属模块</label>
              <span>{{ host.module }}</span>
            </div>
            <div class="detail-item">
              <label>所属集群</label>
              <span>{{ host.set }}</span>
            </div>
            <div class="detail-item">
              <label>创建时间</label>
              <span>2024-01-15 10:30:00</span>
            </div>
          </div>
        </div>
      </bk-box>

      <div class="detail-actions">
        <bk-button theme="default">编辑</bk-button>
        <bk-button theme="default">转移</bk-button>
        <bk-button theme="default">删除</bk-button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ResourceHostDetails',
  data () {
    return {
      hostId: '',
      host: null,
      mockData: {
        1: {
          id: 1,
          host_name: 'web-server-01',
          inner_ip: '192.168.1.101',
          outer_ip: '10.0.0.101',
          cloud_area: '北京一区',
          cloud_vendor: '腾讯云',
          os_type: 'Linux CentOS 7.6',
          status: 'running',
          cpu: '8核',
          memory: '16GB',
          disk: '500GB SSD',
          bk_host_innerip: '192.168.1.101',
          biz_name: '游戏业务',
          module: 'Web模块',
          set: '游戏服务器集群'
        },
        2: {
          id: 2,
          host_name: 'web-server-02',
          inner_ip: '192.168.1.102',
          outer_ip: '10.0.0.102',
          cloud_area: '北京一区',
          cloud_vendor: '腾讯云',
          os_type: 'Linux CentOS 7.6',
          status: 'running',
          cpu: '8核',
          memory: '16GB',
          disk: '500GB SSD',
          bk_host_innerip: '192.168.1.102',
          biz_name: '游戏业务',
          module: 'Web模块',
          set: '游戏服务器集群'
        },
        3: {
          id: 3,
          host_name: 'db-server-01',
          inner_ip: '192.168.1.103',
          outer_ip: '',
          cloud_area: '上海一区',
          cloud_vendor: '阿里云',
          os_type: 'Linux Ubuntu 20.04',
          status: 'stopped',
          cpu: '16核',
          memory: '64GB',
          disk: '1TB SSD',
          bk_host_innerip: '192.168.1.103',
          biz_name: '电商业务',
          module: '数据库模块',
          set: '数据库集群'
        },
        4: {
          id: 4,
          host_name: 'cache-server-01',
          inner_ip: '192.168.1.104',
          outer_ip: '10.0.0.104',
          cloud_area: '上海一区',
          cloud_vendor: '阿里云',
          os_type: 'Linux CentOS 8.0',
          status: 'running',
          cpu: '8核',
          memory: '32GB',
          disk: '256GB SSD',
          bk_host_innerip: '192.168.1.104',
          biz_name: '电商业务',
          module: '缓存模块',
          set: '缓存集群'
        },
        5: {
          id: 5,
          host_name: 'app-server-01',
          inner_ip: '192.168.1.105',
          outer_ip: '10.0.0.105',
          cloud_area: '广州一区',
          cloud_vendor: '华为云',
          os_type: 'Linux CentOS 7.9',
          status: 'running',
          cpu: '4核',
          memory: '8GB',
          disk: '200GB SSD',
          bk_host_innerip: '192.168.1.105',
          biz_name: '云服务',
          module: '应用模块',
          set: '应用集群'
        }
      }
    }
  },
  mounted () {
    this.hostId = this.$route.params.id
    this.host = this.mockData[this.hostId] || {
      id: this.hostId,
      host_name: `host-${this.hostId}`,
      inner_ip: `192.168.1.${100 + parseInt(this.hostId)}`,
      outer_ip: '',
      cloud_area: '未知区域',
      cloud_vendor: '未知厂商',
      os_type: '-',
      status: 'unknown',
      cpu: '-',
      memory: '-',
      disk: '-',
      bk_host_innerip: '-',
      biz_name: '-',
      module: '-',
      set: '-'
    }
  }
}
</script>

<style lang="scss" scoped>
.cmdb-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;

  .breadcrumb {
    margin-bottom: 8px;
    font-size: 13px;
    color: #909399;

    a {
      color: #175ee5;
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }

    .separator {
      margin: 0 8px;
    }
  }

  h2 {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }
}

.detail-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-card {
  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 16px 0;
    padding-bottom: 12px;
    border-bottom: 1px solid #eaeaea;
  }
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.detail-item {
  label {
    display: block;
    font-size: 13px;
    color: #909399;
    margin-bottom: 4px;
  }

  span {
    font-size: 14px;
    color: #303133;
  }
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

  &.status-unknown {
    background: #fff7e6;
    color: #fa8c16;
  }
}

.detail-actions {
  display: flex;
  gap: 12px;
}
</style>
