<template>
  <bk-select
    v-model="localValue"
    :disabled="disabled || readonly"
    :clearable="true"
    searchable
    @change="handleChange">
    <bk-option
      v-for="tz in timezoneList"
      :key="tz.value"
      :id="tz.value"
      :name="tz.label">
    </bk-option>
  </bk-select>
</template>

<script>
export default {
  name: 'cmdb-form-timezone',
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
  data() {
    return {
      localValue: '',
      timezoneList: [
        { value: 'UTC', label: 'UTC (GMT+0:00)' },
        { value: 'Asia/Shanghai', label: 'Asia/Shanghai (GMT+8:00)' },
        { value: 'Asia/Tokyo', label: 'Asia/Tokyo (GMT+9:00)' },
        { value: 'America/New_York', label: 'America/New_York (GMT-5:00)' },
        { value: 'America/Los_Angeles', label: 'America/Los_Angeles (GMT-8:00)' },
        { value: 'Europe/London', label: 'Europe/London (GMT+0:00)' },
        { value: 'Europe/Paris', label: 'Europe/Paris (GMT+1:00)' }
      ]
    }
  },
  watch: {
    value: {
      immediate: true,
      handler(val) {
        this.localValue = val
      }
    }
  },
  methods: {
    handleChange(val) {
      this.$emit('input', val)
    }
  }
}
</script>
