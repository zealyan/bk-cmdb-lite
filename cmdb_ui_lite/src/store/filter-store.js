import Vue from 'vue'

const FilterStore = new Vue({
  data() {
    return {
      properties: [],
      selected: [],
      condition: {}
    }
  },
  computed: {
    hasCondition() {
      const has = this.selected.some(property => {
        const value = this.condition[property.id]?.value
        return value !== null && value !== undefined && !!String(value).length
      })
      console.log('[DEBUG] FilterStore hasCondition computed', has)
      return has
    }
  },
  watch: {
    selected(newVal) {
      console.log('[DEBUG] FilterStore selected watch', newVal.length, newVal.map(p => p.bk_property_name))
      this.initCondition()
    }
  },
  methods: {
    initCondition() {
      console.log('[DEBUG] FilterStore initCondition')
      const newCondition = {}
      this.selected.forEach((property) => {
        if (this.condition[property.id]) {
          newCondition[property.id] = this.condition[property.id]
        } else {
          newCondition[property.id] = {
            operator: '$eq',
            value: ''
          }
        }
      })
      this.condition = newCondition
      console.log('[DEBUG] FilterStore initCondition done', Object.keys(newCondition).length)
    },
    setProperties(properties) {
      console.log('[DEBUG] FilterStore setProperties', properties.length)
      this.properties = properties
    },
    updateSelected(selected) {
      console.log('[DEBUG] FilterStore updateSelected', selected.length, selected.map(p => p.bk_property_name))
      this.selected = selected
    },
    updateCondition(propertyId, operator, value) {
      console.log('[DEBUG] FilterStore updateCondition', { propertyId, operator, value })
      this.condition[propertyId] = { operator, value }
    },
    removeSelected(propertyId) {
      console.log('[DEBUG] FilterStore removeSelected', propertyId)
      const index = this.selected.findIndex(p => p.bk_property_id === propertyId)
      if (index > -1) {
        this.selected.splice(index, 1)
      }
    },
    resetAll() {
      console.log('[DEBUG] FilterStore resetAll')
      this.selected = []
      this.condition = {}
    }
  }
})

export default FilterStore