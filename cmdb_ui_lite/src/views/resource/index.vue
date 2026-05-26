<template>
  <div class="cmdb-page">
    <div class="page-header">
      <h2>资源目录</h2>
    </div>

    <div v-bkloading="{ isLoading: loading }" class="resource-content">
      <div v-if="error" class="error-message">
        <i class="bk-icon icon-cc-tips"></i>
        <span>{{ error }}</span>
        <bk-button text theme="primary" @click="loadData">重试</bk-button>
      </div>

      <template v-else>
        <div
          v-for="classification in classificationsWithModels"
          :key="classification.bk_classification_id"
          class="classification-section">
          <div class="classification-header">
            <i :class="getClassificationIcon(classification.bk_classification_id)"></i>
            <h3>{{ classification.bk_classification_name }}</h3>
            <span class="model-count">{{ classification.bk_objects?.length || 0 }} 个模型</span>
          </div>

          <div class="resource-grid">
            <div
              v-for="model in classification.bk_objects"
              :key="model.bk_obj_id"
              class="resource-card"
              :class="{ 'is-hover': hoveredModel === model.bk_obj_id }"
              @click="handleModelClick(model)"
              @mouseenter="hoveredModel = model.bk_obj_id"
              @mouseleave="hoveredModel = null">
              <div class="card-icon" :class="getIconClass(model.bk_obj_id)">
                <i :class="'bk-icon ' + (model.bk_obj_icon || 'icon-cc-default')"></i>
              </div>
              <div class="card-info">
                <h4>{{ model.bk_obj_name }}</h4>
                <p>{{ getModelDescription(model.bk_obj_id) }}</p>
              </div>
              <div class="card-arrow">
                <i class="bk-icon icon-cc-arrow-square-right"></i>
              </div>
            </div>
          </div>
        </div>

        <div v-if="classificationsWithModels.length === 0 && !loading" class="empty-state">
          <i class="bk-icon icon-cc-search-list"></i>
          <p>暂无可用的资源模型</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
import { mapState, mapGetters, mapActions } from 'vuex'

export default {
  name: 'ResourceIndex',
  data() {
    return {
      hoveredModel: null
    }
  },
  computed: {
    ...mapState('objectModelClassify', {
      loading: 'loading',
      error: 'error'
    }),
    ...mapGetters('objectModelClassify', {
      classifications: 'classifications',
      classificationsWithModels: 'classifications'
    })
  },
  async mounted() {
    await this.loadData()
  },
  methods: {
    ...mapActions('objectModelClassify', [
      'searchClassificationsObjects'
    ]),

    async loadData() {
      try {
        await this.searchClassificationsObjects()
      } catch (error) {
        console.error('[ResourceIndex] 加载数据失败:', error)
      }
    },

    handleModelClick(model) {
      console.log('[ResourceIndex] 点击模型:', model.bk_obj_id, model.bk_obj_name)
      this.$router.push({
        name: 'ResourceInstanceList',
        params: { objId: model.bk_obj_id }
      })
    },

    getIconClass(objId) {
      const iconMap = {
        bk_switch: 'switch-icon',
        bk_host: 'host-icon',
        bk_slb: 'lb-icon',
        bk_slb_server: 'server-icon',
        bk_slb_listener: 'listener-icon'
      }
      return iconMap[objId] || 'default-icon'
    },

    getClassificationIcon(classificationId) {
      const iconMap = {
        bk_network: 'bk-icon icon-cc-network',
        bk_host_manage: 'bk-icon icon-cc-host',
        bk_loadbalance: 'bk-icon icon-cc-loadbalance'
      }
      return iconMap[classificationId] || 'bk-icon icon-cc-app'
    },

    getModelDescription(objId) {
      const descMap = {
        bk_switch: '交换机网络设备管理',
        bk_host: '管理所有主机资源',
        bk_slb: '负载均衡器实例',
        bk_slb_server: '后端服务器实例',
        bk_slb_listener: '负载均衡监听器'
      }
      return descMap[objId] || '查看和管理实例'
    }
  }
}
</script>

<style lang="scss" scoped>
.cmdb-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;

  h2 {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }
}

.resource-content {
  min-height: 200px;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px;
  background: #fff1f0;
  border: 1px solid #ffa198;
  border-radius: 4px;
  color: #ea3636;

  .bk-icon {
    font-size: 16px;
  }
}

.classification-section {
  margin-bottom: 32px;

  &:last-child {
    margin-bottom: 0;
  }
}

.classification-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #eaeaea;

  .bk-icon {
    font-size: 20px;
    color: #3a84ff;
  }

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }

  .model-count {
    font-size: 12px;
    color: #979ba5;
    background: #f0f1f5;
    padding: 2px 8px;
    border-radius: 10px;
  }
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.resource-card {
  background: #fff;
  border-radius: 4px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  border: 1px solid #eaeaea;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: transparent;
    transition: background 0.2s;
  }

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
    border-color: #3a84ff;

    &::before {
      background: #3a84ff;
    }

    .card-arrow {
      opacity: 1;
      transform: translateX(0);
    }
  }

  .card-icon {
    width: 48px;
    height: 48px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    color: #fff;
    flex-shrink: 0;

    &.host-icon {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    &.switch-icon {
      background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }

    &.lb-icon {
      background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }

    &.server-icon {
      background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }

    &.listener-icon {
      background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    }

    &.default-icon {
      background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
      color: #63656e;
    }

    .bk-icon {
      font-size: 24px;
    }
  }

  .card-info {
    flex: 1;
    min-width: 0;

    h4 {
      font-size: 15px;
      font-weight: 600;
      color: #303133;
      margin: 0 0 4px 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    p {
      font-size: 13px;
      color: #909399;
      margin: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }

  .card-arrow {
    flex-shrink: 0;
    opacity: 0;
    transform: translateX(-10px);
    transition: all 0.2s;

    .bk-icon {
      font-size: 20px;
      color: #3a84ff;
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #979ba5;

  .bk-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }

  p {
    font-size: 14px;
    margin: 0;
  }
}
</style>
