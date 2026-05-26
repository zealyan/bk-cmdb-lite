<template>
  <div class="editable-property">
    <!-- 详情态 -->
    <div v-if="!isEditing" class="property-display">
      <span class="property-value">{{ displayValue }}</span>
      <i v-if="isEditable" class="icon-cc-edit property-edit-icon" @click.stop="startEdit"></i>
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
      copyTipsText: '复制成功'
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
        const { bk_property_type } = this.property
        if (bk_property_type === 'bool') {
          return value ? '是' : '否'
        }
        return String(value)
      }
      
      if (typeof value === 'boolean') {
        const { bk_property_type } = this.property
        if (bk_property_type === 'bool') {
          return value ? '是' : '否'
        }
        return value ? '是' : '否'
      }
      
      try {
        return String(value)
      } catch {
        return '-'
      }
    }
  },
  methods: {
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
      const changed = this.editValue !== this.value
      this.$emit('confirm', {
        property: this.property,
        value: this.editValue,
        changed
      })
      this.$emit('end-edit')
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
.editable-property {
  display: flex;
  align-items: center;
  width: 100%;

  .property-display {
    display: flex;
    align-items: center;
    gap: 4px;
    cursor: pointer;
    flex: 1;
    
    .property-value {
      color: #313238;
      font-size: 14px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      flex: 1;
    }
    
    .property-edit-icon {
      visibility: hidden;
      cursor: pointer;
      font-size: 16px;
      color: #3c96ff;
      transition: color 0.2s;
      
      &:hover {
        color: #3a84ff;
      }
    }
    
    &:hover .property-edit-icon {
      visibility: visible;
    }
    
    .property-copy {
      margin: 2px 0 0 2px;
      color: #3c96ff;
      cursor: pointer;
      display: none;
      font-size: 16px;
    }
    
    &:hover .property-copy {
      display: inline-block;
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
        text-align: center;
        background: rgba(0, 0, 0, 0.7);
        border-radius: 4px;
        font-size: 12px;
        color: #fff;
        white-space: nowrap;
        padding: 0 8px;
      }
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
