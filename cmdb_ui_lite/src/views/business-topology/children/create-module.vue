<template>
  <div class="node-create-layout">
    <h2 class="node-create-title">新建模块</h2>
    <div class="node-create-path" :title="topoPath">添加节点已选择：{{ topoPath }}</div>
    <div class="node-create-form" :style="{ 'max-height': Math.min(600, 400) + 'px' }">
      <!-- 创建类型选择 -->
      <div class="form-item clearfix mt30">
        <div class="create-type fl">
          <input class="type-radio"
            type="radio"
            id="formTemplate"
            name="createType"
            v-model="withTemplate"
            :value="1"
            disabled>
          <label for="formTemplate" class="disabled-label">从模板新建</label>
          <span class="type-desc">(暂不支持)</span>
        </div>
        <div class="create-type fl ml50">
          <input class="type-radio"
            type="radio"
            id="createDirectly"
            name="createType"
            v-model="withTemplate"
            :value="0">
          <label for="createDirectly">直接新建</label>
        </div>
      </div>

      <!-- 从模板新建 - 暂时隐藏 -->
      <div class="form-item" v-if="withTemplate === 1" style="display: none;">
        <label>服务模板<span class="red-star">*</span></label>
        <bk-select style="width: 100%;"
          :clearable="false"
          v-model="template">
          <bk-option v-for="(option, index) in templateList"
            :key="index"
            :id="option.id"
            :name="option.name">
          </bk-option>
        </bk-select>
      </div>

      <!-- 模块名称 -->
      <div class="form-item">
        <label>
          模块名称
          <span class="red-star">*</span>
          <i class="bk-icon icon-question-circle" v-bk-tooltips.top="'模块名称提示'" v-if="withTemplate === 1"></i>
        </label>
        <bk-input class="form-textarea" v-if="withTemplate === 1"
          v-model="moduleName"
          :placeholder="'请输入模块名称'"
          :disabled="false">
        </bk-input>
        <bk-input class="form-textarea" v-else
          type="textarea"
          v-model="moduleNameMulti"
          :rows="rows"
          placeholder="请输入模块名称，多个模块用换行分隔"
          @keydown="handleKeydown"
          @paste="handlePaste">
        </bk-input>
      </div>

      <!-- 所属服务分类 - 仅直接新建时显示 -->
      <div class="form-item clearfix" v-if="withTemplate === 0">
        <label>所属服务分类<span class="red-star">*</span></label>
        <bk-select class="service-class fl"
          v-model="firstClass"
          :clearable="false"
          placeholder="请选择一级分类">
          <bk-option v-for="(item, index) in firstClassList"
            :key="index"
            :id="item.id"
            :name="item.name">
          </bk-option>
        </bk-select>
        <bk-select class="service-class fr"
          v-model="secondClass"
          :clearable="false"
          placeholder="请选择二级分类">
          <bk-option v-for="(item, index) in secondClassList"
            :key="index"
            :id="item.id"
            :name="item.name">
          </bk-option>
        </bk-select>
      </div>
    </div>
    <div class="node-create-options">
      <bk-button theme="primary" class="mr10"
        :disabled="!canSubmit"
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
      withTemplate: 0, // 默认直接新建
      template: '',
      templateList: [],
      moduleName: '',
      moduleNameMulti: '',
      rows: 1,
      // 服务分类 - 默认值
      firstClass: 'default',
      secondClass: 'default',
      // 服务分类列表 - 写死为 default
      firstClassList: [
        { id: 'default', name: '默认分类' }
      ],
      secondClassList: [
        { id: 'default', name: '默认分类' }
      ]
    }
  },
  computed: {
    topoPath() {
      const nodePath = [...(this.parentNode.parents || []), this.parentNode]
      return nodePath.map(node => node.data?.bk_inst_name || node.name).join(' / ')
    },
    canSubmit() {
      if (this.withTemplate === 1) {
        return this.moduleName.trim().length > 0
      } else {
        return this.moduleNameMulti.trim().length > 0 && this.firstClass && this.secondClass
      }
    },
    currentTemplate() {
      return this.templateList.find(item => item.id === this.template) || {}
    }
  },
  watch: {
    withTemplate(val) {
      if (val === 1) {
        // 从模板新建 - 暂不支持
        this.moduleName = ''
      } else {
        // 直接新建
        this.moduleNameMulti = ''
        // 重置服务分类为默认值
        this.firstClass = 'default'
        this.secondClass = 'default'
      }
    },
    template(template) {
      if (template) {
        this.moduleName = this.currentTemplate.name || ''
      } else {
        this.moduleName = ''
      }
    }
  },
  methods: {
    setRows() {
      setTimeout(() => {
        const rows = this.moduleNameMulti.split('\n').length
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
      const data = {
        service_category_id: this.secondClass,
        service_template_id: this.withTemplate === 1 ? this.template : 0
      }

      if (this.withTemplate === 1) {
        data.bk_module_name = this.moduleName.trim()
      } else {
        const nameList = this.moduleNameMulti.split('\n')
          .filter(name => name.trim().length > 0)
          .map(name => name.trim())
        data.bk_module_name = nameList
      }

      console.log('[CreateModule] 提交数据:', data)
      this.$emit('submit', data)
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
  font-size: 22px;
  color: #333948;
  font-weight: normal;
}

.node-create-path {
  padding: 23px 26px 0;
  margin: 0 0 -5px 0;
  font-size: 12px;
  color: #63656e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-create-form {
  padding: 0 26px 27px;
  overflow: visible;
}

.mt30 {
  margin-top: 30px;
}

.form-item {
  margin: 15px 0 0 0;
  position: relative;

  label {
    display: block;
    padding: 7px 0;
    line-height: 19px;
    font-size: 14px;
    color: #63656e;

    .red-star {
      color: #ff5656;
      font-size: 14px;
    }

    .bk-icon {
      color: #c4c6cc;
      font-size: 14px;
      margin-left: 4px;
      cursor: pointer;

      &:hover {
        color: #979ba5;
      }
    }
  }

  .service-class {
    width: 260px;
    display: inline-block;
  }

  .form-textarea {
    ::v-deep textarea {
      min-height: auto !important;
      line-height: 22px;
      overflow-y: auto;
    }
  }

  .create-type {
    display: flex;
    align-items: center;
    line-height: 19px;

    .type-radio {
      -webkit-appearance: none;
      width: 16px;
      height: 16px;
      padding: 3px;
      border: 1px solid #979ba5;
      border-radius: 50%;
      background-clip: content-box;
      outline: none;
      cursor: pointer;

      &:checked {
        border-color: #3a84ff;
        background-color: #3a84ff;
      }

      &:disabled {
        cursor: not-allowed;
        opacity: 0.5;
      }
    }

    label {
      display: inline;
      padding: 0 0 0 6px;
      font-size: 14px;
      cursor: pointer;
      color: #63656e;

      &.disabled-label {
        color: #c4c6cc;
        cursor: not-allowed;
      }
    }

    .type-desc {
      font-size: 12px;
      color: #979ba5;
      margin-left: 6px;
    }
  }
}

.ml50 {
  margin-left: 50px;
}

.clearfix::after {
  content: '';
  display: table;
  clear: both;
}

.mr10 {
  margin-right: 10px;
}

.node-create-options {
  padding: 9px 20px;
  border-top: 1px solid #dcdee5;
  text-align: right;
  background-color: #fafbfd;
}
</style>