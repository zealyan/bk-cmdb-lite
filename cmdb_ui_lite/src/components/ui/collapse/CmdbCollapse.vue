<template>
  <div :class="['collapse-layout', size]">
    <div class="collapse-trigger" @click="toggle">
      <span :class="['collapse-arrow', 'bk-icon', arrowIconClass, { 'is-collapsed': hidden }]"></span>
      <span class="collapse-text" :title="label">
        <slot name="title">{{ label }}</slot>
      </span>
    </div>
    <transition
      @before-enter="collapseTransition.beforeEnter"
      @enter="collapseTransition.enter"
      @after-enter="collapseTransition.afterEnter"
      @before-leave="collapseTransition.beforeLeave"
      @leave="collapseTransition.leave"
      @after-leave="collapseTransition.afterLeave">
      <div class="collapse-content" v-show="!hidden">
        <slot></slot>
      </div>
    </transition>
  </div>
</template>

<script>
// 与上游 bk-cmdb `components/ui/transition/collapse.js` 中的 JS 钩子逻辑一致，
// 配合 common.scss 的 .collapse-transition 实现高度过渡动画。
const collapseTransition = {
  beforeEnter(el) {
    el.classList.add('collapse-transition')
    if (!el.dataset) {
      el.dataset = {}
    }
    el.dataset.oldPaddingTop = el.style.paddingTop
    el.dataset.oldPaddingBottom = el.style.paddingBottom
    el.style.height = '0'
    el.style.paddingTop = 0
    el.style.paddingBottom = 0
  },
  enter(el) {
    el.dataset.oldOverflow = el.style.overflow
    el.style.overflow = 'hidden'
    if (el.scrollHeight !== 0) {
      el.style.height = `${el.scrollHeight}px`
      el.style.paddingTop = el.dataset.oldPaddingTop
      el.style.paddingBottom = el.dataset.oldPaddingBottom
    } else {
      el.style.height = ''
      el.style.paddingTop = el.dataset.oldPaddingTop
      el.style.paddingBottom = el.dataset.oldPaddingBottom
    }
  },
  afterEnter(el) {
    el.classList.remove('collapse-transition')
    el.style.height = ''
    el.style.overflow = el.dataset.oldOverflow
  },
  beforeLeave(el) {
    if (!el.dataset) el.dataset = {}
    el.dataset.oldPaddingTop = el.style.paddingTop
    el.dataset.oldPaddingBottom = el.style.paddingBottom
    el.dataset.oldOverflow = el.style.overflow
    el.style.height = `${el.scrollHeight}px`
    el.style.overflow = 'hidden'
  },
  leave(el) {
    if (el.scrollHeight !== 0) {
      el.classList.add('collapse-transition')
      el.style.height = 0
      el.style.paddingTop = 0
      el.style.paddingBottom = 0
    }
  },
  afterLeave(el) {
    el.classList.remove('collapse-transition')
    el.style.height = ''
    el.style.overflow = el.dataset.oldOverflow
    el.style.paddingTop = el.dataset.oldPaddingTop
    el.style.paddingBottom = el.dataset.oldPaddingBottom
  }
}

export default {
  name: 'CmdbCollapse',
  props: {
    collapse: Boolean,
    label: {
      type: String
    },
    arrowType: {
      type: String,
      default: 'outlined' // filled
    },
    size: {
      type: String
    },
    autoExpand: { // 是否可以自动展开
      type: Boolean,
      default: false
    },
    list: {
      type: [Object, Array],
      default: () => {}
    }
  },
  data() {
    return {
      hidden: this.collapse,
      collapseTransition
    }
  },
  computed: {
    arrowIconClass() {
      const classMap = {
        outlined: 'icon-angle-down',
        filled: 'icon-down-shape'
      }
      return `${classMap[this.arrowType]} ${this.arrowType}`
    }
  },
  watch: {
    list(val, lastVal) {
      if (JSON.stringify(val) !== JSON.stringify(lastVal) && this.hidden && this.autoExpand) {
        this.toggle()
      }
    },
    collapse(collapse) {
      this.hidden = collapse
    },
    hidden(hidden) {
      this.$emit('update:collapse', hidden)
      this.$emit('collapse-change', hidden)
    }
  },
  methods: {
    toggle() {
      this.hidden = !this.hidden
    }
  }
}
</script>

<style lang="scss" scoped>
.collapse-layout {
  .collapse-trigger {
    display: flex;
    color: #333948;
    font-weight: bold;
    align-items: center;
    cursor: pointer;

    .collapse-arrow {
      font-size: 20px;
      font-weight: 700;
      margin: 0 2px 0 -4px;
      transition: transform .2s ease-in-out;

      &.is-collapsed {
        transform: rotate(-90deg);
      }

      &.filled {
        font-size: 12px;
        color: #63656E;
        margin: 0 4px 0 0;
      }
    }

    .collapse-text {
      flex: 1;
      font-size: 14px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }

  &.small {
    .collapse-arrow {
      &.filled {
        margin-top: -1px;
      }
    }

    .collapse-text {
      font-size: 12px;
    }
  }

  .collapse-content {
    // 高度与内边距过渡依赖全局 .collapse-transition；
    // 分组内部间距由 property-list 控制，此处不加额外 padding。
  }
}
</style>
