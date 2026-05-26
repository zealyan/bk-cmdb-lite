# 新增实例功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现CMDB的新增实例功能，包括后端API和前端UI，支持属性验证（正则表达式、枚举值验证等）

**Architecture:** 基于之前对原项目的分析，实现完整的新增实例流程，包含属性option处理、正则表达式验证、必填字段检查等功能

**Tech Stack:** Python (FastAPI), JavaScript (Vue 2), DuckDB

---

## 文件结构说明

### 后端文件
- **Modify**: `cmdb_server_lite/main.py` - 新增实例API端点和验证逻辑
- **Create**: `cmdb_server_lite/validators.py` - 属性验证工具函数（可选）

### 前端文件
- **Modify**: `cmdb_ui_lite/src/api/client.js` - 新增实例API调用方法
- **Modify**: `cmdb_ui_lite/src/views/general-model/index.vue` - 新增实例弹窗和表单

---

### Task 1: 后端 - 实现属性验证工具函数

**Files:**
- Modify: `cmdb_server_lite/main.py` - 在文件中添加验证工具函数

- [ ] **Step 1: 在main.py中添加验证工具函数**

在main.py文件中，在导入语句后添加以下验证函数：

```python
import re
from typing import Dict, Any, List, Optional

def validate_string_with_regex(value: str, regex: str) -> tuple[bool, str]:
    """验证字符串是否符合正则表达式"""
    try:
        if not re.fullmatch(regex, value):
            return False, f"值 '{value}' 不符合正则表达式规则: {regex}"
        return True, ""
    except re.error as e:
        return False, f"正则表达式格式错误: {str(e)}"

def validate_enum_value(value: Any, options: List[Any]) -> tuple[bool, str]:
    """验证值是否在枚举选项列表中"""
    if not isinstance(options, list):
        return True, ""  # 如果option不是列表，跳过验证
    if value not in options:
        return False, f"值 '{value}' 不在允许的选项列表中: {options}"
    return True, ""

def validate_required_field(value: Any, field_name: str) -> tuple[bool, str]:
    """验证必填字段"""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return False, f"字段 '{field_name}' 为必填项"
    return True, ""

def parse_option_value(option: Any) -> Any:
    """解析option字段值，处理JSON字符串和列表"""
    if isinstance(option, str):
        try:
            import json
            return json.loads(option)
        except (json.JSONDecodeError, TypeError):
            return option
    return option
```

- [ ] **Step 2: 检查添加位置**

将上述函数添加在 `get_db()` 函数之前，约在第30行左右。

---

### Task 2: 后端 - 实现实例验证主逻辑

**Files:**
- Modify: `cmdb_server_lite/main.py` - 添加实例验证函数

- [ ] **Step 1: 添加实例验证函数**

在刚才添加的验证工具函数之后，添加以下主验证函数：

```python
def validate_instance_data(model_id: str, instance_data: Dict[str, Any], attributes: List[Dict[str, Any]]) -> tuple[bool, List[str]]:
    """
    验证实例数据
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    # 获取模型的属性定义
    model_attrs = [attr for attr in attributes if attr.get('bk_obj_id') == model_id]
    
    for attr in model_attrs:
        field_name = attr.get('bk_property_id')
        field_type = attr.get('bk_property_type')
        is_required = attr.get('isrequired', False)
        option = parse_option_value(attr.get('option'))
        default_val = attr.get('default')
        
        value = instance_data.get(field_name)
        
        # 1. 验证必填字段
        if is_required:
            is_valid, err_msg = validate_required_field(value, field_name)
            if not is_valid:
                errors.append(err_msg)
                continue
        
        # 如果值为空且有默认值，使用默认值
        if (value is None or (isinstance(value, str) and value.strip() == "")) and default_val is not None:
            instance_data[field_name] = default_val
            value = default_val
        
        # 如果值仍然为空，跳过验证（非必填）
        if value is None or (isinstance(value, str) and value.strip() == ""):
            continue
        
        # 2. 根据字段类型进行验证
        if field_type in ['singlechar', 'longchar']:
            # 字符串类型：检查正则表达式
            if option and isinstance(option, str) and isinstance(value, str):
                is_valid, err_msg = validate_string_with_regex(value, option)
                if not is_valid:
                    errors.append(err_msg)
        elif field_type in ['enum', 'enumMulti']:
            # 枚举类型：检查值是否在选项中
            if option:
                if field_type == 'enumMulti':
                    # 多选：检查每个值
                    if isinstance(value, list):
                        for v in value:
                            is_valid, err_msg = validate_enum_value(v, option)
                            if not is_valid:
                                errors.append(err_msg)
                    else:
                        # 如果不是列表但有值，单个检查
                        is_valid, err_msg = validate_enum_value(value, option)
                        if not is_valid:
                            errors.append(err_msg)
                else:
                    # 单选
                    is_valid, err_msg = validate_enum_value(value, option)
                    if not is_valid:
                        errors.append(err_msg)
        elif field_type in ['int', 'number']:
            # 数字类型：验证转换
            try:
                if field_type == 'int':
                    int(value)
                else:
                    float(value)
            except (ValueError, TypeError):
                errors.append(f"字段 '{field_name}' 必须是数字类型")
        elif field_type == 'bool':
            # 布尔类型
            if not isinstance(value, bool) and value not in [0, 1, '0', '1', 'true', 'false']:
                errors.append(f"字段 '{field_name}' 必须是布尔类型")
    
    return len(errors) == 0, errors
```

---

### Task 3: 后端 - 实现创建实例API端点

**Files:**
- Modify: `cmdb_server_lite/main.py` - 在文件末尾（但在 `if __name__ == "__main__":` 之前）添加API端点

- [ ] **Step 1: 添加创建实例的API端点**

在 `check_instance_associations` 端点之后，添加以下端点：

```python
@app.post("/api/models/{model_id}/instances")
async def create_instance(
    model_id: str,
    request_data: dict = None
):
    """
    创建新的模型实例
    
    请求示例:
    {
        "data": {
            "field1": "value1",
            "field2": "value2"
        }
    }
    """
    table_name = get_instance_table_name(model_id)
    if not model_exists(model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    
    if not request_data or 'data' not in request_data:
        raise HTTPException(status_code=400, detail="data field is required in request body")
    
    instance_data = request_data['data']
    
    try:
        db = get_db()
        
        # 获取模型的属性定义
        attributes = query_many('SELECT * FROM cc_ObjAttDes')
        
        # 1. 验证实例数据
        is_valid, errors = validate_instance_data(model_id, instance_data, attributes)
        if not is_valid:
            raise HTTPException(status_code=400, detail={"errors": errors})
        
        # 2. 获取表结构，自动生成缺失字段的默认值
        columns_result = db.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        columns = {col[1]: col for col in columns_result}
        
        # 3. 填充系统字段
        import time
        current_time = int(time.time())
        current_timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # 填充默认字段
        if 'creator' not in instance_data:
            instance_data['creator'] = 'admin'
        if 'modifier' not in instance_data:
            instance_data['modifier'] = 'admin'
        if 'create_time' not in instance_data:
            instance_data['create_time'] = current_timestamp
        if 'last_time' not in instance_data:
            instance_data['last_time'] = current_timestamp
        if 'bk_supplier_account' not in instance_data:
            instance_data['bk_supplier_account'] = '0'
        if 'bk_operate_time' not in instance_data:
            instance_data['bk_operate_time'] = current_timestamp
        
        # 生成 bk_inst_id 字段（如果需要）
        if 'bk_inst_id' in columns and 'bk_inst_id' not in instance_data:
            # 获取当前最大ID + 1
            max_result = query_one(f'SELECT MAX(bk_inst_id) as max_id FROM "{table_name}"')
            new_bk_inst_id = (max_result.get('max_id') or 0) + 1
            instance_data['bk_inst_id'] = new_bk_inst_id
        
        # 生成 id 字段
        if 'id' in columns and 'id' not in instance_data:
            max_id_result = query_one(f'SELECT MAX(id) as max_id FROM "{table_name}"')
            new_id = (max_id_result.get('max_id') or 0) + 1
            instance_data['id'] = new_id
        
        # 4. 构建INSERT语句
        field_names = list(instance_data.keys())
        placeholders = [f'"{name}"' for name in field_names]
        value_placeholders = [f'?' for _ in field_names]
        values = [instance_data[name] for name in field_names]
        
        insert_sql = f'INSERT INTO "{table_name}" ({", ".join(placeholders)}) VALUES ({", ".join(value_placeholders)})'
        db.execute(insert_sql, values)
        
        # 5. 获取新创建的实例
        new_instance = query_one(f'SELECT * FROM "{table_name}" WHERE id = ?', [instance_data['id']])
        
        print(f"[INFO] Created new instance in {table_name} with id={instance_data['id']}")
        
        return {
            "success": True,
            "data": new_instance,
            "message": "实例创建成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
```

---

### Task 4: 前端 - API Client 添加创建实例方法

**Files:**
- Modify: `cmdb_ui_lite/src/api/client.js`

- [ ] **Step 1: 在client.js中添加创建实例的API方法**

在 `deleteInstances` 方法之后，添加以下方法：

```javascript
  // 创建新实例
  createInstance (modelId, data) {
    return http.post(`/api/models/${modelId}/instances`, { data })
  }
```

---

### Task 5: 前端 - 查看当前的新增按钮实现

**Files:**
- Read: `cmdb_ui_lite/src/views/general-model/index.vue`

- [ ] **Step 1: 查看当前新增按钮的实现**

读取该文件，了解当前的：
1. 新增按钮的位置和点击处理
2. 相关数据结构
3. 对话框组件的使用模式

---

### Task 6: 前端 - 实现新增实例弹窗表单

**Files:**
- Modify: `cmdb_ui_lite/src/views/general-model/index.vue`

- [ ] **Step 1: 在data中添加弹窗相关数据**

在 `data()` 返回的对象中添加：

```javascript
data() {
  return {
    // ... 现有数据 ...
    
    // 新增实例弹窗
    createDialogVisible: false,
    createForm: {},
    createFormRules: {},
    createFormLoading: false,
    
    // ... 其余现有数据 ...
  }
}
```

- [ ] **Step 2: 添加打开新增弹窗的方法**

在 `methods` 中添加：

```javascript
    // 打开新增实例弹窗
    handleCreateInstance() {
      this.createDialogVisible = true
      this.createForm = {}
      
      // 初始化表单，为每个字段设置默认值
      this.allProperties.forEach(attr => {
        const defaultValue = attr.default
        if (defaultValue !== null && defaultValue !== undefined) {
          this.$set(this.createForm, attr.bk_property_id, defaultValue)
        }
      })
    },
    
    // 关闭新增弹窗
    handleCreateDialogClose() {
      this.createDialogVisible = false
      this.createForm = {}
    },
```

- [ ] **Step 3: 添加提交创建的方法**

继续在 `methods` 中添加：

```javascript
    // 提交创建实例
    async handleCreateSubmit() {
      this.createFormLoading = true
      try {
        const result = await modelAPI.createInstance(this.objId, this.createForm)
        
        if (result.success) {
          this.$bkMessage({ message: '实例创建成功', theme: 'success' })
          this.handleCreateDialogClose()
          // 刷新列表
          await this.loadModelData(this.currentSearchParams)
        } else {
          this.$bkMessage({ message: result.message || '创建失败', theme: 'error' })
        }
      } catch (error) {
        console.error('Create instance error:', error)
        let errorMsg = '创建失败，请稍后重试'
        
        if (error.response && error.response.status === 400) {
          const errorData = error.response.data
          if (errorData && errorData.detail && errorData.detail.errors) {
            errorMsg = errorData.detail.errors.join('; ')
          } else if (errorData && errorData.detail) {
            errorMsg = errorData.detail
          }
        }
        
        this.$bkMessage({ message: errorMsg, theme: 'error' })
      } finally {
        this.createFormLoading = false
      }
    },
```

- [ ] **Step 4: 修改"新增"按钮的处理函数**

找到 `handleCreate` 方法（约在第750行），修改为：

```javascript
    handleCreate() {
      this.handleCreateInstance()
    },
```

---

### Task 7: 前端 - 添加表单弹窗组件

**Files:**
- Modify: `cmdb_ui_lite/src/views/general-model/index.vue`

- [ ] **Step 1: 在模板中添加新增实例弹窗**

在 `</div>` 结束标签之前，添加以下内容（在最后一个 `</template>` 之前）：

```html
    <!-- 新增实例弹窗 -->
    <bk-dialog
      :visible.sync="createDialogVisible"
      title="新增实例"
      width="800px"
      @close="handleCreateDialogClose"
    >
      <bk-form
        ref="createFormRef"
        :model="createForm"
        label-width="130"
        :rules="createFormRules"
      >
        <bk-form-item
          v-for="attr in allProperties"
          :key="attr.bk_property_id"
          :label="attr.bk_property_name"
          :property="attr.bk_property_id"
          :required="attr.isrequired"
        >
          <!-- 字符串输入 -->
          <bk-input
            v-if="['singlechar', 'longchar'].includes(attr.bk_property_type)"
            v-model="createForm[attr.bk_property_id]"
            :placeholder="attr.placeholder || ''"
            :disabled="attr.isreadonly"
          />
          
          <!-- 数字输入 -->
          <bk-input
            v-else-if="['int', 'number'].includes(attr.bk_property_type)"
            v-model="createForm[attr.bk_property_id]"
            type="number"
            :placeholder="attr.placeholder || ''"
            :disabled="attr.isreadonly"
          />
          
          <!-- 布尔值开关 -->
          <bk-switcher
            v-else-if="attr.bk_property_type === 'bool'"
            v-model="createForm[attr.bk_property_id]"
            :disabled="attr.isreadonly"
          />
          
          <!-- 单选枚举 -->
          <bk-select
            v-else-if="attr.bk_property_type === 'enum'"
            v-model="createForm[attr.bk_property_id]"
            :disabled="attr.isreadonly"
            clearable
            :searchable="true"
          >
            <bk-option
              v-for="option in parseOptions(attr.option)"
              :key="option"
              :id="option"
              :name="option"
            />
          </bk-select>
          
          <!-- 多选枚举 -->
          <bk-select
            v-else-if="attr.bk_property_type === 'enumMulti'"
            v-model="createForm[attr.bk_property_id]"
            :disabled="attr.isreadonly"
            multiple
            clearable
          >
            <bk-option
              v-for="option in parseOptions(attr.option)"
              :key="option"
              :id="option"
              :name="option"
            />
          </bk-select>
          
          <!-- 日期时间 -->
          <bk-date-picker
            v-else-if="attr.bk_property_type === 'datetime'"
            v-model="createForm[attr.bk_property_id]"
            type="datetime"
            :disabled="attr.isreadonly"
          />
          
          <!-- 日期 -->
          <bk-date-picker
            v-else-if="attr.bk_property_type === 'date'"
            v-model="createForm[attr.bk_property_id]"
            type="date"
            :disabled="attr.isreadonly"
          />
          
          <!-- 时间 -->
          <bk-time-picker
            v-else-if="attr.bk_property_type === 'time'"
            v-model="createForm[attr.bk_property_id]"
            :disabled="attr.isreadonly"
          />
          
          <!-- 文本域 -->
          <bk-textarea
            v-else-if="attr.bk_property_type === 'text'"
            v-model="createForm[attr.bk_property_id]"
            :placeholder="attr.placeholder || ''"
            :disabled="attr.isreadonly"
          />
          
          <!-- 默认输入框 -->
          <bk-input
            v-else
            v-model="createForm[attr.bk_property_id]"
            :placeholder="attr.placeholder || ''"
            :disabled="attr.isreadonly"
          />
        </bk-form-item>
      </bk-form>
      
      <div slot="footer">
        <bk-button @click="handleCreateDialogClose">取消</bk-button>
        <bk-button
          theme="primary"
          :loading="createFormLoading"
          @click="handleCreateSubmit"
        >
          确定
        </bk-button>
      </div>
    </bk-dialog>
  </div>
</template>
```

- [ ] **Step 2: 添加解析option的工具方法**

在 `methods` 中添加：

```javascript
    // 解析选项（处理JSON字符串）
    parseOptions(option) {
      if (!option) return []
      if (Array.isArray(option)) return option
      try {
        const parsed = JSON.parse(option)
        return Array.isArray(parsed) ? parsed : []
      } catch {
        return []
      }
    },
```

---

### Task 8: 测试 - 验证后端API

**Files:**
- Create: `cmdb_server_lite/test_create_instance.py`

- [ ] **Step 1: 创建测试脚本**

```python
import requests
import json

BASE_URL = "http://localhost:8000"

def test_create_instance():
    """测试创建实例API"""
    
    # 1. 测试创建SLB实例
    print("=== 测试创建SLB实例 ===")
    
    model_id = "bk_slb"
    
    # 准备测试数据
    test_data = {
        "data": {
            "bk_slb_name": "测试SLB-001",
            "bk_vendor": "tencent",
            "bk_region": "ap-guangzhou",
            "bk_cloud_id": 0,
            "bk_status": "normal",
            "bk_outer_ip": "119.29.29.29",
            "bk_inner_ip": "10.0.0.1",
            "bk_pay_type": 1,
            "bk_biz_id": 2,
            "bk_host_id": 123
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/models/{model_id}/instances",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print("✅ 创建成功")
        else:
            print("❌ 创建失败")
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")

if __name__ == "__main__":
    test_create_instance()
```

- [ ] **Step 2: 确保后端服务运行，执行测试**

先重启后端服务，然后运行：

```bash
cd /workspace/bk-cmdb/cmdb_server_lite
python test_create_instance.py
```

---

### Task 9: 集成测试 - 完整流程验证

**Files:**
- Test: 浏览器中进行手动测试

- [ ] **Step 1: 启动所有服务**

确保：
1. 后端服务运行在 http://localhost:8000
2. 前端服务运行在 http://localhost:8080

- [ ] **Step 2: 前端测试步骤**

1. 访问 http://localhost:8080
2. 选择一个模型（如"负载均衡"）
3. 点击"新增"按钮
4. 填写表单，测试：
   - 必填字段验证
   - 正则表达式验证
   - 枚举值选择
   - 提交成功后刷新列表

---

## 验证清单

完成后请验证以下功能：

- [ ] 后端API可以正常创建实例
- [ ] 必填字段验证生效
- [ ] 正则表达式验证生效（如果有定义）
- [ ] 枚举值验证生效
- [ ] 默认值自动填充
- [ ] 前端弹窗正常显示和提交
- [ ] 创建后列表可以正确刷新显示新实例
- [ ] 错误信息友好展示
