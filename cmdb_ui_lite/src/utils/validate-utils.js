/**
 * 表单校验工具函数
 * 参考原项目: /workspace/bk-cmdb/src/ui/src/utils/tools.js getValidateRules
 * 
 * 支持的校验规则:
 * - int: 整数类型，支持 min/max 范围限制
 * - float: 浮点数类型，支持 min/max 范围限制
 * - singlechar/longchar: 字符串类型，支持正则校验
 * - enum/enummulti: 枚举类型
 */

/**
 * 解析属性的 option 字段
 * option 可能是字符串（JSON或正则表达式）或对象
 * @param {string|object} option - 属性选项
 * @returns {object|string|null} 解析后的选项对象或原字符串（用于正则表达式）
 */
export function parseOption(option) {
  if (!option) {
    return null
  }
  
  if (typeof option === 'string') {
    try {
      return JSON.parse(option)
    } catch (e) {
      // 如果不是有效的JSON，可能是正则表达式字符串，直接返回原字符串
      return option
    }
  }
  
  return option
}

/**
 * 获取属性的校验规则
 * 参考: /workspace/bk-cmdb/src/ui/src/utils/tools.js getValidateRules
 * @param {object} property - 属性对象
 * @returns {object} 校验规则对象
 */
export function getValidateRules(property) {
  const rules = {}
  
  if (!property) {
    return rules
  }
  
  const {
    bk_property_type: propertyType,
    option,
    isrequired,
    ismultiple
  } = property
  
  // 必填校验
  if (isrequired) {
    rules.required = true
  }
  
  const parsedOption = parseOption(option)
  
  // int/float 类型范围校验
  if (['int', 'float'].includes(propertyType) && parsedOption) {
    if (parsedOption.min !== undefined && parsedOption.min !== '' && parsedOption.min !== null) {
      rules.min_value = Number(parsedOption.min)
    }
    if (parsedOption.max !== undefined && parsedOption.max !== '' && parsedOption.max !== null) {
      rules.max_value = Number(parsedOption.max)
    }
  }
  
  // 字符串类型校验
  if (['singlechar', 'longchar'].includes(propertyType)) {
    rules[propertyType] = true
    rules.length = propertyType === 'singlechar' ? 256 : 2000
    
    // 正则校验
    if (parsedOption && typeof parsedOption === 'string') {
      rules.remoteString = parsedOption
    }
  }
  
  // 整数类型校验
  if (propertyType === 'int') {
    rules.number = true
  }
  
  // 浮点数类型校验
  if (propertyType === 'float') {
    rules.float = true
  }
  
  return rules
}

/**
 * 校验单个值
 * @param {any} value - 待校验的值
 * @param {object} property - 属性对象
 * @returns {object} { valid: boolean, message: string }
 */
export function validateValue(value, property) {
  if (!property) {
    return { valid: true, message: '' }
  }
  
  const {
    bk_property_type: propertyType,
    bk_property_name: propertyName,
    isrequired,
    option
  } = property
  
  const errors = []
  
  // 必填校验
  if (isrequired && (value === undefined || value === null || value === '')) {
    return {
      valid: false,
      message: `${propertyName}不能为空`
    }
  }
  
  // 如果值为空且非必填，则通过校验
  if (value === undefined || value === null || value === '') {
    return { valid: true, message: '' }
  }
  
  const parsedOption = parseOption(option)
  
  // int 类型校验
  if (propertyType === 'int') {
    const numValue = Number(value)
    
    // 检查是否为整数
    if (!Number.isInteger(numValue)) {
      errors.push('请输入整数')
    }
    
    // 范围校验
    if (parsedOption) {
      const min = parsedOption.min !== undefined && parsedOption.min !== '' ? Number(parsedOption.min) : null
      const max = parsedOption.max !== undefined && parsedOption.max !== '' ? Number(parsedOption.max) : null
      
      if (min !== null && numValue < min) {
        errors.push(`最小值为 ${min}`)
      }
      if (max !== null && numValue > max) {
        errors.push(`最大值为 ${max}`)
      }
    }
  }
  
  // float 类型校验
  if (propertyType === 'float') {
    const numValue = parseFloat(value)
    
    // 检查是否为有效数字
    if (isNaN(numValue)) {
      errors.push('请输入有效的数字')
    }
    
    // 范围校验
    if (parsedOption) {
      const min = parsedOption.min !== undefined && parsedOption.min !== '' ? Number(parsedOption.min) : null
      const max = parsedOption.max !== undefined && parsedOption.max !== '' ? Number(parsedOption.max) : null
      
      if (min !== null && numValue < min) {
        errors.push(`最小值为 ${min}`)
      }
      if (max !== null && numValue > max) {
        errors.push(`最大值为 ${max}`)
      }
    }
  }
  
  // 字符串类型校验
  if (['singlechar', 'longchar'].includes(propertyType)) {
    const strValue = String(value)
    const maxLen = propertyType === 'singlechar' ? 256 : 2000
    
    if (strValue.length > maxLen) {
      errors.push(`长度不能超过 ${maxLen} 个字符`)
    }
    
    // 正则校验
    if (parsedOption && typeof parsedOption === 'string') {
      try {
        const regex = new RegExp(parsedOption)
        if (!regex.test(strValue)) {
          errors.push('格式不正确')
        }
      } catch (e) {
        // 正则表达式无效，跳过校验
      }
    }
  }
  
  return {
    valid: errors.length === 0,
    message: errors[0] || ''
  }
}

/**
 * 获取属性的范围提示文本
 * @param {object} property - 属性对象
 * @returns {string} 范围提示文本
 */
export function getRangeHint(property) {
  if (!property) {
    return ''
  }
  
  const { bk_property_type: propertyType, option } = property
  
  if (!['int', 'float'].includes(propertyType)) {
    return ''
  }
  
  const parsedOption = parseOption(option)
  if (!parsedOption) {
    return ''
  }
  
  const min = parsedOption.min !== undefined && parsedOption.min !== '' ? Number(parsedOption.min) : null
  const max = parsedOption.max !== undefined && parsedOption.max !== '' ? Number(parsedOption.max) : null
  
  if (min !== null && max !== null) {
    return `范围: ${min} ~ ${max}`
  } else if (min !== null) {
    return `最小值: ${min}`
  } else if (max !== null) {
    return `最大值: ${max}`
  }
  
  return ''
}

/**
 * 获取校验规则对象（用于 vee-validate 或自定义校验）
 * @param {object} property - 属性对象
 * @returns {object} 校验规则
 */
export function getValidator(property) {
  return {
    // 校验函数
    validate: (value) => {
      const result = validateValue(value, property)
      return result.valid ? true : result.message
    }
  }
}

export default {
  parseOption,
  getValidateRules,
  validateValue,
  getRangeHint,
  getValidator
}
