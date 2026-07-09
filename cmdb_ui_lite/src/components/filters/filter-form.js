import Vue from 'vue'
import FilterForm from './filter-form.vue'
import FilterStore from './store'

export default {
  show(props = {}) {
    const exist = FilterStore.getComponent('FilterForm')
    if (exist) {
      exist.$refs.FilterForm.open()
      return exist
    }

    const vm = new Vue({
      created() {
        FilterStore.setComponent('FilterForm', this)
      },
      beforeDestroy() {
        FilterStore.setComponent('FilterForm', null)
      },
      render(h) {
        return h(FilterForm, {
          ref: 'FilterForm',
          props,
          on: {
            closed: () => {
              this.$el && this.$el.parentElement && this.$el.parentElement.removeChild(this.$el)
              this.$destroy()
            }
          }
        })
      }
    })

    vm.$mount()
    document.body.appendChild(vm.$el)
    vm.$refs.FilterForm.open()

    if (vm.$router) {
      const unwatch = vm.$watch('$route', () => {
        vm.$refs.FilterForm.close()
        unwatch()
      })
    }

    return vm
  }
}