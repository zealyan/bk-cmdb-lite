<template>
  <div class="service-category-layout" v-bkloading="{ isLoading: loading, opacity: 1 }">
    <!-- 功能提示：对齐原项目 cmdb-tips（默认 icon=icon-cc-exclamation-tips，蓝色提示条） -->
    <div class="category-tips">
      <i class="icon-cc-exclamation-tips category-tips-icon"></i>
      <span class="category-tips-text">服务分类可以帮助业务梳理服务用途。支持根据业务拓展更多分类。</span>
    </div>

    <!-- 搜索过滤 -->
    <div class="category-filter">
      <bk-input class="filter-input"
        :clearable="true"
        :placeholder="'请输入关键字（分类名称 / ID）'"
        v-model.trim="keyword">
      </bk-input>
    </div>

    <!-- 分类卡片网格：每张卡片 = 一个一级分类 -->
    <div class="category-list">
      <div
        :class="['category-item', 'bgc-white', { editing: editMainId === root.id }]"
        v-for="root in displayList" :key="root.id">
        <!-- 卡片标题栏：一级分类名 + 操作按钮 -->
        <div class="category-title">
          <div class="main-edit" v-if="editMainId === root.id">
            <category-input class="main-input"
              ref="editInput"
              :value="root.name"
              placeholder="请输入一级分类名称"
              @on-confirm="handleEditMainConfirm"
              @on-cancel="handleCloseEditMain">
            </category-input>
          </div>
          <template v-else>
            <div class="category-name">
              <template v-if="root.is_built_in">
                <div class="category-name-text is-built-in">
                  <div class="text-inner">
                    <span class="main-name" :title="root.name">{{ root.name }}</span>
                    <span class="main-id">{{ root.id }}</span>
                  </div>
                </div>
                <span class="built-in-sign">内置</span>
              </template>
              <div v-else class="category-name-text" @click.stop="handleEditMain(root)">
                <div class="text-inner">
                  <span class="main-name" :title="root.name">{{ root.name }}</span>
                  <span class="main-id">{{ root.id }}</span>
                </div>
              </div>
            </div>
            <div class="menu-operational" v-if="!root.is_built_in">
              <bk-button class="menu-btn"
                :text="true"
                @click="handleShowAddChild(root.id)">
                <i class="bk-icon icon-cc-plus"></i>
              </bk-button>
              <bk-button v-if="!root.children.length" class="menu-btn"
                :text="true"
                @click="handleDelete(root)">
                <i class="bk-icon icon-cc-del"></i>
              </bk-button>
              <span v-else class="menu-btn no-allow-btn" v-bk-tooltips="'请先清空二级分类'">
                <i class="bk-icon icon-cc-del"></i>
              </span>
            </div>
          </template>
        </div>

        <!-- 二级分类列表（可滚动，固定高度） -->
        <div class="child-category">
          <div v-for="child in root.children"
            :class="['child-item', {
              'child-edit': editChildId === child.id,
              'is-built-in': child.is_built_in
            }]"
            :key="child.id">
            <category-input v-if="editChildId === child.id"
              class="child-input"
              :value="child.name"
              placeholder="请输入二级分类名称"
              @on-confirm="handleEditChildConfirm"
              @on-cancel="handleCloseEditChild">
            </category-input>
            <template v-else>
              <div class="child-title">
                <span :title="child.name">{{ child.name }}</span>
                <span class="child-id" :title="child.id">{{ child.id }}</span>
                <div class="child-edit" v-if="!child.is_built_in">
                  <bk-button class="child-edit-btn"
                    theme="primary"
                    :text="true"
                    @click.stop="handleEditChild(child)">
                    <i class="bk-icon icon-cc-edit-shape"></i>
                  </bk-button>
                  <!-- 删除按钮：未被模块占用时可点击删除；已被占用则渲染为禁用态（灰色 + not-allowed + 提示） -->
                  <bk-button v-if="!child.usage_amount" class="child-edit-btn"
                    theme="primary"
                    :text="true"
                    @click.stop="handleDelete(root, child)">
                    <i class="bk-icon icon-cc-tips-close"></i>
                  </bk-button>
                  <i v-else class="bk-icon icon-cc-tips-close child-del-disabled"
                    v-bk-tooltips="childDelTips"></i>
                </div>
              </div>
            </template>
          </div>

          <!-- 卡片底部「添加」二级分类 -->
          <div class="child-item is-add" v-if="!root.is_built_in && addChildOf !== root.id">
            <div class="child-title">
              <bk-button class="add-btn" :text="true" @click="handleShowAddChild(root.id)">
                <div class="btn-group">
                  <i class="bk-icon icon-cc-plus"></i>
                  <span>添加</span>
                </div>
              </bk-button>
            </div>
          </div>
          <div class="child-item child-edit" v-if="addChildOf === root.id">
            <category-input class="child-input"
              :value="''"
              placeholder="请输入二级分类名称"
              @on-confirm="handleAddChildConfirm"
              @on-cancel="handleCloseAddChild">
            </category-input>
          </div>
        </div>
      </div>

      <!-- 新建一级分类卡片（虚线边框） -->
      <div class="category-item add-item"
        :style="{ 'border-style': showAddMain ? 'solid' : 'dashed' }"
        v-show="!keyword">
        <div class="category-title" :style="{ 'border-bottom-style': showAddMain ? 'solid' : 'dashed' }">
          <div class="main-edit" style="width: 100%;" v-if="showAddMain">
            <category-input class="main-input"
              ref="addInput"
              :value="''"
              placeholder="请输入一级分类名称"
              @on-confirm="handleAddMainConfirm"
              @on-cancel="handleCloseAddMain">
            </category-input>
          </div>
        </div>
        <div class="child-category"></div>
        <bk-button v-show="!showAddMain" class="add-root-btn" @click="handleAddBox">
          <i class="bk-icon icon-cc-plus"></i>
          <span>新建一级分类</span>
        </bk-button>
      </div>
    </div>

    <!-- 空态 -->
    <div v-if="!displayList.length && !loading" class="category-empty">
      <i class="bk-icon icon-cc-square"></i>
      <p v-if="keyword">未找到匹配「{{ keyword }}」的服务分类</p>
    </div>
  </div>
</template>

<script>
import categoryInput from './children/category-input.vue'
import { serviceAPI } from '@/api/service.js'

export default {
  name: 'BusinessServiceCategory',
  components: {
    categoryInput
  },
  data() {
    return ({
      loading: false,
      bizId: this.$route.params.bizId,
      categories: [],
      editMainId: null,
      editChildId: null,
      addChildOf: null,
      showAddMain: false,
      keyword: '',
      // 二级分类被模块占用时删除禁用的提示文案（对齐原项目「二级分类删除提示」）
      childDelTips: '该分类已被模块使用，不可删除',
    })
  },
  computed: {
    // 按关键字过滤（名称或 ID，大小写不敏感），覆盖一级与二级
    displayList() {
      if (!this.keyword) return this.categories
      const kw = String(this.keyword).toLowerCase()
      return this.categories.filter((root) => {
        if (String(root.name).toLowerCase().includes(kw) || String(root.id).includes(kw)) return true
        return (root.children || []).some(child =>
          String(child.name).toLowerCase().includes(kw) || String(child.id).includes(kw))
      })
    }
  },
  watch: {
    // 业务切换时重载
    '$route.params.bizId'(bizId) {
      this.bizId = bizId
      this.resetEditState()
      this.getCategories()
    }
  },
  created() {
    this.getCategories()
  },
  methods: {
    /**
     * 拉取服务分类列表并组装为两级树。
     * 后端返回扁平列表（info），前端按 bk_parent_id / bk_root_id 组装。
     */
    async getCategories() {
      this.loading = true
      try {
        const res = await serviceAPI.getServiceCategories(this.bizId)
        const list = (res && res.info) || []
        // 内置 Default 分类（bk_biz_id=0 全局 + is_built_in=1）不在此管理页展示，
        // 对齐原项目 service-category/index.vue：
        //   list.filter(c => !c.bk_parent_id && !(c.name === 'Default' && c.is_built_in))
        // 差异说明：原项目仅过滤一级，二级 Default 因失去父级而自然不渲染；
        // lite 的 assembleTree 会把孤儿二级提升为根节点，故两级一并过滤。
        const visible = list.filter(item => !(item.is_built_in && item.name === 'Default'))
        this.categories = this.assembleTree(visible)
      } catch (e) {
        console.error('[ServiceCategory] 加载分类失败:', e)
        this.$handleApiError(e)
      } finally {
        this.loading = false
      }
    },

    // 将扁平分类列表组装为两级树（bk_parent_id=0 为一级；其余挂到对应 root）
    assembleTree(list = []) {
      const nodes = list.map(item => ({
        id: item.id,
        name: item.name,
        bk_parent_id: item.bk_parent_id,
        bk_root_id: item.bk_root_id,
        is_built_in: !!item.is_built_in,
        // 该分类被模块引用的数量（usage_amount）；>0 表示已被使用，删除禁用
        usage_amount: item.usage_amount || 0,
        children: []
      }))
      const map = {}
      nodes.forEach(n => { map[n.id] = n })
      const roots = []
      nodes.forEach(n => {
        if (n.bk_parent_id === 0 || n.bk_parent_id === n.id) {
          roots.push(n)
        } else {
          const parent = map[n.bk_parent_id]
          if (parent) parent.children.push(n)
          else roots.push(n) // 孤儿节点兜底，避免丢失
        }
      })
      // 一级按 id 升序（后端已保证），二级保持后端返回顺序
      return roots
    },

    // ── 编辑态打开 ──
    handleAddBox() {
      this.resetEditState()
      this.showAddMain = true
    },
    handleCloseAddMain() {
      this.showAddMain = false
    },
    handleShowAddChild(rootId) {
      this.resetEditState()
      this.addChildOf = rootId
    },
    handleCloseAddChild() {
      this.addChildOf = null
    },
    handleEditMain(root) {
      this.resetEditState()
      this.editMainId = root.id
    },
    handleCloseEditMain() {
      this.editMainId = null
    },
    handleEditChild(child) {
      this.resetEditState()
      this.editChildId = child.id
    },
    handleCloseEditChild() {
      this.editChildId = null
    },
    resetEditState() {
      this.editMainId = null
      this.editChildId = null
      this.addChildOf = null
      this.showAddMain = false
    },

    // ── 确认提交（按当前态分流）──
    handleAddMainConfirm(value) {
      this.submitCreate((value || '').trim(), 0)
    },
    handleAddChildConfirm(value) {
      const parentId = this.addChildOf
      this.submitCreate((value || '').trim(), parentId)
    },
    handleEditMainConfirm(value) {
      const id = this.editMainId
      const root = this.categories.find(c => c.id === id)
      if (!root) { this.resetEditState(); return }
      const name = (value || '').trim()
      if (!name || name === root.name) { this.resetEditState(); return }
      this.submitUpdate(id, name)
    },
    handleEditChildConfirm(value) {
      const id = this.editChildId
      const child = this.findChild(id)
      if (!child) { this.resetEditState(); return }
      const name = (value || '').trim()
      if (!name || name === child.name) { this.resetEditState(); return }
      this.submitUpdate(id, name)
    },

    findChild(childId) {
      for (const root of this.categories) {
        const hit = (root.children || []).find(c => c.id === childId)
        if (hit) return hit
      }
      return null
    },

    async submitCreate(name, parentId) {
      if (!name) { this.resetEditState(); return }
      this.loading = true
      try {
        if (parentId) {
          await serviceAPI.createServiceCategory(this.bizId, { name, bk_parent_id: parentId })
          this.$bkMessage({ theme: 'success', message: '二级分类创建成功' })
        } else {
          await serviceAPI.createServiceCategory(this.bizId, { name })
          this.$bkMessage({ theme: 'success', message: '一级分类创建成功' })
        }
        this.resetEditState()
        await this.getCategories()
      } catch (e) {
        console.error('[ServiceCategory] 创建失败:', e)
        this.$handleApiError(e)
      } finally {
        this.loading = false
      }
    },

    async submitUpdate(catId, name) {
      this.loading = true
      try {
        await serviceAPI.updateServiceCategory(catId, name)
        this.$bkMessage({ theme: 'success', message: '修改成功' })
        this.resetEditState()
        await this.getCategories()
      } catch (e) {
        console.error('[ServiceCategory] 修改失败:', e)
        this.$handleApiError(e)
      } finally {
        this.loading = false
      }
    },

    // ── 删除（确认后调用后端，级联删除子分类）──
    handleDelete(root, child) {
      const id = child ? child.id : root.id
      const name = child ? child.name : root.name
      const hasChildren = !child && root.children && root.children.length
      this.$bkInfo({
        title: '确认删除该服务分类？',
        subTitle: hasChildren
          ? `「${name}」下存在 ${root.children.length} 个子分类，删除后将一并移除，且不可恢复。`
          : `删除后不可恢复，确认删除「${name}」？`,
        confirmFn: async () => {
          try {
            await serviceAPI.deleteServiceCategory(id)
            this.$bkMessage({ theme: 'success', message: '删除成功' })
            this.resetEditState()
            await this.getCategories()
          } catch (e) {
            console.error('[ServiceCategory] 删除失败:', e)
            this.$handleApiError(e)
          }
        }
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.service-category-layout {
  padding: 15px 20px 0;
  height: 100%;
  overflow: auto;

  .category-tips {
    display: flex;
    align-items: center;
    margin-bottom: 12px;
    padding: 8px 16px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;
    background-color: #f0f8ff;
    border: 1px solid #a3c5fd;
    border-radius: 2px;
    .category-tips-icon {
      flex: 0 0 16px;
      margin-right: 6px;
      font-size: 16px;
      line-height: 16px;
      color: #3a84ff;
    }
    .category-tips-text {
      flex: 1;
    }
  }

  .category-filter {
    margin-bottom: 12px;
    .filter-input {
      width: 260px;
    }
  }

  .category-list {
    display: flex;
    flex-flow: row wrap;
  }

  .category-item {
    position: relative;
    flex: 0 0 calc(25% - 15px);
    border: 1px solid #dcdee5;
    border-radius: 0 0 2px 2px;
    margin-left: 20px;
    margin-bottom: 20px;
    overflow: hidden;
    background-color: #fff;

    &:hover:not(.add-item) {
      box-shadow: 0 2px 6px 0 rgba(0, 0, 0, 0.1);
      .menu-operational {
        display: flex;
      }
    }
    &:nth-child(4n+1) {
      margin-left: 0;
    }

    // 新建一级分类卡片（虚线）
    &.add-item {
      .category-name {
        color: #dcdee5 !important;
      }
      .child-title {
        color: #dcdee5 !important;
        background-color: transparent !important;
      }
      .add-root-btn {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: transparent;
        border: none;
        color: #979ba5;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        &:hover {
          color: #3a84ff;
        }
        .bk-icon {
          font-size: 16px;
          margin-right: 4px;
        }
      }
    }
  }

  .category-title {
    @include space-between;
    background-color: #fafbfd;
    padding: 0 12px;
    height: 52px;
    font-size: 14px;
    color: #63656e;
    font-weight: bold;
    border-bottom: 1px solid #dcdee5;

    .main-edit {
      display: flex;
      align-items: center;
      width: 100%;
      .main-input {
        flex: 1;
      }
    }

    .category-name {
      display: flex;
      flex: 1;
      width: 100%;
      overflow: hidden;

      .category-name-text {
        max-width: 100%;
        .text-inner {
          max-width: 100%;
          display: inline-flex;
          flex-direction: column;
          padding: 2px 6px;
          line-height: normal;
          cursor: pointer;
          &:hover {
            background: #f0f1f5;
          }
          .main-id {
            font-size: 12px;
            font-weight: 400;
            color: #c4c6cc;
            &::before {
              content: "#";
            }
          }
          .main-id,
          .main-name {
            @include ellipsis;
          }
          .main-name {
            height: 20px;
            line-height: 20px;
          }
        }
        &.is-built-in {
          max-width: calc(100% - 40px);
          .text-inner {
            cursor: initial;
            &:hover {
              background: transparent;
            }
          }
        }
      }
      .built-in-sign {
        display: inline-block;
        height: 20px;
        line-height: 20px;
        margin: 2px 0 0 4px;
        padding: 0 6px;
        font-size: 12px;
        color: #ffffff;
        text-align: center;
        background-color: #d3d5dd;
        border-radius: 2px;
      }
    }
  }

  .child-category {
    height: 280px;
    padding: 0 10px 10px 38px;
    @include scrollbar-y;

    .child-item {
      @include space-between;
      position: relative;
      z-index: 10;
      line-height: 32px;

      &:hover:not(.is-built-in):not(.is-add) {
        .child-title {
          background-color: #fafbfd;
          color: #3a84ff;
        }
        > span {
          display: none;
        }
        .child-edit {
          display: block;
        }
        .child-id {
          display: none;
        }
      }
      &:first-child {
        padding-top: 14px;
        &::after {
          height: 30px;
          top: 0;
        }
      }
      &::after {
        content: '';
        position: absolute;
        top: -15px;
        left: -20px;
        display: block;
        width: 30px;
        height: 32px;
        border-bottom: 1px solid #dcdee5;
        border-left: 1px solid #dcdee5;
        z-index: -1;
      }

      .child-title {
        @include ellipsis;
        @include space-between;
        color: #63656e;
        font-size: 14px;
        font-weight: normal;
        flex: 1;
        padding-right: 8px;
        padding-left: 8px;
        margin-left: 10px;
        > span {
          @include ellipsis;
          padding-right: 10px;
        }
        .child-id {
          min-width: 42px;
          font-size: 12px;
          color: #c4c6cc;
          padding-right: 6px;
          text-align: right;
          &::before {
            content: "#";
          }
        }
        .btn-group {
          @include space-between;
        }
      }
      .child-edit {
        display: none;
        margin-left: auto;
        .child-edit-btn {
          .bk-icon {
            font-size: 14px;
          }
          // 对齐原项目 bk-cmdb：编辑/删除两图标间距由首个按钮的 mr10（margin-right:10px）提供
          &:not(:last-child) {
            margin-right: 10px;
          }
        }
        // 二级分类被模块占用时，删除图标渲染为禁用态（对齐原项目 icon-cc-tips-close + not-allowed）
        .child-del-disabled {
          font-size: 14px;
          color: #dcdee5;
          cursor: not-allowed;
          outline: none;
        }
      }
      .child-input {
        margin-left: 10px;
        padding-left: 8px;
        flex: 1;
      }
      &.is-add {
        .add-btn {
          color: #979ba5;
          &:hover {
            color: #3a84ff;
          }
        }
      }
    }
  }

  .menu-operational {
    display: none;
    padding: 6px 0;
    line-height: 30px;
    .menu-btn {
      display: block;
      width: 100%;
      height: 30px;
      line-height: 30px;
      padding: 0 7px;
      text-align: left;
      color: #979ba5;
      outline: none;
      &:hover {
        color: #3a84ff;
      }
      &:disabled {
        color: #dcdee5;
        background-color: transparent;
      }
      &.no-allow-btn {
        cursor: not-allowed;
        color: #dcdee5;
        background-color: transparent;
      }
      .bk-icon {
        font-size: 16px;
      }
    }
  }

  .category-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 20px;
    color: #979ba5;

    .bk-icon {
      font-size: 48px;
      margin-bottom: 12px;
      color: #c4c6cc;
    }
    p {
      margin: 0;
      font-size: 14px;
    }
  }
}

@media screen and (min-width: 1920px) {
  .service-category-layout .category-item {
    flex: 0 0 calc(20% - 16px) !important;
    &:nth-child(4n+1) {
      margin-left: 20px !important;
    }
    &:nth-child(5n+1) {
      margin-left: 0 !important;
    }
  }
}
</style>
