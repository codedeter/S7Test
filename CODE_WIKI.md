# PLC 数据监控系统 - Code Wiki

## 1. 项目概述

这是一个基于 Python + Flask + SocketIO 的工业 PLC 数据监控系统，主要功能包括：

- **实时数据采集**：通过 snap7 库连接西门子 S7 系列 PLC
- **多设备管理**：支持同时监控多个 PLC 设备
- **故障检测与推理**：多种设备类型的专用故障检测器和根因分析
- **异常检测**：基于统计分析的异常数据识别
- **实时数据推送**：SocketIO 实时推送数据到前端
- **数据持久化**：SQLite 数据库存储，支持按设备分区管理
- **滑块下行异常检测**：专门针对 RX 系列设备的特殊检测功能

**版本**：3.1.0

---

## 2. 目录结构

```
.
├── config/                    # 配置模块
│   ├── __init__.py
│   ├── config.py             # 主配置类
│   ├── devices_config.py     # 设备配置
│   └── plc_tags.py           # PLC 标签配置
├── docs/                     # 文档目录
├── plc_definitions/          # PLC 定义文件
├── public/                   # 前端静态文件
│   ├── icon.ico
│   └── index.html
├── src/                      # 源代码主目录
│   ├── analysis/             # 分析模块（故障检测、异常检测）
│   ├── api/                  # REST API 路由
│   ├── data/                 # 数据存储
│   ├── devices/              # 设备管理
│   ├── parsers/              # 解析器
│   ├── plc/                  # PLC 通信
│   ├── serialization/        # 数据序列化
│   ├── services/             # 业务服务层
│   ├── socketio_handler/     # SocketIO 处理
│   ├── startup/              # 启动管理
│   ├── utils/                # 工具函数
│   └── server.py             # 主服务器入口
├── tests/                    # 测试模块
├── tools/                    # 工具脚本
├── .env.example              # 环境变量示例
├── requirements.txt          # Python 依赖
├── run.py                    # 启动脚本
├── start.bat                 # Windows 启动脚本
└── start.sh                  # Linux/Mac 启动脚本
```

---

## 3. 系统架构

### 3.1 架构分层

```
┌─────────────────────────────────────────────────────────┐
│                  Web 客户端层                           │
│              (浏览器 / 监控面板)                        │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│               API & SocketIO 层                        │
│         (Flask REST API + SocketIO 实时推送)          │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                业务服务层 (DataProcessor)              │
│  ┌─────────────┬─────────────┬──────────────┐         │
│  │数据处理     │故障检测     │异常分析      │         │
│  └─────────────┴─────────────┴──────────────┘         │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                 设备管理层 (DeviceManager)             │
│    ┌──────────────┬──────────────┬──────────────┐      │
│    │PLCClient     │PLCClient     │连接池管理    │      │
│    │(设备1)       │(设备2)       │健康检查      │      │
│    └──────────────┴──────────────┴──────────────┘      │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                 PLC 设备层                              │
│    (S7-1200 / S7-1500 / 其他工业设备)                 │
└─────────────────────────────────────────────────────────┘
```

### 3.2 数据流向

```
PLC 设备 
    ↓
PLCClient (snap7 通信)
    ↓
DeviceCollector (数据采集)
    ↓
DataProcessor (数据处理中心)
    ├─→ DataStorage (持久化存储)
    ├─→ DataAnalyzer (异常检测)
    ├─→ FaultDetector (故障检测)
    ├─→ SliderDetector (滑块检测)
    └─→ DroolsEngine (规则引擎)
            ↓
    SocketIO 实时推送
            ↓
    Web 客户端
```

---

## 4. 核心模块说明

### 4.1 配置模块 (`config/`)

#### [config.py](file:///workspace/config/config.py)
- **Config 类**：主配置类，包含所有系统配置
- **功能**：
  - PLC 连接配置（IP、机架、槽位）
  - 数据采集配置（采样间隔、历史保留天数）
  - 分析参数配置（窗口大小、阈值）
  - 服务器配置（端口、调试模式）
  - 数据库配置（路径、缓存大小）
  - 连接池配置（最大工作线程、健康检查间隔）
- **特点**：支持通过环境变量覆盖默认配置

#### [devices_config.py](file:///workspace/config/devices_config.py)
- 设备配置定义和管理
- 定义 `DeviceType` 枚举类
- `create_device_configs()` 函数返回设备配置列表

### 4.2 设备管理模块 (`src/devices/`)

#### [device_manager.py](file:///workspace/src/devices/device_manager.py)
- **DeviceManager 类**：核心设备管理器
  - 设备注册与管理
  - 连接池管理
  - 数据采集调度
  - 连接状态监控

#### [connection_manager.py](file:///workspace/src/devices/connection_manager.py)
- 连接池管理
- 连接健康检查
- 自动重连机制（指数退避策略）

#### [device_config.py](file:///workspace/src/devices/device_config.py)
- `DeviceConfig` 数据类：设备配置定义

### 4.3 分析模块 (`src/analysis/`)

#### [fault_detector_base.py](file:///workspace/src/analysis/fault_detector_base.py) - 故障检测框架

**核心类**：

1. **FaultBit (dataclass)**
   - 故障位定义
   - 字段：name, bit_position, severity, description, related_variables

2. **FaultDetectionResult (dataclass)**
   - 故障检测结果
   - 字段：fault_name, detected, severity, description, related_variables

3. **BaseFaultDetector (abstract class)**
   - 所有设备特定故障检测器的基类
   - 提供通用的故障检测逻辑
   - **子类需实现**：
     - `_init_fault_bits()`：初始化故障位定义
     - `_init_fault_relations()`：初始化故障与变量的关系
   - **主要方法**：
     - `detect_faults()`：检测所有故障位
     - `get_active_faults()`：获取活动故障列表
     - `get_fault_summary()`：获取故障摘要

4. **FaultDetectorRegistry**
   - 故障检测器注册中心
   - 管理所有设备类型的检测器
   - 提供统一的故障检测入口

5. **RXSeriesFaultAnalyzer**
   - RX 系列设备专用故障分析器
   - 包含滑块下行异常检测功能

#### [rxb800_fault_detector.py](file:///workspace/src/analysis/rxb800_fault_detector.py)
- **RXB800FaultDetector 类**：RXB800 设备专用故障检测器
- 包含 88 个故障位定义
- 支持条件过滤（安全条件不满足时忽略某些故障）

#### [rxa1300_fault_detector.py](file:///workspace/src/analysis/rxa1300_fault_detector.py)
- **RXA1300FaultDetector 类**：RXA1300 设备专用故障检测器

#### [configurable_fault_detector.py](file:///workspace/src/analysis/configurable_fault_detector.py)
- 可配置的故障检测器
- 支持通过配置创建检测器（用于 RX 系列其他设备）

#### [data_analyzer.py](file:///workspace/src/analysis/data_analyzer.py)
- **DataAnalyzer 类**：数据异常分析器
- 基于 Z 分数和趋势分析
- 提供预测功能

#### [fault_tracker.py](file:///workspace/src/analysis/fault_tracker.py)
- **FaultTracker 类**：故障追踪器
- 追踪活动故障
- 计算故障持续时间
- 支持故障恢复检测

- **AnomalyTracker 类**：异常追踪器
- 追踪活动异常
- 支持异常过期清理

#### [slider_down_detector.py](file:///workspace/src/analysis/slider_down_detector.py)
- **SliderDownAbnormalDetector 类**：滑块下行异常检测器
- 基于梯形图分析
- 检测滑块下行指令发出但未执行的异常
- 推理前置条件不满足的原因

#### [drools_lite_engine.py](file:///workspace/src/analysis/drools_lite_engine.py)
- **DroolsLiteEngine 类**：轻量级规则引擎
- 支持事实插入和规则匹配

#### [fault_reasoner.py](file:///workspace/src/analysis/fault_reasoner.py)
- **FaultReasoningEngine 类**：故障推理引擎
- 根因分析
- 故障关联性推理

#### [io_fault_integrator.py](file:///workspace/src/analysis/io_fault_integrator.py)
- **IOFaultIntegrator 类**：IO 故障集成器
- IO 变量与故障的映射管理

### 4.4 数据处理模块 (`src/services/`)

#### [data_processor.py](file:///workspace/src/services/data_processor.py) - 核心服务层

**DataProcessor 类**：数据处理中心

**主要职责**：
- 协调数据采集、处理和分发
- 集成所有分析组件
- 管理数据缓冲区
- 准备 SocketIO 推送数据

**核心属性**：
- `data_storage`：数据存储实例
- `data_analyzer`：数据异常分析器
- `drools_engine`：规则引擎
- `fault_tracker`：故障追踪器
- `anomaly_tracker`：异常追踪器
- `slider_detector`：滑块检测器
- `fault_reasoner`：故障推理器
- `io_fault_integrator`：IO 故障集成器

**核心方法**：
- `process_device_data()`：处理设备数据（主入口）
- `detect_device_faults()`：检测设备故障
- `prepare_socketio_data()`：准备 SocketIO 数据
- `get_pending_anomalies()`：获取待处理异常
- `get_fault_status()`：获取故障状态

### 4.5 数据存储模块 (`src/data/`)

#### [data_storage.py](file:///workspace/src/data/data_storage.py)

**DataStorage 类**：SQLite 数据存储管理器

**核心特性**：
- 异步写入（后台线程批量写入）
- LRU 缓存（减少数据库查询）
- 按设备分区管理
- 自动清理过期数据
- 数据库优化（VACUUM/ANALYZE）

**主要数据表**：
1. `plc_data`：PLC 数据记录
2. `anomalies`：异常记录
3. `fault_records`：故障记录
4. `devices`：设备配置表

**主要方法**：
- `batch_insert_plc_data()`：批量插入 PLC 数据
- `insert_anomaly()`：插入异常记录
- `insert_fault_record()`：插入故障记录
- `get_plc_data_by_device()`：按设备查询 PLC 数据
- `get_anomalies_by_device()`：按设备查询异常
- `get_faults_by_device()`：按设备查询故障
- `delete_device_data()`：删除指定设备的所有数据
- `get_device_data_summary()`：获取设备数据汇总

### 4.6 API 模块 (`src/api/`)

#### [routes.py](file:///workspace/src/api/routes.py)
- REST API 路由定义
- 主要端点：
  - `/api/health`：健康检查
  - `/api/devices`：设备列表
  - `/api/data`：历史数据查询
  - `/api/anomalies`：异常记录查询
  - `/api/faults/active`：活动故障查询
  - `/api/storage/stats`：存储统计
  - `/api/device/{device_id}/data`：按设备查询数据
  - `/api/device/{device_id}/data` (DELETE)：删除设备数据

### 4.7 SocketIO 模块 (`src/socketio_handler/`)

#### [events.py](file:///workspace/src/socketio_handler/events.py)
- **SocketIOHandler 类**：SocketIO 事件处理器
- **DataCollectionTask 类**：数据采集任务
- 事件处理：
  - `connect`：客户端连接
  - `disconnect`：客户端断开
  - `subscribe`：订阅设备/标签
  - `unsubscribe`：取消订阅
  - `request_full_snapshot`：请求完整数据快照

#### [subscription_manager.py](file:///workspace/src/socketio_handler/subscription_manager.py)
- **SubscriptionManager 类**：订阅管理器
- 管理客户端订阅

### 4.8 启动管理模块 (`src/startup/`)

#### [startup_manager.py](file:///workspace/src/startup/startup_manager.py)
- **StartupManager 类**：启动管理器
- **StartupPhase 枚举**：启动阶段定义
- 启动阶段：
  1. 数据库初始化
  2. 设备管理器创建
  3. 设备初始化
  4. Flask 应用创建
  5. 路由注册
  6. 服务启动
  7. 后台连接启动

### 4.9 工具模块 (`src/utils/`)

#### [error_handling.py](file:///workspace/src/utils/error_handling.py)
- **GlobalErrorHandler 类**：全局异常处理器
- **ErrorType 枚举**：错误类型定义
- 提供安全执行、重试机制

#### [validation.py](file:///workspace/src/utils/validation.py)
- **ConfigValidator 类**：配置验证器
- **RuntimeChecker 类**：运行时检查器

### 4.10 主服务器模块

#### [server.py](file:///workspace/src/server.py)
- **create_app()**：创建 Flask 应用
- **init_devices()**：初始化设备
- **start_background_connection()**：启动后台连接
- **register_shutdown_handlers()**：注册关闭处理器
- **main()**：主入口函数

启动流程：
1. 创建 StartupManager
2. 初始化数据库
3. 创建 DeviceManager
4. 初始化设备
5. 创建 Flask 应用和 SocketIO
6. 注册路由
7. 初始化服务
8. 启动后台连接
9. 运行服务器

---

## 5. 关键类与函数

### 5.1 DeviceManager（设备管理器）
**位置**：[src/devices/device_manager.py](file:///workspace/src/devices/device_manager.py)

**主要方法**：
- `add_device(config)`：添加设备
- `connect_all()`：连接所有设备
- `collect_data()`：采集数据
- `get_device_status(device_id)`：获取设备状态

### 5.2 DataProcessor（数据处理器）
**位置**：[src/services/data_processor.py](file:///workspace/src/services/data_processor.py)

**核心流程**：
```python
process_device_data(all_device_data)
  ├─ 数据缓冲管理
  ├─ 数据存储（异步写入）
  ├─ 异常检测（DataAnalyzer）
  ├─ 规则引擎（DroolsLiteEngine）
  ├─ 滑块检测（SliderDownDetector）
  └─ 故障检测（FaultDetector）
```

### 5.3 BaseFaultDetector（故障检测器基类）
**位置**：[src/analysis/fault_detector_base.py](file:///workspace/src/analysis/fault_detector_base.py)

**检测流程**：
1. 检查故障位状态（DB51 数据）
2. 对于状态类型故障：直接检查位值
3. 对于模拟量类型故障：检查相关变量是否超出范围
4. 应用安全条件过滤
5. 返回检测结果

### 5.4 DataStorage（数据存储）
**位置**：[src/data/data_storage.py](file:///workspace/src/data/data_storage.py)

**异步写入机制**：
- 使用 Queue 缓冲写入任务
- 后台线程批量处理
- 支持回调通知

---

## 6. 数据库设计

### 6.1 表结构

#### plc_data 表 - PLC 数据记录
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| timestamp | DATETIME | 时间戳 |
| device_id | TEXT | 设备 ID（分区键） |
| db_number | INTEGER | 数据块号 |
| address | INTEGER | 地址 |
| tag_name | TEXT | 标签名 |
| value | REAL | 值 |
| quality | INTEGER | 数据质量 |

#### anomalies 表 - 异常记录
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| timestamp | DATETIME | 时间戳 |
| device_id | TEXT | 设备 ID（分区键） |
| db_number | INTEGER | 数据块号 |
| address | INTEGER | 地址 |
| tag_name | TEXT | 标签名 |
| value | REAL | 值 |
| predicted_value | REAL | 预测值 |
| confidence | REAL | 置信度 |
| message | TEXT | 异常信息 |

#### fault_records 表 - 故障记录
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| fault_name | TEXT | 故障名称 |
| device_id | TEXT | 设备 ID（分区键） |
| start_time | DATETIME | 开始时间 |
| end_time | DATETIME | 结束时间 |
| duration_seconds | REAL | 持续时间（秒） |
| severity | TEXT | 严重程度 |
| related_variables | TEXT | 相关变量 |
| resolved | INTEGER | 是否已解决（0/1） |
| notes | TEXT | 备注 |

#### devices 表 - 设备配置
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| device_id | TEXT | 设备 ID（唯一） |
| device_name | TEXT | 设备名称 |
| ip_address | TEXT | IP 地址 |
| device_type | TEXT | 设备类型 |
| rack | INTEGER | 机架号 |
| slot | INTEGER | 槽位号 |
| enabled | INTEGER | 是否启用 |
| last_connected | DATETIME | 最后连接时间 |
| status | TEXT | 设备状态 |

### 6.2 索引优化

| 索引名 | 表 | 字段 | 用途 |
|--------|----|------|------|
| idx_plc_data_device_id | plc_data | device_id | 按设备查询 |
| idx_plc_data_timestamp | plc_data | timestamp | 按时间查询 |
| idx_plc_data_device_timestamp | plc_data | device_id, timestamp | 设备+时间联合查询 |
| idx_plc_data_db_address | plc_data | db_number, address | 数据块+地址查询 |
| idx_plc_data_device_db | plc_data | device_id, db_number | 设备+数据块查询 |
| idx_anomalies_device_id | anomalies | device_id | 按设备查询 |
| idx_anomalies_timestamp | anomalies | timestamp | 按时间查询 |
| idx_anomalies_device_timestamp | anomalies | device_id, timestamp | 设备+时间联合查询 |
| idx_fault_records_device | fault_records | device_id | 按设备查询 |
| idx_fault_records_resolved | fault_records | resolved | 按状态查询 |
| idx_fault_records_device_resolved | fault_records | device_id, resolved | 设备+状态查询 |
| idx_devices_device_id | devices | device_id | 设备配置查询 |

---

## 7. API 接口文档

### 7.1 健康检查
```
GET /api/health
```
返回系统健康状态

### 7.2 设备管理
```
GET /api/devices
```
获取所有设备列表

```
GET /api/device/{device_id}/status
```
获取指定设备状态

### 7.3 数据查询
```
GET /api/data?startTime=&endTime=&dbNumber=&deviceId=
```
查询历史 PLC 数据

```
GET /api/device/{device_id}/data?startTime=&endTime=&dbNumber=
```
按设备查询历史数据

### 7.4 异常查询
```
GET /api/anomalies?startTime=&endTime=&deviceId=
```
查询异常记录

```
GET /api/device/{device_id}/anomalies?startTime=&endTime=
```
按设备查询异常

### 7.5 故障查询
```
GET /api/faults/active?deviceId=
```
查询活动故障

```
GET /api/device/{device_id}/faults
```
按设备查询故障

### 7.6 存储管理
```
GET /api/storage/stats
```
获取存储统计

```
POST /api/storage/optimize
```
优化数据库

### 7.7 设备数据管理
```
DELETE /api/device/{device_id}/data
```
删除指定设备的所有数据

---

## 8. SocketIO 事件

### 8.1 服务端 → 客户端

| 事件 | 说明 |
|------|------|
| data | 推送增量数据 |
| fault_update | 故障状态更新 |
| anomaly_update | 异常状态更新 |

### 8.2 客户端 → 服务端

| 事件 | 说明 |
|------|------|
| connect | 连接 |
| disconnect | 断开 |
| subscribe | 订阅设备/标签 |
| unsubscribe | 取消订阅 |
| request_full_snapshot | 请求完整数据快照 |
| ping | 心跳检测 |

---

## 9. 配置说明

### 9.1 环境变量

所有配置项可通过环境变量覆盖：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| PLC_HOST | 172.15.14.150 | PLC IP 地址 |
| PLC_RACK | 0 | 机架号 |
| PLC_SLOT | 1 | 槽位号 |
| PLC_CONNECTION_TIMEOUT | 10000 | 连接超时（ms） |
| PLC_RETRY_INTERVAL | 5000 | 重连间隔（ms） |
| DATA_SAMPLING_INTERVAL | 100 | 采样间隔（ms） |
| DATA_HISTORY_DAYS | 30 | 历史保留天数 |
| ANALYSIS_WINDOW_SIZE | 60 | 分析窗口大小 |
| ANALYSIS_THRESHOLD | 0.8 | 异常阈值 |
| SERVER_PORT | 3000 | 服务器端口 |
| SERVER_HOST | 0.0.0.0 | 监听地址 |
| DATABASE_PATH | ./database.db | 数据库路径 |
| SIMULATION_MODE | 1 | 模拟模式（0/1） |

### 9.2 设备 ID 映射

| 设备 ID | 设备类型 | 说明 |
|---------|----------|------|
| plc_001 | RXA1300 | 主 PLC |
| plc_002 | RXB800 | RXB800 设备 |
| plc_rxa800 | RXA800 | RXA800 设备 |
| plc_rxa630_1 | RXA630 | RXA630 设备 1 |
| plc_rxa630_2 | RXA630 | RXA630 设备 2 |
| plc_rxa630_3 | RXA630 | RXA630 设备 3 |

---

## 10. 依赖关系

### 10.1 Python 依赖

| 库 | 版本 | 用途 |
|----|------|------|
| python-snap7 | 1.3.0 | PLC 通信 |
| flask | 2.3.3 | Web 框架 |
| flask-socketio | 5.3.6 | SocketIO 支持 |
| numpy | 1.26.4 | 数值计算 |
| pandas | 2.2.2 | 数据处理 |
| scikit-learn | 1.4.2 | 机器学习/统计 |
| matplotlib | 3.8.4 | 数据可视化 |
| msgpack | 1.0.8 | 数据序列化 |
| python-dotenv | 1.0.0 | 环境变量 |
| eventlet | 0.33.3 | 异步支持 |
| gevent | 23.9.1 | 异步支持 |
| openpyxl | 3.1.2 | Excel 解析 |

### 10.2 模块依赖图

```
server.py
├─ config/
│   ├─ config.py
│   └─ devices_config.py
├─ src/devices/
│   ├─ device_manager.py
│   ├─ connection_manager.py
│   └─ device_config.py
├─ src/api/
│   └─ routes.py
├─ src/services/
│   └─ data_processor.py
│       ├─ src/data/data_storage.py
│       ├─ src/analysis/
│       │   ├─ data_analyzer.py
│       │   ├─ fault_detector_base.py
│       │   ├─ rxb800_fault_detector.py
│       │   ├─ rxa1300_fault_detector.py
│       │   ├─ configurable_fault_detector.py
│       │   ├─ fault_tracker.py
│       │   ├─ slider_down_detector.py
│       │   ├─ drools_lite_engine.py
│       │   ├─ fault_reasoner.py
│       │   └─ io_fault_integrator.py
│       └─ src/utils/
│           ├─ error_handling.py
│           └─ validation.py
├─ src/socketio_handler/
│   ├─ events.py
│   └─ subscription_manager.py
└─ src/startup/
    └─ startup_manager.py
```

---

## 11. 部署与运行

### 11.1 快速启动

#### Windows
```batch
start.bat
```

#### Linux/Mac
```bash
chmod +x start.sh
./start.sh
```

#### 手动启动
```bash
pip install -r requirements.txt
python run.py
```

### 11.2 访问

- Web 界面：http://localhost:3000
- API 文档：参考 [API 接口文档](#7-api-接口文档)

### 11.3 生产环境部署建议

1. **环境配置**：
   - 创建 `.env` 文件（从 `.env.example` 复制）
   - 修改 PLC_HOST 和其他必要配置
   - 设置 SIMULATION_MODE=0 关闭模拟模式

2. **安全性**：
   - 修改 SERVER_HOST 为具体 IP（非 0.0.0.0）
   - 修改默认端口
   - 使用 VPN 或内网访问 PLC

3. **数据管理**：
   - 定期备份 `database.db`
   - 配置合适的 DATA_HISTORY_DAYS
   - 定期执行数据库优化

---

## 12. 扩展开发

### 12.1 添加新设备类型

1. 在 `config/devices_config.py` 中添加设备配置
2. 在 `src/analysis/` 中创建新的故障检测器（继承 BaseFaultDetector）
3. 在 `src/analysis/fault_detector_base.py` 的 `create_detector()` 中注册
4. 在 `src/services/data_processor.py` 的 `_get_device_type()` 中添加映射

### 12.2 添加新的故障检测规则

1. 在设备特定的检测器中添加 FaultBit 定义
2. 在 `_init_fault_relations()` 中定义相关变量
3. 如需特殊过滤逻辑，重写 `_should_filter_fault()` 方法

### 12.3 添加新的 API 端点

1. 在 `src/api/routes.py` 中添加路由
2. 实现业务逻辑（可调用 DataProcessor）
3. 注册到 Flask 应用

---

## 13. 常见问题排查

### 13.1 PLC 连接失败
- 检查 PLC IP 地址是否正确
- 确认网络连接正常
- 验证 Rack 和 Slot 配置
- 检查防火墙设置

### 13.2 端口被占用
- 修改 `config/config.py` 中的 `SERVER_PORT`
- 或停止占用端口的程序

### 13.3 数据库访问错误
- 确保只有一个服务器实例运行
- 删除 `database.db` 后重启

### 13.4 设备数据查询慢
- 系统已自动创建设备 ID 索引
- 确保数据库文件所在磁盘有足够空间
- 定期清理过期数据

---

## 14. 参考文档

- [README.md](file:///workspace/README.md) - 用户指南
- [SLIDER_DOWN_DETECTION.md](file:///workspace/SLIDER_DOWN_DETECTION.md) - 滑块下行检测说明
- [docs/system_architecture.md](file:///workspace/docs/system_architecture.md) - 系统架构文档
- [docs/fault_detector_architecture.md](file:///workspace/docs/fault_detector_architecture.md) - 故障检测器架构
- [docs/fault_rules_integration.md](file:///workspace/docs/fault_rules_integration.md) - 故障规则集成

---

## 15. 维护记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 3.1.0 | 2026-04-28 | 当前版本，重构模块化架构，新增故障检测器框架，数据库按设备分区 |
| 2.1.0 | - | 重构模块化架构，新增故障检测器框架，数据库按设备分区 |

---

**文档生成时间**：2026-05-12
