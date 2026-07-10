export default {
  methods: {
    disabledTableSettingDefaultBehavior() {
      setTimeout(() => {
        const settingReference = this.$refs?.tableRef?.$el?.querySelector('.bk-table-column-setting .bk-tooltip-ref')
        settingReference && settingReference._tippy && settingReference._tippy.disable()
      }, 1000)
    }
  }
}
