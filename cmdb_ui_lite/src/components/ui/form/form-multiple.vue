<template>
  <div class="cmdb-form-multiple-layout">
    <div class="form-groups" v-if="hasAvailableGroups" ref="formGroups">
      <template v-for="(group, groupIndex) in groupedPropertiesList">
        <div class="property-group" :key="groupIndex" v-if="hasPropertiesInGroup(group.properties).length">
          <div class="group-header" @click="toggleGroup(group.bk_group_id)">
            <i :class="['bk-icon', 'icon-angle-down', { 'icon-flip': !groupState[group.bk_group_id] }]"></i>
            <span class="group-name">{{ group.bk_group_name }}</span>
          </div>
          <div class="group-content" v-show="!groupState[group.bk_group_id]">
            <ul class="property-list">
              <template v-for="(property, propertyIndex) in hasPropertiesInGroup(group.properties)">
                <li :class="['property-item', property.bk_property_type, { 'full-width': isFullWidth(property) }]"
                  :key="propertyIndex">
                  <div class="property-name">
                    <bk-checkbox class="property-name-checkbox"
                      v-model="editable[property.bk_property_id]"
                      :disabled="isDisabledForbidden(property)">
                      <span class="property-name-text"
                        :class="{ required: property.isrequired && editable[property.bk_property_id] }">
                        {{ property.bk_property_name }}
                      </span>
                      <i class="bk-icon icon-cc-tips property-tips"
                        v-if="property.placeholder"
                        v-bk-tooltips="{ trigger: 'mouseenter', content: property.placeholder }">
                      </i>
                    </bk-checkbox>
                  </div>
                  <div class="property-value">
                    <component
                      :is="getComponentName(property.bk_property_type)"
                      :property="property"
                      :value="values[property.bk_property_id]"
                      :disabled="!editable[property.bk_property_id]"
                      :options="parseOptions(property.option)"
                      :unit="property.unit"
                      :multiple="property.ismultiple"
                      :placeholder="getPropertyPlaceholder(property)"
                      @input="handleInput(property.bk_property_id, $event)"
                      @change="handleInput(property.bk_property_id, $event)">
                    </component>
                    <span v-if="errorMessages[property.bk_property_id]" class="form-error">
                      {{ errorMessages[property.bk_property_id] }}
                    </span>
                  </div>
                </li>
              </template>
            </ul>
          </div>
        </div>
      </template>
    </div>
    <div class="form-empty" v-else>
      {{ $t('暂无可批量更新的属性') }}
    </div>
    <div class="form-options" v-if="showOptions">
      <slot name="form-options">
        <bk-button theme="primary" :loading="submitting" :disabled="!hasChange" @click="handleSave">
          {{ submitText }}
        </bk-button>
        <bk-button :disabled="submitting" @click="handleCancel">取消</bk-button>
      </slot>
    </div>
  </div>
</template>

<script>
export default {
  name: 'cmdb-form-multiple',
  props: {
    properties: {
      type: Array,
      default: () => []
    },
    showOptions: {
      type: Boolean,
      default: true
    },
    submitting: {
      type: Boolean,
      default: false
    },
    submitText: {
      type: String,
      default: '提交'
    },
    uneditableProperties: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      values: {},
      editable: {},
      groupState: {},
      errorMessages: {}
    }
  },
  computed: {
    hasChange() {
      return Object.values(this.editable).some(v => v)
    },
    hasAvailableGroups() {
      return this.groupedPropertiesList.some(group => this.hasPropertiesInGroup(group.properties).length > 0)
    },
    groupedPropertiesList() {
      const groups = {}
      this.properties.forEach(property => {
        const groupId = property.bk_group_id || 'default'
        if (!groups[groupId]) {
          groups[groupId] = {
            bk_group_id: groupId,
            bk_group_name: property.bk_group_name || '基本信息',
            properties: []
          }
        }
        groups[groupId].properties.push(property)
      })
      return Object.values(groups)
    }
  },
  created() {
    this.initValues()
    this.initEditableStatus()
    this.initGroupState()
  },
  watch: {
    properties: {
      handler() {
        this.initValues()
        this.initEditableStatus()
        this.initGroupState()
      },
      deep: true
    }
  },
  methods: {
    initValues() {
      const values = {}
      this.properties.forEach(property => {
        if (this.isPropertyEditable(property)) {
          values[property.bk_property_id] = this.getPropertyDefaultValue(property)
        }
      })
      this.values = values
    },
    initEditableStatus() {
      const editable = {}
      this.properties.forEach(property => {
        if (this.isPropertyEditable(property)) {
          editable[property.bk_property_id] = false
        }
      })
      this.editable = editable
    },
    initGroupState() {
      this.groupedPropertiesList.forEach(group => {
        this.$set(this.groupState, group.bk_group_id, false)
      })
    },
    toggleGroup(groupId) {
      this.groupState[groupId] = !this.groupState[groupId]
    },
    isPropertyEditable(property) {
      // 与原项目保持一致: /workspace/bk-cmdb/src/ui/src/components/ui/form/form-multiple.vue
      const BUILTIN_UNEDITABLE_FIELDS = ['bk_updated_by', 'bk_updated_at', 'bk_created_by', 'bk_created_at']
      const UNEDITABLE_TYPES = ['singleasst', 'multiasst', 'foreignkey', 'innerTable', 'table']
      
      if (BUILTIN_UNEDITABLE_FIELDS.includes(property.bk_property_id)) {
        return false
      }
      if (this.uneditableProperties.includes(property.bk_property_id)) {
        return false
      }
      if (UNEDITABLE_TYPES.includes(property.bk_property_type)) {
        return false
      }
      if (property.bk_ishidden) {
        return false
      }
      if (property.bk_issystem) {
        return false
      }
      if (property.bk_isapi) {
        return false
      }
      return property.editable !== false && !property.isreadonly
    },
    isDisabledForbidden(property) {
      return !this.isPropertyEditable(property)
    },
    isFullWidth(property) {
      return ['innerTable', 'table', 'text', 'longchar'].includes(property.bk_property_type)
    },
    hasPropertiesInGroup(properties) {
      return properties.filter(p => this.isPropertyEditable(p))
    },
    getPropertyDefaultValue(property) {
      if (property.default !== null && property.default !== undefined) {
        return property.default
      }
      switch (property.bk_property_type) {
        case 'int':
        case 'float':
          return null
        case 'bool':
          return null
        case 'enum':
        case 'list':
        case 'enumMulti':
          return ''
        case 'date':
        case 'time':
        case 'datetime':
          return ''
        default:
          return ''
      }
    },
    getComponentName(type) {
      const componentMap = {
        'singlechar': 'cmdb-form-singlechar',
        'longchar': 'cmdb-form-longchar',
        'int': 'cmdb-form-int',
        'float': 'cmdb-form-float',
        'bool': 'cmdb-form-bool',
        'enum': 'cmdb-form-enum',
        'enumMulti': 'cmdb-form-enummulti',
        'list': 'cmdb-form-list',
        'date': 'cmdb-form-date',
        'time': 'cmdb-form-time',
        'datetime': 'cmdb-form-datetime',
        'timezone': 'cmdb-form-timezone',
        'organization': 'cmdb-form-organization',
        'user': 'cmdb-form-user'
      }
      return componentMap[type] || 'cmdb-form-singlechar'
    },
    getPropertyPlaceholder(property) {
      return property.placeholder || ''
    },
    parseOptions(option) {
      if (!option) return []
      if (Array.isArray(option)) return option
      try {
        const parsed = JSON.parse(option)
        return Array.isArray(parsed) ? parsed : []
      } catch {
        return []
      }
    },
    handleInput(propertyId, value) {
      this.$set(this.values, propertyId, value)
      if (this.editable[propertyId]) {
        this.validateProperty(propertyId, value)
      }
    },
    validateProperty(propertyId, value) {
      if (!this.editable[propertyId]) {
        this.$delete(this.errorMessages, propertyId)
        return true
      }
      
      const property = this.properties.find(p => p.bk_property_id === propertyId)
      if (!property) return true

      const errors = []
      if (property.isrequired && (value === undefined || value === null || value === '')) {
        errors.push(`${property.bk_property_name}不能为空`)
      }

      if (errors.length > 0) {
        this.$set(this.errorMessages, propertyId, errors[0])
        return false
      } else {
        this.$delete(this.errorMessages, propertyId)
        return true
      }
    },
    validateAll() {
      let isValid = true
      const errors = {}
      
      const editableProperties = this.properties.filter(p => this.editable[p.bk_property_id])
      
      editableProperties.forEach(property => {
        const value = this.values[property.bk_property_id]
        if (!this.validateProperty(property.bk_property_id, value)) {
          isValid = false
          errors[property.bk_property_id] = this.errorMessages[property.bk_property_id]
        }
      })
      
      this.errorMessages = errors
      return isValid
    },
    getMultipleValues() {
      const result = {}
      Object.keys(this.editable).forEach(propertyId => {
        if (this.editable[propertyId]) {
          result[propertyId] = this.values[propertyId]
        }
      })
      return result
    },
    handleSave() {
      if (!this.hasChange) {
        this.$bkMessage({ message: '请选择要更新的属性', theme: 'warning' })
        return
      }
      
      if (this.validateAll()) {
        this.$emit('submit', this.getMultipleValues())
      }
    },
    handleCancel() {
      this.$emit('cancel')
    },
    reset() {
      this.initValues()
      this.initEditableStatus()
      this.errorMessages = {}
    }
  }
}
</script>

<style lang="scss" scoped>
.cmdb-form-multiple-layout {
  height: 100%;
  overflow-y: auto;
  
  .form-groups {
    padding: 0 24px;
  }
  .property-group {
    padding: 7px 0 10px 0;
    border-bottom: 1px solid #e6e6e6;
    &:first-child {
      padding: 28px 0 10px 0;
    }
    &:last-child {
      border-bottom: none;
    }
  }
  .group-header {
    display: flex;
    align-items: center;
    padding: 12px 0;
    cursor: pointer;
    user-select: none;
    .icon-angle-down {
      margin-right: 8px;
      font-size: 12px;
      color: #63656e;
      transition: transform 0.2s;
      &.icon-flip {
        transform: rotate(-90deg);
      }
    }
    .group-name {
      font-size: 14px;
      font-weight: 500;
      color: #313238;
    }
  }
  .group-content {
    padding-bottom: 10px;
  }
  .property-list {
    padding: 4px 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0 54px;
  }
  .property-item {
    width: calc(50% - 27px);
    margin: 12px 0 0;
    font-size: 12px;
    flex: 0 0 calc(50% - 27px);
    max-width: 50%;
    display: flex;
    flex-direction: column;
    &.full-width {
      flex: 1 1 100%;
      width: 100%;
      max-width: 100%;
    }
    .property-name {
      display: flex;
      align-items: center;
      margin: 2px 0 6px;
      .property-name-checkbox {
        width: 100%;
        display: flex;
        align-items: center;
        .property-name-text {
          font-size: 14px;
          color: #63656e;
          margin-left: 4px;
          &.required::after {
            content: "*";
            color: #ff5656;
            margin-left: 4px;
          }
        }
        .property-tips {
          margin-left: 4px;
          color: #c3cdd7;
          cursor: help;
        }
      }
    }
    .property-value {
      position: relative;
      flex: 1;
    }
    .form-error {
      position: absolute;
      top: 100%;
      left: 0;
      font-size: 12px;
      color: #ff5656;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
  .form-empty {
    height: 200px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #979ba5;
    font-size: 14px;
  }
  .form-options {
    display: flex;
    gap: 10px;
    padding: 20px 24px;
    border-top: 1px solid #e6e6e6;
    background: #fafbfc;
  }
}

// 平板端适配
@media screen and (max-width: 1199px) {
  .cmdb-form-multiple-layout {
    .property-list {
      flex-direction: column;
      gap: 0;
    }
    .property-item {
      width: 100%;
      flex: 1 1 100%;
      max-width: 100%;
      margin: 8px 0;
    }
  }
}

// 移动端适配
@media screen and (max-width: 768px) {
  .cmdb-form-multiple-layout {
    .form-groups {
      padding: 0 16px;
    }
    .property-group {
      &:first-child {
        padding: 16px 0 10px 0;
      }
    }
    .group-header {
      padding: 10px 0;
      background: #f5f7fa;
      border-radius: 4px;
      padding-left: 12px;
      .group-name {
        font-size: 13px;
      }
    }
    .property-list {
      flex-direction: column;
      gap: 0;
    }
    .property-item {
      width: 100%;
      flex: 1 1 100%;
      max-width: 100%;
      margin: 8px 0;
    }
    .form-options {
      position: sticky;
      bottom: 0;
      padding: 12px 16px;
      gap: 8px;
      flex-wrap: wrap;
      .bk-button {
        flex: 1;
        min-width: 80px;
      }
    }
  }
}
</style>
