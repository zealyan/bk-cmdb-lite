export const getConditionSelect = (val, oldVal) => {
  const addSelect = []
  const deleteSelect = []

  if (!oldVal || !val) {
    return { addSelect: val || [], deleteSelect: oldVal || [] }
  }

  val.forEach(item => {
    const index = oldVal.findIndex(oldItem => oldItem.bk_property_id === item.bk_property_id)
    if (index === -1) {
      addSelect.push(item)
    }
  })

  oldVal.forEach(item => {
    const index = val.findIndex(newItem => newItem.bk_property_id === item.bk_property_id)
    if (index === -1) {
      deleteSelect.push(item)
    }
  })

  return { addSelect, deleteSelect }
}

export const updatePropertySelect = (selected, handleRemove, addSelect, deleteSelect, action, filterCondition = []) => {
  deleteSelect.forEach(item => {
    const index = selected.indexOf(item)
    if (index > -1) {
      selected.splice(index, 1)
    }
  })

  addSelect.forEach(item => {
    if (action === 'push') {
      const isInFilter = filterCondition.includes(item.bk_property_id)
      if (!isInFilter && !selected.includes(item)) {
        selected.push(item)
      }
    }
  })
}

export const isPasteSplit = (id) => {
  return ['bk_host_innerip', 'bk_host_outerip', 'bk_host_innerip_v6', 'bk_host_outerip_v6'].includes(id)
}