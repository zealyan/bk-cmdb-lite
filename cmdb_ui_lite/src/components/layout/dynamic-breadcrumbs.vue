<template>
  <div class="breadcrumbs-layout clearfix">
    <i class="icon icon-cc-arrow fl" v-if="from" @click="handleClick"></i>
    <h1 class="current fl" v-bk-overflow-tips>{{ current }}</h1>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
  name: 'DynamicBreadcrumbs',
  computed: {
    ...mapGetters(['title']),
    current() {
      const menuI18n = this.$route.meta?.menu?.i18n
      return this.title || this.$route.meta?.title || menuI18n || ''
    },
    from() {
      const menu = this.$route.meta?.menu || {}
      if (menu.relative) {
        return { name: Array.isArray(menu.relative) ? menu.relative[0] : menu.relative }
      }
      return null
    }
  },
  methods: {
    handleClick() {
      if (this.from) {
        this.$router.push(this.from)
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.breadcrumbs-layout {
  display: flex;
  align-items: center;
  padding: 14px 20px;
  height: 53px;
  background: #fff;
  box-shadow: 0px 2px 4px 0px rgba(0, 0, 0, 0.06);

  .icon-cc-arrow {
    display: block;
    width: 24px;
    height: 24px;
    line-height: 24px;
    font-size: 14px;
    text-align: center;
    margin-right: 3px;
    color: $primaryColor;
    cursor: pointer;

    &:hover {
      color: #699df4;
    }
  }

  .current {
    font-size: 16px;
    line-height: 24px;
    color: #313238;
    font-weight: normal;
    margin: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .fl {
    float: left;
  }

  .clearfix::after {
    content: '';
    display: table;
    clear: both;
  }
}
</style>
