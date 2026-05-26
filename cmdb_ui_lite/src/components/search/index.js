import EnumSearch from './enum.vue'
import ListSearch from './list.vue'
import SinglecharSearch from './singlechar.vue'
import IntSearch from './int.vue'
import BoolSearch from './bool.vue'
import LongcharSearch from './longchar.vue'
import FloatSearch from './float.vue'
import DateSearch from './date.vue'
import TimeSearch from './time.vue'
import TimezoneSearch from './timezone.vue'
import ObjuserSearch from './objuser.vue'

export default {
  install(Vue) {
    Vue.component('cmdb-search-enum', EnumSearch)
    Vue.component('cmdb-search-list', ListSearch)
    Vue.component('cmdb-search-singlechar', SinglecharSearch)
    Vue.component('cmdb-search-int', IntSearch)
    Vue.component('cmdb-search-bool', BoolSearch)
    Vue.component('cmdb-search-longchar', LongcharSearch)
    Vue.component('cmdb-search-float', FloatSearch)
    Vue.component('cmdb-search-date', DateSearch)
    Vue.component('cmdb-search-time', TimeSearch)
    Vue.component('cmdb-search-timezone', TimezoneSearch)
    Vue.component('cmdb-search-objuser', ObjuserSearch)
  }
}

export {
  EnumSearch,
  ListSearch,
  SinglecharSearch,
  IntSearch,
  BoolSearch,
  LongcharSearch,
  FloatSearch,
  DateSearch,
  TimeSearch,
  TimezoneSearch,
  ObjuserSearch
}
