$env:PYTHONPATH = "C:\Users\44673\Desktop\文件往这里存！！！\TRAE\S7Test"
Set-Location "C:\Users\44673\Desktop\文件往这里存！！！\TRAE\S7Test"

Write-Host "========================================"
Write-Host "    PLC数据监控系统 - 启动脚本"
Write-Host "========================================"
Write-Host ""

Write-Host "[提示] 正在启动服务器..."

python src/server.py