# API 接口使用说明

## 基础信息

- **Base URL**: `http://localhost:8002`
- **响应格式**: JSON
- **通用响应结构**:
```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

---

## 场景接口 `/ai/scenarios/`

### 创建场景
```
POST /api/ai/scenarios/
```

**请求体**:
```json
{
  "code": "SCN-001",
  "name": "用户登录场景",
  "project_id": 1,
  "test_types": ["functional", "api"],
  "linked_requirement": "REQ-001",
  "skills_content": "## Skills配置\n\n你是一个测试工程师...",
  "status": "draft"
}
```

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| code | string | 是 | 场景编码，格式如 `"SCN-001"` |
| name | string | 是 | 场景名称 |
| project_id | number | 否 | 关联项目ID |
| test_types | string[] | 否 | 测试类型数组，默认 `[]` |
| linked_requirement | string | 否 | 关联需求/备注 |
| status | string | 否 | `draft`/`ready`/`invalid`，默认 `draft` |
| skills_content | string | 否 | Skills 配置内容 (Markdown 格式) |

**响应示例**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "project_id": 1,
    "code": "SCN-001",
    "name": "用户登录场景",
    "test_types": ["functional", "api"],
    "linked_requirement": "REQ-001",
    "status": "draft",
    "skills_content": "## Skills配置\n\n你是一个测试工程师...",
    "created_at": "2026-05-09T10:00:00",
    "updated_at": null
  }
}
```

### 获取场景列表
```
GET /api/ai/scenarios/?project_id=1&skip=0&limit=100
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | number | 否 | 筛选指定项目的场景 |
| skip | number | 否 | 跳过记录数，默认 0 |
| limit | number | 否 | 返回记录数，默认 100 |

### 获取单个场景
```
GET /api/ai/scenarios/{id}
```

### 更新场景
```
PUT /api/ai/scenarios/{id}
```

**请求体** (部分字段):
```json
{
  "name": "更新后的场景名称",
  "test_types": ["functional", "api", "performance"],
  "status": "ready"
}
```

### 删除场景
```
DELETE /api/ai/scenarios/{id}
```

---

## 测试用例接口 `/ai/testcases/`

### 创建测试用例
```
POST /api/ai/testcases/
```

**请求体**:
```json
{
  "project_id": 1,
  "title": "用户登录成功",
  "type": "functional",
  "priority": "P1",
  "module": "用户模块",
  "preconditions": "用户已注册",
  "steps": ["打开登录页", "输入用户名密码", "点击登录"],
  "expected": "登录成功，跳转到首页",
  "source": "manual",
  "requirement_id": 1,
  "scenario_id": 1,
  "scenario_name": "用户登录场景"
}
```

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| project_id | number | 是 | 关联项目ID |
| title | string | 是 | 用例标题 |
| type | string | 是 | 测试类型: `functional`/`api`/`performance`/`security`/`compatibility`/`regression` |
| priority | string | 是 | 优先级: `P1`/`P2`/`P3`/`P4` |
| module | string | 否 | 所属模块/场景名称 |
| preconditions | string | 否 | 前置条件 |
| steps | string[] | 是 | 测试步骤数组 |
| expected | string | 是 | 预期结果 |
| source | string | 是 | 来源: `ai`/`manual` |
| requirement_id | number | 是 | 关联需求ID |
| scenario_id | number | 否 | 关联场景ID |
| scenario_name | string | 否 | 场景分组名 (冗余字段) |

**响应示例**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "project_id": 1,
    "case_id": "TC-260509-001",
    "title": "用户登录成功",
    "type": "functional",
    "status": "draft",
    "priority": "P1",
    "module": "用户模块",
    "preconditions": "用户已注册",
    "steps": ["打开登录页", "输入用户名密码", "点击登录"],
    "expected": "登录成功，跳转到首页",
    "source": "manual",
    "clone_status": "original",
    "cloned_from": null,
    "requirement_id": 1,
    "scenario_id": 1,
    "scenario_name": "用户登录场景",
    "created_at": "2026-05-09T10:00:00",
    "updated_at": null
  }
}
```

### 获取测试用例列表
```
GET /api/ai/testcases/?project_id=1&type=functional&status=draft&skip=0&limit=100
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | number | 否 | 筛选指定项目的用例 |
| type | string | 否 | 筛选测试类型 |
| status | string | 否 | 筛选审批状态 |
| skip | number | 否 | 跳过记录数，默认 0 |
| limit | number | 否 | 返回记录数，默认 100 |

### 获取单个测试用例
```
GET /api/ai/testcases/{id}
```

### 更新测试用例
```
PUT /api/ai/testcases/{id}
```

**请求体** (部分字段):
```json
{
  "title": "更新后的标题",
  "status": "approved",
  "steps": ["新步骤1", "新步骤2"]
}
```

### 克隆测试用例
```
POST /api/ai/testcases/{id}/clone
```

**响应示例**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 2,
    "project_id": 1,
    "case_id": "TC-260509-002",
    "title": "用户登录成功 (克隆)",
    "type": "functional",
    "status": "draft",
    "priority": "P1",
    "clone_status": "draft",
    "cloned_from": 1,
    ...
  }
}
```

### 删除测试用例
```
DELETE /api/ai/testcases/{id}
```

---

## 测试数据接口 `/ai/testdata/`

### 创建测试数据
```
POST /api/ai/testdata/
```

**请求体**:
```json
{
  "project_id": 1,
  "testcase_id": 1,
  "field": "username",
  "value": "testuser",
  "data_type": "string",
  "source": "manual",
  "status": "valid",
  "scenario": "登录数据",
  "scenario_id": 1,
  "category": "用户数据"
}
```

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| project_id | number | 是 | 关联项目ID |
| testcase_id | number | 否 | 关联测试用例ID |
| field | string | 是 | 字段名 |
| value | string | 否 | 字段值 |
| data_type | string | 是 | 数据类型: `string`/`number`/`boolean` 等 |
| source | string | 是 | 来源: `ai`/`manual` |
| status | string | 否 | 状态: `valid`/`invalid`，默认 `valid` |
| scenario | string | 否 | 分组名/场景分组 |
| scenario_id | number | 否 | 关联场景ID |
| category | string | 否 | 分类 (与 scenario 同义) |

**响应示例**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "project_id": 1,
    "testcase_id": 1,
    "field": "username",
    "value": "testuser",
    "data_type": "string",
    "source": "manual",
    "status": "valid",
    "scenario": "登录数据",
    "scenario_id": 1,
    "category": "用户数据",
    "created_at": "2026-05-09T10:00:00",
    "updated_at": null
  }
}
```

### 获取测试数据列表
```
GET /api/ai/testdata/?project_id=1&testcase_id=1&source=manual&skip=0&limit=100
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | number | 否 | 筛选指定项目的数据 |
| testcase_id | number | 否 | 筛选指定用例的数据 |
| source | string | 否 | 筛选来源 |
| skip | number | 否 | 跳过记录数，默认 0 |
| limit | number | 否 | 返回记录数，默认 100 |

### 获取单个测试数据
```
GET /api/ai/testdata/{id}
```

### 更新测试数据
```
PUT /api/ai/testdata/{id}
```

**请求体** (部分字段):
```json
{
  "value": "new_value",
  "status": "invalid"
}
```

### 删除测试数据
```
DELETE /api/ai/testdata/{id}
```

---

## 已通过用例接口 `/ai/approved-cases/`

### 创建已通过用例
```
POST /api/ai/approved-cases/
```

**请求体**:
```json
{
  "project_id": 1,
  "case_id": "TC-260509-001",
  "source_testcase_id": "1",
  "title": "用户登录成功",
  "scenario_name": "用户登录场景",
  "type": "functional",
  "priority": "P1",
  "module": "用户模块",
  "preconditions": "用户已注册",
  "steps": ["打开登录页", "输入用户名密码", "点击登录"],
  "expected": "登录成功，跳转到首页",
  "requirement_id": 1,
  "test_data": [
    {"field": "username", "value": "testuser", "data_type": "string"},
    {"field": "password", "value": "123456", "data_type": "string"}
  ]
}
```

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| project_id | number | 是 | 关联项目ID |
| case_id | string | 是 | 用例编号 |
| source_testcase_id | string | 是 | 来源测试用例ID |
| title | string | 是 | 用例标题 |
| scenario_name | string | 否 | 场景分组名 |
| type | string | 是 | 测试类型 |
| priority | string | 是 | 优先级 |
| module | string | 否 | 所属模块 |
| preconditions | string | 否 | 前置条件 |
| steps | string[] | 是 | 测试步骤 |
| expected | string | 是 | 预期结果 |
| requirement_id | number | 否 | 关联需求ID |
| test_data | JSON | 否 | 测试数据列表 |

**响应示例**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "project_id": 1,
    "case_id": "TC-260509-001",
    "source_testcase_id": "1",
    "title": "用户登录成功",
    "scenario_name": "用户登录场景",
    "type": "functional",
    "priority": "P1",
    "module": "用户模块",
    "preconditions": "用户已注册",
    "steps": ["打开登录页", "输入用户名密码", "点击登录"],
    "expected": "登录成功，跳转到首页",
    "requirement_id": 1,
    "test_data": [...],
    "approved_at": "2026-05-09T10:00:00"
  }
}
```

### 获取已通过用例列表
```
GET /api/ai/approved-cases/?project_id=1&source_testcase_id=1&skip=0&limit=100
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | number | 否 | 筛选指定项目 |
| source_testcase_id | string | 否 | 筛选来源测试用例ID |
| skip | number | 否 | 跳过记录数，默认 0 |
| limit | number | 否 | 返回记录数，默认 100 |

---

## 用例生成接口 `/ai/case-generator/`

> **当前实现状态**：需求数据使用 Mock 方案，待后续其他模块提供真实需求服务后替换。

### 基于场景生成测试用例
```
POST /api/ai/case-generator/scenarios/{scenario_id}/generate
```

**前置条件**：场景需关联需求（`linked_requirement` 字段，如 `"REQ-001"`）

**请求体**:
```json
{
  "strategies": ["positive", "negative"],
  "language": "zh"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| strategies | string[] | 否 | 测试策略: `positive`(正向), `negative`(负向), `boundary`(边界值), `ui`(UI交互), `security`(安全性)，默认 `["positive", "negative"]` |
| language | string | 否 | 输出语言: `zh`(中文), `en`(英文)，默认 `zh` |

**响应示例**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "generated_count": 3,
    "cases": [
      {
        "id": 1,
        "case_id": "TC-260509-001",
        "title": "用户登录成功",
        "type": "positive",
        "priority": "P1",
        "module": null,
        "preconditions": "用户已注册",
        "steps": ["打开登录页", "输入正确用户名密码", "点击登录"],
        "expected": "登录成功，跳转到首页",
        "scenario_id": 1,
        "scenario_name": "用户登录场景"
      }
    ]
  }
}
```

**实现说明**：
- 读取 Scenario 的 `linked_requirement` 字段（如 `REQ-001`）
- 从需求服务获取需求内容（当前为 Mock 数据）
- 调用 LLM 生成测试用例
- 用例 `source` 字段标记为 `ai`

### 基于场景生成测试数据
```
POST /api/ai/case-generator/scenarios/{scenario_id}/generate-data
```

**前置条件**：场景需关联需求（`linked_requirement` 字段，如 `"REQ-001"`）

**请求体**:
```json
{
  "count": 5,
  "language": "zh"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| count | number | 否 | 生成条数，默认 5 |
| language | string | 否 | 输出语言: `zh`(中文), `en`(英文)，默认 `zh` |

**响应示例**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "generated_count": 4,
    "data": [
      {
        "id": 1,
        "project_id": 1,
        "field": "username",
        "value": "testuser001",
        "data_type": "string",
        "source": "ai",
        "status": "valid",
        "scenario": "用户登录场景",
        "scenario_id": 1
      }
    ]
  }
}
```

**实现说明**：
- 读取 Scenario 的 `linked_requirement` 字段（如 `REQ-001`）
- 从需求服务获取需求内容（当前为 Mock 数据）
- 调用 LLM 生成测试数据
- 数据 `source` 字段标记为 `ai`

---

## 需求数据说明

**当前状态**：需求数据使用 Mock 方案

```python
MOCK_REQUIREMENTS = {
    "REQ-001": {
        "name": "用户登录功能",
        "content": "## 需求描述\n..."
    }
}
```

**后续扩展**：
- 替换为真实的需求服务（`/requirements/{id}` 接口）
- 需求数据存储到数据库
- 其他服务调用需求微服务获取需求内容

---

## 数据库表

| 表名 | 说明 |
|------|------|
| `TestHub_scenarios` | 测试场景 |
| `TestHub_testcases` | 测试用例 |
| `TestHub_testdata` | 测试数据 |
| `TestHub_approved_cases` | 已通过用例 |
| `TestHub_chat_sessions` | 对话会话 |

**表结构 - TestHub_scenarios**:
```sql
CREATE TABLE TestHub_scenarios (
  id SERIAL PRIMARY KEY,
  project_id INTEGER,
  code VARCHAR(50) NOT NULL,
  name VARCHAR(255) NOT NULL,
  test_types JSONB,
  linked_requirement TEXT,
  status VARCHAR(20) DEFAULT 'draft',
  skills_content TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP,
  UNIQUE(project_id, code)
);
```

**表结构 - TestHub_testcases**:
```sql
CREATE TABLE TestHub_testcases (
  id SERIAL PRIMARY KEY,
  project_id INTEGER NOT NULL,
  case_id VARCHAR(50) UNIQUE NOT NULL,
  title VARCHAR(500) NOT NULL,
  type VARCHAR(50) NOT NULL,
  status VARCHAR(20) DEFAULT 'draft',
  priority VARCHAR(10) NOT NULL,
  module VARCHAR(100),
  preconditions TEXT,
  steps JSONB NOT NULL,
  expected TEXT NOT NULL,
  source VARCHAR(20) NOT NULL,
  clone_status VARCHAR(20) DEFAULT 'original',
  cloned_from INTEGER,
  requirement_id INTEGER NOT NULL,
  scenario_id INTEGER,
  scenario_name VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP
);
```

**表结构 - TestHub_testdata**:
```sql
CREATE TABLE TestHub_testdata (
  id SERIAL PRIMARY KEY,
  project_id INTEGER NOT NULL,
  testcase_id INTEGER,
  field VARCHAR(100) NOT NULL,
  value TEXT,
  data_type VARCHAR(50) NOT NULL,
  source VARCHAR(20) NOT NULL,
  status VARCHAR(20) DEFAULT 'valid',
  scenario VARCHAR(100),
  scenario_id INTEGER,
  category VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP
);
```

**表结构 - TestHub_approved_cases**:
```sql
CREATE TABLE TestHub_approved_cases (
  id SERIAL PRIMARY KEY,
  project_id INTEGER NOT NULL,
  case_id VARCHAR(50) NOT NULL,
  source_testcase_id VARCHAR(50) NOT NULL,
  title VARCHAR(500) NOT NULL,
  scenario_name VARCHAR(100),
  type VARCHAR(50) NOT NULL,
  priority VARCHAR(10) NOT NULL,
  module VARCHAR(100),
  preconditions TEXT,
  steps JSONB NOT NULL,
  expected TEXT NOT NULL,
  requirement_id INTEGER,
  test_data JSONB,
  approved_at TIMESTAMP DEFAULT NOW()
);
```

---

## 通用错误响应

```json
{
  "code": 400,
  "message": "Error message here",
  "data": null
}
```

| 状态码 | 说明 |
|--------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
