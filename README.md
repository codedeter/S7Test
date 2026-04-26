# PLC数据监控系统 - 部署指南

## 📋 系统简介

这是一个基于 Python + Flask + SocketIO 的 PLC 数据监控系统，用于：
- 实时采集 PLC 数据（通过 snap7 库连接西门子 PLC）
- 监控 DB1 数据块、M 区、I 区、Q 区数据
- 数据存储到 SQLite 数据库
- 实时 Web 界面展示
- 故障检测与报警

## 🖥️ 系统要求

- **操作系统**: Windows 7/10/11 或 Linux (Ubuntu, CentOS等)
- **Python**: 3.8 或更高版本
- **网络**: 能够访问 PLC 设备（默认 172.15.14.150）

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
PLC_IP = '172.15.14.150'  # PLC IP地址
PLC_RACK = 0               # PLC机架号
PLC_SLOT = 1               # PLC槽号
SERVER_HOST = '0.0.0.0'   # 服务器监听地址
SERVER_PORT = 3000         # 服务器端口
DATA_SAMPLING_INTERVAL = 1000  # 数据采样间隔（毫秒）
```

### 修改 PLC 连接地址

如果 PLC 地址不是默认的 `172.15.14.150`，请修改 `config/config.py` 中的 `PLC_IP` 参数。

## 📁 目录结构

```
PLCMonitor/
├── config/              # 配置目录
│   ├── __pycache__/   # (自动生成)
│   ├── config.py       # 系统配置
│   └── plc_tags.py     # PLC标签配置
├── public/             # 前端文件
│   └── index.html      # 主页面
├── src/                # 源代码
│   ├── __pycache__/   # (自动生成)
│   ├── analysis/       # 数据分析模块
│   │   ├── data_analyzer.py
│   │   ├── fault_engine.py
│   │   └── plc_variable_loader.py
│   ├── api/            # API路由
│   │   └── api_routes.py
│   ├── data/           # 数据存储
│   │   └── data_storage.py
│   ├── plc/            # PLC通信
│   │   ├── plc_client.py
│   │   └── plc_data_collector.py
│   └── server.py       # 主服务器
├── GLABAL.db          # PLC DB1定义文件（参考用）
├── PLCValues.xlsx     # PLC变量表（参考用）
├── database.db        # 数据存储（自动生成）
├── requirements.txt   # Python依赖
├── start.bat          # Windows启动脚本
├── start.sh          # Linux启动脚本
└── README.md         # 本文件
```

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

## 📊 数据说明

### 数据库表结构

**plc_data 表** - PLC数据记录
- `id`: 自增ID
- `timestamp`: 时间戳
- `db_number`: 数据块号
- `address`: 地址
- `tag_name`: 标签名
- `value`: 值
- `quality`: 数据质量

**anomalies 表** - 异常记录
- `id`: 自增ID
- `timestamp`: 时间戳
- `db_number`: 数据块号
- `address`: 地址
- `tag_name`: 标签名
- `value`: 值
- `predicted_value`: 预测值
- `confidence`: 置信度
- `message`: 异常信息

## 🔒 安全建议

1. **生产环境**: 将 `SERVER_HOST` 改为 `127.0.0.1` 或具体IP地址
2. **数据库**: 定期备份 `database.db` 文件
3. **网络**: 建议使用VPN或内网连接访问PLC
4. **端口**: 生产环境建议修改默认端口 3000

## 📞 技术支持

如有问题，请检查：
1. 终端错误信息
2. PLC连接状态
3. 浏览器控制台 (F12)

## 📄 许可证

本系统仅供内部使用。

---

**版本**: 1.0.0
**更新日期**: 2026-04-23
