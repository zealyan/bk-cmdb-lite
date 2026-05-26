<template>
  <div class="page-header">
    <h2>业务列表</h2>
  </div>

  <div class="card search-bar">
    <el-form :inline="true" :model="searchForm">
      <el-form-item label="业务名称">
        <el-input v-model="searchForm.name" placeholder="请输入业务名称" clearable />
      </el-form-item>
      <el-form-item label="业务ID">
        <el-input v-model="searchForm.id" placeholder="请输入业务ID" clearable />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>

  <div class="card table-container">
    <div class="table-toolbar">
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        新建业务
      </el-button>
    </div>

    <el-table :data="tableData" stripe v-loading="loading">
      <el-table-column prop="bk_biz_id" label="业务ID" width="100" />
      <el-table-column prop="bk_biz_name" label="业务名称" min-width="150" />
      <el-table-column prop="bk_biz_tester" label="运维人员" width="120" />
      <el-table-column prop="bk_biz_productor" label="产品人员" width="120" />
      <el-table-column prop="bk_biz_developer" label="开发人员" width="120" />
      <el-table-column prop="bk_biz_module_num" label="模块数" width="80" align="center" />
      <el-table-column prop="bk_biz_set_num" label="集群数" width="80" align="center" />
      <el-table-column prop="bk_biz_host_num" label="主机数" width="80" align="center" />
      <el-table-column prop="create_time" label="创建时间" width="180" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleView(row)">查看</el-button>
          <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button link type="primary" @click="handleTopology(row)">拓扑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
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
import { Plus } from '@element-plus/icons-vue'

const loading = ref(false)
const searchForm = reactive({
  name: '',
  id: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const tableData = ref([
  {
    bk_biz_id: 2,
    bk_biz_name: '蓝鲸',
    bk_biz_tester: 'admin',
    bk_biz_productor: 'admin',
    bk_biz_developer: 'admin',
    bk_biz_module_num: 12,
    bk_biz_set_num: 5,
    bk_biz_host_num: 156,
    create_time: '2024-01-15 10:30:00'
  },
  {
    bk_biz_id: 3,
    bk_biz_name: '配置平台',
    bk_biz_tester: 'admin',
    bk_biz_productor: 'admin',
    bk_biz_developer: 'admin',
    bk_biz_module_num: 8,
    bk_biz_set_num: 3,
    bk_biz_host_num: 42,
    create_time: '2024-02-20 14:20:00'
  }
])

const handleSearch = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
  }, 500)
}

const handleReset = () => {
  searchForm.name = ''
  searchForm.id = ''
}

const handleCreate = () => {
  console.log('create business')
}

const handleView = (row) => {
  console.log('view', row)
}

const handleEdit = (row) => {
  console.log('edit', row)
}

const handleTopology = (row) => {
  console.log('topology', row)
}

const handleDelete = (row) => {
  console.log('delete', row)
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
  }
  
  .pagination {
    margin-top: 16px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
