<template>
  <div class="breadcrumbs-layout clearfix">
    <template v-if="customize.enable">
      <i class="icon icon-cc-arrow fl" v-if="customize.backward" @click="customize.backward"></i>
      <h1 class="current fl" v-bk-overflow-tips>{{ customize.title }}</h1>
    </template>
    <template v-else>
      <i class="icon icon-cc-arrow fl" v-if="from" @click="handleClick"></i>
      <h1 class="current fl" v-bk-overflow-tips>{{ current }}</h1>
    </template>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
  name: 'DynamicBreadcrumbs',
  computed: {
    ...mapGetters(['title', 'breadcrumbs']),
    customize() {
      return this.breadcrumbs
    },
    current() {
      if (this.breadcrumbs.enable) {
        return this.breadcrumbs.title
      }
      const menuI18n = this.$route.meta?.menu?.i18n
      return this.title || this.$route.meta?.title || menuI18n || ''
    },
    defaultFrom() {
      const menu = this.$route.meta?.menu || {}
      if (menu.relative) {
        const relative = Array.isArray(menu.relative) ? menu.relative[0] : menu.relative
        if (typeof relative === 'string') {
          return { name: relative }
        }
        return relative
      }
      return null
    },
    from() {
      return this.defaultFrom
    }
  },
  watch: {
    $route(newRoute, oldRoute) {
      if (newRoute.name !== oldRoute.name ||
          JSON.stringify(newRoute.params) !== JSON.stringify(oldRoute.params)) {
        this.$store.commit('setCustomBreadcrumbs', { enable: false })
        this.$store.commit('setTitle', '')
      }
    }
  },
  methods: {
    handleClick() {
      if (this.breadcrumbs.enable && this.breadcrumbs.backward) {
        this.breadcrumbs.backward()
      } else if (this.from) {
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
