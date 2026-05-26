<template>
  <bk-popover ref="popover" :tippy-options="{
    delay: 0,
    hideOnClick: true,
    interactive: true,
    placement: 'bottom-start',
    animateFill: false,
    sticky: true,
    theme: 'light',
    boundary: 'window',
    trigger: 'click',
    zIndex: 9999,
    onHidden: () => {
      confirm()
    }
  }">
    <bk-button class="form-condition-button" :style="{ marginTop: selected.length ? '5px' : 0 }"
      :text="true"
      :disabled="disabled"
      @click="openPopover">
      <i class="bk-icon icon-plus-circle"></i>
      {{ text }}
    </bk-button>
    <property-selector
      v-if="isShow"
      :key="popKey"
      slot="content"
      ref="addConditionComp"
      :selected="currentSelected"
      :properties="properties"
      :height="height"
      @change="handleChange">
    </property-selector>
  </bk-popover>
</template>

<script>
import PropertySelector from './property-selector.vue'
import FilterStore from '@/store/filter-store.js'

export default {
  name: 'ConditionPicker',
  components: {
    PropertySelector
  },
  props: {
    disabled: {
      type: Boolean,
      default: false
    },
    text: {
      type: String,
      default: '添加条件'
    },
    selected: {
      type: Array,
      default: () => []
    },
    properties: {
      type: Array,
      default: () => []
    },
    handler: Function
  },
  data() {
    return {
      height: 490,
      isShow: false,
      popKey: 0
    }
  },
  computed: {
    currentSelected() {
      const val = FilterStore.selected.length > 0 ? FilterStore.selected : this.selected
      console.log('[DEBUG] ConditionPicker currentSelected computed', {
        fromFilterStore: FilterStore.selected.length,
        fromProps: this.selected.length,
        result: val.length
      })
      return val
    }
  },
  created() {
    console.log('[DEBUG] ConditionPicker created', {
      propsSelected: this.selected.length,
      propsProperties: this.properties.length
    })
    if (this.properties.length > 0) {
      FilterStore.setProperties(this.properties)
    }
  },
  watch: {
    properties: {
      immediate: true,
      handler(newVal) {
        console.log('[DEBUG] ConditionPicker properties watch', newVal?.length)
        if (newVal && newVal.length > 0) {
          FilterStore.setProperties(newVal)
        }
      }
    }
  },
  methods: {
    openPopover() {
      console.log('[DEBUG] ConditionPicker openPopover called', {
        popKey: this.popKey,
        selected: this.selected.length,
        filterStoreSelected: FilterStore.selected.length
      })
      this.isShow = false
      this.$nextTick(() => {
        this.isShow = true
        this.popKey++
        if (this.selected.length > 0) {
          FilterStore.updateSelected(this.selected)
        }
        console.log('[DEBUG] ConditionPicker openPopover done', {
          newPopKey: this.popKey,
          isShow: this.isShow
        })
      })
    },
    confirm() {
      console.log('[DEBUG] ConditionPicker confirm called')
      this.isShow = false
    },
    handleChange() {
      console.log('[DEBUG] ConditionPicker handleChange called')
      const selected = this.$refs?.addConditionComp?.localSelected ?? this.currentSelected
      console.log('[DEBUG] ConditionPicker handleChange selected', selected?.length, selected?.map(p => p.bk_property_name))
      FilterStore.updateSelected([...selected])
      if (this.handler) {
        this.handler([...selected])
      }
    }
  }
}
</script>
<style lang="scss" scoped>
.form-condition-button {
  :deep(> div) {
    display: flex;
    align-items: center;
    .bk-icon {
      line-height: normal;
    }
  }
}
</style>