# PLC数据监控系统 - 技术文档

## 📋 系统简介

这是一个基于 Python + Flask + SocketIO 的 PLC 数据监控系统，用于：
- 实时采集 PLC 数据（通过 snap7 库连接西门子 PLC）
- 监控多个数据块（DB1、DB10、DB51等）数据
- 数据存储到 SQLite 数据库，**按设备ID分区管理**
- 实时 Web 界面展示
- **故障检测与推理** - 支持多种设备类型的故障位检测
- **异常分析** - 基于统计分析和规则引擎的异常检测

## 🖥️ 系统要求

- **操作系统**: Windows 7/10/11 或 Linux (Ubuntu, CentOS等)
- **Python**: 3.8 或更高版本
- **网络**: 能够访问 PLC 设备

## 🚀 快速部署

### Windows 系统

1. **解压部署包**到目标目录

2. **双击运行** `start.bat`

3. **等待安装完成**，首次运行会自动创建虚拟环境并安装依赖（约3-5分钟）

4. **打开浏览器**，访问 `http://localhost:3000`

### Linux/Mac 系统

1. **解压部署包**到目标目录

2. **打开终端**，进入部署目录

3. **添加执行权限**：
   ```bash
   chmod +x start.sh
   ```

4. **运行启动脚本**：
   ```bash
   ./start.sh
   ```

5. **打开浏览器**，访问 `http://localhost:3000`

## ⚙️ 配置说明

### PLC 连接配置

编辑 `config/config.py` 文件：

```python
# PLC连接配置
PLC_HOST = '172.15.14.150'   # PLC IP地址
PLC_RACK = 0                  # PLC机架号
PLC_SLOT = 1                  # PLC槽号
PLC_RETRY_INTERVAL = 5000     # 重连间隔（毫秒）

# 服务器配置
SERVER_HOST = '0.0.0.0'       # 服务器监听地址
SERVER_PORT = 3000            # 服务器端口

# 数据采集配置
DATA_SAMPLING_INTERVAL = 1000  # 数据采样间隔（毫秒）
```

### 设备配置

编辑 `config/devices_config.py` 文件添加或修改设备配置：

```python
def create_device_configs():
    return [
        DeviceConfig(
            device_id='plc_001',
            device_name='主PLC',
            device_type=DeviceType.PLC_S7_1200,
            ip_address='172.15.14.150',
            rack=0,
            slot=1,
            enabled=True
        ),
        # 添加更多设备...
    ]
```

## 📁 目录结构

```
PLCMonitor/
├── config/                  # 配置目录
│   ├── __pycache__/         # (自动生成)
│   ├── config.py            # 系统配置
│   ├── devices_config.py    # 设备配置
│   └── plc_tags.py          # PLC标签配置
├── public/                  # 前端文件
│   └── index.html           # 主页面
├── src/                     # 源代码
│   ├── __pycache__/         # (自动生成)
│   ├── analysis/            # 数据分析模块
│   │   ├── data_analyzer.py          # 数据异常分析器
│   │   ├── fault_detector_base.py    # 故障检测器基类框架
│   │   ├── fault_engine.py           # 规则引擎
│   │   ├── fault_tracker.py          # 故障/异常追踪器
│   │   ├── drools_lite_engine.py     # Drools Lite规则引擎
│   │   ├── plc_variable_loader.py    # PLC变量加载器
│   │   ├── rxb800_fault_detector.py  # RXB800故障检测器
│   │   ├── rxb800_rules.py           # RXB800故障规则
│   │   └── slider_down_detector.py   # 滑块下行异常检测器
│   ├── api/                 # API路由
│   │   └── routes.py        # REST API路由
│   ├── data/                # 数据存储
│   │   └── data_storage.py  # SQLite数据库操作（支持设备分区）
│   ├── devices/             # 设备管理
│   │   ├── device_config.py # 设备配置类
│   │   └── device_manager.py # 设备管理器
│   ├── plc/                 # PLC通信
│   │   ├── plc_client.py    # PLC客户端（向后兼容）
│   │   └── plc_data_collector.py # PLC数据采集
│   ├── services/            # 业务服务
│   │   └── data_processor.py # 数据处理服务
│   ├── socketio_handler/    # SocketIO处理
│   │   └── events.py         # SocketIO事件处理
│   │   └── optimized_handler.py # 优化的SocketIO处理
│   └── server.py            # 主服务器入口
├── plc_definitions/         # PLC定义文件
│   └── README.md
├── database.db              # 数据存储（自动生成）
├── requirements.txt         # Python依赖
├── start.bat                # Windows启动脚本
├── start.sh                 # Linux启动脚本
├── SLIDER_DOWN_DETECTION.md # 滑块下行检测文档
└── README.md               # 本文件
```

## 🧩 核心模块说明

### 1. 故障检测框架 (`src/analysis/fault_detector_base.py`)

提供通用的故障检测位管理和推理能力：

- **BaseFaultDetector**: 故障检测器基类，所有设备特定检测器应继承此类
- **FaultBit**: 故障位定义数据类
- **FaultDetectionResult**: 故障检测结果数据类
- **FaultDetectorRegistry**: 故障检测器注册中心，管理所有设备类型的检测器

### 2. 设备特定检测器

- **RXB800FaultDetector**: RXB800设备专用故障检测器，包含88个故障位定义

### 3. 异常检测模块

- **DataAnalyzer**: 基于Z分数和趋势分析的统计异常检测
- **AnomalyTracker**: 活动异常追踪器，支持异常恢复和过期清理
- **FaultTracker**: 活动故障追踪器，支持故障恢复检测

### 4. 滑块下行异常检测 (`src/analysis/slider_down_detector.py`)

基于梯形图分析，检测滑块下行指令发出但未执行的异常情况，并推理出前置条件不满足的原因。

### 5. 数据处理服务 (`src/services/data_processor.py`)

协调数据采集、处理和分发的核心服务：
- 数据采集回调处理
- 事实插入规则引擎
- 故障结果收集
- SocketIO数据分发

### 6. 数据存储服务 (`src/data/data_storage.py`)

支持按设备ID分区的数据库操作：
- 多设备数据隔离存储
- 设备专用查询方法
- 设备数据汇总统计
- 设备数据批量删除

## 📊 数据库设计

### 数据分区架构

系统采用**按设备ID分区**的数据库设计，实现多设备数据隔离管理：

```
┌─────────────────────────────────────────────────────────┐
│                    数据库分区架构                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │                   plc_data                      │   │
│  │  ┌───────┬───────────┬───────────┐             │   │
│  │  │plc_001│   plc_002 │   plc_003 │  ...        │   │
│  │  └───────┴───────────┴───────────┘             │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                              │
│                         ▼                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │            设备ID索引 (idx_plc_data_device_id)   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  设备专用查询方法:                                       │
│  - get_plc_data_by_device(device_id)                  │
│  - get_anomalies_by_device(device_id)                 │
│  - get_faults_by_device(device_id)                    │
│  - delete_device_data(device_id)                       │
│  - get_device_data_summary()                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 表结构

#### plc_data 表 - PLC数据记录
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增ID |
| timestamp | DATETIME | 时间戳 |
| device_id | TEXT | **设备ID（分区键）** |
| db_number | INTEGER | 数据块号 |
| address | INTEGER | 地址 |
| tag_name | TEXT | 标签名 |
| value | REAL | 值 |
| quality | INTEGER | 数据质量 |

#### anomalies 表 - 异常记录
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增ID |
| timestamp | DATETIME | 时间戳 |
| device_id | TEXT | **设备ID（分区键）** |
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
| id | INTEGER | 自增ID |
| fault_name | TEXT | 故障名称 |
| device_id | TEXT | **设备ID（分区键）** |
| start_time | DATETIME | 开始时间 |
| end_time | DATETIME | 结束时间 |
| duration_seconds | REAL | 持续时间 |
| severity | TEXT | 严重程度 |
| related_variables | TEXT | 相关变量 |
| resolved | INTEGER | 是否已解决（0/1） |

#### devices 表 - 设备配置
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增ID |
| device_id | TEXT | 设备ID（唯一） |
| device_name | TEXT | 设备名称 |
| ip_address | TEXT | IP地址 |
| device_type | TEXT | 设备类型 |
| rack | INTEGER | 机架号 |
| slot | INTEGER | 槽号 |
| enabled | INTEGER | 是否启用 |
| last_connected | DATETIME | 最后连接时间 |
| status | TEXT | 设备状态 |

### 索引优化

系统自动创建以下索引提升查询性能：

| 索引名称 | 表名 | 字段 | 用途 |
|----------|------|------|------|
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

### 设备专用方法

| 方法名 | 功能 | 参数 |
|--------|------|------|
| get_plc_data_by_device | 按设备查询PLC数据 | device_id, start_time, end_time, db_number |
| get_anomalies_by_device | 按设备查询异常记录 | device_id, start_time, end_time |
| get_faults_by_device | 按设备查询故障记录 | device_id |
| get_active_faults | 按设备查询活动故障 | device_id（可选） |
| get_record_count | 按设备统计记录数 | table_name, device_id（可选） |
| get_device_data_summary | 获取各设备数据汇总 | 无 |
| get_device_anomaly_summary | 获取各设备异常汇总 | 无 |
| get_device_ids | 获取所有启用的设备ID | 无 |
| delete_device_data | 删除指定设备的所有数据 | device_id |

## 🔌 API 接口

### 获取设备状态
```
GET /api/status
```

### 获取单个设备状态
```
GET /api/device/{device_id}/status
```

### 查询历史数据
```
GET /api/data?startTime=&endTime=&dbNumber=&deviceId=
```

### 查询设备数据（按设备分区）
```
GET /api/device/{device_id}/data?startTime=&endTime=&dbNumber=
```

### 查询异常记录
```
GET /api/anomalies?startTime=&endTime=&deviceId=
```

### 查询设备异常（按设备分区）
```
GET /api/device/{device_id}/anomalies?startTime=&endTime=
```

### 查询活动故障
```
GET /api/faults/active?deviceId=
```

### 查询设备故障（按设备分区）
```
GET /api/device/{device_id}/faults
```

### 删除设备数据
```
DELETE /api/device/{device_id}/data
```

## 📈 SocketIO 数据格式

### 数据格式

服务器通过SocketIO发送的数据包格式：

```javascript
{
  type: 'batch',
  device_id: 'plc_001',
  sequence: 123,
  timestamp: 1715893200000,
  count: 264,
  compressed: false,
  size: 1024,
  payload: {
    'tag_name_1': {
      tag_name: '油温',
      value: 45.2,
      quality: 1,
      address: 0,
      db_number: 1
    },
    'tag_name_2': {
      tag_name: '滑块压力',
      value: 120.5,
      quality: 1,
      address: 2,
      db_number: 1
    }
    // ...更多数据项
  }
}
```

### 前端处理

前端使用 `validateDataPacket()` 函数验证数据包，并通过 `updateCharts()` 更新图表。关键功能：

1. **请求防抖**：防止重复API请求
   - `isStatusRequestInProgress` 标志控制 `/api/status` 请求
   - `isLoadDevicesInProgress` 标志控制设备列表请求

2. **图表数据匹配**：
   - 油温图表：匹配包含"油温"的标签
   - 水温图表：匹配包含"水温"的标签
   - 压力图表：匹配"滑块压力"或"总压力"
   - 位置图表：匹配"滑块位移"或"滑块位置"
   - 速度图表：匹配"滑块速度"

## 🛠️ 常见问题

### 1. PLC 连接失败

**症状**: 终端显示 "PLC连接失败"

**解决方法**:
- 检查 PLC IP 地址是否正确
- 检查网络连接是否正常
- 确认 PLC 的 Rack 和 Slot 配置
- 防火墙是否允许连接

### 2. 端口被占用

**症状**: "端口 3000 已被占用"

**解决方法**:
- 修改 `config/config.py` 中的 `SERVER_PORT`
- 或停止占用端口的其他程序

### 3. 依赖安装失败

**症状**: pip 安装时报错

**解决方法**:
- 确保 Python 版本 >= 3.8
- 升级 pip: `python -m pip install --upgrade pip`
- 安装 Visual C++ Build Tools (Windows)

### 4. 数据库访问错误

**症状**: "SQLite objects created in a thread..."

**解决方法**:
- 确保同时只有一个服务器实例运行
- 删除 `database.db` 文件后重新启动

### 5. 设备数据查询慢

**症状**: 查询特定设备数据响应缓慢

**解决方法**:
- 系统已自动创建设备ID索引，首次查询后会自动优化
- 确保数据库文件所在磁盘有足够空间
- 定期清理过期数据

### 6. 前端图表无数据

**症状**: 前端连接成功但图表不显示数据

**解决方法**:
- 检查浏览器控制台是否有错误
- 清除浏览器缓存后刷新
- 检查服务器日志确认数据是否发送
- 确认数据格式包含完整的 `tag_name`、`value` 等字段

### 7. API 请求被取消

**症状**: 浏览器网络标签显示请求状态为 "canceled"

**解决方法**:
- 检查是否有浏览器扩展拦截请求
- 尝试使用无痕模式
- 清除浏览器缓存
- 确认CORS配置正确

## 🔒 安全建议

1. **生产环境**: 将 `SERVER_HOST` 改为 `127.0.0.1` 或具体IP地址
2. **数据库**: 定期备份 `database.db` 文件
3. **网络**: 建议使用VPN或内网连接访问PLC
4. **端口**: 生产环境建议修改默认端口 3000
5. **设备隔离**: 使用设备ID分区功能隔离不同设备的数据
6. **CORS配置**: 仅允许受信任的域名访问API

## 📞 技术支持

如有问题，请检查：
1. 终端错误信息
2. PLC连接状态
3. 浏览器控制台 (F12)
4. 服务器日志输出

## 📄 许可证

本系统仅供内部使用。

---

**版本**: 2.2.0
**更新日期**: 2026-05-17
**更新说明**:
- 修复Socket.IO数据格式不匹配问题
- 完善数据对象结构，包含完整的tag_name、value、quality、address、db_number等字段
- 添加前端请求防抖机制，防止重复API请求
- 优化图表数据更新逻辑
- 增强CORS配置支持跨域访问
- 修复浏览器端请求超时和取消问题
- 提升系统整体稳定性
