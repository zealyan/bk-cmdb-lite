<template>
  <div class="create-mainline-layout">
    <h2 class="node-create-title">新建{{ childModelName }}</h2>
    <div class="node-create-path" :title="topoPath">添加节点已选择：{{ topoPath }}</div>

    <div class="node-create-form">
      <!-- 名称（必填，多名称换行分隔，对齐原项目 set/module 批量新建交互） -->
      <div class="form-item">
        <label>
          {{ nameAttrName }}
          <span class="red-star">*</span>
        </label>
        <bk-input class="form-textarea"
          type="textarea"
          v-model="nameText"
          :rows="nameRows"
          :placeholder="`请输入${childModelName}名称，多个用换行分隔`"
          @keydown="handleKeydown"
          @paste="handlePaste">
        </bk-input>
      </div>

      <!-- 自定义层其它可编辑属性（动态渲染，非系统字段） -->
      <div class="form-item" v-for="attr in editableAttrs" :key="attr.bk_property_id">
        <label>{{ attr.bk_property_name }}</label>
        <bk-input v-model="attrValues[attr.bk_property_id]"
          :placeholder="`请输入${attr.bk_property_name}`">
        </bk-input>
      </div>
    </div>

    <div class="node-create-options">
      <bk-button theme="primary" class="mr10"
        :disabled="!nameText.trim()"
        :loading="submitting"
        @click="handleSubmit">
        提交
      </bk-button>
      <bk-button theme="default" @click="handleCancel">取消</bk-button>
    </div>
  </div>
</template>

<script>
import modelAttribute from '@/api/modelAttribute'

// 系统/拓扑字段：不参与新建表单（由后端按主线顺序自动填充 bk_parent_id/bk_biz_id 等）
const SYSTEM_FIELDS = new Set([
  'id', 'bk_inst_id', 'bk_obj_id', 'bk_parent_id', 'bk_biz_id',
  'create_time', 'last_time', 'default', 'creator', 'modifier',
  'bk_supplier_account', 'bk_ispaused', 'bk_obj_icon', 'bk_comment'
])

export default {
  name: 'CreateMainlineNode',
  props: {
    // 被点击的父节点（在其下创建子主线层实例）
    parentNode: {
      type: Object,
      required: true
    },
    // 待创建子模型的 bk_obj_id（如 'appsys' / 'zone'），由父组件按主线顺序算出
    childModel: {
      type: String,
      required: true
    },
    // 待创建子模型的展示名（如 '应用系统'）
    childModelName: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      nameText: '',
      nameRows: 1,
      submitting: false,
      allAttrs: [],
      attrValues: {},
      nameField: 'bk_inst_name'
    }
  },
  computed: {
    // 名称字段展示名（取名称属性 bk_property_name，否则回退为模型名）
    nameAttrName() {
      const nameAttr = this.allAttrs.find(a => a.bk_property_id === this.nameField)
      return (nameAttr && nameAttr.bk_property_name) || this.childModelName || '名称'
    },
    // 除名称字段外的可编辑自定义属性
    editableAttrs() {
      return this.allAttrs.filter(a =>
        a.bk_property_id !== this.nameField &&
        !SYSTEM_FIELDS.has(a.bk_property_id) &&
        a.bk_property_id !== 'bk_inst_name'
      )
    },
    topoPath() {
      const nodePath = [...(this.parentNode.parents || []), this.parentNode]
      return nodePath.map(node => node.data?.bk_inst_name || node.name).join(' / ')
    }
  },
  async created() {
    await this.loadAttributes()
  },
  methods: {
    async loadAttributes() {
      try {
        const attrs = await modelAttribute.getModelAttributes(this.childModel)
        this.allAttrs = Array.isArray(attrs) ? attrs : []
        // 自定义主线层名称字段恒为 bk_inst_name；内置层（set/module）走专用对话框，不会到此
        this.nameField = 'bk_inst_name'
      } catch (e) {
        console.error('[CreateMainlineNode] 加载模型属性失败:', e)
        this.allAttrs = []
      }
    },
    setNameRows() {
      const rows = this.nameText.split('\n').length
      this.nameRows = Math.min(3, Math.max(rows, 1))
    },
    handleKeydown(value, keyEvent) {
      if (['Enter', 'NumpadEnter'].includes(keyEvent.code)) {
        this.nameRows = Math.min(this.nameRows + 1, 3)
      } else if (keyEvent.code === 'Backspace') {
        this.setNameRows()
      }
    },
    handlePaste() {
      this.setNameRows()
    },
    handleSubmit() {
      if (!this.nameText.trim() || this.submitting) return
      const names = this.nameText.split('\n')
        .map(n => n.trim()).filter(n => n.length)
      if (!names.length) return

      // 收集其它可编辑属性（跳过空值）
      const attrs = {}
      this.editableAttrs.forEach(attr => {
        const v = (this.attrValues[attr.bk_property_id] ?? '').toString().trim()
        if (v) attrs[attr.bk_property_id] = v
      })

      this.submitting = true
      this.$emit('submit', { names, attrs })
    },
    handleCancel() {
      this.$emit('cancel')
    }
  }
}
</script>

<style lang="scss" scoped>
.create-mainline-layout {
  position: relative;
}
.node-create-title {
  margin-top: -15px;
  padding: 0 26px;
  line-height: 30px;
  font-size: 24px;
  color: #444444;
  font-weight: normal;
}
.node-create-path {
  padding: 14px 26px 0;
  margin: 0 0 -5px 0;
  font-size: 12px;
  color: #63656e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.node-create-form {
  padding: 20px 26px 32px;
}
.form-item {
  margin: 15px 0 0 0;
  position: relative;

  label {
    display: block;
    padding: 0 0 10px;
    line-height: 19px;
    font-size: 14px;
    color: #63656e;

    .red-star {
      color: #f00;
      font-size: 14px;
    }
  }

  .form-textarea {
    ::v-deep textarea {
      min-height: auto !important;
      line-height: 22px;
    }
  }
}
.mr10 {
  margin-right: 10px;
}
.node-create-options {
  padding: 9px 20px;
  border-top: 1px solid #dcdee5;
  text-align: right;
  background-color: #fafbfd;
  font-size: 0;
}
</style>
