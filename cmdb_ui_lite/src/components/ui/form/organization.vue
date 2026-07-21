<template>
  <bk-select
    :multiple="localMultiple"
    searchable
    display-tag
    v-model="localValue"
    :disabled="disabled || readonly"
    :placeholder="placeholder">
    <bk-option
      v-for="id in optionList"
      :key="id"
      :id="id"
      :name="String(id)">
    </bk-option>
  </bk-select>
</template>

<script>
export default {
  name: 'cmdb-form-organization',
  props: {
    value: {
      type: [Array, String, Number],
      default: () => ([])
    },
    property: {
      type: Object,
      default: () => ({})
    },
    disabled: Boolean,
    readonly: Boolean,
    placeholder: {
      type: String,
      default: ''
    }
  },
  computed: {
    localMultiple() {
      // 组织字段是否多选：优先取属性定义，默认多选（部门 ID 数组）
      const isMultiple = this.property && this.property.ismultiple
      return isMultiple === undefined ? true : !!isMultiple
    },
    // 与 MongoDB organization 规则一致：存储为「部门 ID 数组」（bson.A / []interface{}）。
    // 读取时保持数组（单值/字符串规整为数组）；变更时回写数组。
    // 注：部门名称解析依赖 organization/department 接口，lite 后端暂未提供，
    // 此处先以 ID 展示，待补齐 org API 后可接入名称反查。
    localValue: {
      get() {
        if (this.value === null || this.value === undefined || this.value === '') return []
        if (Array.isArray(this.value)) return this.value
        if (typeof this.value === 'string') {
          return this.value.includes(',') ? this.value.split(',').map(v => v.trim()) : [this.value]
        }
        return [this.value]
      },
      set(val) {
        if (Array.isArray(val)) {
          this.$emit('input', val)
        } else {
          this.$emit('input', (val === '' || val === null || val === undefined) ? [] : [val])
        }
      }
    },
    // 无 org API 时以已选 ID 作为可选项（可移除/保留）；单选场景可切换。
    optionList() {
      return this.localValue
    }
  }
}
</script>
