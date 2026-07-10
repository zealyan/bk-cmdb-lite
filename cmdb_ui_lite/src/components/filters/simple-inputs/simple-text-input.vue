<template>
  <div class="text-input-wrapper">
    <bk-tag-input
      v-if="isMultiple"
      ref="tagInput"
      v-model="localValue"
      :placeholder="placeholder"
      :has-delete-icon="true"
      :allow-create="true"
      :allow-auto-match="true"
      :collapse-tags="true"
      :paste-fn="handlePasteFn"
      @remove-all="handleClear"
      @change="handleChange">
    </bk-tag-input>
    <bk-input
      v-else
      v-model="localValue"
      :placeholder="placeholder"
      @change="handleChange">
    </bk-input>
  </div>
</template>

<script>
export default {
  name: 'SimpleTextInput',
  props: {
    value: {
      type: [String, Array],
      default: ''
    },
    placeholder: {
      type: String,
      default: ''
    }
  },
  computed: {
    isMultiple() {
      return Array.isArray(this.value)
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
  },
  methods: {
    handlePasteFn(value) {
      if (!value) return this.localValue
      const values = value.split(/,|;|\n/)
        .map(v => v.trim())
        .filter(v => v.length > 0)
      const newValue = [...new Set([...this.localValue, ...values])]
      this.localValue = newValue
      return newValue
    },
    handleChange(val) {
      this.$emit('input', val)
      this.$emit('change', val)
    },
    handleClear() {
      this.localValue = []
      this.$emit('input', [])
      this.$emit('change', [])
    }
  }
}
</script>

<style lang="scss" scoped>
.text-input-wrapper {
  width: 100%;
}
</style>
