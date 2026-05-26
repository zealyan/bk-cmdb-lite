<template>
  <div class="page-header">
    <h2>业务拓扑</h2>
  </div>

  <div class="card topology-container">
    <div class="topology-toolbar">
      <el-select v-model="selectedBiz" placeholder="请选择业务" @change="handleBizChange">
        <el-option label="蓝鲸" :value="2" />
        <el-option label="配置平台" :value="3" />
      </el-select>
      <el-button @click="handleRefresh">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <div class="topology-view">
      <div class="topology-tree">
        <el-tree
          :data="treeData"
          :props="treeProps"
          @node-click="handleNodeClick"
          node-key="id"
          default-expand-all
        >
          <template #default="{ node, data }">
            <span class="tree-node">
              <el-icon :color="getNodeColor(data.type)">
                <component :is="getNodeIcon(data.type)" />
              </el-icon>
              <span class="node-label">{{ node.label }}</span>
              <span class="node-count" v-if="data.count">({{ data.count }})</span>
            </span>
          </template>
        </el-tree>
      </div>

      <div class="topology-info">
        <el-empty v-if="!selectedNode" description="请选择节点查看详情" />
        <div v-else class="node-detail">
          <h3>{{ selectedNode.bk_inst_name }}</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="节点类型">
              {{ selectedNode.bk_obj_id }}
            </el-descriptions-item>
            <el-descriptions-item label="节点ID">
              {{ selectedNode.bk_inst_id }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { Refresh, OfficeBuilding, Grid, Box } from '@element-plus/icons-vue'

const selectedBiz = ref(2)
const selectedNode = ref(null)

const treeProps = {
  children: 'children',
  label: 'bk_inst_name'
}

const treeData = ref([
  {
    id: 'biz-2',
    bk_inst_id: 2,
    bk_inst_name: '蓝鲸',
    bk_obj_id: 'biz',
    type: 'biz',
    count: 156,
    children: [
      {
        id: 'set-1',
        bk_inst_id: 1,
        bk_inst_name: '正式集群',
        bk_obj_id: 'set',
        type: 'set',
        count: 100,
        children: [
          { id: 'module-1', bk_inst_id: 1, bk_inst_name: '接入层', bk_obj_id: 'module', type: 'module', count: 50 },
          { id: 'module-2', bk_inst_id: 2, bk_inst_name: '应用层', bk_obj_id: 'module', type: 'module', count: 30 },
          { id: 'module-3', bk_inst_id: 3, bk_inst_name: '存储层', bk_obj_id: 'module', type: 'module', count: 20 }
        ]
      },
      {
        id: 'set-2',
        bk_inst_id: 2,
        bk_inst_name: '测试集群',
        bk_obj_id: 'set',
        type: 'set',
        count: 56,
        children: [
          { id: 'module-4', bk_inst_id: 4, bk_inst_name: '测试模块', bk_obj_id: 'module', type: 'module', count: 56 }
        ]
      }
    ]
  }
])

const getNodeIcon = (type) => {
  const icons = {
    biz: OfficeBuilding,
    set: Grid,
    module: Box
  }
  return icons[type] || Box
}

const getNodeColor = (type) => {
  const colors = {
    biz: '#3a84ff',
    set: '#699df4',
    module: '#8fa0b9'
  }
  return colors[type] || '#8fa0b9'
}

const handleBizChange = () => {
  console.log('biz change', selectedBiz.value)
}

const handleRefresh = () => {
  console.log('refresh')
}

const handleNodeClick = (data) => {
  selectedNode.value = data
}
</script>

<style lang="scss" scoped>
.topology-container {
  height: calc(100vh - 180px);
  
  .topology-toolbar {
    padding: 16px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    gap: 12px;
  }
  
  .topology-view {
    display: flex;
    height: calc(100% - 60px);
    
    .topology-tree {
      width: 300px;
      border-right: 1px solid var(--border-color);
      padding: 16px;
      overflow-y: auto;
      
      .tree-node {
        display: flex;
        align-items: center;
        gap: 8px;
        
        .node-label {
          flex: 1;
        }
        
        .node-count {
          color: var(--text-secondary);
          font-size: 12px;
        }
      }
    }
    
    .topology-info {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      
      .node-detail {
        h3 {
          margin-bottom: 16px;
          font-size: 16px;
        }
      }
    }
  }
}
</style>
