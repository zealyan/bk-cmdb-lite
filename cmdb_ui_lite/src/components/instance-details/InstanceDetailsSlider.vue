<template>
  <bk-sideslider
    :is-show.sync="visible"
    :title="title"
    :width="sliderWidth"
    transfer
    ext-cls="instance-details-sideslider"
    @update:isShow="handleClose">
    <div slot="content" class="details-content" v-bkloading="{ isLoading: loading }">
      <div v-if="error" class="details-error">
        <p>{{ error }}</p>
      </div>
      <cmdb-details
        v-else
        :inst="instanceData"
        :properties="properties"
        :property-groups="propertyGroups"
        :show-options="false"
        :invisible-properties="invisibleProperties">
      </cmdb-details>
    </div>
  </bk-sideslider>
</template>

<script>
import Vue from 'vue'
import CmdbDetails from '../ui/details/CmdbDetails.vue'
import instanceAPI from '@/api/instance'
import modelAttributeAPI from '@/api/modelAttribute'

export default {
  name: 'InstanceDetailsSlider',

  components: {
    CmdbDetails
  },

  data() {
    return {
      visible: false,
      title: '',
      objId: '',
      instId: null,
      instanceData: {},
      properties: [],
      propertyGroups: [],
      loading: false,
      error: null,
      invisibleProperties: [],
      windowWidth: window.innerWidth
    }
  },
  computed: {
    sliderWidth() {
      if (this.isMobile) {
        return '100%';
      }
      return 700;
    },
    isMobile() {
      return this.windowWidth < 768;
    }
  },
  mounted() {
    window.addEventListener('resize', this.handleResize);
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.handleResize);
  },

  methods: {
    handleResize() {
      this.windowWidth = window.innerWidth;
    },
    async show(options = {}) {
      this.title = options.title || '实例详情'
      this.objId = options.bk_obj_id
      this.instId = options.bk_inst_id
      this.visible = true
      this.resetData()

      await Promise.all([
        this.loadProperties(),
        this.loadInstanceData()
      ])
    },

    hide() {
      this.visible = false
      this.resetData()
    },

    resetData() {
      this.instanceData = {}
      this.properties = []
      this.propertyGroups = []
      this.error = null
    },

    async loadProperties() {
      try {
        const data = await modelAttributeAPI.getModelAttributes(this.objId)

        if (Array.isArray(data)) {
          this.properties = data
        } else if (data && data.info) {
          this.properties = data.info
        } else if (data && data.attributes) {
          this.properties = data.attributes
        }

        console.log('[InstanceDetails] 加载属性成功:', {
          objId: this.objId,
          propertyCount: this.properties.length
        })
      } catch (error) {
        console.error('[InstanceDetails] 加载属性失败:', error)
        this.error = '加载属性信息失败'
      }
    },

    async loadInstanceData() {
      this.loading = true
      this.error = null

      try {
        const data = await instanceAPI.getInstanceDetails(this.objId, this.instId)

        if (data && typeof data === 'object') {
          this.instanceData = data
        } else {
          this.instanceData = {}
        }

        console.log('[InstanceDetails] 加载实例数据成功:', {
          objId: this.objId,
          instId: this.instId,
          instanceData: this.instanceData
        })
      } catch (error) {
        console.error('[InstanceDetails] 加载实例数据失败:', error)
        this.error = '加载实例详情失败'
        this.instanceData = {}
      } finally {
        this.loading = false
      }
    },

    handleClose() {
      this.hide()
    }
  }
}
</script>

<style lang="scss" scoped>
.instance-details-sideslider {
  .details-content {
    padding: 0;
    min-height: 100%;
    height: 100%;
    overflow: hidden;

    .details-error {
      padding: 60px 20px;
      text-align: center;
      color: #ff4d4f;
      font-size: 14px;
    }
  }
}

:deep(.bk-sideslider-content) {
  height: 100%;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

/* 移动端竖屏样式 */
@media (max-width: 767px) {
  .instance-details-sideslider {
    :deep(.bk-sideslider-footer) {
      display: none;
    }
  }
}
</style>
