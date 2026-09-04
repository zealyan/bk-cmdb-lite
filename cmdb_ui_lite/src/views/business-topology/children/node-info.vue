<template>
  <div class="node-info-layout" v-bkloading="{ isLoading: loading }">
    <div v-if="!node" class="empty-state">
      <div class="placeholder-text">请选择拓扑节点</div>
      <div class="placeholder-desc">点击左侧拓扑树节点查看节点信息</div>
    </div>
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
    </div>

    <!-- 展示态：与原项目 cmdb-details 一致，纯展示 + 触发 on-edit/on-delete -->
    <cmdb-details
      v-else-if="!isEditing"
      :inst="instanceData"
      :properties="properties"
      :property-groups="propertyGroups"
      :invisible-properties="invisibleProperties"
      :show-options="canEdit || canDelete"
      :show-edit="canEdit"
      :show-delete="canDelete"
      @on-edit="handleEdit"
      @on-delete="handleDelete">
      <!-- prepend：在基础信息（default 属性组）之上展示模块所属服务分类 -->
      <template slot="prepend" v-if="isModuleNode">
        <div class="service-category-extra">
          <span class="sc-label">服务分类</span>
          <span class="sc-value" v-if="loadingCategory">加载中...</span>
          <span class="sc-value" v-else>{{ categoryDisplayName }}</span>
        </div>
      </template>
    </cmdb-details>

    <!-- 编辑态：内联表单（无弹出框，与原项目详情行内编辑一致） -->
    <div v-else class="inline-edit-panel">
      <!-- 模块节点：服务分类（一级 / 二级）专用选择器，置于通用字段之上 -->
      <div class="service-category-edit" v-if="isModuleNode">
        <label class="sc-edit-label">服务分类</label>
        <div class="sc-edit-selects">
          <bk-select class="sc-edit-select" v-model="editFirstClass" :clearable="false" placeholder="请选择一级分类"
            @change="handleFirstClassChange">
            <bk-option v-for="item in editCategoryTree"
              :key="item.id"
              :id="item.id"
              :name="item.name">
            </bk-option>
          </bk-select>
          <bk-select class="sc-edit-select" v-model="editSecondClass" :clearable="false" placeholder="请选择二级分类">
            <bk-option v-for="item in editSecondClassOptions"
              :key="item.id"
              :id="item.id"
              :name="item.name">
            </bk-option>
          </bk-select>
        </div>
      </div>
      <bk-form :model="editForm" :rules="editRules" ref="editForm">
        <bk-form-item
          v-for="property in editableProperties"
          :key="property.bk_property_id"
          :label="property.bk_property_name"
          :property="property.bk_property_id"
          :required="property.isrequired">
          <component
            :is="getFormComponent(property.bk_property_type)"
            v-model="editForm[property.bk_property_id]"
            :property="property">
          </component>
        </bk-form-item>
      </bk-form>
      <div class="inline-edit-actions">
        <bk-button theme="primary" :loading="editLoading" @click="handleEditSubmit">保存</bk-button>
        <bk-button @click="handleEditCancel">取消</bk-button>
      </div>
    </div>
  </div>
</template>

<script>
import CmdbDetails from '@/components/ui/details/CmdbDetails.vue'
import { modelAPI } from '@/api/client'
import { topoAPI } from '@/api/topo'
import instanceAPI from '@/api/instance'
import modelAttributeAPI from '@/api/modelAttribute'
import { serviceAPI } from '@/api/service'

// 简化的表单组件
import FormBool from '@/components/ui/form/bool.vue'
import FormDate from '@/components/ui/form/date.vue'
import FormDatetime from '@/components/ui/form/datetime.vue'
import FormEnum from '@/components/ui/form/enum.vue'
import FormEnumMulti from '@/components/ui/form/enummulti.vue'
import FormFloat from '@/components/ui/form/float.vue'
import FormInt from '@/components/ui/form/int.vue'
import FormList from '@/components/ui/form/list.vue'
import FormLongchar from '@/components/ui/form/longchar.vue'
import FormSinglechar from '@/components/ui/form/singlechar.vue'
import FormTime from '@/components/ui/form/time.vue'

export default {
  name: 'NodeInfo',
  components: {
    CmdbDetails,
    FormBool,
    FormDate,
    FormDatetime,
    FormEnum,
    FormEnumMulti,
    FormFloat,
    FormInt,
    FormList,
    FormLongchar,
    FormSinglechar,
    FormTime
  },
  props: {
    node: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      loading: false,
      error: null,
      instanceData: {},
      properties: [],
      propertyGroups: [],
      invisibleProperties: [],
      // 模块节点服务分类（两级路径）：一级 / 二级名称，展示在基础信息属性组之上
      serviceCategoryPath: null,
      loadingCategory: false,
      // 内联编辑态（替代原 bk-dialog 弹出框，与原项目详情行内编辑一致）
      isEditing: false,
      editForm: {},
      editRules: {},
      editLoading: false,
      // 编辑态服务分类选择器（两级：一级分类 -> 二级分类；二级 id 作为 service_category_id）
      editCategoryTree: [],
      editFirstClass: '',
      editSecondClass: ''
    }
  },
  computed: {
    isBizNode() {
      return this.node?.data?.bk_obj_id === 'biz'
    },
    isSetNode() {
      return this.node?.data?.bk_obj_id === 'set'
    },
    isModuleNode() {
      return this.node?.data?.bk_obj_id === 'module'
    },
    isInternalNode() {
      // 内置节点不允许编辑/删除
      if (!this.node) return false
      return this.node.data?.default !== 0 && this.node.data?.default !== undefined
    },
    canEdit() {
      return !this.isInternalNode
    },
    canDelete() {
      return !this.isInternalNode
    },
    editableProperties() {
      // 只允许编辑业务自定义字段（非系统字段、非只读）
      return this.properties.filter(p => {
        if (p.bk_issystem || p.isreadonly) return false
        // 排除主键和ID字段
        if (['id', 'bk_inst_id'].includes(p.bk_property_id)) return false
        // 编辑时不显示模板ID等关联字段
        if (p.bk_property_id === 'service_template_id') return false
        // 服务分类由专用两级选择器编辑，不进入通用编辑表单（避免渲染成裸 int 字段）
        if (p.bk_property_id === 'service_category_id') return false
        return true
      })
    },
    categoryDisplayName() {
      // 模块节点「服务分类：一级 / 二级」展示文案
      if (!this.serviceCategoryPath) return '--'
      const first = this.serviceCategoryPath.first_level && this.serviceCategoryPath.first_level.name
      const second = this.serviceCategoryPath.second_level && this.serviceCategoryPath.second_level.name
      if (first && second) return `${first} / ${second}`
      if (first) return first
      return '--'
    },
    editSecondClassOptions() {
      // 编辑态：当前一级分类下的二级分类选项
      const matched = this.editCategoryTree.find(c => c.id === this.editFirstClass)
      return matched ? (matched.children || []) : []
    }
  },
  watch: {
    node: {
      immediate: true,
      handler(node) {
        if (node && node.data) {
          this.loadData()
        } else {
          this.reset()
        }
      }
    }
  },
  methods: {
    async loadData() {
      this.loading = true
      this.error = null
      this.reset()

      const objId = this.node.data.bk_obj_id
      const instId = this.node.data.bk_inst_id

      try {
        // 并行加载属性、分组和实例数据
        await Promise.all([
          this.loadProperties(objId),
          this.loadInstanceData(objId, instId)
        ])
        // 模块节点：加载所属服务分类两级路径，展示在基础信息之上
        if (this.isModuleNode) {
          const catId = this.instanceData.service_category_id
          if (catId) {
            await this.loadServiceCategory(catId)
          } else {
            this.serviceCategoryPath = null
          }
        }
      } catch (err) {
        console.error('[NodeInfo] 加载数据失败:', err)
        this.error = err.message || '加载数据失败'
      } finally {
        this.loading = false
      }
    },

    async loadProperties(objId) {
      try {
        const [attributes, groups] = await Promise.all([
          modelAttributeAPI.getModelAttributes(objId),
          modelAPI.getModelPropertyGroups(objId).catch(() => ({}))
        ])

        if (Array.isArray(attributes)) {
          this.properties = attributes
        } else if (attributes && attributes.info) {
          this.properties = attributes.info
        } else if (attributes && attributes.attributes) {
          this.properties = attributes.attributes
        }

        if (groups && groups.groups) {
          this.propertyGroups = groups.groups.sort(
            (a, b) => (a.bk_group_index || 0) - (b.bk_group_index || 0)
          )
        }
      } catch (error) {
        console.error('[NodeInfo] 加载属性失败:', error)
        throw new Error('加载属性信息失败')
      }
    },

    async loadInstanceData(objId, instId) {
      try {
        const data = await instanceAPI.getInstanceDetails(objId, instId)
        if (data && typeof data === 'object') {
          this.instanceData = data
        } else {
          throw new Error('未找到节点数据')
        }
      } catch (error) {
        console.error('[NodeInfo] 加载实例数据失败:', error)
        throw new Error('获取节点详情失败')
      }
    },

    reset() {
      this.instanceData = {}
      this.properties = []
      this.propertyGroups = []
      this.serviceCategoryPath = null
      this.isEditing = false
      this.editForm = {}
      this.editCategoryTree = []
      this.editFirstClass = ''
      this.editSecondClass = ''
    },

    async loadServiceCategory(catId) {
      // 加载模块所属服务分类的两级路径（一级 / 二级名称），展示用
      this.loadingCategory = true
      try {
        const res = await serviceAPI.getServiceCategory(catId)
        const data = res && (res.data || res) ? (res.data || res) : null
        this.serviceCategoryPath = data
      } catch (err) {
        console.error('[NodeInfo] 加载服务分类失败:', err)
        this.serviceCategoryPath = null
      } finally {
        this.loadingCategory = false
      }
    },

    async loadCategoryTree() {
      // 编辑态：拉取业务的全量服务分类，组装为两级选择树
      const bizId = this.node.data.bk_biz_id
      try {
        const res = await serviceAPI.getServiceCategories(bizId)
        const info = (res && (res.info || res.data && res.data.info)) || []
        const firstList = info.filter(c => !c.bk_parent_id)
        firstList.forEach(fc => {
          fc.children = info.filter(c => c.bk_parent_id === fc.id)
        })
        this.editCategoryTree = firstList
      } catch (err) {
        console.error('[NodeInfo] 加载服务分类树失败:', err)
        this.editCategoryTree = []
      }
    },

    getFormComponent(propertyType) {
      const map = {
        'bool': 'FormBool',
        'date': 'FormDate',
        'datetime': 'FormDatetime',
        'enum': 'FormEnum',
        'enummulti': 'FormEnumMulti',
        'float': 'FormFloat',
        'int': 'FormInt',
        'list': 'FormList',
        'longchar': 'FormLongchar',
        'shortchar': 'FormSinglechar',
        'singlechar': 'FormSinglechar',
        'text': 'FormLongchar',
        'time': 'FormTime',
        'char': 'FormSinglechar'
      }
      return map[propertyType] || 'FormSinglechar'
    },

    // 进入内联编辑态（替代原弹出框）
    async handleEdit() {
      this.editForm = { ...this.instanceData }
      this.editLoading = false
      this.isEditing = true
      // 模块节点：初始化服务分类选择器（预置当前一级/二级）
      if (this.isModuleNode) {
        this.editFirstClass = this.serviceCategoryPath && this.serviceCategoryPath.first_level
          ? this.serviceCategoryPath.first_level.id : ''
        this.editSecondClass = this.serviceCategoryPath && this.serviceCategoryPath.second_level
          ? this.serviceCategoryPath.second_level.id : ''
        await this.loadCategoryTree()
        // 树加载后，若当前一级无二级选项则回退到首个一级的首个二级
        if (this.editFirstClass && !this.editSecondClassOptions.length) {
          this.editFirstClass = this.editCategoryTree.length ? this.editCategoryTree[0].id : ''
          this.editSecondClass = this.editSecondClassOptions.length ? this.editSecondClassOptions[0].id : ''
        }
      }
      this.$nextTick(() => {
        this.$refs.editForm && this.$refs.editForm.clearValidate()
      })
    },

    handleFirstClassChange() {
      // 切换一级分类后，二级分类列表与默认选中同步刷新
      this.editSecondClass = this.editSecondClassOptions.length ? this.editSecondClassOptions[0].id : ''
    },

    handleEditCancel() {
      this.isEditing = false
      this.editForm = {}
    },

    async handleEditSubmit() {
      try {
        const valid = await this.$refs.editForm.validate()
        if (!valid) return

        this.editLoading = true
        const objId = this.node.data.bk_obj_id
        const instId = this.node.data.bk_inst_id

        // 收集变更的字段
        const data = {}
        for (const property of this.editableProperties) {
          const field = property.bk_property_id
          const value = this.editForm[field]
          // 简化处理：始终提交可编辑字段
          data[field] = value
        }

        // 模块节点：服务分类（二级分类 id 作为 service_category_id）单独计入更新。
        // 注意：null/空（用户清空但未选）时**不提交该字段**，由后端沿用原值，
        // 避免把分类误覆盖为 0（悬空引用）。仅当用户实际选中了某个二级分类才写入。
        if (this.isModuleNode && this.editSecondClass) {
          data.service_category_id = Number(this.editSecondClass)
        }

        await modelAPI.updateInstance(objId, instId, data)

        this.$bkMessage({
          theme: 'success',
          message: '修改成功'
        })

        this.isEditing = false
        this.editForm = {}

        // 重新加载数据
        await this.loadData()

        // 通知父组件刷新拓扑树（父组件会通过 initTopology 重新拉取拓扑，
        // 树节点标签自动同步为服务端的新名称）。
        // 注意：node 为只读 prop（bk-big-tree 节点对象，data 已被冻结），
        // 不可在此直接修改其属性，否则会抛出 Attempted to assign to readonly property。
        this.$emit('updated', this.node)
      } catch (error) {
        console.error('[NodeInfo] 更新失败:', error)
        this.$handleApiError(error)
      } finally {
        this.editLoading = false
      }
    },

    handleDelete() {
      const name = this.instanceData[this.getNameField()] || this.node.data.bk_inst_name
      this.$bkInfo({
        title: `确定删除「${name}」？`,
        subTitle: '删除后不可恢复，请谨慎操作',
        confirmFn: async () => {
          try {
            const objId = this.node.data.bk_obj_id
            const instId = this.node.data.bk_inst_id

            // biz/set/module 及自定义主线层统一走拓扑删除接口，
            // 复用后端 delete_node 的「内置业务禁删 + 非空闲机池子节点禁删 +
            // 含主机禁删 + 级联删下游 + 关联引用校验」
            const bizId = this.node.data.bk_biz_id
            await topoAPI.deleteNode(objId, instId, { bk_biz_id: bizId })

            this.$bkMessage({
              theme: 'success',
              message: '删除成功'
            })

            this.$emit('deleted', this.node)
          } catch (error) {
            console.error('[NodeInfo] 删除失败:', error)
            this.$handleApiError(error)
          }
        }
      })
    },

    getNameField() {
      const map = {
        'biz': 'bk_biz_name',
        'set': 'bk_set_name',
        'module': 'bk_module_name'
      }
      return map[this.node.data.bk_obj_id] || 'bk_inst_name'
    }
  }
}
</script>

<style lang="scss" scoped>
.node-info-layout {
  height: 100%;
  width: 100%;
  box-sizing: border-box;
}

.empty-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #c4c6cc;
  font-size: 14px;
}

/* 模块节点服务分类展示块（基础信息属性组之上，对齐原项目 node-extra-info） */
.service-category-extra {
  display: flex;
  align-items: center;
  padding: 16px 0 8px;
  margin: 0 0 8px;
  font-size: 14px;
  line-height: 26px;
  border-bottom: 1px solid #f0f1f5;

  .sc-label {
    /* 与下方基础信息 .property-name 完全一致：140px 列宽 + 文字右贴冒号，
       使「服务分类 → 冒号 → 值」间距与基础信息各属性一致（标签宽度收窄、无多余空隙）；
       值文本从 140px 起，垂直对齐基础信息属性值文本，而非分组折叠 icon */
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

  .sc-value {
    color: #313238;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

/* 编辑态服务分类选择器（置于通用字段之上）
   结构与模块名称属性一致：标签在上、控件在下（原项目 form-service-category .title 独占一行） */
.service-category-edit {
  padding: 0 24px 12px;

  .sc-edit-label {
    /* 与 .bk-form-item .bk-label 完全一致：标签在上、左对齐、无多余间距 */
    display: block;
    font-size: 14px;
    color: #63656e;
    text-align: left;
    line-height: 24px;
    margin: 2px 0 6px;
  }

  .sc-edit-selects {
    /* 两个选择器合并宽度 = 模块名称 input 宽度（单列宽），与原项目 form-service-category 一致 */
    display: flex;
    align-items: center;
    width: calc(50% - 27px);
    max-width: 554px;
  }

  .sc-edit-select {
    flex: 1;
    min-width: 0;

    & + .sc-edit-select {
      /* 两个选择器间距，与原项目 .category-selector + .category-selector 一致 */
      margin-left: 10px;
    }
  }
}

.placeholder-text {
  font-size: 16px;
  color: #c4c6cc;
  margin-bottom: 8px;
}

.placeholder-desc {
  font-size: 13px;
  color: #c4c6cc;
}

.error-state {
  color: #ff4d4f;
  padding: 20px;
  text-align: center;
}

/* 内联编辑面板：无弹出框，与原项目 cmdb-form 两栏布局一致（标签在上、控件在下） */
.inline-edit-panel {
  height: 100%;
  padding: 24px 0 0;
  overflow-y: auto;
  box-sizing: border-box;

  /* 与原项目 .form-groups / .property-list 一致：两栏 + 54px 列间距 */
  ::v-deep .bk-form {
    display: flex;
    flex-wrap: wrap;
    gap: 0 54px;
    padding: 0 24px;
  }

  /* 与原项目 .property-item 一致：每栏 50% 减去半列间距 */
  ::v-deep .bk-form-item {
    display: flex;
    flex-direction: column;
    flex: 0 0 calc(50% - 27px);
    width: calc(50% - 27px);
    max-width: 50%;
    margin: 12px 0 0;

    /* 覆盖 bk-magic-vue 默认 label 左浮动，改为标签在上 */
    .bk-label {
      float: none;
      width: auto !important;
      text-align: left;
      margin: 2px 0 6px;
      line-height: 24px;

      .bk-label-text {
        font-size: 14px;
        color: #63656e;
      }
    }

    /* 覆盖 bk-magic-vue 默认 content 左浮动，使控件拉伸填满整栏 */
    .bk-form-content {
      float: none;
      margin-left: 0 !important;
      display: flex;
      min-height: 32px;

      > * {
        flex: 1;
      }
    }
  }

  .inline-edit-actions {
    padding: 10px 24px;
    text-align: right;
    border-top: 1px solid #dcdee5;
    margin-top: 12px;

    .bk-button {
      min-width: 76px;
      margin-left: 8px;
    }
  }
}
</style>
