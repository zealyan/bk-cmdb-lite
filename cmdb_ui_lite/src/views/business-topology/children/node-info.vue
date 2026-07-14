<template>
  <div class="node-info-layout" v-bkloading="{ isLoading: loading }">
    <!-- 详情模式 -->
    <div v-if="mode === 'details'" class="node-details">
      <div class="details-header">
        <h3 class="node-title">{{ instance[nodeNameField] || node.name }}</h3>
        <div class="node-type-tag">{{ nodeTypeLabel }}</div>
      </div>

      <!-- 节点额外信息（模块显示服务分类、模板等） -->
      <div class="extra-info" v-if="isModuleNode">
        <div class="extra-item">
          <span class="extra-label">服务分类：</span>
          <span class="extra-value">{{ serviceCategoryName || '默认分类' }}</span>
        </div>
        <div class="extra-item" v-if="instance.service_template_id">
          <span class="extra-label">服务模板：</span>
          <span class="extra-value">{{ serviceTemplateName || '-' }}</span>
        </div>
      </div>
      <div class="extra-info" v-if="isSetNode && instance.set_template_id">
        <div class="extra-item">
          <span class="extra-label">集群模板：</span>
          <span class="extra-value">{{ setTemplateName || '-' }}</span>
        </div>
      </div>

      <!-- 属性分组展示 -->
      <div class="property-groups">
        <div class="property-group">
          <h4 class="group-title">基础信息</h4>
          <div class="property-list">
            <div
              class="property-item"
              v-for="property in basicProperties"
              :key="property.bk_property_id">
              <span class="property-label">{{ property.bk_property_name }}</span>
              <span class="property-value">
                <template v-if="property.bk_property_type === 'bool'">
                  {{ instance[property.bk_property_id] ? '是' : '否' }}
                </template>
                <template v-else-if="property.bk_property_type === 'enum'">
                  {{ getEnumLabel(property, instance[property.bk_property_id]) }}
                </template>
                <template v-else-if="property.bk_property_id === 'create_time' || property.bk_property_id === 'last_time'">
                  {{ formatTime(instance[property.bk_property_id]) }}
                </template>
                <template v-else>
                  {{ instance[property.bk_property_id] !== undefined && instance[property.bk_property_id] !== null ? instance[property.bk_property_id] : '--' }}
                </template>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="details-options" v-if="node.data.default === 0">
        <bk-button theme="primary" class="mr10" @click="handleEdit">编辑</bk-button>
        <bk-button hover-theme="danger" @click="handleDelete">删除节点</bk-button>
      </div>
    </div>

    <!-- 编辑模式 -->
    <div v-else-if="mode === 'edit'" class="node-edit">
      <div class="edit-header">
        <h3 class="node-title">编辑{{ nodeTypeLabel }}</h3>
      </div>

      <bk-form :model="editForm" :rules="editRules" ref="editForm">
        <!-- 名称字段 -->
        <bk-form-item :label="nameFieldLabel" :property="nodeNameField" :required="true">
          <bk-input v-model="editForm[nodeNameField]" :placeholder="`请输入${nameFieldLabel}`"></bk-input>
        </bk-form-item>

        <!-- 集群描述 -->
        <bk-form-item label="集群描述" property="bk_set_desc" v-if="isSetNode">
          <bk-input
            type="textarea"
            v-model="editForm.bk_set_desc"
            :rows="3"
            placeholder="请输入集群描述">
          </bk-input>
        </bk-form-item>

        <!-- 集群环境 -->
        <bk-form-item label="集群环境" property="bk_set_env" v-if="isSetNode">
          <bk-select v-model="editForm.bk_set_env" :clearable="false">
            <bk-option id="1" name="测试"></bk-option>
            <bk-option id="2" name="体验"></bk-option>
            <bk-option id="3" name="正式"></bk-option>
          </bk-select>
        </bk-form-item>

        <!-- 服务状态 -->
        <bk-form-item label="服务状态" property="bk_service_status" v-if="isSetNode">
          <bk-select v-model="editForm.bk_service_status" :clearable="false">
            <bk-option id="1" name="开放"></bk-option>
            <bk-option id="2" name="关闭"></bk-option>
          </bk-select>
        </bk-form-item>

        <!-- 服务分类 - 模块节点 -->
        <bk-form-item label="所属服务分类" property="service_category_id" v-if="isModuleNode">
          <bk-select v-model="editForm.service_category_id" :clearable="false">
            <bk-option id="default" name="默认分类"></bk-option>
          </bk-select>
        </bk-form-item>
      </bk-form>

      <div class="edit-options">
        <bk-button theme="primary" class="mr10" @click="handleSubmit">保存</bk-button>
        <bk-button theme="default" @click="handleCancel">取消</bk-button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'NodeInfo',
  props: {
    node: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      loading: false,
      mode: 'details',
      instance: {},
      editForm: {},
      serviceCategoryName: '',
      serviceTemplateName: '',
      setTemplateName: '',
      editRules: {}
    }
  },
  computed: {
    isBizNode() {
      return this.node.data.bk_obj_id === 'biz'
    },
    isSetNode() {
      return this.node.data.bk_obj_id === 'set'
    },
    isModuleNode() {
      return this.node.data.bk_obj_id === 'module'
    },
    nodeTypeLabel() {
      const map = {
        biz: '业务',
        set: '集群',
        module: '模块'
      }
      return map[this.node.data.bk_obj_id] || '节点'
    },
    nodeNameField() {
      const map = {
        biz: 'bk_biz_name',
        set: 'bk_set_name',
        module: 'bk_module_name'
      }
      return map[this.node.data.bk_obj_id] || 'bk_inst_name'
    },
    nodeIdField() {
      const map = {
        biz: 'bk_biz_id',
        set: 'bk_set_id',
        module: 'bk_module_id'
      }
      return map[this.node.data.bk_obj_id] || 'bk_inst_id'
    },
    nameFieldLabel() {
      const map = {
        biz: '业务名称',
        set: '集群名称',
        module: '模块名称'
      }
      return map[this.node.data.bk_obj_id] || '节点名称'
    },
    basicProperties() {
      const commonProps = [
        { bk_property_id: this.nodeIdField, bk_property_name: 'ID', bk_property_type: 'int' },
        { bk_property_id: this.nodeNameField, bk_property_name: this.nameFieldLabel, bk_property_type: 'singlechar' },
        { bk_property_id: 'creator', bk_property_name: '创建人', bk_property_type: 'singlechar' },
        { bk_property_id: 'modifier', bk_property_name: '修改人', bk_property_type: 'singlechar' },
        { bk_property_id: 'create_time', bk_property_name: '创建时间', bk_property_type: 'datetime' },
        { bk_property_id: 'last_time', bk_property_name: '更新时间', bk_property_type: 'datetime' }
      ]

      if (this.isSetNode) {
        return [
          ...commonProps,
          { bk_property_id: 'bk_set_desc', bk_property_name: '集群描述', bk_property_type: 'longchar' },
          { bk_property_id: 'bk_set_env', bk_property_name: '集群环境', bk_property_type: 'enum' },
          { bk_property_id: 'bk_service_status', bk_property_name: '服务状态', bk_property_type: 'enum' }
        ]
      }

      if (this.isModuleNode) {
        return [
          ...commonProps,
          { bk_property_id: 'service_category_id', bk_property_name: '服务分类', bk_property_type: 'singlechar' }
        ]
      }

      return commonProps
    }
  },
  watch: {
    node: {
      immediate: true,
      handler(node) {
        if (node) {
          this.mode = 'details'
          this.fetchNodeDetail()
        }
      }
    }
  },
  methods: {
    async fetchNodeDetail() {
      this.loading = true
      try {
        const { data } = await this.$http.get(`/api/v1/topo/node/${this.node.data.bk_obj_id}/${this.node.data.bk_inst_id}`, {
          params: {
            bk_biz_id: this.getBizId()
          }
        })
        this.instance = data || {}
      } catch (error) {
        console.error('获取节点详情失败:', error)
        this.$bkMessage({
          theme: 'error',
          message: '获取节点详情失败'
        })
      } finally {
        this.loading = false
      }
    },
    getBizId() {
      // 从节点数据中获取业务ID
      if (this.isBizNode) {
        return this.node.data.bk_inst_id
      }
      // 从节点的父节点或data中获取
      return this.node.data.bk_biz_id || this.$route.params.bizId
    },
    getEnumLabel(property, value) {
      const envMap = { '1': '测试', '2': '体验', '3': '正式' }
      const statusMap = { '1': '开放', '2': '关闭' }
      if (property.bk_property_id === 'bk_set_env') {
        return envMap[value] || value
      }
      if (property.bk_property_id === 'bk_service_status') {
        return statusMap[value] || value
      }
      return value
    },
    formatTime(time) {
      if (!time) return '--'
      if (typeof time === 'string') return time
      return new Date(time).toLocaleString()
    },
    handleEdit() {
      this.editForm = { ...this.instance }
      this.mode = 'edit'
    },
    handleCancel() {
      this.mode = 'details'
      this.editForm = {}
    },
    async handleSubmit() {
      try {
        const valid = await this.$refs.editForm.validate()
        if (!valid) return

        const params = {
          bk_biz_id: this.getBizId()
        }

        // 根据节点类型组装更新参数
        if (this.isBizNode) {
          params.bk_biz_name = this.editForm.bk_biz_name
        } else if (this.isSetNode) {
          params.bk_set_name = this.editForm.bk_set_name
          params.bk_set_desc = this.editForm.bk_set_desc
          params.bk_set_env = this.editForm.bk_set_env
          params.bk_service_status = this.editForm.bk_service_status
        } else if (this.isModuleNode) {
          params.bk_module_name = this.editForm.bk_module_name
          params.service_category_id = this.editForm.service_category_id
        }

        await this.$http.put(`/api/v1/topo/node/${this.node.data.bk_obj_id}/${this.node.data.bk_inst_id}`, params)

        this.$bkMessage({
          theme: 'success',
          message: '修改成功'
        })

        // 更新本地数据
        this.instance = { ...this.instance, ...params }
        // 更新节点名称
        if (this.editForm[this.nodeNameField]) {
          this.node.data.bk_inst_name = this.editForm[this.nodeNameField]
          this.node.name = this.editForm[this.nodeNameField]
        }

        this.mode = 'details'
      } catch (error) {
        console.error('更新节点失败:', error)
        this.$bkMessage({
          theme: 'error',
          message: error.message || '更新失败'
        })
      }
    },
    handleDelete() {
      this.$bkInfo({
        title: `确定删除 ${this.node.name}？`,
        subTitle: '删除后不可恢复，请谨慎操作',
        confirmFn: async () => {
          try {
            await this.$http.delete(`/api/v1/topo/node/${this.node.data.bk_obj_id}/${this.node.data.bk_inst_id}`, {
              params: {
                bk_biz_id: this.getBizId()
              }
            })
            this.$bkMessage({
              theme: 'success',
              message: '删除成功'
            })
            this.$emit('deleted')
          } catch (error) {
            console.error('删除节点失败:', error)
            this.$bkMessage({
              theme: 'error',
              message: error.message || '删除失败'
            })
          }
        }
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.node-info-layout {
  height: 100%;
  overflow-y: auto;
  padding: 0 20px 20px;
}

.details-header,
.edit-header {
  display: flex;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #dcdee5;
  margin-bottom: 16px;
}

.node-title {
  font-size: 16px;
  font-weight: 500;
  color: #313238;
  margin: 0;
}

.node-type-tag {
  margin-left: 8px;
  padding: 2px 8px;
  background: #e1ecff;
  color: #3a84ff;
  font-size: 12px;
  border-radius: 2px;
}

.extra-info {
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 2px;
  margin-bottom: 16px;
}

.extra-item {
  display: flex;
  align-items: center;
  line-height: 24px;
  font-size: 13px;
}

.extra-label {
  color: #63656e;
  min-width: 80px;
}

.extra-value {
  color: #313238;
  font-weight: 500;
}

.property-groups {
  margin-bottom: 20px;
}

.property-group {
  margin-bottom: 16px;
}

.group-title {
  font-size: 14px;
  font-weight: 500;
  color: #313238;
  margin: 0 0 12px 0;
  padding-left: 8px;
  border-left: 3px solid #3a84ff;
}

.property-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0;
  border: 1px solid #dcdee5;
  border-radius: 2px;
}

.property-item {
  display: flex;
  padding: 10px 16px;
  border-bottom: 1px solid #f0f1f5;
  font-size: 13px;
  line-height: 20px;

  &:nth-last-child(-n+2) {
    border-bottom: none;
  }

  &:nth-child(odd) {
    border-right: 1px solid #f0f1f5;
  }
}

.property-label {
  color: #63656e;
  min-width: 80px;
  flex-shrink: 0;
}

.property-value {
  color: #313238;
  word-break: break-all;
}

.details-options,
.edit-options {
  padding: 16px 0;
  border-top: 1px solid #dcdee5;
}

.mr10 {
  margin-right: 10px;
}

.node-edit {
  .bk-form {
    margin-top: 16px;
  }
}
</style>
