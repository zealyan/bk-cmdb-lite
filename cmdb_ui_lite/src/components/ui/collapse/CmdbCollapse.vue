<template>
  <div class="cmdb-collapse">
    <div class="collapse-header" @click="handleToggle">
      <i class="bk-icon icon-down-shape collapse-icon" :class="{ collapsed: isCollapsed }"></i>
      <span class="collapse-label">{{ label }}</span>
    </div>
    <div class="collapse-content" v-show="!isCollapsed">
      <slot></slot>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CmdbCollapse',
  props: {
    label: {
      type: String,
      default: ''
    },
    collapse: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      isCollapsed: this.collapse
    }
  },
  methods: {
    handleToggle() {
      this.isCollapsed = !this.isCollapsed
      this.$emit('update:collapse', this.isCollapsed)
    }
  }
}
</script>

<style lang="scss" scoped>
.cmdb-collapse {
  .collapse-header {
    display: flex;
    align-items: center;
    cursor: pointer;
    padding: 7px 0;
    
    &:first-child {
      padding: 28px 0 10px 0;
    }

    .collapse-icon {
      font-size: 12px;
      font-weight: bold;
      color: #333948;
      transition: transform 0.2s ease-in-out;
      margin-right: 6px;
      
      &.collapsed {
        transform: rotate(-90deg);
      }
    }

    .collapse-label {
      font-size: 16px;
      line-height: 16px;
      color: #333948;
      font-weight: 500;
    }
  }

  .collapse-content {
    padding-top: 4px;
  }
}
</style>
