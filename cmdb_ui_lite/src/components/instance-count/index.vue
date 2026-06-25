<template>
  <span class="instance-count">
    <template v-if="loading">
      <span class="count-loading">--</span>
    </template>
    <template v-else>
      <span class="count-value">{{ count }}</span>
    </template>
  </span>
</template>

<script>
export default {
  name: 'InstanceCount',
  props: {
    objId: {
      type: String,
      required: true
    },
    counts: {
      type: Array,
      default: () => []
    }
  },
  computed: {
    instanceData() {
      return this.counts.find(item => item.bk_obj_id === this.objId)
    },
    loading() {
      return !this.instanceData
    },
    count() {
      if (this.instanceData?.error) {
        return '--'
      }
      return this.instanceData?.inst_count || 0
    }
  }
}
</script>

<style lang="scss" scoped>
.instance-count {
  display: inline-block;
  width: 35px;
  font-size: 14px;
  height: 24px;
  line-height: 24px;
  color: #C4C6CC;
  text-align: right;
}

.count-loading {
  color: #C4C6CC;
}

.count-value {
  color: #979ba5;
}
</style>