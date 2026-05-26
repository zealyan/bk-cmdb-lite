import Vue from 'vue'
import InstanceDetailsSlider from '../../instance-details/InstanceDetailsSlider.vue'

let detailsInstance = null

export default function (options) {
  if (!detailsInstance) {
    const Constructor = Vue.extend(InstanceDetailsSlider)
    const el = document.createElement('div')
    document.body.appendChild(el)
    detailsInstance = new Constructor({
      el
    })
  }

  detailsInstance.show(options)

  return detailsInstance
}
