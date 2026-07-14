<template>
  <div class="node-info-layout" v-bkloading="{ isLoading: loading }">
    <div v-if="!node" class="empty-state">
      <div class="placeholder-text">请选择拓扑节点</div>
      <div class="placeholder-desc">点击左侧拓扑树节点查看节点信息</div>
    </div>
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
    </div>
    <cmdb-details
      v-else
      :inst="instanceData"
      :properties="properties"
      :property-groups="propertyGroups"
      :invisible-properties="invisibleProperties"
      :show-options="canEdit || canDelete"
      :show-edit="canEdit"
      :show-delete="canDelete"
      @on-edit="handleEdit"
      @on-delete="handleDelete">
    </cmdb-details>

    <!-- 编辑弹窗 -->
    <bk-dialog
      v-model="editDialog.visible"
      :title="editDialog.title"
      width="600"
      :loading="editDialog.loading"
      @confirm="handleEditSubmit"
      @cancel="handleEditCancel">
      <bk-form :model="editDialog.form" :rules="editDialog.rules" ref="editForm" label-width="100">
        <bk-form-item v-for="property in editableProperties" :key="property.bk_property_id"
          :label="property.bk_property_name"
          :property="property.bk_property_id"
          :required="property.isrequired">
          <component
            :is="getFormComponent(property.bk_property_type)"
            v-model="editDialog.form[property.bk_property_id]"
            :property="property">
          </component>
        </bk-form-item>
      </bk-form>
    </bk-dialog>
  </div>
</template>

<script>
import CmdbDetails from '@/components/ui/details/CmdbDetails.vue'
import { modelAPI } from '@/api/client'
import instanceAPI from '@/api/instance'
import modelAttributeAPI from '@/api/modelAttribute'

// 简化的表单组件
import FormBool from '@/components/ui/form/bool.vue'
import FormDate from '@/components/ui/form/date.vue'
import FormDatetime from '@/components/ui/form/datetime.vue'
import FormEnum from '@/components/ui/form/enum.vue'
import FormEnumMulti from '@/components/ui/form/enummulti.vue'
import FormFloat from '@/components/ui/form/float.vue'
import FormInt from '@/components/ui/form/int.vue'
import FormList from '@/components/ui/form/list.vue'
import FormLongchar from '@/components/ui/form/longchar.vue'
import FormSinglechar from '@/components/ui/form/singlechar.vue'
import FormTime from '@/components/ui/form/time.vue'

export default {
  name: 'NodeInfo',
  components: {
    CmdbDetails,
    FormBool,
    FormDate,
    FormDatetime,
    FormEnum,
    FormEnumMulti,
    FormFloat,
    FormInt,
    FormList,
    FormLongchar,
    FormSinglechar,
    FormTime
  },
  props: {
    node: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      loading: false,
      error: null,
      instanceData: {},
      properties: [],
      propertyGroups: [],
      invisibleProperties: [],
      editDialog: {
        visible: false,
        title: '',
        loading: false,
        form: {},
        rules: {}
      }
    }
  },
  computed: {
    isBizNode() {
      return this.node?.data?.bk_obj_id === 'biz'
    },
    isSetNode() {
      return this.node?.data?.bk_obj_id === 'set'
    },
    isModuleNode() {
      return this.node?.data?.bk_obj_id === 'module'
    },
    isInternalNode() {
      // 内置节点不允许编辑/删除
      if (!this.node) return false
      return this.node.data?.default !== 0 && this.node.data?.default !== undefined
    },
    canEdit() {
      return !this.isInternalNode
    },
    canDelete() {
      return !this.isInternalNode
    },
    editableProperties() {
      // 只允许编辑业务自定义字段（非系统字段、非只读）
      return this.properties.filter(p => {
        if (p.bk_issystem || p.isreadonly) return false
        // 排除主键和ID字段
        if (['id', 'bk_inst_id'].includes(p.bk_property_id)) return false
        // 编辑时不显示模板ID等关联字段
        if (p.bk_property_id === 'service_template_id') return false
        return true
      })
    }
  },
  watch: {
    node: {
      immediate: true,
      handler(node) {
        if (node && node.data) {
          this.loadData()
        } else {
          this.reset()
        }
      }
    }
  },
  methods: {
    async loadData() {
      this.loading = true
      this.error = null
      this.reset()

      const objId = this.node.data.bk_obj_id
      const instId = this.node.data.bk_inst_id

      try {
        // 并行加载属性、分组和实例数据
        await Promise.all([
          this.loadProperties(objId),
          this.loadInstanceData(objId, instId)
        ])
      } catch (err) {
        console.error('[NodeInfo] 加载数据失败:', err)
        this.error = err.message || '加载数据失败'
      } finally {
        this.loading = false
      }
    },

    async loadProperties(objId) {
      try {
        const [attributes, groups] = await Promise.all([
          modelAttributeAPI.getModelAttributes(objId),
          modelAPI.getModelPropertyGroups(objId).catch(() => ({}))
        ])

        if (Array.isArray(attributes)) {
          this.properties = attributes
        } else if (attributes && attributes.info) {
          this.properties = attributes.info
        } else if (attributes && attributes.attributes) {
          this.properties = attributes.attributes
        }

        if (groups && groups.groups) {
          this.propertyGroups = groups.groups.sort(
            (a, b) => (a.bk_group_index || 0) - (b.bk_group_index || 0)
          )
        }
      } catch (error) {
        console.error('[NodeInfo] 加载属性失败:', error)
        throw new Error('加载属性信息失败')
      }
    },

    async loadInstanceData(objId, instId) {
      try {
        const data = await instanceAPI.getInstanceDetails(objId, instId)
        if (data && typeof data === 'object') {
          this.instanceData = data
        } else {
          throw new Error('未找到节点数据')
        }
      } catch (error) {
        console.error('[NodeInfo] 加载实例数据失败:', error)
        throw new Error('获取节点详情失败')
      }
    },

    reset() {
      this.instanceData = {}
      this.properties = []
      this.propertyGroups = []
    },

    getFormComponent(propertyType) {
      const map = {
        'bool': 'FormBool',
        'date': 'FormDate',
        'datetime': 'FormDatetime',
        'enum': 'FormEnum',
        'enummulti': 'FormEnumMulti',
        'float': 'FormFloat',
        'int': 'FormInt',
        'list': 'FormList',
        'longchar': 'FormLongchar',
        'shortchar': 'FormSinglechar',
        'singlechar': 'FormSinglechar',
        'text': 'FormLongchar',
        'time': 'FormTime',
        'char': 'FormSinglechar'
      }
      return map[propertyType] || 'FormSinglechar'
    },

    handleEdit() {
      this.editDialog.title = `编辑${this.node.data.bk_obj_name || '节点'}`
      this.editDialog.form = { ...this.instanceData }
      this.editDialog.visible = true
      this.$nextTick(() => {
        this.$refs.editForm && this.$refs.editForm.clearValidate()
      })
    },

    handleEditCancel() {
      this.editDialog.visible = false
      this.editDialog.form = {}
    },

    async handleEditSubmit() {
      try {
        const valid = await this.$refs.editForm.validate()
        if (!valid) return

        this.editDialog.loading = true
        const objId = this.node.data.bk_obj_id
        const instId = this.node.data.bk_inst_id

        // 收集变更的字段
        const data = {}
        for (const property of this.editableProperties) {
          const field = property.bk_property_id
          const value = this.editDialog.form[field]
          // 简化处理：始终提交可编辑字段
          data[field] = value
        }

        await modelAPI.updateInstance(objId, instId, data)

        this.$bkMessage({
          theme: 'success',
          message: '修改成功'
        })

        this.editDialog.visible = false
        this.editDialog.form = {}

        // 重新加载数据
        await this.loadData()

        // 更新节点的展示名称
        const nameField = this.getNameField()
        if (nameField && data[nameField]) {
          this.node.data.bk_inst_name = data[nameField]
          this.node.name = data[nameField]
        }

        // 通知父组件刷新拓扑树
        this.$emit('updated', this.node)
      } catch (error) {
        console.error('[NodeInfo] 更新失败:', error)
        this.$bkMessage({
          theme: 'error',
          message: error.message || '更新失败'
        })
      } finally {
        this.editDialog.loading = false
      }
    },

    handleDelete() {
      const name = this.instanceData[this.getNameField()] || this.node.data.bk_inst_name
      this.$bkInfo({
        title: `确定删除「${name}」？`,
        subTitle: '删除后不可恢复，请谨慎操作',
        confirmFn: async () => {
          try {
            const objId = this.node.data.bk_obj_id
            const instId = this.node.data.bk_inst_id
            await modelAPI.deleteInstances(objId, [instId])

            this.$bkMessage({
              theme: 'success',
              message: '删除成功'
            })

            this.$emit('deleted', this.node)
          } catch (error) {
            console.error('[NodeInfo] 删除失败:', error)
            this.$bkMessage({
              theme: 'error',
              message: error.message || '删除失败'
            })
          }
        }
      })
    },

    getNameField() {
      const map = {
        'biz': 'bk_biz_name',
        'set': 'bk_set_name',
        'module': 'bk_module_name'
      }
      return map[this.node.data.bk_obj_id] || 'bk_inst_name'
    }
  }
}
</script>

<style lang="scss" scoped>
.node-info-layout {
  height: 100%;
  width: 100%;
  box-sizing: border-box;
}

.empty-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #c4c6cc;
  font-size: 14px;
}

.placeholder-text {
  font-size: 16px;
  color: #c4c6cc;
  margin-bottom: 8px;
}

.placeholder-desc {
  font-size: 13px;
  color: #c4c6cc;
}

.error-state {
  color: #ff4d4f;
  padding: 20px;
  text-align: center;
}
</style>
