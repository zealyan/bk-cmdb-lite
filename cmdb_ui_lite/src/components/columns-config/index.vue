<template>
  <div class="config-layout clearfix">
    <div class="config-wrapper config-unselected fl">
      <div class="wrapper-header unselected-header">
        <bk-input class="header-filter"
          type="text"
          clearable
          right-icon="bk-icon icon-search"
          placeholder="搜索属性"
          v-model.trim="filter">
        </bk-input>
      </div>
      <ul v-if="unselectedProperties.length" class="property-list property-list-unselected">
        <li class="property-item"
          v-for="(property, index) in unselectedProperties" :key="index"
          @click="selectProperty(property)">
          <span class="property-name">{{property['bk_property_name']}}</span>
          <i class="bk-icon icon-arrows-right"></i>
        </li>
      </ul>
      <div v-else class="data-empty">
        <div class="empty-icon"></div>
        <div class="empty-text">{{ filter ? '没有找到匹配的属性' : '暂无数据' }}</div>
      </div>
    </div>
    <div class="config-wrapper config-selected fl">
      <div class="wrapper-header selected-header">
        <label class="header-label">已选属性</label>
      </div>
      <div class="property-list-layout">
        <ul class="property-list property-list-selected">
          <li class="property-item disabled"
            v-for="(property, index) in undragbbleProperties" :key="'disabled-' + index">
            <span class="property-name" :title="property['bk_property_name']">{{property['bk_property_name']}}</span>
          </li>
        </ul>
        <draggable 
          element="ul" 
          class="property-list property-list-selected"
          v-model="localDrabbleProperties"
          :options="{ animation: 150 }">
          <li class="property-item"
            v-for="(property, index) in localDrabbleProperties" :key="'draggable-' + index">
            <i class="icon-triple-dot"></i>
            <span class="property-name" :title="property['bk_property_name']">{{property['bk_property_name']}}</span>
            <i class="bk-icon icon-close" @click.stop="unselectProperty(property)"></i>
          </li>
        </draggable>
      </div>
    </div>
    <div class="config-options clearfix">
      <bk-button class="config-button fl" theme="primary" @click="handleApply">
        {{confirmText || '应用'}}
      </bk-button>
      <bk-button class="config-button fl" theme="default" @click="handleCancel">取消</bk-button>
      <bk-button class="config-button fr" theme="default" @click="handleReset" v-if="showReset">
        还原默认
      </bk-button>
    </div>
  </div>
</template>

<script>
import draggable from 'vuedraggable'

export default {
  name: 'cmdb-columns-config',
  components: {
    draggable
  },
  props: {
    properties: {
      type: Array,
      default() {
        return []
      }
    },
    selected: {
      type: Array,
      default() {
        return []
      }
    },
    disabledColumns: {
      type: Array,
      default() {
        return []
      }
    },
    min: {
      type: Number,
      default: 1
    },
    max: {
      type: Number,
      default: 20
    },
    confirmText: {
      type: String,
      default: ''
    },
    showReset: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      filter: '',
      localSelected: []
    }
  },
  computed: {
    sortedProperties() {
      return [...this.properties].sort((propertyA, propertyB) => 
        propertyA.bk_property_name.localeCompare(propertyB.bk_property_name, 'zh-Hans-CN', { sensitivity: 'accent' })
      )
    },
    unselectedProperties() {
      return this.sortedProperties.filter((property) => {
        const unselected = !this.localSelected.includes(property.bk_property_id)
        const includesFilter = property.bk_property_name.toLowerCase().indexOf(this.filter.toLowerCase()) !== -1
        return unselected && includesFilter
      })
    },
    undragbbleProperties() {
      const undragbbleProperties = []
      this.disabledColumns.forEach((id) => {
        const isSelected = this.localSelected.includes(id)
        if (isSelected) {
          const property = this.properties.find(property => property.bk_property_id === id)
          if (property) {
            undragbbleProperties.push(property)
          }
        }
      })
      return undragbbleProperties
    },
    localDrabbleProperties: {
      get() {
        const drabbleProperties = []
        this.localSelected.forEach((propertyId) => {
          if (!this.disabledColumns.includes(propertyId)) {
            const property = this.properties.find(property => property.bk_property_id === propertyId)
            if (property) {
              drabbleProperties.push(property)
            }
          }
        })
        return drabbleProperties
      },
      set(value) {
        this.localSelected = [
          ...this.undragbbleProperties.map(p => p.bk_property_id),
          ...value.map(p => p.bk_property_id)
        ]
      }
    }
  },
  watch: {
    selected() {
      this.initLocalSelected()
    }
  },
  created() {
    this.initLocalSelected()
  },
  methods: {
    initLocalSelected() {
      this.localSelected = this.selected.filter(propertyId => 
        this.properties.some(property => property.bk_property_id === propertyId)
      )
    },
    selectProperty(property) {
      if (this.localSelected.length < this.max) {
        this.localSelected.push(property.bk_property_id)
      } else {
        this.$bkInfo(`最多选择${this.max}项`)
      }
    },
    unselectProperty(property) {
      if (this.localSelected.length > this.min) {
        this.localSelected = this.localSelected.filter(propertyId => propertyId !== property.bk_property_id)
      } else {
        this.$bkInfo(`至少选择${this.min}项`)
      }
    },
    handleApply() {
      if (this.localSelected.length > this.max) {
        this.$bkInfo(`最多选择${this.max}项`)
      } else if (this.localSelected.length < this.min) {
        this.$bkInfo(`至少选择${this.min}项`)
      } else {
        const properties = [...this.undragbbleProperties, ...this.localDrabbleProperties]
        this.$emit('on-apply', properties)
        this.$emit('apply', properties)
      }
    },
    handleCancel() {
      this.$emit('on-cancel')
      this.$emit('cancel')
    },
    handleReset() {
      this.$bkInfo({
        title: '确认还原配置',
        subTitle: '是否还原为系统默认的列表属性配置？',
        extCls: 'bk-dialog-sub-header-center',
        confirmFn: () => {
          this.$emit('on-reset')
          this.$emit('reset')
        }
      })
    },
  }
}
</script>

<style lang="scss" scoped>
.config-layout {
  height: 100%;
  font-size: 14px;
  position: relative;
}
.config-wrapper {
  width: 50%;
  height: 100%;
  border-right: 1px solid #e7e9ef;
  float: left;
  box-sizing: border-box;
  padding-bottom: 62px;
  
  .wrapper-header {
    height: 78px;
    padding: 20px 24px;
    line-height: 36px;
    box-sizing: border-box;
    .header-label {
      display: inline-block;
      vertical-align: middle;
      min-width: 120px;
    }
    .header-filter {
      display: inline-block;
      vertical-align: middle;
      width: 100%;
    }
  }
}
.property-list-layout {
  height: calc(100% - 78px);
  padding: 0;
  overflow-y: auto;
  box-sizing: border-box;
  padding-bottom: 62px;
}
.property-list {
  &-selected {
    .property-item {
      cursor: move;
    }
  }
  &-unselected {
    height: calc(100% - 78px);
    overflow-y: auto;
    padding-bottom: 62px;
    box-sizing: border-box;
  }
  .property-item {
    position: relative;
    height: 42px;
    line-height: 42px;
    padding: 0 0 0 24px;
    cursor: pointer;
    &.disabled {
      cursor: not-allowed;
    }
    &:hover {
      background-color: #f9f9f9;
    }
    .property-name {
      display: inline-block;
      vertical-align: top;
      max-width: calc(100% - 50px);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .icon-triple-dot {
                position: absolute;
                left: 15px;
                top: 19px;
            }
    .icon-arrows-right {
      position: absolute;
      top: 11px;
      right: 15px;
      font-size: 20px;
      color: #979ba5;
    }
    .icon-close {
      position: absolute;
      top: 0;
      right: 0;
      width: 42px;
      height: 42px;
      line-height: 42px;
      text-align: center;
      color: #c4c6cc;
      font-size: 20px;
      cursor: pointer;
      &:hover {
        color: #7d8088;
      }
    }
  }
}
.config-options {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 62px;
  padding: 13px 24px;
  background-color: #f9f9f9;
  box-sizing: border-box;
  z-index: 10;
  .config-button {
    min-width: 110px;
    margin: 0 0 0 10px;
    &:first-child {
      margin: 0;
    }
  }
}
.data-empty {
  height: calc(100% - 78px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  .empty-icon {
    width: 100px;
    height: 80px;
    background: 
      linear-gradient(#e7e9ef 0 0) 10px 10px /20px 14px,
      linear-gradient(#e7e9ef 0 0) 35px 10px /20px 14px,
      linear-gradient(#e7e9ef 0 0) 60px 10px /20px 14px,
      linear-gradient(#e7e9ef 0 0) 10px 30px /20px 14px,
      linear-gradient(#e7e9ef 0 0) 35px 30px /20px 14px,
      linear-gradient(#e7e9ef 0 0) 60px 30px /20px 14px,
      linear-gradient(#e7e9ef 0 0) 10px 50px /20px 14px;
    background-repeat: no-repeat;
  }
  .empty-text {
    margin-top: 16px;
    color: #979ba5;
    font-size: 12px;
  }
}
.clearfix::after {
  content: '';
  display: table;
  clear: both;
}
.fl {
  float: left;
}
.fr {
  float: right;
}
</style>
