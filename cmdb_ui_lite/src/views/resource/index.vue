<template>
  <div class="classify-layout clearfix">
    <div class="classify-filter">
      <bk-input class="filter-input"
        clearable
        placeholder="请输入关键字"
        right-icon="icon-search"
        v-model.trim="filter">
      </bk-input>
    </div>
    <div v-show="!isEmpty">
      <div class="classify-waterfall fl"
        v-for="col in classifyColumns.length"
        :key="col">
        <div class="classify"
          v-for="classify in classifyColumns[col - 1]"
          :key="classify['bk_classification_id']">
          <h4 class="classify-name" :title="classify['bk_classification_name']">
            <span class="classify-name-text">{{classify['bk_classification_name']}}</span>
            <span class="classify-name-count">{{classify.bk_objects.length}}</span>
          </h4>
          <div class="models-layout">
            <div :class="['models-link']"
              :title="model['bk_obj_name']"
              v-for="(model) in classify.bk_objects"
              :key="model.bk_obj_id"
              @click="redirect(model)">
              <i :class="['model-icon','bk-icon', model['bk_obj_icon'] || 'icon-cc-default']"></i>
              <span class="model-name">{{model['bk_obj_name']}}</span>
              <i class="model-star bk-icon"
                :class="[isCollected(model) ? 'icon-star-shape' : 'icon-star']"
                @click.prevent.stop="toggleCollection(model)">
              </i>
              <div class="model-instance-count">
                <instance-count :obj-id="model.bk_obj_id" :counts="instanceCounts" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="isEmpty && !loading" class="cmdb-data-empty">
      <i class="bk-icon icon-search-list"></i>
      <p>暂无匹配的资源模型</p>
      <bk-button text theme="primary" @click="handleClearFilter">清空</bk-button>
    </div>
  </div>
</template>

<script>
import { mapState, mapGetters, mapActions } from 'vuex'
import debounce from 'lodash.debounce'
import { MENU_RESOURCE_INSTANCE, MENU_RESOURCE_COLLECTION, MENU_RESOURCE_HOST } from '@/dictionary/menu-symbol'
import { BUILTIN_MODELS } from '@/dictionary/model-constants'
import InstanceCount from '@/components/instance-count/index.vue'
import { modelAPI } from '@/api/client'

export default {
  name: 'ResourceIndex',
  components: {
    InstanceCount
  },
  data() {
    return {
      filter: '',
      matchedModels: null,
      instanceCounts: []
    }
  },
  computed: {
    ...mapState('objectModelClassify', {
      loading: 'loading',
      error: 'error'
    }),
    ...mapGetters('objectModelClassify', {
      classifications: 'classifications'
    }),
    ...mapGetters('userCustom', ['resourceCollection']),
    filteredClassifications() {
      const result = []
      this.classifications.forEach((classification) => {
        const models = classification.bk_objects.filter((model) => {
          // 隐藏不可见模型（与原项目 resource-manage 一致）
          if (model.bk_ishidden) return false
          // 隐藏已停用的模型（与原项目 resource-manage 一致）
          if (model.bk_ispaused) return false
          // 资源目录展示由模型属性 bk_isresourcedir 控制（1=展示，0=不展示）。
          // biz/set/module 经 migrate 显式标记为 1，默认初始化即可在资源目录看到其模型实例列表。
          if (model.bk_isresourcedir === 0) return false
          const isMatched = this.matchedModels ? this.matchedModels.includes(model.bk_obj_id) : true
          return isMatched
        })
        if (models.length) {
          result.push({
            ...classification,
            bk_objects: models
          })
        }
      })
      return result
    },
    classifyColumns() {
      const colHeight = [0, 0, 0, 0]
      const classifyColumns = [[], [], [], []]
      this.filteredClassifications.forEach((classify) => {
        const minColHeight = Math.min(...colHeight)
        const rowIndex = colHeight.indexOf(minColHeight)
        classifyColumns[rowIndex].push(classify)
        colHeight[rowIndex] += this.calcWaterfallHeight(classify)
      })
      return classifyColumns
    },
    isEmpty() {
      return this.filteredClassifications.length === 0
    },
    allObjIds() {
      const ids = []
      this.filteredClassifications.forEach((classify) => {
        classify.bk_objects.forEach((model) => {
          ids.push(model.bk_obj_id)
        })
      })
      return ids
    }
  },
  watch: {
    filter: {
      handler(val) {
        this.debounceFilter(val)
      }
    },
    allObjIds: {
      handler(ids) {
        if (ids.length > 0) {
          this.loadInstanceCounts(ids)
        }
      },
      immediate: true
    }
  },
  created() {
    this.debounceFilter = debounce(this.handleFilter, 300)
  },
  async mounted() {
    await this.loadData()
    await this.loadUserCustom()
  },
  methods: {
    ...mapActions('objectModelClassify', [
      'searchClassificationsObjects'
    ]),
    ...mapActions('userCustom', [
      'searchUsercustom',
      'saveUsercustom'
    ]),
    async loadData() {
      try {
        await this.searchClassificationsObjects()
      } catch (error) {
        console.error('[ResourceIndex] 加载数据失败:', error)
      }
    },
    async loadUserCustom() {
      try {
        await this.searchUsercustom()
      } catch (error) {
        console.error('[ResourceIndex] 加载用户配置失败:', error)
      }
    },
    async loadInstanceCounts(objIds) {
      try {
        const response = await modelAPI.getInstanceCounts(objIds)
        this.instanceCounts = response.counts || []
      } catch (error) {
        console.error('[ResourceIndex] 加载实例数量失败:', error)
        this.instanceCounts = objIds.map(id => ({
          bk_obj_id: id,
          inst_count: 0,
          error: true
        }))
      }
    },
    handleFilter(val) {
      if (!val) {
        this.matchedModels = null
        return
      }
      const keyword = val.toLowerCase()
      const matched = []
      this.classifications.forEach((classification) => {
        classification.bk_objects.forEach((model) => {
          if (
            model.bk_obj_name.toLowerCase().includes(keyword) ||
            model.bk_obj_id.toLowerCase().includes(keyword)
          ) {
            matched.push(model.bk_obj_id)
          }
        })
      })
      this.matchedModels = matched
    },
    handleClearFilter() {
      this.filter = ''
      this.matchedModels = null
    },
    calcWaterfallHeight(classify) {
      return 46 + 16 + (classify.bk_objects.length * 36)
    },
    redirect(model) {
      // 内置模型 host 使用专属资源路由 /resource/host（与「主机」收藏项完全一致），
      // 其余模型走通用实例路由 /resource/instance/:objId。
      // 这样无论是从「资源目录树」点主机，还是从「主机」收藏项进入，都落在同一入口，
      // 左侧「主机」收藏项的选中态始终同步（对齐原 bk-cmdb 的 host 专属路由语义）。
      if (model.bk_obj_id === BUILTIN_MODELS.HOST) {
        this.$router.push({ name: MENU_RESOURCE_HOST })
      } else {
        this.$router.push({
          name: MENU_RESOURCE_INSTANCE,
          params: {
            objId: model.bk_obj_id
          }
        })
      }
    },
    isCollected(model) {
      return this.resourceCollection.includes(model.bk_obj_id)
    },
    async toggleCollection(model) {
      const isCollected = this.isCollected(model)
      const oldCollection = this.resourceCollection || []
      let newCollection
      if (isCollected) {
        newCollection = oldCollection.filter(id => id !== model.bk_obj_id)
      } else {
        newCollection = [...oldCollection, model.bk_obj_id]
      }
      try {
        await this.saveUsercustom({
          [MENU_RESOURCE_COLLECTION]: newCollection
        })
        this.$bkMessage({
          message: isCollected ? '已取消收藏' : '已添加收藏',
          theme: 'primary'
        })
      } catch (error) {
        console.error('[ResourceIndex] 收藏操作失败:', error)
        this.$handleApiError(error)
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.classify-layout {
  padding: 20px;
  min-height: 100%;
}

.classify-filter {
  margin-bottom: 20px;

  .filter-input {
    width: 280px;
  }
}

.classify-waterfall {
  width: 25%;
  padding: 0 10px;
  box-sizing: border-box;

  &:first-child {
    padding-left: 0;
  }

  &:last-child {
    padding-right: 0;
  }
}

.classify {
  margin: 0 0 20px 0;
  background-color: #fff;
  border: 1px solid #ebf0f5;
  box-shadow: 0px 3px 6px 0px rgba(51, 60, 72, 0.05);
}

.classify-name {
  padding: 13px 5px;
  margin: 0 20px;
  line-height: 20px;
  font-size: 0;
  color: #313238;
  border-bottom: 1px solid #ebf0f5;

  &-text {
    display: inline-block;
    padding: 0 2px 0 0;
    vertical-align: middle;
    max-width: calc(100% - 40px);
    font-size: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &-count {
    display: inline-block;
    width: 40px;
    vertical-align: middle;
    font-size: 12px;
    color: #979ba5;
  }
}

.models-layout {
  padding: 8px 0;

  .models-link {
    display: block;
    height: 38px;
    font-size: 0;
    position: relative;
    padding: 7px 25px;
    cursor: pointer;

    &:hover {
      background-color: #ecf3ff;
    }

    &:before {
      content: "";
      display: inline-block;
      height: 100%;
      vertical-align: middle;
    }

    &:hover .model-icon,
    &:hover .model-name {
      color: #3A84FF;
    }

    &:hover .model-star {
      display: inline-block;
    }

    .model-icon,
    .model-name {
      display: inline-block;
      vertical-align: middle;
    }

    .model-icon {
      font-size: 16px;
      color: #798AAD;
    }

    .model-name {
      max-width: calc(100% - 80px);
      margin: 0 0 0 12px;
      font-size: 14px;
      line-height: 24px;
      color: #313238;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .model-star {
      display: none;
      width: 24px;
      height: 24px;
      margin-left: 5px;
      line-height: 24px;
      text-align: center;
      font-size: 14px;
      cursor: pointer;
      vertical-align: middle;

      &.icon-star-shape {
        color: #FFB400;
        display: inline-block;
      }
    }

    .model-instance-count {
      float: right;
      display: inline-block;
      width: 35px;
      font-size: 14px;
      height: 24px;
      line-height: 24px;
      color: #C4C6CC;
      text-align: right;
    }
  }
}

.cmdb-data-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #979ba5;

  .bk-icon {
    font-size: 64px;
    margin-bottom: 16px;
    color: #c4c6cc;
  }

  p {
    font-size: 14px;
    margin: 0 0 12px 0;
  }
}

.fl {
  float: left;
}

.clearfix::after {
  content: "";
  display: table;
  clear: both;
}
</style>
