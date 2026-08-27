<template>
  <bk-select
    v-model="localValue"
    :multiple="multiple"
    :placeholder="placeholder"
    :clearable="!multiple">
    <!--
      bk-select 的 option 项必须用 <bk-option> 子组件显式声明（id / name 必填），
      组件内部通过 registerOption 收集渲染。直接传 :options 在本版本不会渲染，
      这正是“枚举下拉为空 / 数据丢失”的根因。选中值取枚举 id（如 '1'），
      与后端实例存储的枚举值（bk_os_type='1'）一致。
    -->
    <bk-option
      v-for="item in optionList"
      :key="String(item.id)"
      :id="item.id"
      :name="item.name">
    </bk-option>
  </bk-select>
</template>

<script>
export default {
  name: 'SimpleEnumSelect',
  props: {
    value: {
      type: [String, Array],
      default: ''
    },
    placeholder: {
      type: String,
      default: ''
    },
    property: {
      type: Object,
      default: () => ({})
    }
  },
  computed: {
    multiple() {
      return this.property.ismultiple || this.property.bk_property_type === 'enummulti'
    },
    optionList() {
      try {
        const option = this.property.option
        if (!option) return []
        const parsed = typeof option === 'string' ? JSON.parse(option) : option
        if (Array.isArray(parsed)) {
          return parsed.map(item => ({
            id: item.id,
            name: item.name || item.id
          }))
        }
      } catch (e) {
        console.error('Parse enum option failed:', e)
      }
      return []
    },
    localValue: {
      get() {
        return this.value
      },
      set(val) {
        this.$emit('input', val)
        this.$emit('change', val)
      }
    }
  }
}
</script>
