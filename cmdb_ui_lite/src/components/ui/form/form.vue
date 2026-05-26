<template>
  <div class="cmdb-form-layout">
    <div class="form-groups">
      <template v-for="(group, groupIndex) in groupedPropertiesList">
        <div class="property-group" :key="groupIndex" v-if="hasEditableProperties(group.properties)">
          <div class="group-header" @click="toggleGroup(group.bk_group_id)">
            <i :class="['bk-icon', 'icon-angle-down', { 'icon-flip': !groupState[group.bk_group_id] }]"></i>
            <span class="group-name">{{ group.bk_group_name }}</span>
          </div>
          <div class="group-content" v-show="!groupState[group.bk_group_id]">
            <ul class="property-list">
              <li
                v-for="(property, pIndex) in group.properties"
                :key="pIndex"
                v-if="checkEditable(property)"
                class="property-item"
                :class="[property.bk_property_type, { 'full-width': isFullWidth(property) }]">
                <div class="property-name">
                  <span class="property-name-text" :class="{ required: property.isrequired }">
                    {{ property.bk_property_name }}
                  </span>
                  <i class="bk-icon icon-cc-tips property-tips"
                    v-if="property.placeholder"
                    v-bk-tooltips="{ trigger: 'mouseenter', content: property.placeholder }">
                  </i>
                </div>
                <div class="property-value">
                  <slot :name="property.bk_property_id">
                    <component
                      :is="getComponentName(property.bk_property_type)"
                      :property="property"
                      :value="values[property.bk_property_id]"
                      :disabled="checkDisabled(property)"
                      :readonly="property.isreadonly"
                      @input="handleInput(property.bk_property_id, $event)"
                      @change="handleInput(property.bk_property_id, $event)">
                    </component>
                  </slot>
                  <span v-if="errorMessages[property.bk_property_id]" class="form-error">
                    {{ errorMessages[property.bk_property_id] }}
                  </span>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </template>
    </div>

    <div class="form-options" v-if="showOptions">
      <slot name="form-options">
        <bk-button theme="primary" :loading="submitting" @click="handleSave">
          {{ submitText }}
        </bk-button>
        <bk-button @click="handleCancel">取消</bk-button>
      </slot>
    </div>
  </div>
</template>

<script>
// 不能更新修改的字段(在可能发生编辑操作的页面里不显示出来)
// 与原项目保持一致: /workspace/bk-cmdb/src/ui/src/dictionary/model-constants.js
const BUILTIN_UNEDITABLE_FIELDS = ['bk_updated_by', 'bk_updated_at', 'bk_created_by', 'bk_created_at']

const UNEDITABLE_ASSOCIATION_TYPES = ['singleasst', 'multiasst', 'foreignkey']

export default {
  name: 'cmdb-form',
  props: {
    properties: {
      type: Array,
      default: () => []
    },
    values: {
      type: Object,
      default: () => ({})
    },
    type: {
      type: String,
      default: 'create',
      validator: val => ['create', 'update'].includes(val)
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
    isMobile: {
      type: Boolean,
      default: false
    },
    uneditableProperties: {
      type: Array,
      default: () => []
    },
    disabledProperties: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      groupState: {},
      errorMessages: {}
    }
  },
  computed: {
    groupedPropertiesList() {
      const groups = {}
      this.properties.forEach(property => {
        const groupId = property.bk_property_group || 'default'
        if (!groups[groupId]) {
          groups[groupId] = {
            bk_group_id: groupId,
            bk_group_name: property.bk_property_group_name || property.bk_group_name || '基本信息',
            properties: []
          }
        }
        groups[groupId].properties.push(property)
      })
      return Object.values(groups).map(group => ({
        ...group,
        properties: this.filterGroupProperties(group.properties)
      }))
    }
  },
  created() {
    this.initGroupState()
  },
  methods: {
    initGroupState() {
      this.groupedPropertiesList.forEach(group => {
        this.$set(this.groupState, group.bk_group_id, false)
      })
    },
    toggleGroup(groupId) {
      this.groupState[groupId] = !this.groupState[groupId]
    },
    hasEditableProperties(properties) {
      return properties.some(p => this.checkEditable(p))
    },
    filterGroupProperties(properties) {
      return properties.filter(property => {
        const isAsst = UNEDITABLE_ASSOCIATION_TYPES.includes(property.bk_property_type)
        const isBuiltinUneditable = BUILTIN_UNEDITABLE_FIELDS.includes(property.bk_property_id)
        const isHidden = property.bk_ishidden
        const isSystem = property.bk_issystem
        return !isAsst && !isBuiltinUneditable && !isHidden && !isSystem
      })
    },
    checkEditable(property) {
      if (this.type === 'create') {
        return !property.bk_isapi
      }
      return property.editable && !property.bk_isapi && !this.uneditableProperties.includes(property.bk_property_id)
    },
    checkDisabled(property) {
      if (this.type === 'create') {
        return false
      }
      return !property.editable || property.isreadonly || this.disabledProperties.includes(property.bk_property_id)
    },
    isFullWidth(property) {
      return ['innerTable', 'table', 'text', 'longchar'].includes(property.bk_property_type)
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
        'date': 'cmdb-form-date',
        'time': 'cmdb-form-time',
        'datetime': 'cmdb-form-datetime',
        'timezone': 'cmdb-form-timezone',
        'list': 'cmdb-form-list',
        'organization': 'cmdb-form-organization',
        'user': 'cmdb-form-user'
      }
      return componentMap[type] || 'cmdb-form-singlechar'
    },
    handleInput(propertyId, value) {
      const newValues = { ...this.values, [propertyId]: value }
      this.$emit('update:values', newValues)
      this.$emit('input', propertyId, value)
      this.validateProperty(propertyId, value)
    },
    validateProperty(propertyId, value) {
      const property = this.properties.find(p => p.bk_property_id === propertyId)
      if (!property) return true

      const errors = []
      if (property.isrequired && (value === undefined || value === null || value === '')) {
        errors.push(`${property.bk_property_name}不能为空`)
      }

      if (property.option && property.option.regex) {
        try {
          const regex = new RegExp(property.option.regex)
          if (value && !regex.test(value)) {
            errors.push(property.option.regex_message || '格式不正确')
          }
        } catch (e) {}
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
      
      const visibleProperties = []
      this.groupedPropertiesList.forEach(group => {
        const hasEditableProps = this.hasEditableProperties(group.properties)
        if (hasEditableProps) {
          group.properties.forEach(property => {
            if (this.checkEditable(property)) {
              visibleProperties.push(property)
            }
          })
        }
      })
      
      visibleProperties.forEach(property => {
        const value = this.values[property.bk_property_id]
        if (!this.validateProperty(property.bk_property_id, value)) {
          isValid = false
          errors[property.bk_property_id] = this.errorMessages[property.bk_property_id]
        }
      })
      this.errorMessages = errors
      return isValid
    },
    handleSave() {
      if (this.validateAll()) {
        this.$emit('submit', { ...this.values })
      }
    },
    handleCancel() {
      this.$emit('cancel')
    }
  }
}
</script>

<style lang="scss" scoped>
.cmdb-form-layout {
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
    &.full-width,
    &.innertable {
      flex: 1 1 100%;
      width: 100%;
      max-width: 100%;
    }
    .property-name {
      display: flex;
      align-items: center;
      margin: 2px 0 6px;
      .property-name-text {
        font-size: 14px;
        color: #63656e;
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
  .form-options {
    display: flex;
    gap: 10px;
    padding: 20px 24px;
    border-top: 1px solid #e6e6e6;
    background: #fafbfc;
    .button-save {
      min-width: 76px;
    }
    .button-cancel {
      min-width: 76px;
    }
  }
}

@media screen and (max-width: 1199px) {
  .cmdb-form-layout {
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

@media screen and (max-width: 768px) {
  .cmdb-form-layout {
    .form-groups {
      padding: 0 16px;
    }
    .property-group {
      border-bottom: none;
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
    .group-content {
      padding: 10px 0;
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
      .property-name {
        margin: 0 0 4px 0;
        .property-name-text {
          font-size: 13px;
        }
      }
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

@media screen and (max-width: 480px) {
  .cmdb-form-layout {
    .form-groups {
      padding: 0 12px;
    }
    .property-group {
      &:first-child {
        padding: 12px 0 8px 0;
      }
    }
    .group-header {
      padding: 8px 12px;
      .icon-angle-down {
        font-size: 10px;
      }
      .group-name {
        font-size: 12px;
      }
    }
    .property-item {
      margin: 6px 0;
      .property-name {
        margin: 0 0 2px 0;
        .property-name-text {
          font-size: 12px;
        }
      }
      .form-error {
        font-size: 11px;
      }
    }
    .form-options {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      padding: 12px;
      margin: 0;
      border-radius: 0;
      box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
      .bk-button {
        height: 36px;
        line-height: 36px;
        font-size: 14px;
      }
    }
  }
}
</style>
