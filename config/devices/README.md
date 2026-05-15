# 设备配置目录

本目录用于存放 PLC 设备配置文件。

## 配置文件格式

支持 **YAML** 和 **JSON** 格式的配置文件。

### YAML 示例 (`plc_example.yml`)

```yaml
device_id: plc_example
device_name: 示例PLC设备
device_type: s7_1500
ip_address: 192.168.1.100
rack: 0
slot: 1
connection_timeout: 10000
retry_interval: 5000
max_retry_attempts: 0
reconnect_backoff_enabled: true
enabled: true
description: 这是一个示例配置文件

db_definitions:
  - db_number: 1
    size: 83
    bool_vars:
      0:
        - [0, 保压选择]
        - [1, 双手合格]
        - [2, 电机启动主控]
    int_vars:
      32: ['压机模式', 'Int']
    real_vars:
      44: ['油温', 'Real']
```

### 可用的设备类型

- `s7_200` - S7-200
- `s7_300` - S7-300
- `s7_400` - S7-400
- `s7_1200` - S7-1200
- `s7_1500` - S7-1500 (默认)

## 使用方法

1. 在此目录下创建新的配置文件（.yml 或 .json）
2. 重启服务，系统会自动加载新配置

## 兼容性说明

- 如果没有配置文件，系统会自动回退使用 `config/devices_config.py` 中的默认配置
- 配置文件格式与原代码中的配置结构保持兼容

## 配置优先级

1. 配置文件中的设备（最高）
2. 硬编码的默认配置（最低）
