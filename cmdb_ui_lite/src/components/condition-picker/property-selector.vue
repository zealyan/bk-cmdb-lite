<template>
  <div class="property-selector-content" :style="{ height: `${height}px` }">
    <div class="property-selector-options">
      <bk-input class="options-filter"
        v-model.trim="filter"
        right-icon="icon-search"
        placeholder="请输入字段名称或唯一标识"
        clearable>
      </bk-input>
    </div>
    <div class="property-selector-container">
      <div class="property-selector-group clearfix"
        v-for="model in models"
        v-show="isShowGroup(model)"
        :key="model.id">
        <label class="group-label">
          {{model.bk_obj_name}}
          <span class="count">
            （{{matchedPropertyMap[model.bk_obj_id] ? matchedPropertyMap[model.bk_obj_id].length : 0}}）
          </span>
        </label>
        <bk-checkbox
          :disabled="getCheckDisabled(model.bk_obj_id)"
          :indeterminate="indeterminate[model.bk_obj_id]"
          :checked="allChecked[model.bk_obj_id]"
          @change="handleChangeAllCheck(model.bk_obj_id, $event)"
          class="all-check">
          全选
        </bk-checkbox>
        <div class="group-property-list">
          <bk-checkbox
            :class="['group-property-item',
                     { 'is-checked': isChecked(property),
                       'is-checked-diabled': isDisabled(model, property) }]"
            v-for="property in matchedPropertyMap[model.bk_obj_id]"
            v-show="isShowProperty(property)"
            :key="property.id"
            :title="property.bk_property_name"
            :checked="isChecked(property)"
            :disabled="isDisabled(model, property)"
            @change="handleChange(property, $event)">
            <div style="width: calc(100% - 30px);"
              v-bk-tooltips.top-start="{
                disabled: !isDisabled(model, property),
                content: '该字段不支持配置'
              }">
              <div class="group-property-name">{{property.bk_property_name}}</div>
            </div>
            <i class="icon-cc-selected"></i>
          </bk-checkbox>
        </div>
      </div>
    </div>

    <cmdb-data-empty v-if="isShowEmpty"
      :stuff="dataEmpty"
      @clear="handleClearFilter"></cmdb-data-empty>
  </div>
</template>

<script>
import debounce from 'lodash.debounce'

export default {
  name: 'PropertySelector',
  props: {
    height: {
      type: Number,
      default: 490
    },
    selected: {
      type: Array,
      default: () => ([])
    },
    disabledPropertyMap: {
      type: Object,
      default: () => ({})
    },
    models: {
      type: Array,
      default: () => ([])
    },
    propertyMap: {
      type: [Object, Array],
      default: () => ({})
    }
  },
  data() {
    return {
      filter: '',
      matchedPropertyMap: {},
      localSelected: [],
      indeterminate: {},
      allChecked: {},
      disabledPropertyCounts: {},
      dataEmpty: {
        type: 'empty',
        payload: {
          defaultText: '暂无数据'
        }
      }
    }
  },
  computed: {
    isShowEmpty() {
      let isNoData = true
      Object.values(this.matchedPropertyMap).forEach((value) => {
        if (value && value.length > 0) isNoData = false
      })
      return isNoData
    }
  },
  watch: {
    propertyMap: {
      handler(val) {
        this.matchedPropertyMap = JSON.parse(JSON.stringify(val))
        this.initDisabledProperty()
        this.initChecked()
      },
      immediate: true
    },
    selected: {
      handler(val) {
        this.localSelected = [...val]
        this.initChecked()
      },
      immediate: true
    },
    filter(val) {
      this.handleFilter(val)
      this.dataEmpty.type = val ? 'search' : 'empty'
    }
  },
  methods: {
    handleFilter: debounce(function(filter) {
      if (!filter.length) {
        this.matchedPropertyMap = JSON.parse(JSON.stringify(this.propertyMap))
      } else {
        const matchedPropertyMapOther = {}
        const lowerCaseFilter = filter.toLowerCase()
        Object.keys(this.propertyMap).forEach((modelId) => {
          const properties = this.propertyMap[modelId] || []
          matchedPropertyMapOther[modelId] = properties.filter((property) => {
            const lowerCaseName = (property.bk_property_name || '').toLowerCase()
            const lowerPropertyId = (property.bk_property_id || '').toLowerCase()
            return lowerCaseName.indexOf(lowerCaseFilter) > -1 || lowerPropertyId.indexOf(lowerCaseFilter) > -1
          })
        })
        this.matchedPropertyMap = matchedPropertyMapOther
      }
      Object.keys(this.matchedPropertyMap).forEach(property => this.allCheckState({ bk_obj_id: property }))
    }, 300),

    isShowGroup(model) {
      const props = this.matchedPropertyMap[model.bk_obj_id]
      return props && props.length > 0
    },

    isShowProperty(property) {
      const modelId = property.bk_obj_id
      return this.matchedPropertyMap[modelId] && this.matchedPropertyMap[modelId].some(target => target === property)
    },

    isChecked(property) {
      return this.localSelected.some(target => target.bk_property_id === property.bk_property_id)
    },

    isDisabled(model, property) {
      return this.disabledPropertyMap[model.bk_obj_id] && this.disabledPropertyMap[model.bk_obj_id].includes(property.bk_property_id)
    },

    getLength(bkObjId) {
      const length = (this.matchedPropertyMap[bkObjId] || []).length
      const disabledLength = this.disabledPropertyCounts[bkObjId] || 0
      return { length, disabledLength }
    },

    getCheckDisabled(bkObjId) {
      const { length, disabledLength } = this.getLength(bkObjId)
      return length === disabledLength
    },

    updateLocalSelected(property, checked) {
      const index = this.localSelected.findIndex(target => target.bk_property_id === property.bk_property_id)
      if (checked && index === -1) {
        this.localSelected.push(property)
      }
      if (!checked && index > -1) {
        this.localSelected.splice(index, 1)
      }
    },

    handleChange(property, checked) {
      this.updateLocalSelected(property, checked)
      this.allCheckState(property)
      this.$emit('change')
    },

    handleChangeAllCheck(bkObjId, checked) {
      this.$set(this.indeterminate, bkObjId, false)
      this.$set(this.allChecked, bkObjId, checked)
      const properties = this.matchedPropertyMap[bkObjId] || []
      properties.forEach((target) => {
        const isDisabled = this.disabledPropertyMap[bkObjId] && this.disabledPropertyMap[bkObjId].includes(target.bk_property_id)
        if (!isDisabled) {
          this.updateLocalSelected(target, checked)
        }
      })
      this.$emit('change')
    },

    allCheckState({ bk_obj_id: bkObjId }) {
      const { length, disabledLength } = this.getLength(bkObjId)
      if (length === 0) return
      const matchedPropertyMapIdSet = new Set()
      const properties = this.matchedPropertyMap[bkObjId] || []
      properties.forEach(property => matchedPropertyMapIdSet.add(property.bk_property_id))
      const currentCheckedCount = this.localSelected.filter(target => target.bk_obj_id === bkObjId
        && matchedPropertyMapIdSet.has(target.bk_property_id)).length || 0

      let isIndeterminate = false
      let isChecked = false

      if (currentCheckedCount > 0) {
        if (currentCheckedCount === length - disabledLength) {
          isChecked = true
        } else {
          isIndeterminate = true
        }
      }
      this.$set(this.indeterminate, bkObjId, isIndeterminate)
      this.$set(this.allChecked, bkObjId, isChecked)
    },

    handleClearFilter() {
      this.filter = ''
    },

    initChecked() {
      this.models.forEach((model) => {
        const objId = model.bk_obj_id
        if (objId) {
          this.allCheckState({ bk_obj_id: objId })
        }
      })
    },

    initDisabledProperty() {
      Object.keys(this.matchedPropertyMap).forEach((bkObjId) => {
        let length = 0
        const properties = this.matchedPropertyMap[bkObjId] || []
        properties.forEach((target) => {
          const isDisabled = this.disabledPropertyMap[bkObjId] && this.disabledPropertyMap[bkObjId].includes(target.bk_property_id)
          if (isDisabled) {
            length += 1
          }
        })
        this.$set(this.disabledPropertyCounts, bkObjId, length)
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.property-selector-content {
  width: 400px;
  max-height: 500px;
  padding: 10px 14px;
  margin: -.3rem -.6rem;
}
.property-selector-container {
  max-height: calc(100% - 32px);
  margin-right: -14px;
  margin-left: -14px;
  padding: 0 14px;
  overflow-y: auto;
}
.property-selector-group {
  margin-top: 15px;

  .group-label {
    display: block;
    font-weight: bold;
    font-size: 12px;
    color: #313237;
    float: left;

    .count {
      font-size: 12px;
      color: #63656E;
      font-weight: normal;
    }
  }

  .all-check {
    float: right;
    ::v-deep(.bk-checkbox-text) {
      font-size: 12px;
    }
  }

  .group-property-list {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    margin-top: 4px;
    gap: 3px 14px;
    float: left;
    width: 100%;

    .group-property-item {
      display: inline-flex;
      align-items: center;
      flex: calc(50% - 4px);
      line-height: 32px;
      padding-left: 6px;
      margin-left: -6px;

      .group-property-name {
        display: block;
        width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .icon-cc-selected {
        font-size: 24px;
        color: #3A84FF;
        opacity: 0;
      }

      &.is-checked,
      &:hover {
        background: #F5F7FA;
        border-radius: 2px;
      }

      &.is-checked {
        ::v-deep(.bk-checkbox-text) {
          color: #3A84FF;
        }
        .icon-cc-selected {
          opacity: 1;
        }
      }

      &.is-checked-diabled {
        background: #f9fafd;
        ::v-deep(.bk-checkbox-text),
        .icon-cc-selected {
          color: #dcdee5;
        }
      }

      ::v-deep {
        .bk-checkbox {
          flex: 16px 0 0;
          opacity: 0;
          position: absolute;
        }
        .bk-checkbox-text {
          font-size: 12px;
          padding-right: 10px;
          margin: 0;
          width: 100%;
          display: flex;
          justify-content: space-between;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }
  }
}
</style>
