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
      @click="isShow = true">
      <i class="bk-icon icon-plus-circle"></i>
      {{ text }}
    </bk-button>
    <property-selector
      slot="content"
      v-if="isShow"
      ref="addConditionComp"
      :selected="selected"
      :disabled-property-map="disabledProperties"
      :models="models"
      :property-map="propertyMap"
      :height="height"
      @change="handleChange">
    </property-selector>
  </bk-popover>
</template>

<script>
import FilterStore from '@/components/filters/store'
import PropertySelector from './property-selector.vue'

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
    type: {
      type: Number,
      default: 3 // 1动态分组 2资源实例 3主机高级筛选
    },
    selected: {
      type: Array,
      default: () => ([])
    },
    propertyMap: {
      type: [Object, Array],
      default: () => ({})
    },
    handler: Function
  },
  data() {
    return {
      height: 490,
      isShow: false
    }
  },
  computed: {
    groups() {
      const sequence = ['host', 'module', 'set', 'biz']
      return Object.keys(this.propertyMap).map((modelId) => {
        return {
          id: modelId,
          name: modelId,
          children: this.propertyMap[modelId]
        }
      }).sort((groupA, groupB) => sequence.indexOf(groupA.id) - sequence.indexOf(groupB.id))
    },
    models() {
      const modelNameMap = {
        host: '主机',
        module: '模块',
        set: '集群',
        biz: '业务'
      }
      return this.groups.map(group => ({
        id: group.id,
        bk_obj_name: modelNameMap[group.id] || group.name,
        bk_obj_id: group.id
      }))
    },
    disabledProperties() {
      const disabledPropertyMap = {}
      this.groups.forEach((group) => {
        disabledPropertyMap[group.id] = []
      })
      return disabledPropertyMap
    }
  },
  watch: {
    isShow(val) {
      if (val) {
        const { bottom = 0 } = this.$refs?.popover?.$el?.getClientRects()?.[0] || {}
        const dis = window.innerHeight - bottom
        if (dis > 370 && dis < 500) {
          this.height = dis - 10
        } else {
          this.height = 490
        }
      }
    }
  },
  methods: {
    confirm() {
      this.isShow = false
    },
    handleChange() {
      const selected = this.$refs?.addConditionComp?.localSelected ?? this.selected
      if (this.type !== 3) {
        // type=1/2 时：更新 FilterStore 并通知父组件
        setTimeout(() => {
          FilterStore.updateSelected(selected)
          FilterStore.updateUserBehavior(selected)
          this.$emit('change', [...selected])
          this.handler && this.handler([...selected])
        })
        return
      }
      setTimeout(() => {
        FilterStore.updateSelected(selected)
        FilterStore.updateUserBehavior(selected)
        this.$emit('change', [...selected])
      })
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
