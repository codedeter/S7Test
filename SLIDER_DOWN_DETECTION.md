# 滑块下行异常检测系统

## 概述

本项目新增了滑块下行异常检测功能，能够在检测到滑块下行指令发出但实际未执行时，推理出具体的前置条件不满足原因。

## 新增文件

### 1. `src/analysis/slider_down_detector.py`
滑块下行异常检测核心模块，提供以下功能：

- **SliderDownCondition**: 定义滑块下行的前置条件
- **SliderDownAbnormalDetector**: 异常检测器主类
  - `update_facts(facts)`: 更新PLC数据
  - `check_abnormal()`: 检查异常状态
  - `get_abnormal_reasoning()`: 获取详细的推理报告

### 2. 更新的文件
- `src/analysis/fault_engine.py`: 集成滑块检测功能
  - 新增 `check_slider_down_abnormal()` 方法
  - 新增 `get_slider_down_reasoning()` 方法
  - 更新 `format_fault_report()` 支持滑块异常分析
  - 新增多个滑块下行相关故障规则

## 滑块下行前置条件

基于梯形图分析，滑块下行需要满足以下条件：

| 条件名称 | 变量名 | 期望值 | 说明 |
|---------|--------|--------|------|
| 急停合格 | 急停合格 | 0 | 急停按钮未按下 |
| 滑块在上限 | 滑块上限 | 1 | 滑块处于上限位置 |
| 双手合格 | 双手合格 | 1 | 双手操作按钮合格 |
| 电机启动主控 | 电机启动主控 | 1 | 电机主控已启动 |
| 允许下行 | 允许下行 | 1 | 系统允许滑块下行 |
| 移动台合格 | 移动台合格 | 1 | 移动台位置合格 |
| 驱动器正常 | 驱动器正常 | 0 | 驱动器无故障 |
| 系统无错误 | 系统Error | 0 | 系统无错误信号 |
| 安全爪打开 | 安全爪打开到位 | 1 | 安全爪已打开到位 |
| 安全爪主控 | 安全爪主控 | 1 | 安全爪主控激活 |

## 使用方法

### 基本使用

```python
from src.analysis.slider_down_detector import create_slider_detector

# 创建检测器
detector = create_slider_detector()

# 更新PLC数据
plc_data = {
    '急停合格': 0,
    '滑块上限': 1,
    '双手合格': 1,
    '电机启动主控': 1,
    '滑块慢下': 1,  # 下行指令
    # ... 其他变量
}
detector.update_facts(plc_data)

# 检查异常
result = detector.check_abnormal()
if result['abnormal']:
    # 获取推理报告
    report = detector.get_abnormal_reasoning()
    print(report)
```

### 集成到故障引擎

```python
from src.analysis.fault_engine import create_fault_rules, format_fault_report

# 创建规则引擎
engine = create_fault_rules()

# 更新事实数据
engine.update_facts(plc_data)

# 检查滑块下行异常
slider_result = engine.check_slider_down_abnormal()
slider_reasoning = engine.get_slider_down_reasoning()

# 常规故障检测
triggered_rules = engine.forward_chain()

# 生成完整报告
report = format_fault_report(triggered_rules, plc_data, slider_reasoning)
print(report)
```

## 示例文件

- `simple_test.py`: 简单功能测试
- `example_usage.py`: 完整使用示例

## 运行测试

```bash
# 简单测试
python simple_test.py

# 使用示例
python example_usage.py
```

## 异常推理报告示例

```
============================================================
滑块下行异常推理报告
============================================================

异常描述: 检测到滑块下行指令发出，但存在前置条件不满足，1个前置条件不满足

不满足的前置条件 (1个):

1. 急停合格
   描述: 急停按钮未按下
   期望值: 0
   当前值: 1
   状态: 不满足

当前状态:
  下行指令: 激活
  滑块移动: 是

============================================================
建议排查顺序:
1. 检查急停按钮状态
2. 确认滑块是否在上限位置
3. 检查双手操作按钮
4. 确认电机是否已启动
5. 检查安全门和安全爪状态
6. 查看系统错误和驱动器状态
============================================================
```

## 新增故障规则

| 规则ID | 规则名称 | 说明 |
|--------|---------|------|
| F001 | 滑块下行异常 | 下行指令发出但滑块未移动 |
| F001_1 | 急停阻止下行 | 急停按下阻止滑块下行 |
| F001_2 | 双手不合格 | 双手操作不合格 |
| F001_3 | 电机未启动 | 电机主控未启动 |
| F001_4 | 驱动器故障 | 驱动器检测到故障 |
| F001_5 | 系统错误 | PLC检测到系统错误 |
| F001_6 | 不允许下行 | 系统未允许下行 |
| F001_7 | 移动台不合格 | 移动台位置不合格 |
| F001_8 | 安全爪未打开 | 安全爪未完全打开 |
