<template>
  <div class="create-set-layout">
    <h2 class="node-create-title">新建集群</h2>
    <div class="node-create-path" :title="topoPath">添加节点已选择：{{ topoPath }}</div>
    <div class="node-create-form">
      <!-- 暂时注释掉从模板新建
      <bk-radio-group class="form-item mb20" v-model="withTemplate">
        <bk-radio :value="true">从模板新建</bk-radio>
        <bk-radio :value="false">直接新建</bk-radio>
      </bk-radio-group>
      <div class="form-item" v-if="withTemplate">
        <label>
          集群模板
          <span class="red-star">*</span>
        </label>
        <bk-select style="width: 100%;"
          :clearable="false"
          placeholder="请选择集群模板"
          v-model="setTemplate">
          <bk-option v-for="option in setTemplateList"
            :key="option.id"
            :id="option.id"
            :name="option.name">
          </bk-option>
        </bk-select>
      </div>
      -->
      <div class="form-item">
        <label>
          集群名称
          <span class="red-star">*</span>
        </label>
        <bk-input class="form-textarea"
          type="textarea"
          v-model="setName"
          :rows="rows"
          placeholder="请输入集群名称，多个集群用换行分隔"
          @keydown="handleKeydown"
          @paste="handlePaste">
        </bk-input>
      </div>
    </div>
    <div class="node-create-options">
      <bk-button theme="primary" class="mr10"
        :disabled="!setName.trim()"
        @click="handleCreateSet">
        提交
      </bk-button>
      <bk-button theme="default" @click="handleCancel">取消</bk-button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CreateSet',
  props: {
    parentNode: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      withTemplate: false,
      setTemplate: '',
      setName: '',
      rows: 1,
      setTemplateList: []
    }
  },
  computed: {
    topoPath() {
      const nodePath = [...(this.parentNode.parents || []), this.parentNode]
      return nodePath.map(node => node.data?.bk_inst_name || node.name).join(' / ')
    }
  },
  watch: {
    withTemplate(value) {
      if (value) {
        this.setTemplate = this.setTemplateList[0] ? this.setTemplateList[0].id : ''
      } else {
        this.setTemplate = ''
      }
    }
  },
  methods: {
    setRows() {
      setTimeout(() => {
        const rows = this.setName.split('\n').length
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
    handleCreateSet() {
      if (!this.setName.trim()) return
      const nameList = this.setName.split('\n').filter(name => name.trim().length)
        .map(name => name.trim())
      this.$emit('submit', {
        set_template_id: this.setTemplate || 0,
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
.node-create-layout {
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

  .bk-form-radio {
    display: inline-block;
    margin-right: 70px;
  }

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

  .form-error {
    position: absolute;
    top: 100%;
    left: 0;
    font-size: 12px;
    color: #ea3636;

    &.second-class {
      left: 270px;
    }
  }

  .form-textarea {
    ::v-deep textarea {
      min-height: auto !important;
      line-height: 22px;
    }
  }
}

.mb20 {
  margin-bottom: 20px;
}

.mr10 {
  margin-right: 10px;
}

.add-template {
  width: 20%;
  line-height: 38px;
  cursor: pointer;
  color: #63656e;
  font-size: 12px;

  .icon-plus-circle {
    margin-top: -2px;
    font-size: 14px;
    color: #979ba5;
  }
}

.node-create-options {
  padding: 9px 20px;
  border-top: 1px solid #dcdee5;
  text-align: right;
  background-color: #fafbfd;
  font-size: 0;
}
</style>
