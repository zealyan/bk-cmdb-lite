<!--
 * 转移至模块选择器（含 tab：空闲模块 / 业务模块）
 * 原项目: src/ui/src/views/business-topology/host/module-selector-with-tab.vue
 *
 * lite 适配说明：
 * - 去掉原项目的权限校验（cmdb-auth / no-permission / translateAuth / $OPERATION）
 *   与跨业务转移（acrossBusiness）tab，聚焦"空闲模块"与"业务模块"两个核心场景。
 * - 跨业务转移依赖独立业务的拓扑数据，留待后续阶段实现。
-->

<template>
  <div class="module-selector-with-tab">
    <bk-tab :active.sync="tab.active" type="border-card">
      <bk-tab-panel
        v-for="(panel, index) in availableTabList"
        v-bind="panel.props"
        render-directive="if"
        :key="index">
        <div class="tab-content">
          <div class="content-container" v-bkloading="{ isLoading: loading }">
            <component
              class="selector-component"
              :is="panel.component.name"
              v-bind="panel.component.props"
              @cancel="handleCancel"
              @confirm="handleConfirm">
            </component>
          </div>
        </div>
      </bk-tab-panel>
    </bk-tab>
  </div>
</template>

<script>
  import ModuleSelector from './module-selector.vue'

  export default {
    name: 'module-selector-with-tab',
    components: {
      [ModuleSelector.name]: ModuleSelector
    },
    props: {
      modules: {
        type: Array,
        default() {
          return []
        }
      },
      business: {
        type: Object,
        default() {
          return {}
        }
      },
      confirmLoading: {
        type: Boolean,
        default: false
      },
      active: {
        type: String,
        default: 'idle'
      }
    },
    data() {
      return {
        loading: false,
        tab: {
          list: [
            {
              props: {
                name: 'idle',
                label: '转移到空闲模块',
                visible: true
              },
              component: {
                name: ModuleSelector.name,
                props: {
                  moduleType: 'idle',
                  business: {},
                  confirmText: '',
                  confirmLoading: false
                }
              }
            },
            {
              props: {
                name: 'business',
                label: '转移到业务模块',
                visible: true
              },
              component: {
                name: ModuleSelector.name,
                props: {
                  moduleType: 'business',
                  business: {},
                  confirmLoading: false
                }
              }
            }
          ],
          active: this.active
        }
      }
    },
    computed: {
      bizId() {
        return this.business.bk_biz_id
      },
      isIdleSetModules() {
        return this.modules.every(module => module.default >= 1)
      },
      availableTabList() {
        const availableTabList = []
        this.tab.list.forEach((tab) => {
          tab.component.props.business = this.business
          const defaultChecked = this.modules.map(module => module.bk_module_id)
          const firstSelectionModules = this.modules.map(module => module.bk_module_id).sort()
          tab.component.props.previousModules = firstSelectionModules
          tab.component.props.defaultChecked = defaultChecked
          tab.component.props.confirmText = tab.props.name === 'idle' && this.isIdleSetModules ? '确定' : ''
          availableTabList.push(tab)
        })
        return availableTabList
      },
      activeTab() {
        return this.availableTabList.find(tab => tab.props.name === this.tab.active)
      }
    },
    watch: {
      confirmLoading(value) {
        this.activeTab.component.props.confirmLoading = value
      }
    },
    methods: {
      handleCancel() {
        this.$emit('cancel')
      },
      handleConfirm() {
        const currentTab = this.activeTab
        const tab = { tabName: currentTab.props.name, moduleType: currentTab.component.props.moduleType }
        // eslint-disable-next-line prefer-rest-params
        this.$emit('confirm', tab, ...arguments)
      }
    }
  }
</script>

<style lang="scss" scoped>
    .module-selector-with-tab {
        height: var(--height);

        .tab-content,
        .selector-component,
        .content-container {
            height: 100%;
        }

        ::v-deep .bk-tab {
            height: 100%;
            .bk-tab-header {
                padding: 0;
                height: 43px;
                background-image: linear-gradient(transparent 41px,#dcdee5 0);
                .bk-tab-label-list {
                    height: 42px;
                    .bk-tab-label-item {
                        line-height: 42px;
                        min-width: auto;
                        &.active {
                            color: #313238;
                            background-color: #fff;
                        }
                        &:not(.is-disabled):hover {
                            color: #313238;
                        }
                    }
                }
            }
            .bk-tab-header-setting {
                height: 42px;
                line-height: 42px;
            }
            .bk-tab-section {
                padding: 0;
                height: calc(100% - 43px);
                overflow: visible;
                .bk-tab-content {
                    height: 100%;
                }
            }
        }
    }
</style>
