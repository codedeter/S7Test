# 故障规则管理功能集成指南

## 功能概述

在前端UI中添加故障规则管理功能，用户可以：
- 查看内置故障规则
- 添加自定义故障规则
- 编辑和删除自定义规则
- 重新加载故障规则

## 已添加的文件

### 1. API接口 (`src/api/routes.py`)
已添加以下API端点：
- `GET /api/fault-rules` - 获取故障规则列表
- `POST /api/fault-rules` - 添加自定义规则
- `PUT /api/fault-rules/<rule_name>` - 更新规则
- `DELETE /api/fault-rules/<rule_name>` - 删除规则
- `GET /api/fault-rules/devices` - 获取支持的设备列表
- `POST /api/fault-rules/reload` - 重新加载规则

### 2. 规则存储
- `config/custom_fault_rules.json` - 自定义规则存储文件

## 集成步骤

### 步骤1: 添加CSS样式

在 `public/index.html` 的 `</style>` 标签前添加以下内容：

```css
    /* 故障规则管理样式 */
    .fault-rules-header {
      display: flex;
      gap: 10px;
      margin-bottom: 15px;
      flex-wrap: wrap;
    }
    .device-select {
      padding: 8px 12px;
      border: 1px solid #d9d9d9;
      border-radius: 4px;
      font-size: 14px;
    }
    .btn {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      transition: all 0.3s;
    }
    .btn-primary { background-color: #1890ff; color: white; }
    .btn-primary:hover { background-color: #40a9ff; }
    .btn-secondary { background-color: #f0f0f0; color: #333; }
    .btn-secondary:hover { background-color: #d9d9d9; }
    .btn-small {
      padding: 4px 8px;
      font-size: 12px;
      background-color: #1890ff;
      color: white;
      border: none;
      border-radius: 3px;
      cursor: pointer;
      margin-right: 5px;
    }
    .btn-danger { background-color: #f5222d !important; }
    .rules-stats {
      display: flex;
      gap: 20px;
      margin-bottom: 15px;
      padding: 10px;
      background-color: #f5f5f5;
      border-radius: 4px;
    }
    .stat-item { font-size: 13px; color: #666; }
    .stat-item strong { color: #1890ff; }
    .fault-rules-list { max-height: 400px; overflow-y: auto; }
    .rules-section { margin-bottom: 15px; }
    .rules-section h4 {
      color: #666;
      font-size: 13px;
      margin-bottom: 10px;
      padding-bottom: 5px;
      border-bottom: 1px solid #e8e8e8;
    }
    .rule-item {
      padding: 10px;
      margin-bottom: 8px;
      border-radius: 4px;
      border: 1px solid #e8e8e8;
    }
    .rule-item.builtin { background-color: #fafafa; }
    .rule-item.custom {
      background-color: #f0f7ff;
      border-color: #91d5ff;
    }
    .rule-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 5px;
    }
    .rule-name { font-weight: 600; color: #333; }
    .rule-badge { font-size: 11px; padding: 2px 6px; border-radius: 3px; }
    .severity-critical { background-color: #fff1f0; color: #f5222d; }
    .severity-warning { background-color: #fffbe6; color: #faad14; }
    .severity-info { background-color: #e6f7ff; color: #1890ff; }
    .builtin-badge { background-color: #f0f0f0; color: #666; }
    .rule-details {
      font-size: 12px;
      color: #666;
      display: flex;
      gap: 15px;
      margin-bottom: 5px;
    }
    .rule-desc { font-size: 12px; color: #999; }
    .rule-actions { margin-top: 8px; text-align: right; }
    .rule-modal { width: 500px; max-width: 90%; }
    .form-group { margin-bottom: 15px; }
    .form-group label {
      display: block;
      margin-bottom: 5px;
      font-weight: 500;
      color: #333;
    }
    .form-group input, .form-group select {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid #d9d9d9;
      border-radius: 4px;
      font-size: 14px;
    }
    .form-row { display: flex; gap: 15px; }
    .form-row .form-group { flex: 1; }
    .form-actions {
      text-align: right;
      margin-top: 20px;
      padding-top: 15px;
      border-top: 1px solid #e8e8e8;
    }
    .form-actions .btn { margin-left: 10px; }
```

### 步骤2: 添加HTML卡片

在"异常提醒"卡片后、"PLC变量列表"卡片前添加：

```html
    <div class="card">
      <h2>⚙️ 故障规则管理</h2>
      <div class="fault-rules-header">
        <select id="device-selector" class="device-select">
          <option value="RXB800">RXB800</option>
          <option value="RXA1300">RXA1300</option>
        </select>
        <button class="btn btn-primary" onclick="showAddRuleModal()">+ 添加规则</button>
        <button class="btn btn-secondary" onclick="reloadRules()">重新加载</button>
      </div>
      <div class="rules-stats" id="rules-stats"></div>
      <div class="fault-rules-list" id="fault-rules-list">
        <p style="color: #999; text-align: center;">加载中...</p>
      </div>
    </div>
```

### 步骤3: 添加模态框

在现有模态框后添加：

```html
  <!-- 添加/编辑规则模态框 -->
  <div class="modal-overlay" id="rule-modal-overlay">
    <div class="modal rule-modal">
      <div class="modal-header">
        <h3 class="modal-title" id="rule-modal-title">添加故障规则</h3>
        <button class="modal-close" onclick="closeRuleModal()">&times;</button>
      </div>
      <div class="modal-body">
        <form id="rule-form">
          <input type="hidden" id="rule-edit-id">
          <div class="form-group">
            <label>规则名称 *</label>
            <input type="text" id="rule-name" required placeholder="如：自定义故障1">
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>位位置 *</label>
              <input type="number" id="rule-bit-position" required min="0">
            </div>
            <div class="form-group">
              <label>严重程度 *</label>
              <select id="rule-severity" required>
                <option value="warning">警告</option>
                <option value="critical">紧急</option>
                <option value="info">信息</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>描述</label>
            <input type="text" id="rule-description" placeholder="故障描述">
          </div>
          <div class="form-group">
            <label>检测类型</label>
            <select id="rule-condition-type">
              <option value="status">状态位</option>
              <option value="analog">模拟量</option>
            </select>
          </div>
          <div class="form-group">
            <label>动态阈值变量</label>
            <input type="text" id="rule-threshold-var" placeholder="如：油超温温度">
          </div>
          <div class="form-group">
            <label>相关变量</label>
            <input type="text" id="rule-related-vars" placeholder="逗号分隔">
          </div>
          <div class="form-group">
            <label>单位</label>
            <input type="text" id="rule-unit" placeholder="如：°C">
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-secondary" onclick="closeRuleModal()">取消</button>
            <button type="submit" class="btn btn-primary">保存</button>
          </div>
        </form>
      </div>
    </div>
  </div>
```

### 步骤4: 添加JavaScript

在 `<script>` 标签内添加故障规则管理代码：

```javascript
let editingRule = null;

function loadFaultRules(deviceType = 'RXB800') {
  fetch(`/api/fault-rules?device_type=${deviceType}`)
    .then(res => res.json())
    .then(data => {
      renderRules(data);
      renderStats(data);
    })
    .catch(err => console.error('加载规则失败:', err));
}

function renderStats(data) {
  const stats = document.getElementById('rules-stats');
  stats.innerHTML = `
    <div class="stat-item">总数: <strong>${data.total_count}</strong></div>
    <div class="stat-item">内置: <strong>${data.builtin_rules?.length || 0}</strong></div>
    <div class="stat-item">自定义: <strong>${data.custom_rules?.length || 0}</strong></div>
  `;
}

function renderRules(data) {
  const list = document.getElementById('fault-rules-list');
  let html = '';
  
  if (data.builtin_rules && data.builtin_rules.length > 0) {
    html += '<div class="rules-section"><h4>内置规则</h4>';
    data.builtin_rules.forEach(rule => {
      html += renderRuleItem(rule, true);
    });
    html += '</div>';
  }
  
  if (data.custom_rules && data.custom_rules.length > 0) {
    html += '<div class="rules-section"><h4>自定义规则</h4>';
    data.custom_rules.forEach(rule => {
      html += renderRuleItem(rule, false);
    });
    html += '</div>';
  }
  
  list.innerHTML = html || '<p style="color: #999; text-align: center;">暂无规则</p>';
}

function renderRuleItem(rule, isBuiltin) {
  const severityClass = `severity-${rule.severity}`;
  return `
    <div class="rule-item ${isBuiltin ? 'builtin' : 'custom'}">
      <div class="rule-header">
        <span class="rule-name">${rule.name}</span>
        <span class="rule-badge ${severityClass}">${getSeverityText(rule.severity)}</span>
        ${isBuiltin ? '<span class="rule-badge builtin-badge">内置</span>' : ''}
      </div>
      <div class="rule-details">
        <span>位位置: ${rule.bit_position}</span>
        ${rule.unit ? `<span>单位: ${rule.unit}</span>` : ''}
      </div>
      ${rule.description ? `<div class="rule-desc">${rule.description}</div>` : ''}
      ${!isBuiltin ? `
        <div class="rule-actions">
          <button class="btn-small" onclick="editRule(${JSON.stringify(rule).replace(/"/g, '&quot;')})">编辑</button>
          <button class="btn-small btn-danger" onclick="deleteRule('${rule.name}')">删除</button>
        </div>
      ` : ''}
    </div>
  `;
}

function getSeverityText(severity) {
  const map = { critical: '紧急', warning: '警告', info: '信息' };
  return map[severity] || severity;
}

function showAddRuleModal() {
  editingRule = null;
  document.getElementById('rule-modal-title').textContent = '添加故障规则';
  document.getElementById('rule-edit-id').value = '';
  document.getElementById('rule-form').reset();
  document.getElementById('rule-modal-overlay').style.display = 'flex';
}

function editRule(rule) {
  editingRule = rule;
  document.getElementById('rule-modal-title').textContent = '编辑故障规则';
  document.getElementById('rule-edit-id').value = rule.name;
  document.getElementById('rule-name').value = rule.name;
  document.getElementById('rule-bit-position').value = rule.bit_position;
  document.getElementById('rule-severity').value = rule.severity;
  document.getElementById('rule-description').value = rule.description || '';
  document.getElementById('rule-condition-type').value = rule.condition_type || 'status';
  document.getElementById('rule-threshold-var').value = rule.threshold_var || '';
  document.getElementById('rule-related-vars').value = (rule.related_variables || []).join(',');
  document.getElementById('rule-unit').value = rule.unit || '';
  document.getElementById('rule-modal-overlay').style.display = 'flex';
}

function closeRuleModal() {
  document.getElementById('rule-modal-overlay').style.display = 'none';
  editingRule = null;
}

document.getElementById('rule-form').addEventListener('submit', function(e) {
  e.preventDefault();
  
  const deviceType = document.getElementById('device-selector').value;
  const data = {
    device_type: deviceType,
    name: document.getElementById('rule-name').value,
    bit_position: parseInt(document.getElementById('rule-bit-position').value),
    severity: document.getElementById('rule-severity').value,
    description: document.getElementById('rule-description').value,
    condition_type: document.getElementById('rule-condition-type').value,
    threshold_var: document.getElementById('rule-threshold-var').value || null,
    related_variables: document.getElementById('rule-related-vars').value
      ? document.getElementById('rule-related-vars').value.split(',').map(s => s.trim())
      : [],
    unit: document.getElementById('rule-unit').value || ''
  };
  
  const method = editingRule ? 'PUT' : 'POST';
  const url = editingRule 
    ? `/api/fault-rules/${encodeURIComponent(editingRule.name)}`
    : '/api/fault-rules';
  
  fetch(url, {
    method: method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  .then(res => res.json())
  .then(() => {
    closeRuleModal();
    loadFaultRules(deviceType);
  })
  .catch(err => console.error('保存规则失败:', err));
});

function deleteRule(ruleName) {
  if (!confirm(`确定要删除规则 "${ruleName}" 吗？`)) return;
  
  const deviceType = document.getElementById('device-selector').value;
  
  fetch(`/api/fault-rules/${encodeURIComponent(ruleName)}`, {
    method: 'DELETE',
    headers: { 'device_type': deviceType }
  })
  .then(res => res.json())
  .then(() => {
    loadFaultRules(deviceType);
  })
  .catch(err => console.error('删除规则失败:', err));
}

function reloadRules() {
  fetch('/api/fault-rules/reload', { method: 'POST' })
    .then(res => res.json())
    .then(() => {
      const deviceType = document.getElementById('device-selector').value;
      loadFaultRules(deviceType);
      alert('规则已重新加载');
    })
    .catch(err => console.error('重新加载失败:', err));
}

document.getElementById('device-selector').addEventListener('change', function() {
  loadFaultRules(this.value);
});
```

## 使用说明

1. **查看规则**: 选择设备类型后自动显示该设备的所有故障规则
2. **添加规则**: 点击"+ 添加规则"按钮，填写表单后保存
3. **编辑规则**: 点击自定义规则右侧的"编辑"按钮
4. **删除规则**: 点击自定义规则右侧的"删除"按钮
5. **重新加载**: 点击"重新加载"按钮使规则生效

## 自定义规则存储

自定义规则保存在 `config/custom_fault_rules.json` 文件中，格式如下：

```json
{
  "RXB800": [
    {
      "name": "自定义故障1",
      "bit_position": 100,
      "severity": "warning",
      "description": "自定义故障描述",
      "condition_type": "status",
      "threshold_var": null,
      "related_variables": [],
      "unit": ""
    }
  ]
}
```

## API文档

### GET /api/fault-rules
获取指定设备的故障规则列表

**参数**: `device_type` (可选，默认RXB800)

**响应**:
```json
{
  "device_type": "RXB800",
  "builtin_rules": [...],
  "custom_rules": [...],
  "total_count": 88
}
```

### POST /api/fault-rules
添加自定义故障规则

**请求体**:
```json
{
  "device_type": "RXB800",
  "name": "自定义故障",
  "bit_position": 100,
  "severity": "warning",
  "description": "描述",
  "condition_type": "status",
  "threshold_var": "阈值变量名",
  "related_variables": ["变量1", "变量2"],
  "unit": "°C"
}
```

### PUT /api/fault-rules/<rule_name>
更新自定义故障规则

**请求体**: 同POST

### DELETE /api/fault-rules/<rule_name>
删除自定义故障规则

**请求头**: `device_type` - 设备类型

### POST /api/fault-rules/reload
重新加载故障规则

### GET /api/fault-rules/devices
获取支持的设备类型列表

**响应**:
```json
{
  "devices": ["RXB800", "RXA1300"]
}
```

## 故障规则字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 规则名称（唯一标识） |
| `bit_position` | integer | 是 | DB51中的位位置 |
| `severity` | string | 是 | 严重程度: critical/warning/info |
| `description` | string | 否 | 故障描述 |
| `condition_type` | string | 否 | 检测类型: status/analog |
| `threshold_var` | string | 否 | 动态阈值变量名 |
| `related_variables` | array | 否 | 相关变量列表 |
| `unit` | string | 否 | 单位 |