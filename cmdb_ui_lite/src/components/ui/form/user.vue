<template>
  <bk-member-selector
    v-model="localValue"
    :disabled="disabled || readonly">
  </bk-member-selector>
</template>

<script>
export default {
  name: 'cmdb-form-user',
  props: {
    value: {
      default: ''
    },
    property: {
      type: Object,
      default: () => ({})
    },
    disabled: Boolean,
    readonly: Boolean
  },
  computed: {
    // 与 MongoDB objuser 规则一致：存储为「逗号拼接的英文名串」（如 "admin,test,zhangsan"）。
    // 读取时拆分为数组喂给成员选择器；变更时数组合并为逗号串回写。
    localValue: {
      get() {
        if (!this.value) return []
        if (Array.isArray(this.value)) return this.value
        return String(this.value).split(',')
      },
      set(val) {
        if (Array.isArray(val)) {
          this.$emit('input', val.join(','))
        } else {
          this.$emit('input', val)
        }
      }
    }
  }
}
</script>
