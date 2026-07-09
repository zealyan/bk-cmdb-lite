export default function useSideslider(data, options = {}) {
  const isChanged = { value: false }
  const { watchOnce = true } = options

  const defaultInfoData = {
    subTitle: '离开将会导致未保存信息丢失',
    title: '确认离开当前页？',
    okText: '离开',
    cancelText: '取消'
  }
  let infoData = JSON.parse(JSON.stringify(defaultInfoData))

  if (data) {
    setTimeout(() => {
      let hasWatched = false
      const originalValue = JSON.stringify(data)
      const checkChanged = () => {
        if (hasWatched && watchOnce) return
        const currentValue = JSON.stringify(data)
        if (currentValue !== originalValue) {
          isChanged.value = true
          hasWatched = true
        }
      }
      const observer = new MutationObserver(checkChanged)
      if (Array.isArray(data)) {
        const proxyData = new Proxy(data, {
          set(target, prop, value) {
            target[prop] = value
            checkChanged()
            return true
          }
        })
        Object.assign(data, proxyData)
      }
    }, 300)
  }

  const beforeClose = (confirmCallback, cancelCallback) => new Promise((resolve, reject) => {
    if (!isChanged.value) {
      confirmCallback && confirmCallback()
      resolve(true)
      return
    }
    const { subTitle, title, okText, cancelText } = infoData
    window.$bkInfo({
      title,
      subTitle,
      clsName: 'custom-info-confirm default-info',
      okText,
      cancelText,
      confirmFn() {
        confirmCallback && confirmCallback()
        resolve(true)
      },
      cancelFn() {
        cancelCallback && cancelCallback()
        reject(false)
      }
    })
  })

  const reset = () => {
    setTimeout(() => {
      isChanged.value = false
    })
  }

  const setChanged = (v) => {
    isChanged.value = v
  }

  const setInfoData = (data = {}) => {
    infoData = Object.assign({}, JSON.parse(JSON.stringify(defaultInfoData)), data)
  }

  return {
    beforeClose,
    isChanged,
    reset,
    setChanged,
    setInfoData
  }
}