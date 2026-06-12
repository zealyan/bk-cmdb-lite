/**
 * 表单校验工具函数
 * 参考原项目: /workspace/bk-cmdb/src/ui/src/utils/tools.js getValidateRules
 * 
 * 支持的校验规则:
 * - int: 整数类型，支持 min/max 范围限制
 * - float: 浮点数类型，支持 min/max 范围限制
 * - singlechar/longchar: 字符串类型，支持正则校验
 * - enum/enummulti: 枚举类型
 * 
 * 字符长度限制(基于 UTF-8 字节数):
 * - singlechar: 256 字节
 * - longchar: 2000 字节
 */

/**
 * singlechar/longchar 的最大长度(按 UTF-8 字节数计算)
 * 与原项目保持一致
 */
export const SINGLECHAR_MAX_BYTES = 256
export const LONGCHAR_MAX_BYTES = 2000

/**
 * 计算字符串的 UTF-8 字节数
 * 与原项目保持一致: singlechar 限制 256 字节, longchar 限制 2000 字节
 * @param {string} str - 输入字符串
 * @returns {number} UTF-8 字节数
 */
export function utf8ByteLength(str) {
  if (str === undefined || str === null) return 0
  const s = String(str)
  let length = 0
  for (let i = 0; i < s.length; i++) {
    const code = s.charCodeAt(i)
    if (code < 0x80) {
      length += 1
    } else if (code < 0x800) {
      length += 2
    } else if (code >= 0xD800 && code <= 0xDBFF) {
      // 处理 UTF-16 代理对 (surrogate pair)
      // 即一个字符由两个 16-bit code unit 组成
      length += 4
      i++ // 跳过下一个 code unit
    } else {
      length += 3
    }
  }
  return length
}

/**
 * 根据属性类型获取最大字节数
 * @param {string} propertyType - 属性类型
 * @returns {number|null} 最大字节数，非字符串类型返回 null
 */
export function getMaxBytesByType(propertyType) {
  if (propertyType === 'singlechar') return SINGLECHAR_MAX_BYTES
  if (propertyType === 'longchar') return LONGCHAR_MAX_BYTES
  return null
}

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
    const maxBytes = propertyType === 'singlechar' ? SINGLECHAR_MAX_BYTES : LONGCHAR_MAX_BYTES
    const byteLength = utf8ByteLength(strValue)
    
    // UTF-8 字节数限制（与原项目保持一致）
    if (byteLength > maxBytes) {
      errors.push(`请输入${maxBytes}个字符以内的内容`)
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
  getValidator,
  utf8ByteLength,
  getMaxBytesByType,
  SINGLECHAR_MAX_BYTES,
  LONGCHAR_MAX_BYTES
}
