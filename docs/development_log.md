# 项目研发日志

## 项目概述

**项目名称**: PLC故障监测与推理系统  
**开发周期**: 2026年4月  
**目标**: 构建一个基于Python的PLC故障监测与智能推理系统，支持多设备接入和故障根因分析。

---

## 目录

1. [2026-04-29 - 启动流程优化](#2026-04-29---启动流程优化)
2. [2026-04-29 - 前后端数据交互优化](#2026-04-29---前后端数据交互优化)
3. [2026-04-29 - 设备连接管理优化](#2026-04-29---设备连接管理优化)
4. [2026-04-29 - 代码健壮性优化](#2026-04-29---代码健壮性优化)
5. [2026-04-29 - 数据存储优化](#2026-04-29---数据存储优化)
6. [2026-04-29 - 技术文档更新](#2026-04-29---技术文档更新)
7. [2026-04-29 - 故障监测与异常检测优化](#2026-04-29---故障监测与异常检测优化)
8. [2026-04-29 - 故障推理逻辑优化](#2026-04-29---故障推理逻辑优化)
9. [2026-04-29 - IO变量集成](#2026-04-29---io变量集成)
10. [2026-04-29 - 模块交互逻辑检查](#2026-04-29---模块交互逻辑检查)

---

## 2026-04-29 - 启动流程优化

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/startup/__init__.py` | 启动模块导出 |
| `src/startup/startup_manager.py` | 启动管理器核心类 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/server.py` | 集成启动管理器，添加信号处理和优雅关闭 |
| `src/api/routes.py` | 新增健康检查API端点 |

### 功能特性

- ✅ **启动状态管理** - 跟踪每个启动阶段的状态和耗时
- ✅ **信号处理** - SIGINT/SIGTERM信号处理，实现优雅关闭
- ✅ **健康检查API** - `/api/health` 和 `/api/startup/status` 端点
- ✅ **异常处理** - 阶段失败标记和错误信息记录

---

## 2026-04-29 - 前后端数据交互优化

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/serialization/__init__.py` | 序列化模块导出 |
| `src/serialization/data_serializer.py` | 数据序列化和压缩 |
| `src/socketio_handler/subscription_manager.py` | 客户端订阅管理 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/socketio_handler/events.py` | 新增订阅、取消订阅、心跳检测事件 |
| `src/services/data_processor.py` | 添加数据缓存和增量推送机制 |

### 功能特性

- ✅ **增量推送** - 只发送变化的数据，减少网络流量
- ✅ **数据压缩** - 支持zlib + MessagePack压缩
- ✅ **客户端订阅** - 支持设备/标签级别订阅
- ✅ **序列号机制** - 确保数据顺序，支持断点续传

---

## 2026-04-29 - 设备连接管理优化

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/devices/connection_manager.py` | 新增连接池管理器 |
| `src/devices/device_manager.py` | 集成连接池，添加统计数据 |
| `src/api/routes.py` | 新增连接池状态API |

### 功能特性

- ✅ **连接池管理** - 统一管理所有设备连接
- ✅ **智能退避策略** - 指数退避+随机抖动，避免重试风暴
- ✅ **健康检查线程** - 定期检查连接状态
- ✅ **连接统计** - 连接成功率、读取成功率、字节数统计

---

## 2026-04-29 - 代码健壮性优化

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/utils/error_handling.py` | 全局异常处理和日志模块 |
| `src/utils/validation.py` | 配置验证和运行时检查 |

### 功能特性

- ✅ **全局异常捕获** - `sys.excepthook` 统一处理
- ✅ **错误回调机制** - 支持多监听器
- ✅ **安全执行** - `safe_execute()` 自动捕获异常
- ✅ **重试机制** - `retry_with_backoff()` 带退避策略
- ✅ **配置验证** - 完整的验证规则
- ✅ **运行时检查** - 网络、端口、磁盘空间检查

---

## 2026-04-29 - 数据存储优化

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/data/data_storage.py` | 异步写入、LRU缓存、查询优化 |
| `src/api/routes.py` | 新增存储统计和数据库优化API |

### 功能特性

- ✅ **异步写入** - 使用Queue实现非阻塞写入
- ✅ **LRU缓存** - 最近最少使用缓存，大小限制10000条
- ✅ **批量聚合** - 一次处理最多10个写入任务
- ✅ **分页支持** - `limit` 和 `offset` 参数
- ✅ **存储统计** - 插入/更新/查询次数统计

---

## 2026-04-29 - 技术文档更新

### 修改文件

| 文件 | 说明 |
|------|------|
| `docs/fault_detector_architecture.md` | 更新故障检测器架构 |
| `docs/fault_rules_integration.md` | 更新故障规则集成指南 |

### 新增文件

| 文件 | 说明 |
|------|------|
| `docs/system_architecture.md` | 系统架构文档 |

---

## 2026-04-29 - 故障监测与异常检测优化

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/analysis/anomaly_detector.py` | 增强版异常检测器 |
| `src/analysis/enhanced_fault_detector.py` | 增强版故障检测器 |

### 功能特性

- ✅ **多算法异常检测** - Z-score、值突增/突降、值卡住、变化率检测
- ✅ **异常聚合** - 管理活跃异常和历史记录
- ✅ **故障分类** - 7种分类（温度、压力、油位、电机、网络、安全、系统）
- ✅ **故障严重程度** - 4级（INFO、WARNING、CRITICAL、EMERGENCY）
- ✅ **内置RX系列故障定义** - 20个通用故障

---

## 2026-04-29 - 故障推理逻辑优化

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/analysis/fault_reasoner.py` | 基础故障推理引擎 |
| `src/analysis/enhanced_fault_reasoner.py` | 增强版故障推理引擎 |

### 功能特性

- ✅ **多策略推理** - 直接原因、链式推理、统计分析、时序分析
- ✅ **故障关系规则** - 支持CAUSE、TRIGGER、SYMPTOM、CONCURRENT、PRECONDITION、CORRELATION
- ✅ **时序分析** - 根据故障发生时间顺序推断
- ✅ **置信度评估** - 考虑时间延迟和因果链的置信度计算
- ✅ **故障记录** - 记录故障发生和解决的时间序列

### 有效故障关系规则

| 源故障 | 目标故障 | 关系类型 | 置信度 | 说明 |
|--------|----------|----------|--------|------|
| 过滤器压差高 | 上油箱滤油受阻 | CAUSE | 0.92 | 压差高指示过滤器堵塞 |
| 急停按钮 | 紧急停止 | TRIGGER | 0.99 | 急停按钮触发紧急停止 |

---

## 2026-04-29 - IO变量集成

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/devices/io_variable_manager.py` | IO变量管理器（单例模式） |
| `src/analysis/io_fault_integrator.py` | IO故障集成器 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/parsers/xlsx_variable_parser.py` | 增强地址格式支持和健壮性 |

### 功能特性

- ✅ **多设备支持** - 为多个设备维护独立的IO配置
- ✅ **XLSX加载** - 支持博图软件导出的XLSX格式
- ✅ **IO-故障映射** - 管理IO变量与故障的关联关系
- ✅ **动态映射** - 支持运行时添加映射关系

---

## 2026-04-29 - 模块交互逻辑检查

### 模块依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                        run.py (入口)                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  startup    │  │   server    │  │    API      │
    │  manager    │  │   (Flask)   │  │  routes     │
    └─────────────┘  └──────┬──────┘  └─────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  devices    │  │   services  │  │  analysis   │
    │  manager    │  │ data        │  │ fault       │
    │  io_manager │  │ processor   │  │ reasoner    │
    └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
           │                │                │
           └────────────────┼────────────────┘
                            ▼
                    ┌─────────────┐
                    │    data     │
                    │   storage   │
                    └─────────────┘
```

### 核心交互流程

**1. 数据采集流程**
```
DeviceManager → PLCClient → 采集数据 → DataProcessor → DataStorage
```

**2. 故障检测流程**
```
DataProcessor → EnhancedFaultDetector → 检测故障 → FaultTracker → DataStorage
```

**3. 故障推理流程**
```
DataProcessor → EnhancedFaultReasoner → 推理根因 → IOFaultIntegrator → 增强结果
```

**4. 数据推送流程**
```
DataProcessor → SocketIOHandler → SubscriptionManager → 客户端
```

### 数据流说明

| 数据类型 | 来源 | 处理 | 存储/推送 |
|----------|------|------|-----------|
| PLC实时数据 | DeviceManager | DataProcessor | DataStorage + SocketIO |
| 故障检测结果 | EnhancedFaultDetector | FaultTracker | DataStorage |
| 故障推理结果 | EnhancedFaultReasoner | IOFaultIntegrator | 实时推送 |
| IO变量配置 | IOVariableManager | 设备初始化 | 内存缓存 |

---

## 当前项目结构

```
src/
├── analysis/                    # 分析模块
│   ├── __init__.py
│   ├── anomaly_detector.py      # 异常检测器
│   ├── configurable_fault_detector.py
│   ├── data_analyzer.py
│   ├── drools_lite_engine.py
│   ├── enhanced_fault_detector.py
│   ├── enhanced_fault_reasoner.py
│   ├── fault_detector_base.py
│   ├── fault_engine.py
│   ├── fault_reasoner.py
│   ├── fault_tracker.py
│   ├── io_fault_integrator.py
│   ├── plc_variable_loader.py
│   ├── rxa1300_fault_detector.py
│   ├── rxb800_fault_detector.py
│   ├── rxb800_rules.py
│   └── slider_down_detector.py
├── api/                         # API模块
│   ├── __init__.py
│   └── routes.py
├── config/                      # 配置模块
│   ├── __init__.py
│   ├── config.py
│   ├── devices_config.py
│   └── plc_tags.py
├── data/                        # 数据存储模块
│   ├── __init__.py
│   └── data_storage.py
├── devices/                     # 设备管理模块
│   ├── __init__.py
│   ├── connection_manager.py
│   ├── device_config.py
│   ├── device_manager.py
│   ├── io_variable_manager.py
│   └── plc_client.py
├── parsers/                     # 解析器模块
│   ├── __init__.py
│   ├── db_file_parser.py
│   └── xlsx_variable_parser.py
├── serialization/               # 序列化模块
│   ├── __init__.py
│   └── data_serializer.py
├── services/                    # 服务模块
│   ├── __init__.py
│   └── data_processor.py
├── socketio_handler/            # SocketIO模块
│   ├── __init__.py
│   ├── events.py
│   └── subscription_manager.py
├── startup/                     # 启动管理模块
│   ├── __init__.py
│   └── startup_manager.py
├── utils/                       # 工具模块
│   ├── __init__.py
│   ├── error_handling.py
│   └── validation.py
└── server.py                    # 服务器入口
```

---

## 待完成事项

| 优先级 | 任务 | 状态 |
|--------|------|------|
| 高 | 集成真实IO变量表 | 待处理 |
| 中 | 扩展故障关系规则 | 待处理 |
| 中 | 添加更多异常检测算法 | 待处理 |
| 低 | 完善测试用例 | 待处理 |

---

## 版本信息

**当前版本**: v1.0  
**最后更新**: 2026-04-29  
**开发状态**: 功能开发完成，待集成真实设备数据