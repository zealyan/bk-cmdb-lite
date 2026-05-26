<template>
  <div class="page-header">
    <h2>主机列表</h2>
  </div>

  <div class="card search-bar">
    <el-form :inline="true" :model="searchForm">
      <el-form-item label="IP/云区域:IP">
        <el-input v-model="searchForm.ip" placeholder="请输入IP，多个用逗号分隔" clearable style="width: 300px" />
      </el-form-item>
      <el-form-item label="业务">
        <el-select v-model="searchForm.bizId" placeholder="请选择业务" clearable style="width: 200px">
          <el-option label="全部" :value="0" />
          <el-option label="蓝鲸" :value="2" />
          <el-option label="配置平台" :value="3" />
        </el-select>
      </el-form-item>
      <el-form-item label="主机状态">
        <el-select v-model="searchForm.status" placeholder="请选择状态" clearable style="width: 150px">
          <el-option label="正常" :value="1" />
          <el-option label="异常" :value="2" />
          <el-option label="未知" :value="3" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>

  <div class="card table-container">
    <div class="table-toolbar">
      <el-button type="primary" @click="handleImport">
        <el-icon><Upload /></el-icon>
        导入
      </el-button>
      <el-button type="primary" @click="handleExport">
        <el-icon><Download /></el-icon>
        导出
      </el-button>
      <el-button @click="handleTransfer">
        <el-icon><Right /></el-icon>
        转移
      </el-button>
      <el-button @click="handleEditMultiple">
        <el-icon><Edit /></el-icon>
        批量编辑
      </el-button>
    </div>

    <el-table :data="tableData" stripe v-loading="loading" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" />
      <el-table-column prop="bk_host_innerip" label="内网IP" width="150">
        <template #default="{ row }">
          <el-link type="primary" @click="handleViewHost(row)">{{ row.bk_host_innerip }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="bk_cloud_id" label="云区域" width="100" />
      <el-table-column prop="bk_biz_name" label="所属业务" width="120" />
      <el-table-column prop="bk_module_name" label="模块" width="120" />
      <el-table-column prop="bk_set_name" label="集群" width="120" />
      <el-table-column prop="bk_os_name" label="操作系统" width="100" />
      <el-table-column prop="bk_cpu_module" label="CPU型号" width="150" />
      <el-table-column prop="bk_mem" label="内存(MB)" width="100" align="right" />
      <el-table-column prop="bk_disk" label="磁盘(GB)" width="100" align="right" />
      <el-table-column prop="bk_cloud_inst_id" label="云主机ID" width="180" show-overflow-tooltip />
      <el-table-column prop="bk_host_outerip" label="外网IP" width="150" show-overflow-tooltip />
      <el-table-column prop="last_time" label="更新时间" width="180" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleViewHost(row)">查看</el-button>
          <el-button link type="primary" @click="handleEditHost(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <span class="selected-info">已选择 {{ selectedRows.length }} 项</span>
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { Upload, Download, Right, Edit } from '@element-plus/icons-vue'

const loading = ref(false)
const selectedRows = ref([])

const searchForm = reactive({
  ip: '',
  bizId: 0,
  status: null
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 100
})

const tableData = ref([
  {
    bk_host_id: 1,
    bk_host_innerip: '10.0.0.1',
    bk_cloud_id: 0,
    bk_biz_name: '蓝鲸',
    bk_module_name: '接入层',
    bk_set_name: '正式集群',
    bk_os_name: 'Linux',
    bk_cpu_module: 'Intel Xeon',
    bk_mem: 8192,
    bk_disk: 500,
    bk_cloud_inst_id: 'ins-12345678',
    bk_host_outerip: '123.123.123.1',
    last_time: '2024-03-15 14:30:00'
  },
  {
    bk_host_id: 2,
    bk_host_innerip: '10.0.0.2',
    bk_cloud_id: 0,
    bk_biz_name: '蓝鲸',
    bk_module_name: '应用层',
    bk_set_name: '正式集群',
    bk_os_name: 'Linux',
    bk_cpu_module: 'Intel Xeon',
    bk_mem: 16384,
    bk_disk: 1000,
    bk_cloud_inst_id: 'ins-23456789',
    bk_host_outerip: '123.123.123.2',
    last_time: '2024-03-15 14:25:00'
  },
  {
    bk_host_id: 3,
    bk_host_innerip: '10.0.0.3',
    bk_cloud_id: 1,
    bk_biz_name: '配置平台',
    bk_module_name: '测试模块',
    bk_set_name: '测试集群',
    bk_os_name: 'Linux',
    bk_cpu_module: 'Intel Xeon',
    bk_mem: 4096,
    bk_disk: 200,
    bk_cloud_inst_id: 'ins-34567890',
    bk_host_outerip: '',
    last_time: '2024-03-15 14:20:00'
  }
])

const handleSearch = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
  }, 500)
}

const handleReset = () => {
  searchForm.ip = ''
  searchForm.bizId = 0
  searchForm.status = null
}

const handleSelectionChange = (rows) => {
  selectedRows.value = rows
}

const handleImport = () => {
  console.log('import')
}

const handleExport = () => {
  console.log('export')
}

const handleTransfer = () => {
  console.log('transfer', selectedRows.value)
}

const handleEditMultiple = () => {
  console.log('edit multiple', selectedRows.value)
}

const handleViewHost = (row) => {
  console.log('view host', row)
}

const handleEditHost = (row) => {
  console.log('edit host', row)
}

const handleSizeChange = (val) => {
  pagination.pageSize = val
  handleSearch()
}

const handlePageChange = (val) => {
  pagination.page = val
  handleSearch()
}
</script>

<style lang="scss" scoped>
.search-bar {
  padding: 16px;
  margin-bottom: 16px;
}

.table-container {
  padding: 16px;
  
  .table-toolbar {
    margin-bottom: 16px;
    display: flex;
    gap: 8px;
  }
  
  .pagination {
    margin-top: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .selected-info {
      color: var(--text-secondary);
      font-size: 14px;
    }
  }
}
</style>
