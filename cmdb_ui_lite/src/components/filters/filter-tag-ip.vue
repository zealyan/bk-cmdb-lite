<template>
  <span class="filter-tag" @click="handleClick">
    <label class="tag-name">{{label}}</label>
    <span class="tag-colon">:</span>
    <span class="tag-value">{{displayText}}</span>
    <i class="tag-delete bk-icon icon-close" @mouseenter.prevent.stop @click.stop="handleRemove"></i>
  </span>
</template>

<script>
import FilterStore from './store'
import Utils from './utils'
import FilterForm from './filter-form.js'

export default {
  name: 'FilterTagIp',
  computed: {
    label() {
      const { inner, outer, exact } = FilterStore.IP
      const labels = []
      inner && labels.push('内网IP')
      outer && labels.push('外网IP')
      exact && labels.push('精确')
      return labels.join(' | ')
    },
    value() {
      return Utils.splitIP(FilterStore.IP.text)
    },
    displayText() {
      const count = this.value.length
      const [firstIp] = this.value
      if (count > 2) {
        return `${firstIp}...等${count}个IP`
      }
      return this.value.join(' | ')
    }
  },
  methods: {
    handleClick() {
      FilterForm.show()
    },
    handleRemove() {
      FilterStore.updateIP(Utils.getDefaultIP())
      FilterStore.dispatchSearch()
    }
  }
}
</script>

<style lang="scss" scoped>
.filter-tag {
  display: inline-flex;
  align-items: center;
  margin: 0 3px 10px;
  padding: 0 0 0 5px;
  border-radius: 2px;
  font-size: 12px;
  background: #f0f1f5;
  line-height: 22px;
  cursor: pointer;

  &:hover {
    background-color: #DCDEE5;
  }

  .tag-name {
    max-width: 150px;
    padding-right: 5px;
    color: #63656E;
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tag-colon {
    padding-right: 5px;
  }

  .tag-value {
    max-width: 255px;
    color: #313238;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tag-delete {
    font-size: 20px;
    color: #9b9ea8;

    &:hover {
      color: #313238;
    }
  }
}
</style>