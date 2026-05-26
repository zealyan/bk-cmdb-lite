<template>
  <div class="property-selector-content" :style="{
    height: `${height}px`
  }">
    <div class="property-selector-options">
      <bk-input class="options-filter"
        v-model.trim="filter"
        right-icon="icon-search"
        placeholder="请输入字段名称或唯一标识"
        clearable>
      </bk-input>
    </div>
    <div class="property-selector-container">
      <div class="property-selector-group clearfix">
        <label class="group-label">
          属性
          <span class="count">
            （{{ matchedProperties.length }}）
          </span>
        </label>
        <bk-checkbox
          ref="checkboxRef"
          :indeterminate="indeterminate"
          :checked="allChecked"
          @change="handleAllCheckChange"
          class="all-check"
        >全选</bk-checkbox>
        <div class="group-property-list">
          <bk-checkbox
            :class="['group-property-item',
                     { 'is-checked': isChecked(property),
                       'is-checked-diabled': isDisabled(property) }]"
            v-for="property in matchedProperties"
            :key="property.bk_property_id"
            :title="property.bk_property_name"
            :checked="isChecked(property)"
            :disabled="isDisabled(property)"
            @change="handlePropertyChange(property, $event)">
            <div style="width: calc(100% - 30px);">
              <div class="group-property-name">{{ property.bk_property_name }}</div>
            </div>
            <i class="icon-cc-selected"></i>
          </bk-checkbox>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PropertySelector',
  props: {
    height: {
      type: Number,
      default: 490
    },
    selected: {
      type: Array,
      default: () => []
    },
    properties: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      filter: '',
      localSelected: [],
      allChecked: false,
      indeterminate: false,
      matchedProperties: []
    }
  },
  computed: {
    availableProperties() {
      return this.properties.filter(p => p.bk_property_id !== 'id')
    },
    disabledPropertyIds() {
      return this.selected.map(p => p.bk_property_id)
    }
  },
  watch: {
    filter(val) {
      console.log('[DEBUG] filter watch', val)
      this.handleFilter(val)
    },
    selected: {
      immediate: true,
      deep: true,
      handler(newVal) {
        console.log('[DEBUG] selected prop watch', newVal?.length, newVal?.map(p => p.bk_property_name))
        this.localSelected = [...newVal]
        // 确保 matchedProperties 已经被初始化
        if (this.matchedProperties.length === 0 && this.availableProperties.length > 0) {
          this.matchedProperties = [...this.availableProperties]
          console.log('[DEBUG] selected watcher initialized matchedProperties', this.matchedProperties.length)
        }
        this.checkAllState()
      }
    }
  },
  created() {
    console.log('[DEBUG] created lifecycle', {
      selectedLength: this.selected.length,
      propertiesLength: this.properties.length
    })
    this.localSelected = [...this.selected]
    this.matchedProperties = [...this.availableProperties]
    this.filter = ''
    this.checkAllState()
  },
  mounted() {
    console.log('[DEBUG] mounted lifecycle', {
      selectedLength: this.selected.length,
      propertiesLength: this.properties.length,
      localSelected: this.localSelected.map(p => p.bk_property_name)
    })
    this.localSelected = [...this.selected]
    this.matchedProperties = [...this.availableProperties]
    this.filter = ''
    this.checkAllState()
  },
  methods: {
    handleFilter(filter) {
      console.log('[DEBUG] handleFilter', { filter, availableCount: this.availableProperties.length })
      if (!filter) {
        this.matchedProperties = this.availableProperties
      } else {
        const lowerFilter = filter.toLowerCase()
        this.matchedProperties = this.availableProperties.filter(property => {
          return property.bk_property_name.toLowerCase().includes(lowerFilter) || 
                 property.bk_property_id.toLowerCase().includes(lowerFilter)
        })
      }
      console.log('[DEBUG] handleFilter result', { matchedCount: this.matchedProperties.length })
      this.checkAllState()
    },
    isChecked(property) {
      const checked = this.localSelected.some(target => target.bk_property_id === property.bk_property_id)
      return checked
    },
    isDisabled(property) {
      return this.disabledPropertyIds.includes(property.bk_property_id)
    },
    handlePropertyChange(property, event) {
      console.log('[DEBUG] handlePropertyChange', {
        property: property.bk_property_name,
        eventType: typeof event,
        event
      })
      let checked
      if (typeof event === 'boolean') {
        checked = event
      } else if (event.target) {
        checked = event.target.checked
      } else {
        checked = false
      }
      console.log('[DEBUG] handlePropertyChange resolved', { checked })
      this.updateLocalSelected(property, checked)
      this.checkAllState()
      console.log('[DEBUG] after handlePropertyChange', {
        localSelectedLength: this.localSelected.length,
        allChecked: this.allChecked,
        indeterminate: this.indeterminate
      })
      this.$emit('change')
    },
    handleAllCheckChange(event) {
      console.log('[DEBUG] handleAllCheckChange', {
        eventType: typeof event,
        event
      })
      let checked
      if (typeof event === 'boolean') {
        checked = event
      } else if (event.target) {
        checked = event.target.checked
      } else {
        checked = false
      }
      console.log('[DEBUG] handleAllCheckChange resolved', { checked })
      this.indeterminate = false
      this.allChecked = checked
      console.log('[DEBUG] handleAllCheckChange before', {
        localSelectedLength: this.localSelected.length,
        matchedPropertiesLength: this.matchedProperties.length
      })
      if (checked) {
        this.matchedProperties.forEach(target => {
          if (!this.isDisabled(target)) {
            this.addToSelected(target)
          }
        })
      } else {
        this.localSelected = this.localSelected.filter(item => this.isDisabled(item))
      }
      console.log('[DEBUG] handleAllCheckChange after', {
        localSelectedLength: this.localSelected.length,
        allChecked: this.allChecked
      })
      this.checkAllState()
      console.log('[DEBUG] after checkAllState in allCheck', {
        allChecked: this.allChecked,
        indeterminate: this.indeterminate
      })
      this.$emit('change')
    },
    addToSelected(property) {
      const exists = this.localSelected.some(item => item.bk_property_id === property.bk_property_id)
      if (!exists) {
        this.localSelected.push(property)
        console.log('[DEBUG] addToSelected added', property.bk_property_name)
      } else {
        console.log('[DEBUG] addToSelected already exists', property.bk_property_name)
      }
    },
    updateLocalSelected(property, checked) {
      console.log('[DEBUG] updateLocalSelected', {
        property: property.bk_property_name,
        checked
      })
      const index = this.localSelected.findIndex(item => item.bk_property_id === property.bk_property_id)
      console.log('[DEBUG] updateLocalSelected index', index)
      if (checked && index === -1) {
        this.localSelected.push(property)
        console.log('[DEBUG] updateLocalSelected added')
      } else if (!checked && index > -1) {
        this.localSelected.splice(index, 1)
        console.log('[DEBUG] updateLocalSelected removed')
      }
      console.log('[DEBUG] updateLocalSelected final length', this.localSelected.length)
    },
    checkAllState() {
      console.log('[DEBUG] checkAllState called')
      const availableCount = this.matchedProperties.filter(p => !this.isDisabled(p)).length
      const checkedCount = this.matchedProperties.filter(p => this.isChecked(p) && !this.isDisabled(p)).length
      console.log('[DEBUG] checkAllState counts', {
        availableCount,
        checkedCount
      })
      if (availableCount === 0) {
        this.allChecked = false
        this.indeterminate = false
        console.log('[DEBUG] checkAllState no available items')
        return
      }
      if (checkedCount > 0) {
        if (checkedCount === availableCount) {
          this.allChecked = true
          this.indeterminate = false
          console.log('[DEBUG] checkAllState all checked')
        } else {
          this.allChecked = false
          this.indeterminate = true
          console.log('[DEBUG] checkAllState partially checked, show indeterminate')
        }
      } else {
        this.allChecked = false
        this.indeterminate = false
        console.log('[DEBUG] checkAllState none checked')
      }
      console.log('[DEBUG] checkAllState result', {
        allChecked: this.allChecked,
        indeterminate: this.indeterminate
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
  box-sizing: border-box;
}

.property-selector-options {
  width: 100%;
  box-sizing: border-box;
}

.options-filter {
  width: 100%;
  box-sizing: border-box;
  :deep(.bk-form-control) {
    width: 100%;
    box-sizing: border-box;
  }
  :deep(.bk-input-text) {
    width: 100%;
    box-sizing: border-box;
  }
  :deep(.bk-form-input) {
    width: 100%;
    box-sizing: border-box;
  }
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
}

.group-label {
  display: block;
  font-weight: bold;
  font-size: 12px;
  color: #313237;
  float: left;
}

.count {
  font-size: 12px;
  color: #63656E;
  font-weight: normal;
}

.all-check {
  float: right;
  :deep(.bk-checkbox-text) {
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
}

.group-property-item {
  display: inline-flex;
  align-items: center;
  flex: calc(50% - 4px);
  line-height: 32px;
  padding-left: 6px;
  margin-left: -6px;
  box-sizing: border-box;
  border-radius: 2px;
  transition: background-color 0.2s;
}

.group-property-name {
  display: block;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.icon-cc-selected {
  font-size: 24px;
  color: #3A84FF;
  opacity: 0;
}

.group-property-item {
  &:hover {
    background: #F5F7FA;
  }

  &.is-checked {
    background: #F5F7FA;
  }
}

.group-property-item.is-checked {
  :deep(.bk-checkbox-text) {
    color: #3A84FF;
  }
  .icon-cc-selected {
    opacity: 1;
  }
}

.group-property-item.is-checked-diabled {
  background: #f9fafd;
  :deep(.bk-checkbox-text),
  .icon-cc-selected {
    color: #dcdee5;
  }
}

.group-property-item :deep {
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
    align-items: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.clearfix::after {
  content: '';
  display: table;
  clear: both;
}
</style>