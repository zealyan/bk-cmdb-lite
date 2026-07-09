import Vue from 'vue'
import ColumnsConfig from './index.vue'

export default {
  open({ props, handler }) {
    const vm = new Vue({
      render(h) {
        return h(ColumnsConfig, {
          props: {
            ...props
          },
          on: {
            apply: (properties) => {
              handler?.apply?.(properties)
              this.$el.parentElement.removeChild(this.$el)
              this.$destroy()
            },
            reset: () => {
              handler?.reset?.()
              this.$el.parentElement.removeChild(this.$el)
              this.$destroy()
            },
            cancel: () => {
              this.$el.parentElement.removeChild(this.$el)
              this.$destroy()
            }
          }
        })
      }
    })

    vm.$mount()
    document.body.appendChild(vm.$el)
    return vm
  }
}