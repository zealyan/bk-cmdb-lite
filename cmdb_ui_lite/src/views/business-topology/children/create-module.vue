<template>
  <div class="create-module-layout">
    <h2 class="node-create-title">新建模块</h2>
    <div class="node-create-path" :title="topoPath">添加节点已选择：{{ topoPath }}</div>
    <div class="node-create-form">
      <div class="form-item">
        <label>
          模块名称
          <span class="red-star">*</span>
        </label>
        <bk-input class="form-textarea"
          type="textarea"
          v-model="moduleName"
          :rows="rows"
          placeholder="请输入模块名称，多个模块用换行分隔"
          @keydown="handleKeydown"
          @paste="handlePaste">
        </bk-input>
      </div>
    </div>
    <div class="node-create-options">
      <bk-button theme="primary" class="mr10"
        :disabled="!moduleName.trim()"
        @click="handleCreateModule">
        提交
      </bk-button>
      <bk-button theme="default" @click="handleCancel">取消</bk-button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CreateModule',
  props: {
    parentNode: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      moduleName: '',
      rows: 1
    }
  },
  computed: {
    topoPath() {
      const nodePath = [...(this.parentNode.parents || []), this.parentNode]
      return nodePath.map(node => node.data?.bk_inst_name || node.name).join(' / ')
    }
  },
  methods: {
    setRows() {
      setTimeout(() => {
        const rows = this.moduleName.split('\n').length
        this.rows = Math.min(3, Math.max(rows, 1))
      })
    },
    handleKeydown(value, keyEvent) {
      if (['Enter', 'NumpadEnter'].includes(keyEvent.code)) {
        this.rows = Math.min(this.rows + 1, 3)
      } else if (keyEvent.code === 'Backspace') {
        this.setRows()
      }
    },
    handlePaste() {
      this.setRows()
    },
    handleCreateModule() {
      if (!this.moduleName.trim()) return
      const nameList = this.moduleName.split('\n').filter(name => name.trim().length)
        .map(name => name.trim())
      this.$emit('submit', {
        names: nameList
      })
    },
    handleCancel() {
      this.$emit('cancel')
    }
  }
}
</script>

<style lang="scss" scoped>
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

    > span {
      color: #979ba5;
      font-size: 12px;
    }

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