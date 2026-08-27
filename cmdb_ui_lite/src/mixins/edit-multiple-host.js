/*
 * 批量编辑主机 mixin（lite 适配版）
 *
 * 移植自原项目 src/ui/src/mixins/edit-multiple-host.js：
 *   - 复用 bk-sideslider 外壳 + 动态挂载 cmdb-form-multiple 的编辑范式；
 *   - 与原项目保持一致：多主机同时编辑、提交后刷新列表、关闭前校验未保存修改。
 *
 * lite 适配点（与原项目差异）：
 *   1. 原项目通过 Vuex dispatch 加载属性分组（objectModelFieldGroup/searchGroup）
 *      与提交更新（hostUpdate/updateHost）；lite 无对应 store 模块，改为直接调用
 *      modelAPI.getModelPropertyGroups / modelAPI.batchUpdateInstancesWithSameData。
 *   2. 原项目 form-multiple 依赖外部传入 propertyGroups 做分组；lite 的
 *      form-multiple.vue 现也接收 propertyGroups（从接口加载），按 bk_group_index
 *      排序，与详情页 effectivePropertyGroups 保持一致；未传入时回落到默认分组。
 *   3. 原项目提交时将 bk_host_id 拼成逗号字符串随参数下发；lite 后端批量更新接口
 *      PUT /api/v1/models/<modelId>/instances 接收 { ids, data }，其中 ids 为数组，
 *      与 general-model「批量更新」保持同一调用契约。
 */
import { modelAPI } from '@/api/client'
import RouterQuery from '@/utils/router-query'

export default {
  props: {
    // 主机模型属性列表（由父组件 host-list 传入，等价于原项目 properties）
    properties: {
      type: Array,
      default: () => []
    },
    // 当前选中的主机行（数组，每行直接包含 bk_host_id 等字段）
    selection: {
      type: Array,
      default: () => []
    },
    // 业务 ID（lite 暂不鉴权，仅作透传保留，与原项目字段对齐）
    bizId: {
      type: Number,
      default: 0
    }
  },
  data() {
    return {
      loading: false,
      slider: {
        show: false,
        title: '',
        component: null,
        props: {}
      },
      // 属性分组（从接口加载，透传给 form-multiple 做分组排序）
      propertyGroups: []
    }
  },
  methods: {
    /**
     * 打开批量编辑抽屉
     * 与原项目 handleMultipleEdit 对应：先展示抽屉并加载属性分组，
     * 再动态挂载 cmdb-form-multiple 组件。
     */
    async handleMultipleEdit() {
      if (!this.selection || this.selection.length === 0) {
        this.$bkMessage({
          message: '请先选择要编辑的主机',
          theme: 'warning'
        })
        return
      }

      this.slider.show = true
      this.slider.title = '编辑主机属性'
      this.loading = true

      try {
        // 加载主机模型属性分组（lite 使用 modelAPI，替代原项目 store dispatch）
        const result = await modelAPI.getModelPropertyGroups('host')
        if (result && result.groups) {
          this.propertyGroups = result.groups
        }
      } catch (e) {
        console.error('[edit-multiple-host] 加载属性分组失败:', e)
        // 分组加载失败不阻断编辑，form-multiple 内部会兜底按默认分组渲染
      } finally {
        this.loading = false
        // 动态挂载批量编辑表单组件（全局注册的 cmdb-form-multiple）
        this.slider.component = 'cmdb-form-multiple'
        this.slider.props = {
          properties: this.properties,
          propertyGroups: this.propertyGroups,
          modelId: 'host',
          showOptions: true,
          submitting: false
        }
      }
    },

    /**
     * 提交批量编辑
     * @param {Object} changedValues form-multiple 仅返回勾选并修改过的字段键值对
     */
    async handleMultipleSave(changedValues) {
      const hostIds = (this.selection || [])
        .map(row => row.bk_host_id)
        .filter(id => id !== undefined && id !== null)

      if (hostIds.length === 0) {
        this.$bkMessage({
          message: '未获取到有效主机，请重新选择',
          theme: 'warning'
        })
        return
      }

      this.slider.props = { ...this.slider.props, submitting: true }

      try {
        const result = await modelAPI.batchUpdateInstancesWithSameData(
          'host',
          hostIds,
          changedValues
        )

        if (result) {
          this.slider.show = false
          this.$bkMessage({
            message: `成功更新 ${hostIds.length} 台主机`,
            theme: 'success'
          })
          // 通知父组件刷新列表（与批量更新保持一致：编辑后重载当前页）
          this.$emit('refresh')
          RouterQuery.set({ _t: Date.now() })
        } else {
          this.$bkMessage({
            message: '未获取到更新结果',
            theme: 'error'
          })
        }
      } catch (e) {
        console.error('[edit-multiple-host] 批量更新主机失败:', e)
        this.$handleApiError(e)
      } finally {
        this.slider.props = { ...this.slider.props, submitting: false }
      }
    },

    /**
     * 抽屉关闭前校验：存在未保存修改时弹确认框
     * 与原项目 handleSliderBeforeClose 对应，lite 的 form-multiple 暴露 hasChange 计算属性。
     */
    handleSliderBeforeClose() {
      const formRef = this.$refs.multipleForm
      if (formRef && formRef.hasChange) {
        return new Promise((resolve) => {
          this.$bkInfo({
            title: '确认退出？',
            subTitle: '当前编辑有未保存的修改，是否确认退出？',
            confirmFn: () => {
              resolve(true)
            },
            cancelFn: () => {
              resolve(false)
            }
          })
        })
      }
      return true
    },

    /**
     * 取消按钮点击处理：先校验未保存修改，再关闭抽屉
     */
    async handleCancel() {
      const canClose = await this.handleSliderBeforeClose()
      if (canClose !== false) {
        this.slider.show = false
      }
    }
  }
}
