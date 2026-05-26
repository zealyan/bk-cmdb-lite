<template>
  <div class="cmdb-details" ref="detailsWrapper">
    <slot name="details-header"></slot>
    <template v-for="(group, groupIndex) in sortedGroups">
      <div class="property-group" :key="groupIndex" v-if="groupedProperties[groupIndex]?.length">
        <cmdb-collapse
          :label="group['bk_group_name']"
          :collapse.sync="groupState[group['bk_group_id']]">
          <ul class="property-list clearfix">
            <template v-for="property in groupedProperties[groupIndex]">
              <li :class="['property-item fl', property.bk_property_type, {
                    flex: flexProperties.includes(property['bk_property_id'])
                  }]"
                v-if="!invisibleProperties.includes(property['bk_property_id'])"
                :key="`${property['bk_obj_id']}-${property['bk_property_id']}`">
                <span class="property-name"
                  v-if="!invisibleNameProperties.includes(property['bk_property_id'])"
                  :title="property['bk_property_name']">{{property['bk_property_name']}}
                </span>
                <slot :name="property['bk_property_id']">
                  <cmdb-property-value
                    :is-show-overflow-tips="isShowOverflowTips(property)"
                    :class="'property-value'"
                    :ref="`property-value-${property.id}`"
                    :value="inst[property.bk_property_id]"
                    :instance="inst"
                    :property="property">
                  </cmdb-property-value>
                </slot>
                <template v-if="showCopy
                  && !isEmptyPropertyValue(inst[property.bk_property_id])
                  && property.bk_property_type !== 'innertable'">
                  <div class="copy-box">
                    <i class="property-copy icon-cc-details-copy" @click="handleCopy(property.id)"></i>
                    <transition name="fade">
                      <span class="copy-tips" v-if="showCopyTips === property.id">
                        复制成功
                      </span>
                    </transition>
                  </div>
                </template>
              </li>
            </template>
          </ul>
        </cmdb-collapse>
      </div>
    </template>
    <div class="details-options" v-if="showOptions">
      <slot name="details-options">
        <bk-button v-if="showEdit"
          class="button-edit"
          theme="primary"
          @click="handleEdit">
          {{editText}}
        </bk-button>
        <bk-button v-if="showDelete"
          hover-theme="danger"
          class="button-delete"
          @click="handleDelete">
          {{deleteText}}
        </bk-button>
      </slot>
    </div>
  </div>
</template>

<script>
import CmdbCollapse from '../collapse/CmdbCollapse.vue'
import CmdbPropertyValue from '../../property/CmdbPropertyValue.vue'

export default {
  name: 'CmdbDetails',
  components: {
    CmdbCollapse,
    CmdbPropertyValue
  },
  props: {
    inst: {
      type: Object,
      required: true
    },
    properties: {
      type: Array,
      default: () => []
    },
    propertyGroups: {
      type: Array,
      default: () => []
    },
    invisibleProperties: {
      type: Array,
      default: () => []
    },
    showOptions: {
      type: Boolean,
      default: true
    },
    showEdit: {
      type: Boolean,
      default: true
    },
    showDelete: {
      type: Boolean,
      default: true
    },
    showCopy: {
      type: Boolean,
      default: false
    },
    editButtonText: {
      type: String,
      default: '编辑'
    },
    deleteButtonText: {
      type: String,
      default: '删除'
    },
    flexProperties: {
      type: Array,
      default: () => []
    },
    invisibleNameProperties: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      groupState: {}
    }
  },
  computed: {
    editText() {
      return this.editButtonText || '编辑'
    },
    deleteText() {
      return this.deleteButtonText || '删除'
    },
    groupedProperties() {
      const groups = {}
      const result = []

      this.propertyGroups.forEach(group => {
        groups[group.bk_group_id] = []
      })

      if (Object.keys(groups).length === 0) {
        groups['default'] = []
      }

      this.properties.forEach(property => {
        const groupId = property.bk_property_group_id || 'default'
        if (!groups[groupId]) {
          groups[groupId] = []
        }
        groups[groupId].push(property)
      })

      Object.keys(groups).forEach(groupId => {
        result.push(groups[groupId])
      })

      return result
    },
    sortedGroups() {
      if (this.propertyGroups.length > 0) {
        return this.propertyGroups
      }
      return [{ bk_group_id: 'default', bk_group_name: '基本信息' }]
    }
  },
  created() {
    this.initGroupState()
  },
  methods: {
    initGroupState() {
      this.propertyGroups.forEach(group => {
        this.$set(this.groupState, group.bk_group_id, false)
      })
      this.$set(this.groupState, 'default', false)
    },
    isShowOverflowTips(property) {
      const complexTypes = ['map']
      return !complexTypes.includes(property.bk_property_type)
    },
    isEmptyPropertyValue(value) {
      if (value === null || value === undefined || value === '') {
        return true
      }
      if (Array.isArray(value) && value.length === 0) {
        return true
      }
      if (typeof value === 'object' && Object.keys(value).length === 0) {
        return true
      }
      return false
    },
    handleEdit() {
      this.$emit('on-edit', this.inst)
    },
    handleDelete() {
      this.$emit('on-delete', this.inst)
    },
    handleCopy(propertyId) {
      const components = this.$refs[`property-value-${propertyId}`]
      const component = components ? components[0] : null
      let copyText = ''
      
      if (component && component.getCopyValue) {
        copyText = component.getCopyValue()
      } else {
        const property = this.properties.find(p => p.id === propertyId)
        if (property) {
          const value = this.inst[property.bk_property_id]
          copyText = value !== null && value !== undefined ? String(value) : ''
        }
      }

      const textArea = document.createElement('textarea')
      textArea.value = copyText
      textArea.style.position = 'fixed'
      textArea.style.left = '-9999px'
      document.body.appendChild(textArea)
      textArea.select()
      
      try {
        document.execCommand('copy')
        this.showCopyTips = propertyId
        const timer = setTimeout(() => {
          this.showCopyTips = false
          clearTimeout(timer)
        }, 2000)
      } catch (e) {
        console.error('复制失败:', e)
      }
      
      document.body.removeChild(textArea)
    }
  }
}
</script>

<style lang="scss" scoped>
.cmdb-details {
  height: 100%;
  padding: 0 24px;
  overflow-y: auto;
  box-sizing: border-box;
}

.property-group {
  padding: 7px 0 10px 0;

  &:first-child {
    padding: 28px 0 10px 0;
  }
}

.property-list {
  padding: 4px 0;
  margin: 0;

  .property-item {
    list-style: none;
    width: 50%;
    max-width: 400px;
    margin: 12px 0 0;
    font-size: 14px;
    line-height: 26px;
    display: flex;
    float: left;
    box-sizing: border-box;

    &:hover {
      .property-copy {
        display: inline-block;
      }
    }

    .property-name {
      position: relative;
      flex: none;
      width: 140px;
      padding: 0 16px 0 0;
      color: #63656e;
      text-align: right;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;

      &:after {
        content: ":";
        position: absolute;
        right: 10px;
      }
    }

    .property-value {
      max-width: calc(100% - 140px - 24px);
      padding: 0 15px 0 0;
      color: #313238;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .property-copy {
      margin: 2px 0 0 2px;
      color: #3c96ff;
      cursor: pointer;
      display: none;
      font-size: 16px;
    }

    .copy-box {
      position: relative;
      font-size: 0;

      .copy-tips {
        position: absolute;
        top: -22px;
        left: -18px;
        min-width: 70px;
        height: 26px;
        line-height: 26px;
        font-size: 12px;
        color: #ffffff;
        text-align: center;
        background-color: #9f9f9f;
        border-radius: 2px;
      }

      .fade-enter-active,
      .fade-leave-active {
        transition: all 0.5s;
      }

      .fade-enter {
        top: -14px;
        opacity: 0;
      }

      .fade-leave-to {
        top: -28px;
        opacity: 0;
      }
    }

    &.flex,
    &.innertable {
      display: flex;
      width: 100%;
      max-width: unset;
      padding-right: 15px;

      .property-value {
        width: calc(100% - 140px);
        max-width: 1200px;
      }
    }
  }
}

.details-options {
  padding: 10px 18px;

  .button-edit {
    min-width: 76px;
    margin-right: 4px;
  }

  .button-delete {
    min-width: 76px;
  }
}

.clearfix::after {
  content: "";
  display: table;
  clear: both;
}

.fl {
  float: left;
}

/* 移动端竖屏样式 */
@media (max-width: 767px) {
  .cmdb-details {
    padding: 0 16px;
    padding-bottom: 80px;
  }

  .property-group {
    padding: 7px 0 10px 0;

    &:first-child {
      padding: 28px 0 10px 0;
    }
  }

  .property-list {
    .property-item {
      width: 100%;
      max-width: unset;
      margin: 12px 0 0;
      padding: 14px 0;
      min-height: 60px;
      box-sizing: border-box;
      float: none;

      &:active {
        background-color: #f5f7fa;
      }

      .property-name {
        width: 100px;
        padding: 0 12px 0 0;
        font-size: 12px;

        &:after {
          right: 6px;
        }
      }

      .property-value {
        max-width: calc(100% - 100px);
        padding: 0 10px 0 0;
        font-size: 14px;
      }
    }
  }
}
</style>
