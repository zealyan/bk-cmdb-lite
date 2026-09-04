<template>
  <div class="category-input">
    <bk-input class="category-input-control"
      :ref="inputRef"
      :placeholder="placeholder"
      v-model="localValue"
      :autofocus="true"
      @enter="handleConfirm">
    </bk-input>
    <div class="category-input-operate">
      <span class="text-primary btn-confirm" @click.stop="handleConfirm">确定</span>
      <span class="text-primary" @click="handleCancel">取消</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CategoryInput',
  props: {
    value: {
      type: String,
      default: ''
    },
    placeholder: {
      type: String,
      default: ''
    },
    inputRef: {
      type: String,
      default: ''
    },
    // 编辑态时传入被编辑分类的 id；新建态为 0
    editId: {
      type: Number,
      default: 0
    }
  },
  data() {
    return {
      localValue: this.value
    }
  },
  watch: {
    value(value) {
      this.localValue = value
    },
    localValue(localValue) {
      this.$emit('input', localValue)
    }
  },
  mounted() {
    // 内联输入框挂载后自动聚焦（bk-input 内部 input 经 $refs.input 暴露）
    this.$nextTick(() => {
      const ref = this.$refs[this.inputRef]
      const input = (ref && ref.$refs && ref.$refs.input)
        || (ref && ref.$el && ref.$el.querySelector('input'))
      if (input && input.focus) {
        input.focus()
      }
    })
  },
  methods: {
    handleConfirm() {
      this.$emit('on-confirm', this.localValue, this.editId)
    },
    handleCancel() {
      this.$emit('on-cancel')
    }
  }
}
</script>

<style lang="scss" scoped>
.category-input {
  display: flex;
  align-items: center;
  width: 100%;

  .category-input-control {
    flex: 1;
    margin-right: 10px;
  }

  .category-input-operate {
    display: inline-flex;
    align-items: center;
    font-size: 12px;

    .text-primary {
      cursor: pointer;
      color: #3a84ff;

      &.btn-confirm {
        position: relative;
        margin-right: 10px;

        &::after {
          content: '';
          position: absolute;
          top: 2px;
          right: -6px;
          width: 1px;
          height: 14px;
          background-color: #dcdee5;
        }
      }
    }
  }
}
</style>
