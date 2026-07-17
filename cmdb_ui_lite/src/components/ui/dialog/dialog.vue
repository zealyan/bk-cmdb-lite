<!--
 * 从原项目 bk-cmdb 移植：src/ui/src/components/ui/dialog/dialog.vue
 * 用途：转移到业务模块弹框使用，保持与原项目一致的视口定位实现。
 *
 * lite 适配说明（仅移除 lite 缺失的依赖，定位/样式逻辑与原项目完全一致）：
 * - 去掉 import { addResizeListener, removeResizeListener } from '@/utils/resize-events.js'
 *   （lite 无该 util；本弹框 :height="600" 为数字，autoResize=false，
 *    该 resize 监听本就用不到）。对应移除 mounted/beforeDestroy/resizeHandler。
 * - window.__bk_zIndex_manager 在 lite 不存在，改为常量 2000 兜底。
 * - v-transfer-dom 指令在 main.js 中重新注册（挂到 body，与原项目行为一致，
 *   并避免祖先 transform 破坏 fixed 定位）。
 * - 新增 title prop：lite 的 host-list.vue 通过 :title 传标题，原项目用 header slot，
 *   这里直接支持 prop 以简化调用（不影响原 slot 用法）。
-->

<template>
  <div class="dialog-wrapper"
    v-transfer-dom
    v-show="showWrapper"
    :style="{
      zIndex
    }">
    <div ref="resizeTrigger">
      <transition name="dialog-fade">
        <div class="dialog-body" ref="body"
          v-if="showBody"
          :class="{ 'is-scrollable': bodyScroll }"
          :style="bodyStyle">
          <div class="dialog-header" v-if="showHeader" ref="header">
            <span class="dialog-title" v-if="title">{{ title }}</span>
            <slot name="header"></slot>
          </div>
          <div class="dialog-content">
            <slot></slot>
          </div>
          <div class="dialog-footer" v-if="showFooter" ref="footer">
            <slot name="footer"></slot>
          </div>
          <i class="bk-icon icon-close" v-if="showCloseIcon" @click="handleCloseDialog"></i>
        </div>
      </transition>
    </div>
  </div>
</template>

<script>
  export default {
    name: 'cmdb-dialog',
    props: {
      value: Boolean,
      showHeader: {
        type: Boolean,
        default: true
      },
      showFooter: {
        type: Boolean,
        default: true
      },
      showCloseIcon: {
        type: Boolean,
        default: true
      },
      title: {
        type: String,
        default: ''
      },
      width: {
        type: Number,
        default: 720
      },
      height: Number,
      minHeight: Number,
      bodyScroll: {
        type: Boolean,
        default: true
      }
    },
    data() {
      return {
        timer: null,
        bodyHeight: 0,
        showWrapper: false,
        showBody: false,
        zIndex: 2000
      }
    },
    computed: {
      autoResize() {
        return typeof this.height !== 'number'
      },
      bodyStyle() {
        const style = {
          width: `${this.width}px`,
          '--height': `${this.autoResize ? this.bodyHeight : this.height}px`
        }
        if (!this.autoResize) {
          style.height = `${this.height}px`
          style.maxHeight = 'initial'
        }
        if (this.minHeight) {
          style.minHeight = `${this.minHeight}px`
        }
        return style
      }
    },
    watch: {
      value: {
        immediate: true,
        handler(value) {
          if (value) {
            this.showWrapper = true
            // 原项目用 window.__bk_zIndex_manager.nextZIndex()，lite 无该管理器，常量兜底
            this.zIndex = (window.__bk_zIndex_manager && window.__bk_zIndex_manager.nextZIndex()) || 2000
            this.$nextTick(() => {
              this.showBody = true
            })
          } else {
            this.showBody = false
            this.timer && clearTimeout(this.timer)
            this.timer = setTimeout(() => {
              this.showWrapper = false
            }, 300)
          }
        }
      }
    },
    methods: {
      handleCloseDialog() {
        this.$emit('close')
        this.$emit('input', false)
      }
    }
  }
</script>

<style lang="scss" scoped>
    .dialog-wrapper {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        left: 0;
        background-color: rgba(0, 0, 0, .6);
        z-index: 2000;
        @include scrollbar;
        .dialog-body {
            position: relative;
            margin: 0 auto;
            margin-top: calc((100vh - var(--height)) / 3);
            max-height: calc(100vh - 225px);
            min-height: 100px;
            border-radius: 2px;
            background-color: #fff;
            box-shadow: 0px 4px 12px 0px rgba(0, 0, 0, 0.2);
            overflow: hidden;
            &.is-scrollable {
                @include scrollbar;
            }
            .dialog-header {
                padding: 0 20px;
                height: 50px;
                line-height: 50px;
                font-size: 16px;
                color: #313238;
                border-bottom: 1px solid #dcdee5;
                @include scrollbar;
                .dialog-title {
                    font-weight: normal;
                }
            }
            .icon-close {
                position: absolute;
                top: 6px;
                right: 6px;
                width: 32px;
                height: 32px;
                line-height: 32px;
                font-size: 22px;
                font-weight: 700;
                text-align: center;
                color: #D8D8D8;
                cursor: pointer;
                &:hover {
                    color: #979BA5;
                }
            }
        }
    }
</style>

<style lang="scss">
    .dialog-fade-enter-active,
    .dialog-fade-leave-active {
        transition: opacity .3s ease;
    }
    .dialog-fade-enter,
    .dialog-fade-leave-to {
      opacity: 0;
    }
</style>
