import CmdbForm from './form.vue'
import CmdbFormSinglechar from './singlechar.vue'
import CmdbFormLongchar from './longchar.vue'
import CmdbFormInt from './int.vue'
import CmdbFormFloat from './float.vue'
import CmdbFormBool from './bool.vue'
import CmdbFormEnum from './enum.vue'
import CmdbFormEnummulti from './enummulti.vue'
import CmdbFormDate from './date.vue'
import CmdbFormTime from './time.vue'
import CmdbFormDatetime from './datetime.vue'
import CmdbFormTimezone from './timezone.vue'
import CmdbFormList from './list.vue'
import CmdbFormUser from './user.vue'

export {
  CmdbForm,
  CmdbFormSinglechar,
  CmdbFormLongchar,
  CmdbFormInt,
  CmdbFormFloat,
  CmdbFormBool,
  CmdbFormEnum,
  CmdbFormEnummulti,
  CmdbFormDate,
  CmdbFormTime,
  CmdbFormDatetime,
  CmdbFormTimezone,
  CmdbFormList,
  CmdbFormUser
}

export default {
  install(Vue) {
    Vue.component('cmdb-form', CmdbForm)
    Vue.component('cmdb-form-singlechar', CmdbFormSinglechar)
    Vue.component('cmdb-form-longchar', CmdbFormLongchar)
    Vue.component('cmdb-form-int', CmdbFormInt)
    Vue.component('cmdb-form-float', CmdbFormFloat)
    Vue.component('cmdb-form-bool', CmdbFormBool)
    Vue.component('cmdb-form-enum', CmdbFormEnum)
    Vue.component('cmdb-form-enummulti', CmdbFormEnummulti)
    Vue.component('cmdb-form-date', CmdbFormDate)
    Vue.component('cmdb-form-time', CmdbFormTime)
    Vue.component('cmdb-form-datetime', CmdbFormDatetime)
    Vue.component('cmdb-form-timezone', CmdbFormTimezone)
    Vue.component('cmdb-form-list', CmdbFormList)
    Vue.component('cmdb-form-user', CmdbFormUser)
  }
}
