<template>
  <div :class="['editable-property', { 'action-active': isEditing }]">
    <!-- 详情态：属性值 -->
    <div v-if="!isEditing" class="property-value" v-bk-overflow-tips="overflowTips">{{ displayValue }}</div>

    <!-- 非编辑态：操作图标（编辑 + 复制） -->
    <div class="property-actions" v-show="!isEditing">
      <i
        v-if="isEditable"
        class="property-edit-button icon-cc-edit"
        @click.stop="startEdit">
      </i>
      <div v-if="showCopy" class="copy-box">
        <i class="property-copy icon-cc-details-copy" @click.stop="handleCopy"></i>
        <transition name="fade">
          <span class="copy-tips" v-if="showCopyTips">{{ copyTipsText }}</span>
        </transition>
      </div>
    </div>

    <!-- 编辑态 -->
    <div v-if="isEditing" class="property-edit">
      <div class="edit-form">
        <property-form-element
          ref="propertyFormRef"
          :property="property"
          :value="editValue"
          @input="handleInput"
          @keydown.enter.native="confirmEdit"
          @keydown.esc.native="cancelEdit"
        />
      </div>
      <div class="edit-actions">
        <i class="bk-icon icon-check-line confirm-btn" @click="confirmEdit" title="确认"></i>
        <i class="bk-icon icon-close-line cancel-btn" @click="cancelEdit" title="取消"></i>
      </div>
    </div>
  </div>
</template>

<script>
import PropertyFormElement from './property-form-element.vue'

export default {
  name: 'EditableProperty',
  components: {
    PropertyFormElement
  },
  props: {
    property: {
      type: Object,
      required: true
    },
    value: {
      type: [String, Number, Array, Boolean, Object],
      default: ''
    },
    editable: {
      type: Boolean,
      default: true
    },
    editingPropertyId: {
      type: String,
      default: null
    }
  },
  data() {
    return {
      editValue: '',
      showCopyTips: false,
      copyTipsText: '复制成功',
      // tooltip 边界钳制在浏览器“可见视口”内（而非整篇文档），
      // 避免属性位于长页面底部 / 滚动后 tooltip 被视口边缘裁切。
      // 指令默认 boundary 为 'window'（Popper 里 = 整篇文档高度），此处覆盖为 'viewport'。
      overflowTips: {
        boundary: 'viewport',
        maxWidth: 480
      }
    }
  },
  computed: {
    isEditing() {
      return this.editingPropertyId === this.property.bk_property_id
    },
    isEditable() {
      return this.editable && !this.property.bk_isapi && this.property.editable !== false
    },
    showCopy() {
      const value = this.displayValue
      return value !== '-' && this.property.bk_property_type !== 'inner_table'
    },
    displayValue() {
      let value = this.value
      
      if (value === null || value === undefined || value === '') {
        return '-'
      }
      
      const { bk_property_type } = this.property
      
      // 处理布尔类型
      if (bk_property_type === 'bool') {
        if (typeof value === 'boolean') return value ? '是' : '否'
        if (typeof value === 'string') {
          const lowerValue = value.toLowerCase()
          if (lowerValue === 'true' || lowerValue === '1') return '是'
          if (lowerValue === 'false' || lowerValue === '0') return '否'
        }
        return value ? '是' : '否'
      }
      
      // 处理枚举类型（单选）
      if (bk_property_type === 'enum') {
        return this.formatEnumValue(value)
      }
      
      // 处理多选枚举类型
      if (bk_property_type === 'enummulti') {
        return this.formatEnumMultiValue(value)
      }
      
      // 处理对象类型
      if (typeof value === 'object' && !Array.isArray(value)) {
        if (value.id !== undefined) value = value.id
        else if (value.value !== undefined) value = value.value
        else if (value.name !== undefined) value = value.name
        else if (value.label !== undefined) value = value.label
        else {
          try {
            value = JSON.stringify(value)
          } catch {
            value = String(value)
          }
        }
      }
      
      if (typeof value === 'string' || typeof value === 'number') {
        return String(value)
      }
      
      if (Array.isArray(value)) {
        // 尝试解析多选枚举数组
        if (bk_property_type === 'enummulti') {
          return this.formatEnumMultiValue(value)
        }
        return value.join(', ')
      }
      
      try {
        return String(value)
      } catch {
        return '-'
      }
    }
  },
  methods: {
    // 格式化枚举值
    formatEnumValue(value) {
      const option = this.property?.option
      if (!option) {
        return String(value)
      }
      
      let parsedOption = option
      if (typeof option === 'string') {
        try {
          parsedOption = JSON.parse(option)
        } catch (e) {
          return String(value)
        }
      }
      
      // 新格式: [{id: "xxx", name: "显示名"}]
      if (Array.isArray(parsedOption)) {
        const optionItem = parsedOption.find(opt => opt.id === value || opt.id === String(value))
        return optionItem?.name || String(value)
      }
      
      // 旧格式: { "key1": "name1" }
      if (parsedOption && typeof parsedOption === 'object') {
        return parsedOption[value] || String(value)
      }
      
      return String(value)
    },
    
    // 格式化多选枚举值
    formatEnumMultiValue(value) {
      const option = this.property?.option
      if (!option) {
        return Array.isArray(value) ? value.join(', ') : String(value)
      }
      
      let parsedOption = option
      if (typeof option === 'string') {
        try {
          parsedOption = JSON.parse(option)
        } catch (e) {
          return Array.isArray(value) ? value.join(', ') : String(value)
        }
      }
      
      // 解析值为数组
      let values = value
      if (typeof value === 'string') {
        try {
          values = JSON.parse(value)
        } catch (e) {
          return String(value)
        }
      }
      
      if (!Array.isArray(values)) {
        return String(value)
      }
      
      // 新格式: [{id: "xxx", name: "显示名"}]
      if (Array.isArray(parsedOption)) {
        const names = values.map(v => {
          const optionItem = parsedOption.find(opt => opt.id === v || opt.id === String(v))
          return optionItem?.name
        }).filter(n => n)
        return names.join(', ') || values.join(', ')
      }
      
      // 旧格式: { "key1": "name1" }
      if (parsedOption && typeof parsedOption === 'object') {
        const names = values.map(v => parsedOption[v] || v).filter(n => n)
        return names.join(', ') || values.join(', ')
      }
      
      return values.join(', ')
    },
    
    startEdit() {
      if (!this.isEditable) return
      
      this.editValue = this.value === null || this.value === undefined ? '' : this.value
      this.$emit('start-edit', this.property.bk_property_id)
      
      this.$nextTick(() => {
        this.$refs.propertyFormRef?.focus?.()
      })
    },
    handleInput(value) {
      this.editValue = value
    },
    confirmEdit() {
      // 先进行校验
      const isValid = this.$refs.propertyFormRef?.validate?.()
      if (isValid === false) {
        return
      }
      
      const changed = this.editValue !== this.value
      this.$emit('confirm', {
        property: this.property,
        value: this.editValue,
        changed
      })
      // 不在这里关闭编辑态，由父组件根据保存结果决定
    },
    cancelEdit() {
      this.$emit('end-edit')
      this.editValue = ''
    },
    async handleCopy() {
      const copyText = this.displayValue
      if (!copyText || copyText === '-') return
      
      const success = await this.tryCopy(copyText)
      if (success) {
        this.showCopyTips = true
        setTimeout(() => {
          this.showCopyTips = false
        }, 2000)
      }
    },
    
    async tryCopy(text) {
      if (navigator.clipboard && window.isSecureContext) {
        try {
          await navigator.clipboard.writeText(text)
          return true
        } catch (err) {
          console.debug('Clipboard API failed, trying fallback')
        }
      }
      
      return this.fallbackCopy(text)
    },
    
    fallbackCopy(text) {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      textarea.style.top = '-9999px'
      document.body.appendChild(textarea)
      
      try {
        textarea.select()
        textarea.setSelectionRange(0, text.length)
        
        const success = document.execCommand('copy')
        if (!success) {
          throw new Error('execCommand copy failed')
        }
        return true
      } catch (err) {
        console.debug('Fallback copy failed, showing manual copy')
        this.showManualCopy(text)
        return false
      } finally {
        document.body.removeChild(textarea)
      }
    },
    
    showManualCopy(text) {
      const modal = document.createElement('div')
      modal.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: #fff;
        border: 1px solid #e7e9ef;
        border-radius: 8px;
        padding: 20px;
        z-index: 9999;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        max-width: 400px;
      `
      
      const title = document.createElement('div')
      title.style.cssText = 'font-weight: 600; margin-bottom: 12px; color: #313238;'
      title.textContent = '复制内容'
      modal.appendChild(title)
      
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.cssText = `
        width: 100%;
        min-height: 80px;
        padding: 10px;
        border: 1px solid #e7e9ef;
        border-radius: 4px;
        font-size: 14px;
        resize: none;
        margin-bottom: 12px;
      `
      modal.appendChild(textarea)
      
      const button = document.createElement('button')
      button.textContent = '关闭'
      button.style.cssText = `
        display: block;
        margin: 0 auto;
        padding: 6px 20px;
        background: #3c96ff;
        color: #fff;
        border: none;
        border-radius: 4px;
        cursor: pointer;
      `
      button.onclick = () => {
        document.body.removeChild(modal)
        document.body.removeChild(overlay)
      }
      modal.appendChild(button)
      
      const overlay = document.createElement('div')
      overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.5);
        z-index: 9998;
      `
      overlay.onclick = button.onclick
      
      document.body.appendChild(overlay)
      document.body.appendChild(modal)
      
      textarea.select()
      textarea.setSelectionRange(0, text.length)
    }
  }
}
</script>

<style lang="scss" scoped>
// 与原项目 editable-property.vue 保持一致：
// .property-value 与 .property-actions 作为 .editable-property 的 flex 子项平级排列，
// actions 用 visibility:hidden 占位，hover 时切换可见性，避免图标显隐导致布局位移。
.editable-property {
  display: flex;
  align-items: center;
  width: 100%;

  &:hover,
  &.action-active {
    .property-actions {
      visibility: visible;
    }
  }

  .property-value {
    color: #313238;
    font-size: 14px;
    // 与原项目 cmdb-property-value 的 value-default-theme 保持一致：
    // 最多展示 2 行，超出部分省略号（...），溢出时由 v-bk-overflow-tips 悬浮展示全文
    overflow: hidden;
    text-overflow: ellipsis;
    word-break: break-all;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .property-actions {
    display: flex;
    align-items: center;
    flex: none;
    // 固定 margin-left，使编辑图标与值文本保持恒定间距；
    // 复制图标在 .property-actions 内部再固定间距，保证无论复制图标是否存在，
    // 编辑图标位置都不会左右漂移。
    margin-left: 12px;
    visibility: hidden;
  }

  .property-edit-button {
    flex: none;
    cursor: pointer;
    font-size: 16px;
    color: #3c96ff;

    &:hover {
      color: #3a84ff;
    }
  }

  .copy-box {
    position: relative;
    font-size: 0;
    flex: none;

    .property-copy {
      margin: 0 0 0 8px;
      color: #3c96ff;
      cursor: pointer;
      font-size: 16px;

      &:hover {
        color: #3a84ff;
      }
    }

    .copy-tips {
      position: absolute;
      top: -22px;
      left: -18px;
      min-width: 70px;
      height: 26px;
      line-height: 26px;
      text-align: center;
      background: rgba(0, 0, 0, 0.7);
      border-radius: 4px;
      font-size: 12px;
      color: #fff;
      white-space: nowrap;
      padding: 0 8px;
    }
  }

  .property-edit {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    width: 100%;

    .edit-form {
      flex: 1;
    }

    .edit-actions {
      display: flex;
      gap: 4px;
      padding-top: 2px;

      .confirm-btn,
      .cancel-btn {
        cursor: pointer;
        font-size: 16px;
        padding: 4px;
        border-radius: 2px;
        transition: all 0.2s;
      }

      .confirm-btn {
        color: #2dcb56;
        &:hover {
          background-color: rgba(45, 203, 86, 0.1);
        }
      }

      .cancel-btn {
        color: #979BA5;
        &:hover {
          background-color: rgba(151, 155, 165, 0.1);
        }
      }
    }
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
