# PLC数据监控系统 - 数据流程说明

## 系统架构概览

```
┌─────────────────┐
│ PLC设备         │ ← 物理设备
└────────┬────────┘
         │
┌────────▼────────┐
│ DeviceManager   │ ← 设备连接管理
│  ├─PLCClient    │   PLC连接
│  └─ConnectionPool│   连接池管理
└────────┬────────┘
         │
┌────────▼────────┐
│ DataProcessor   │ ← 数据处理核心
│  ├─DataStorage  │   数据存储
│  ├─DataAnalyzer │   数据分析
│  ├─FaultDetector│   故障检测
│  └─AnomalyDetect│   异常检测
└────────┬────────┘
         │
┌────────▼────────┐
│ SocketIOHandler │ ← 数据推送
│  ├─DataDelta    │   增量更新
│  ├─DataPacker   │   数据打包
│  └─Subscription │   订阅管理
└────────┬────────┘
         │
┌────────▼────────┐
│ 前端界面         │ ← 用户界面
└─────────────────┘
```

## 详细数据流程

### 1. 数据采集流程

```
1. 启动阶段
   ├─server.py:main() 启动
   ├─创建 DeviceManager
   ├─初始化所有设备配置
   └─启动后台连接线程

2. 数据采集
   ├─DataCollectionTask 线程定时采集（100ms间隔）
   ├─调用 device_manager.collect_all()
   │  ├─对每个设备调用 collect_all_data()
   │  ├─PLCClient.read_db() 读取DB块
   │  ├─PLCClient.read_m() 读取M区
   │  ├─PLCClient.read_i() 读取I区
   │  └─PLCClient.read_q() 读取Q区
   └─数据传递给 DataProcessor
```

### 2. 数据处理流程

```
DataProcessor.process_data() 处理数据
├─数据缓存到缓冲区
├─调用 detect_device_faults() 故障检测
├─调用 data_analyzer.analyze() 数据分析
├─调用 slider_detector 滑块检测
├─调用 fault_reasoner 故障推理
├─调用 io_fault_integrator IO故障整合
├─数据存储到 DataStorage
└─更新 latest_* 状态缓存
```

### 3. 数据推送流程

```
SocketIOHandler 推送线程
├─定时调用 prepare_socketio_data() 获取数据
├─计算数据增量变化 (DataDelta)
├─打包数据 (DataPacker)
├─通过订阅管理 (SubscriptionManager)
│  ├─过滤订阅的设备
│  ├─过滤订阅的标签
│  └─发送给对应的客户端
├─SocketIO.emit('data', ...) 推送数据
├─SocketIO.emit('fault_status', ...) 推送故障状态
└─SocketIO.emit('anomaly_update', ...) 推送异常更新
```

## 核心模块职责

### DeviceManager (设备管理)
- 管理多个PLC设备连接
- 连接池管理 (ConnectionPool)
- 网络监控与自动切换
- 数据采集接口

### DataProcessor (数据处理)
- 数据缓存与缓冲
- 故障检测与推理
- 异常检测
- 数据存储接口
- SocketIO数据准备

### SocketIOHandler (数据推送)
- WebSocket事件处理
- 客户端订阅管理
- 增量数据计算
- 数据打包发送

### DataStorage (数据存储)
- 历史数据存储
- 数据查询接口
- 数据持久化

## 数据流时序

```
时间轴 ────────────────────────────────────────────────────────>
      │               │               │               │
  T1  │  PLC采集     │               │               │
      ├─────────────→│               │               │
  T2  │               │  数据处理     │               │
      │               ├─────────────→│               │
  T3  │               │               │  数据推送     │
      │               │               ├─────────────→│
  T4  │  PLC采集     │               │               │
      ├─────────────→│               │               │
  T5  │               │  数据处理     │               │
      │               ├─────────────→│               │
  T6  │               │               │  数据推送     │
      │               │               ├─────────────→│
```

## 关键数据结构

### CollectedData (采集数据)
```python
{
    'device_id': 'plc_001',
    'device_name': 'RXB800压机PLC',
    'timestamp': 1234567890.123,
    'data': [
        {
            'db_number': 1,
            'address': 0,
            'tag_name': '保压选择',
            'value': 1,
            'quality': 1
        }
    ],
    'connected': True
}
```

### ProcessingResult (处理结果)
```python
{
    'device_data_map': {},  # 设备数据映射
    'anomalies': [],        # 异常列表
    'drools_results': [],   # 规则引擎结果
    'slider_results': [],   # 滑块检测结果
    'fault_status': {},     # 故障状态
    'fault_inferences': []  # 故障推理
}
```

## 配置与启动

### 配置文件
- `config/devices_config.py` - 设备配置
- `config/config.py` - 系统配置
- `config/rules/*.json` - 故障规则

### 启动流程
1. 初始化启动管理器
2. 初始化数据库
3. 创建设备管理器
4. 初始化设备配置
5. 创建Flask应用
6. 注册API路由
7. 启动服务
8. 后台连接设备
9. 启动数据采集
10. 启动SocketIO推送
