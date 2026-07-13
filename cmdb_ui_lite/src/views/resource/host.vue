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
        <icon-button
          class="ml10"
          icon="icon-cc-funnel"
          v-bk-tooltips.top="'高级筛选'"
          @click="handleSetFilters">
        </icon-button>
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
import IconButton from '@/components/ui/button/icon-button.vue'
import FilterForm from '@/components/filters/filter-form.js'
import FilterStore, { setupFilterStore } from '@/components/filters/store'
import { modelAPI } from '@/api/client'

export default {
  name: 'ResourceHost',
  components: {
    IconButton
  },
  data () {
    return {
      searchKeyword: '',
      hosts: [],
      paginationConfig: {
        count: 0,
        limit: 10,
        current: 1,
        'limit-list': [10, 20, 50, 100, 500]
      },
      unwatchFilter: null
    }
  },
  mounted() {
    this.initFilterStore()
    this.loadHostList()
  },
  beforeDestroy() {
    if (this.unwatchFilter) {
      this.unwatchFilter()
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
    async initFilterStore() {
      await setupFilterStore({
        bk_biz_id: 0,
        modelIds: ['bk_host'],
        searchHandler: this.searchHandler.bind(this)
      })
      this.unwatchFilter = this.$watch(
        () => [FilterStore.selected, FilterStore.condition, FilterStore.IP],
        () => {
          this.searchHandler()
        },
        { deep: true }
      )
    },
    searchHandler() {
      this.loadHostList()
    },
    async loadHostList() {
      try {
        const filterCondition = FilterStore.condition
        const filterIP = FilterStore.IP
        const filterSelected = FilterStore.selected || []
        
        const params = {
          page: this.paginationConfig.current,
          page_size: this.paginationConfig.limit
        }
        
        if (Object.keys(filterCondition).length > 0) {
          params.condition = []
          Object.keys(filterCondition).forEach(key => {
            const cond = filterCondition[key]
            const val = cond.value
            if (val === null || val === undefined || val === '') return
            
            const property = filterSelected.find(p => p.bk_property_id === key)
            const modelId = property ? property.bk_obj_id : 'bk_host'
            
            let submitValue = val
            if (['$in', '$nin'].includes(cond.operator)) {
              if (typeof val === 'string') {
                submitValue = val.split(/[\n,，;；]/).map(s => s.trim()).filter(s => s.length > 0)
              } else if (!Array.isArray(val)) {
                submitValue = [val]
              }
            }
            
            const existing = params.condition.find(c => c.bk_obj_id === modelId)
            if (existing) {
              existing.condition.push({
                field: key,
                operator: cond.operator || '$eq',
                value: submitValue
              })
            } else {
              params.condition.push({
                bk_obj_id: modelId,
                fields: [],
                condition: [{
                  field: key,
                  operator: cond.operator || '$eq',
                  value: submitValue
                }]
              })
            }
          })
        }
        
        const result = await modelAPI.listInstances('bk_host', params)
        if (result && result.data) {
          this.hosts = result.data.info || []
          this.paginationConfig.count = result.data.count || 0
        }
      } catch (error) {
        console.error('加载主机列表失败:', error)
        this.$bkMessage({
          message: '加载主机列表失败',
          theme: 'error'
        })
      }
    },
    handleSearch (value) {
      this.searchKeyword = value
      this.paginationConfig.current = 1
    },
    handleSetFilters () {
      FilterForm.show()
    },
    handleRefresh () {
      this.loadHostList()
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
      this.loadHostList()
    },
    handleLimitChange (limit) {
      this.paginationConfig.limit = limit
      this.paginationConfig.current = 1
      this.loadHostList()
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
  display: flex;
  align-items: center;
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
