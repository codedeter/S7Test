#!/bin/bash

# PLC数据监控系统 - 启动脚本 (Linux/Mac)

echo "========================================"
echo "   PLC数据监控系统 - 启动脚本"
echo "========================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python3，请先安装"
    exit 1
fi

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "[提示] 创建虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[错误] 创建虚拟环境失败"
        exit 1
    fi
fi

# 激活虚拟环境
echo "[提示] 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "[提示] 安装依赖库..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[错误] 依赖安装失败"
    exit 1
fi

# 启动服务器
echo ""
echo "========================================"
echo "   启动PLC数据监控系统"
echo "========================================"
echo ""
echo "访问地址: http://localhost:3000"
echo "按 Ctrl+C 停止服务器"
echo ""

python src/server.py
