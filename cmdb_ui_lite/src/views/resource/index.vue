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
              <i :class="['model-icon','bk-icon', model['bk_obj_icon']]"></i>
              <span class="model-name">{{model['bk_obj_name']}}</span>
              <i class="model-star bk-icon"
                :class="[isCollected(model) ? 'icon-star-shape' : 'icon-star']"
                @click.prevent.stop="toggleCollection(model)">
              </i>
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
import { MENU_RESOURCE_INSTANCE } from '@/dictionary/menu-symbol'

export default {
  name: 'ResourceIndex',
  data() {
    return {
      filter: '',
      matchedModels: null
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
    filteredClassifications() {
      const result = []
      this.classifications.forEach((classification) => {
        const models = classification.bk_objects.filter((model) => {
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
        colHeight[rowIndex] += classify.bk_objects.length
      })
      return classifyColumns
    },
    isEmpty() {
      return this.filteredClassifications.length === 0
    }
  },
  watch: {
    filter: {
      handler(val) {
        this.debounceFilter(val)
      }
    }
  },
  created() {
    this.debounceFilter = debounce(this.handleFilter, 300)
  },
  async mounted() {
    await this.loadData()
  },
  methods: {
    ...mapActions('objectModelClassify', [
      'searchClassificationsObjects'
    ]),
    async loadData() {
      try {
        await this.searchClassificationsObjects()
      } catch (error) {
        console.error('[ResourceIndex] 加载数据失败:', error)
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
    redirect(model) {
      this.$router.push({
        name: MENU_RESOURCE_INSTANCE,
        params: {
          objId: model.bk_obj_id
        }
      })
    },
    isCollected(model) {
      return false
    },
    toggleCollection(model) {
      this.$bkMessage({
        message: `收藏功能开发中：${model.bk_obj_name}`,
        theme: 'primary'
      })
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
      float: right;
      margin-top: 7px;

      &.icon-star-shape {
        color: #FFB400;
        display: inline-block;
      }
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
