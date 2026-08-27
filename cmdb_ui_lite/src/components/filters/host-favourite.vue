<template>
  <bk-select class="host-favourite"
    ref="selector"
    searchable
    :popover-width="220"
    font-size="normal"
    v-bk-tooltips="'已收藏的条件'"
    @click.native="loadFavourites">
    <icon-button slot="trigger"
      class="fav-trigger"
      icon="icon-cc-star"
      :class="{ 'is-selected': !!activeFav }"
      @click="loadFavourites">
    </icon-button>
    <bk-option v-for="fav in favourites"
      :key="fav.id"
      :id="fav.id"
      :name="fav.name"
      @click.native="handleApply(fav)">
      <div class="fav-item">
        <i class="fav-state bk-icon icon-check-1" v-if="activeFav && activeFav.id === fav.id"></i>
        <span class="fav-name">{{fav.name}}</span>
        <span class="fav-options">
          <i class="option-icon option-delete bk-icon icon-close" @click.stop="handleRemove(fav)"></i>
        </span>
      </div>
    </bk-option>
    <div class="business-extension" slot="extension">
      <a href="javascript:void(0)" class="extension-link" @click="handleCreate">
        <i class="bk-icon icon-plus-circle"></i>
        新增收藏条件
      </a>
    </div>
  </bk-select>
</template>

<script>
import IconButton from '@/components/ui/button/icon-button.vue'
// FilterStore 全局单例：condition / selected / bk_biz_id 等筛选状态单一数据源。
// 业务拓扑主机列表已 watch FilterStore 自动重载，因此本组件直接操作 FilterStore
// 即可驱动列表更新，无需反向接线 host-list.vue。
import FilterStore from '@/components/filters/store'
import favourite from '@/api/favourite'

// 业务拓扑主机列表「已收藏的条件」（HostFavourite）：
//  - 数据落在服务端 cc_HostFavourite，按 user / 租户 / 业务三层隔离（与上游 FavouriteMeta 一致）。
//  - 与通用模型视图的「收藏此条件」（user_custom.filter_collection）是两套独立机制：
//    上游业务拓扑主机列表的「已收藏条件」本就是 HostFavourite，而非 user_custom。
export default {
  name: 'HostFavourite',
  components: {
    IconButton
  },
  data() {
    return {
      favourites: [],
      activeFav: null,
      favToken: 0 // 收藏列表加载代际：每次拉取自增，仅最新请求的结果生效（防竞态覆盖）
               // 注意：不能用 _favToken —— Vue2 不会把 _/$ 前缀的 data 属性代理到实例，
               // 会导致 this.favToken 恒为 undefined，++undefined=NaN，使竞态判断永远成立。
    }
  },
  computed: {
    // 当前业务 ID（host-list.vue 经 setupFilterStore 注入 FilterStore.bk_biz_id）
    bizId() {
      return FilterStore.bk_biz_id || 0
    }
  },
  created() {
    // 进入即预加载当前业务的收藏列表，避免「先展开下拉 → 再异步拉取 → 选项未渲染」
    // 造成的「列表为空」假象。父级 initFilterStore 为异步 fire-and-forget，组件挂载时
    // FilterStore.bk_biz_id 可能仍为 0；下面的 watch 会在其被注入真实业务 ID 后自动重拉。
    this.loadFavourites(false)
    // 业务切换（FilterStore.bk_biz_id 变化，如从 #/business/2 跳到 #/business/3）时重新拉取，
    // 保证收藏列表始终归属当前业务。
    if (FilterStore && typeof FilterStore.$watch === 'function') {
      this._unwatchBiz = FilterStore.$watch('bk_biz_id', () => this.loadFavourites(false))
    }
  },
  beforeDestroy() {
    if (this._unwatchBiz) {
      this._unwatchBiz()
      this._unwatchBiz = null
    }
  },
  methods: {
    /**
     * 拉取当前业务的收藏列表。
     * @param {boolean} showDropdown 拉取完成后是否展开下拉（仅用户主动点击时才为 true，
     *                               进入预加载/业务切换时不展开，避免页面加载即弹窗）。
     */
    /**
     * 拉取当前业务的收藏列表（仅在展开「已收藏」下拉时触发）。
     * 采用「代际 token」去重：同一时刻只认最新一次请求的结果，过期的在途请求直接丢弃，
     * 防止「星标点击触发的旧请求」与「创建后拉取」并发时把含新项的列表覆盖为旧列表
     * （对齐上游 createCollection 不重拉、仅本地 unshift 的语义）。
     */
    async loadFavourites(showDropdown = true) {
      const token = ++this.favToken
      try {
        const list = await favourite.listFavourites(this.bizId)
        if (token !== this.favToken) return // 过期请求，丢弃
        this.favourites = list
      } catch (e) {
        console.error('[HostFavourite] 加载收藏失败', e)
        if (token === this.favToken) this.favourites = []
      }
      if (showDropdown && token === this.favToken) {
        this.$nextTick(() => {
          this.$refs.selector && this.$refs.selector.show && this.$refs.selector.show()
        })
      }
    },
    /**
     * 把收藏项的 query_params（JSON 字符串）解析为 FilterStore.condition 结构
     * { [propertyId]: { operator, value } }
     */
    parseConditions(fav) {
      if (!fav || !fav.query_params) return {}
      try {
        const parsed = JSON.parse(fav.query_params)
        return (parsed && typeof parsed === 'object') ? parsed : {}
      } catch (e) {
        console.error('[HostFavourite] query_params 解析失败', e)
        return {}
      }
    },
    /**
     * 应用收藏（非 toggle）：复用 FilterStore.setActiveCollection 把 conditions 还原到
     * selected/condition 并触发列表重载（host-list 的 watch 会响应）；filter tag 随之增加、
     * 高级筛选抽屉（storageSelected/watch）与其他条件状态同步刷新。
     */
    applyFav(fav) {
      const conditions = this.parseConditions(fav)
      const IP = this.parseIP(fav)
      // 对齐上游：收藏条件含独立 IP 维度（info 字段），应用时一并还原到 FilterStore，
      // 使 filter-tag-ip 标签出现、高级筛选抽屉 IP 输入同步、列表按 IP 过滤。
      FilterStore.setActiveCollection({ id: fav.id, name: fav.name, conditions, IP })
      this.activeFav = fav
      this.$emit('apply', fav)
    },
    /**
     * 解析收藏项的 info（JSON 字符串）为 IP 对象；空/非法返回 null。
     */
    parseIP(fav) {
      if (!fav || !fav.info) return null
      try {
        const parsed = JSON.parse(fav.info)
        return (parsed && typeof parsed === 'object') ? parsed : null
      } catch (e) {
        console.error('[HostFavourite] info(IP) 解析失败', e)
        return null
      }
    },
    /**
     * 选中 ↔ 取消选中（对齐上游 filter-collection 的 toggle 语义）：
     *  - 点击未激活的收藏 → 应用，把 conditions 同步回 selected/condition，filter tag 增加；
     *  - 再次点击已激活的收藏 → 取消选中，setActiveCollection(null) → resetAll()，
     *    清空全部筛选状态（含 IP）与 filter tag，其他条件状态同步归零。
     */
    handleApply(fav) {
      if (this.activeFav && this.activeFav.id === fav.id) {
        // 取消选中：清空筛选状态（移除全部 filter tag / IP）
        FilterStore.setActiveCollection(null)
        this.activeFav = null
        this.$emit('apply', null)
        return
      }
      this.applyFav(fav)
    },
    handleRemove(fav) {
      favourite.deleteFavourite(fav.id, this.bizId).then(() => {
        // 本地即时移除（对齐上游 removeCollection 的 splice）；并作废在途旧请求避免覆盖
        this.favourites = this.favourites.filter(f => f.id !== fav.id)
        this.favToken++
        if (this.activeFav && this.activeFav.id === fav.id) this.activeFav = null
      }).catch(e => console.error('[HostFavourite] 删除收藏失败', e))
    },
    async handleCreate() {
      // 对齐用户级说明的 host 场景缺口：需先设置筛选条件再收藏
      const hasCondition = Object.keys(FilterStore.condition || {}).length > 0
      if (!hasCondition) {
        window.alert('请先在「高级筛选」中设置条件，再收藏当前条件')
        return
      }
      const name = window.prompt('请输入收藏条件名称', '我的收藏条件')
      if (!name || !name.trim()) return

      // 从当前 selected/condition 派生 conditions（对齐 FilterStore.createCollection 语义）
      const conditions = {}
      ;(FilterStore.selected || []).forEach((property) => {
        const id = property.bk_property_id
        const cond = FilterStore.condition[id]
        if (cond) {
          conditions[id] = { operator: cond.operator, value: cond.value }
        }
      })

      const payload = {
        name: name.trim(),
        query_params: JSON.stringify(conditions),
        bk_biz_id: this.bizId,
        type: 'tradition',
        info: JSON.stringify(FilterStore.IP) // 对齐上游：IP 维度序列化进 info 字段
      }

      let created
      try {
        created = await favourite.createFavourite(payload)
      } catch (e) {
        console.error('[HostFavourite] 创建收藏失败', e)
        return
      }

      // 对齐上游 createCollection：提交落盘后，直接用服务端返回的收藏项 unshift 进本地列表，
      // 即时渲染（不依赖重拉）。并令在途的旧 loadFavourites（如星标点击触发）作废，避免覆盖新项。
      const fav = created || { id: Date.now(), name: payload.name, query_params: payload.query_params }
      this.favourites.unshift(fav)
      this.favToken++
      this.activeFav = fav
      this.$nextTick(() => {
        this.$refs.selector && this.$refs.selector.show && this.$refs.selector.show()
      })
      // 收藏即应用（对齐上游语义：收藏数据与条件状态同步）。
      // 注意：此处直接 applyFav，不能复用 handleApply —— 因为上面已把 activeFav 置为该 fav，
      // 复用 handleApply 会误判为「再次点击已激活收藏」而触发取消选中（toggle）。
      this.applyFav(fav)
    }
  }
}
</script>

<style lang="scss" scoped>
.host-favourite {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  width: 32px;
  height: 32px;
  overflow: hidden;

  &.is-disabled {
    cursor: pointer;
  }

  ::v-deep {
    .bk-tooltip-ref {
      display: flex !important;
      align-items: center;
      justify-content: center;
    }
  }
}

.fav-trigger {
  color: #63656e;

  &:hover,
  &.is-selected {
    color: $primaryColor;
  }

  ::v-deep {
    .icon-wrapper:before {
      font-size: 18px;
    }
  }
}

.fav-item {
  display: flex;
  align-items: center;
  padding: 0 16px;
  margin: 0 -16px;

  &:hover {
    .fav-options {
      display: initial;
    }
  }

  .fav-state {
    font-size: 24px;
    margin-left: -14px;

    & ~ .fav-name {
      margin-left: initial;
    }
  }

  .fav-name {
    margin-left: -6px;
    @include ellipsis;
  }

  .fav-options {
    display: none;
    margin-right: -10px;
    margin-left: auto;

    .option-icon {
      width: 24px;
      height: 24px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: $textColor;

      &:hover {
        color: $primaryColor;
      }
    }

    .option-icon.option-delete {
      font-size: 22px;
    }
  }
}

.extension-link {
  display: block;
  line-height: 38px;
  padding: 0 9px;
  font-size: 13px;
  color: #63656E;

  &:hover {
    opacity: .85;
  }

  .bk-icon {
    font-size: 18px;
    color: #979BA5;
    vertical-align: text-top;
  }
}
</style>
