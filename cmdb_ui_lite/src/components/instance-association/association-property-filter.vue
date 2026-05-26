<template>
  <div class="property-filter">
    <bk-select class="property-selector"
      v-model="localSelected.id"
      :clearable="false"
      transfer
      @selected="handlePropertySelected">
      <bk-option
        v-for="property in filteredProperties"
        :key="property.bk_property_id"
        :id="property.bk_property_id"
        :name="property.bk_property_name">
      </bk-option>
    </bk-select>
    <bk-select class="operator-selector"
      v-model="localSelected.operator"
      :clearable="false"
      transfer
      @selected="handleOperatorSelected">
      <bk-option
        v-for="op in operatorOptions"
        :key="op.value"
        :id="op.value"
        :name="op.label">
      </bk-option>
    </bk-select>
    <div class="property-value"
      v-if="Object.keys(selectedProperty).length">
      <component
        class="search-form-el"
        :is="getSearchComponent(selectedProperty.bk_property_type)"
        :options="selectedProperty.option || []"
        :placeholder="'请输入关键字'"
        :property="selectedProperty"
        v-model="localSelected.value">
      </component>
    </div>
  </div>
</template>

<script>
import { modelAPI } from '@/api/client'
import SinglecharSearch from '@/components/search/singlechar.vue'
import IntSearch from '@/components/search/int.vue'
import BoolSearch from '@/components/search/bool.vue'
import EnumSearch from '@/components/search/enum.vue'
import ListSearch from '@/components/search/list.vue'
import LongcharSearch from '@/components/search/longchar.vue'
import FloatSearch from '@/components/search/float.vue'
import DateSearch from '@/components/search/date.vue'
import TimeSearch from '@/components/search/time.vue'
import TimezoneSearch from '@/components/search/timezone.vue'
import ObjuserSearch from '@/components/search/objuser.vue'

export default {
  name: 'AssociationPropertyFilter',
  components: {
    SinglecharSearch,
    IntSearch,
    BoolSearch,
    EnumSearch,
    ListSearch,
    LongcharSearch,
    FloatSearch,
    DateSearch,
    TimeSearch,
    TimezoneSearch,
    ObjuserSearch
  },
  props: {
    objId: {
      type: String,
      required: true
    },
    excludeType: {
      type: Array,
      default() {
        return []
      }
    },
    excludeId: {
      type: Array,
      default() {
        return []
      }
    }
  },
  data() {
    return {
      localSelected: {
        id: '',
        operator: '$eq',
        value: ''
      },
      properties: [],
      filteredProperties: [],
      propertyOperator: {
        default: ['$eq', '$ne'],
        singlechar: ['$regex', '$eq', '$ne'],
        longchar: ['$regex', '$eq', '$ne'],
        int: ['$eq', '$ne', '$gt', '$gte', '$lt', '$lte'],
        float: ['$eq', '$ne', '$gt', '$gte', '$lt', '$lte'],
        objuser: ['$in', '$nin'],
        list: ['$in', '$nin'],
        timezone: ['$in', '$nin'],
        enummulti: ['$in', '$nin'],
        organization: ['$in', '$nin'],
        bool: ['$eq'],
        date: ['$eq', '$ne', '$gt', '$gte', '$lt', '$lte'],
        time: ['$eq', '$ne', '$gt', '$gte', '$lt', '$lte']
      },
      operatorLabel: {
        '$nin': '不包含',
        '$in': '包含',
        '$regex': '包含',
        '$eq': '等于',
        '$ne': '不等于',
        '$gt': '大于',
        '$gte': '大于等于',
        '$lt': '小于',
        '$lte': '小于等于'
      },
      searchComponentMap: {
        singlechar: 'cmdb-search-singlechar',
        longchar: 'cmdb-search-longchar',
        int: 'cmdb-search-int',
        float: 'cmdb-search-float',
        enum: 'cmdb-search-enum',
        enummulti: 'cmdb-search-enum',
        list: 'cmdb-search-list',
        bool: 'cmdb-search-bool',
        date: 'cmdb-search-date',
        time: 'cmdb-search-time',
        timezone: 'cmdb-search-timezone',
        objuser: 'cmdb-search-objuser'
      }
    }
  },
  computed: {
    selectedProperty() {
      return this.filteredProperties.find(({ bk_property_id }) => bk_property_id === this.localSelected.id) || {}
    },
    operatorOptions() {
      if (this.selectedProperty) {
        const propertyType = this.selectedProperty.bk_property_type || 'default'
        const propertyOperator = this.propertyOperator[propertyType] || this.propertyOperator.default
        return propertyOperator.map(operator => ({
          label: this.operatorLabel[operator] || operator,
          value: operator
        }))
      }
      return []
    }
  },
  watch: {
    'localSelected.id'(id) {
      this.localSelected.value = ''
    },
    'localSelected.value'(value) {
      this.$emit('on-value-change', value)
    },
    objId(newVal, oldVal) {
      if (newVal && newVal !== '' && newVal !== oldVal) {
        this.filteredProperties = []
        this.localSelected = {
          id: '',
          operator: '$eq',
          value: ''
        }
        this.loadProperties()
      }
    }
  },
  async mounted() {
    if (this.objId) {
      await this.loadProperties()
    }
  },
  async updated() {
    if (this.objId && this.objId !== '' && this.filteredProperties.length === 0) {
      await this.loadProperties()
    }
  },
  methods: {
    async loadProperties() {
      if (!this.objId || this.objId === '') {
        console.warn('[AssociationPropertyFilter] objId is not set, skipping loadProperties')
        return
      }
      try {
        const response = await modelAPI.getModelAttributes(this.objId)
        // 处理 API 返回格式 {attributes: [...]} 或直接的数组
        const properties = response.attributes || response || []
        this.properties = Array.isArray(properties) ? properties : []
        console.log('[AssociationPropertyFilter] Loaded', this.properties.length, 'properties for', this.objId)
        this.filteredProperties = this.properties.filter((property) => {
          const {
            bk_isapi: bkIsapi,
            bk_property_type: bkPropertyType,
            bk_property_id: bkPropertyId
          } = property
          return !bkIsapi && !this.excludeType.includes(bkPropertyType) && !this.excludeId.includes(bkPropertyId)
        })
        if (this.filteredProperties.length) {
          this.localSelected.id = this.filteredProperties[0].bk_property_id
          this.$emit('on-property-selected', this.filteredProperties[0].bk_property_id, this.filteredProperties[0])
        }
      } catch (err) {
        console.error('加载模型属性失败', err)
      }
    },
    handlePropertySelected(value, data) {
      this.$emit('on-property-selected', value, data)
    },
    handleOperatorSelected(value) {
      this.$emit('on-operator-selected', value)
    },
    clearFilter() {
      this.localSelected.value = ''
    },
    getSearchComponent(propertyType) {
      const componentName = this.searchComponentMap[propertyType] || 'cmdb-search-singlechar'
      console.log('[AssociationPropertyFilter] getSearchComponent:', propertyType, '->', componentName)
      return componentName
    }
  }
}
</script>

<style lang="scss" scoped>
.property-filter {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  
  .property-selector {
    flex: 1;
    min-width: 120px;
  }
  
  .operator-selector {
    flex: 1;
    min-width: 100px;
  }
  
  .property-value {
    flex: 2;
    min-width: 150px;
    position: relative;
    display: flex;
    align-items: center;
    
    .search-form-el {
      width: 100%;
    }
  }
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .property-filter {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    
    .property-selector,
    .operator-selector,
    .property-value {
      width: 100%;
      min-width: auto;
    }
  }
}
</style>
