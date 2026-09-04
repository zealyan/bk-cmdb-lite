/**
 * 实例关联分组 key —— 共享工具
 *
 * 分组唯一性规则：关联定义(bk_obj_asst_id) + 指向(源/目标)。
 *
 * 对齐原项目 bk-cmdb（src/ui/src/views/host-details/children/association-list.vue）：
 *   objAsstId = `${src}_${bk_asst_id}_${dst}`（当前实例为源）
 *             = `${dst}_${bk_asst_id}_${src}`（当前实例为目标）
 *   注释「关联关系id和源或目标的关系（指向）组成唯一性」。
 *
 * 历史问题：key 若只含「指向 + 对端模型」，会把同一对模型上的多种关联类型
 * （如 module→module 的 access 与 mutual_access）去重合并，导致：
 *   1) 「显示空列表」只出现第一种关联（访问），漏掉第二种（互访）；
 *   2) 已有关联也被错误合并进同一分组（标题只取先遇到的那种）。
 *
 * 使用约定：实例关联相关的分组与状态（associationGroups / emptyGroupDefs /
 * initGroupStates 等）必须统一走本函数，否则 groupStates（分页/展开）与分组
 * key 错位，出现分页或展开态异常。
 *
 * @param {boolean} isSource           当前实例是否为关联的源端（否则视为目标端）
 * @param {string|number} bkObjAsstId  关联定义 id（cc_ObjAsst.bk_obj_asst_id，
 *                                     格式 {源}_{关联类型}_{目标}，天然含关联类型）
 * @param {string|number} fallbackObjId 对端模型 ID；bk_obj_asst_id 缺失时的降级回退，
 *                                     避免退化为全量合并
 * @returns {string} 分组 key，如 'to_module_access_module' / 'from_module_access_module'
 */
export function associationGroupKey(isSource, bkObjAsstId, fallbackObjId) {
  const dir = isSource ? 'to' : 'from'
  return `${dir}_${bkObjAsstId || fallbackObjId}`
}
