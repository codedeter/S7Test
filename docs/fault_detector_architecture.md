# 故障检测器架构使用说明

## 架构概览

```
BaseFaultDetector (基类)
    ↓
ConfigurableFaultDetector (可配置检测器)
    ↓
RXFaultDetector (RX系列专用)
    ↓
RXB800FaultDetector / RXA1300FaultDetector (具体设备)
```

## 新增组件

### 1. `configurable_fault_detector.py` - 可配置的故障检测器

提供两种主要类：

- **ConfigurableFaultDetector** - 完全通过配置创建检测器
- **RXFaultDetector** - RX 系列设备的专用检测器（含基础故障）

### 2. `rxa1300_fault_detector.py` - RXA1300 设备检测器

示例展示如何创建新设备检测器

### 3. `fault_tracker.py` - 故障跟踪器

管理故障状态、历史记录和解决状态

## 使用方式

### 方式1: 创建新的专用设备检测器（类继承）

```python
# 示例：创建 RXA1300 检测器
from src.analysis.configurable_fault_detector import RXFaultDetector

class RXA1300FaultDetector(RXFaultDetector):
    def __init__(self):
        # 定义设备特定的故障
        additional_faults = [
            {
                'name': '自定义故障',
                'bit_position': 100,
                'severity': 'warning',
                'description': '设备特定故障'
            }
        ]
        super().__init__('RXA1300', additional_faults)
```

### 方式2: 使用工厂函数直接创建

```python
from src.analysis import create_detector

# 创建任意设备检测器
detector = create_detector('RXB800')     # 使用专用类
detector = create_detector('RXA1300')    # 使用专用类
detector = create_detector('RXB1000')    # 使用通用RX检测器
```

### 方式3: 完全通过配置创建

```python
from src.analysis.configurable_fault_detector import create_detector_from_config

config = {
    'inherit_rx_common': True,  # 是否继承RX系列基础故障
    'faults': [
        {
            'name': '设备特定故障',
            'bit_position': 100,
            'severity': 'warning',
            'description': '...',
            'related_variables': ['变量名'],
            'condition_type': 'analog',  # status/analog
            'threshold_var': '阈值变量名'
        }
    ]
}

detector = create_detector_from_config('MY-RX', config)
```

### 方式4: 使用故障跟踪器

```python
from src.analysis.fault_tracker import FaultTracker
from src.data.data_storage import DataStorage

data_storage = DataStorage()
fault_tracker = FaultTracker(data_storage)

# 记录故障
fault_tracker.record_fault(
    fault_name='油温过高',
    device_id='plc_001',
    severity='warning'
)

# 获取活跃故障
active_faults = fault_tracker.get_active_faults('plc_001')

# 解决故障
fault_tracker.resolve_fault('油温过高', 'plc_001')
```

## 故障配置字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | str | 是 | 故障名称 |
| `bit_position` | int | 是 | DB51中的位位置 |
| `severity` | str | 否 | 严重程度: critical/warning/info |
| `description` | str | 否 | 故障描述 |
| `related_variables` | list | 否 | 相关变量列表 |
| `condition_type` | str | 否 | 检测类型: status/analog/network |
| `threshold_var` | str | 否 | 动态阈值变量名（从DB1读取） |
| `threshold` | float | 否 | 固定阈值 |
| `normal_range` | tuple | 否 | 正常范围 (min, max) |
| `unit` | str | 否 | 单位 |

## RX系列通用故障

所有 RX 系列设备自动包含：

| 故障 | 位 | 说明 |
|------|----|------|
| 上油箱油温过低 | 0 | 油温低于阈值 |
| 上油箱油需冷却 | 1 | 油温需冷却 |
| 上油箱油温过高 | 2 | 油温超阈值 |
| 上油箱滤油受阻 | 3 | 滤油器故障 |
| 上油箱油空 | 4 | 油位过低 |

## 快速参考

### 添加新设备（3步）

1. **创建新文件**: `src/analysis/rxX00_fault_detector.py`
2. **继承 `RXFaultDetector`**，定义设备特定故障
3. **在 `fault_detector_base.py` 的 `create_detector` 中添加注册**

### 或者直接使用配置（推荐）

只需配置设备特定的故障列表，无需创建新文件！

## 文件列表

| 文件 | 说明 |
|------|------|
| `configurable_fault_detector.py` | 可配置架构核心 |
| `rxa1300_fault_detector.py` | RXA1300 示例 |
| `rxb800_fault_detector.py` | RXB800 原始实现（保留） |
| `fault_detector_base.py` | 基类和注册中心（已更新） |
| `fault_tracker.py` | 故障跟踪和状态管理 |
| `drools_lite_engine.py` | 轻量级规则引擎 |
| `data_analyzer.py` | 数据分析器 |
| `slider_down_detector.py` | 滑块检测模块 |