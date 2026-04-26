"""
简单服务器启动测试
"""
import sys
import os

# 确保路径正确
sys.path.insert(0, os.path.dirname(__file__))

print("测试模块导入...")
try:
    from flask import Flask
    print("✅ Flask 导入成功")
except Exception as e:
    print(f"❌ Flask 导入失败: {e}")
    sys.exit(1)

try:
    from flask_socketio import SocketIO
    print("✅ Flask-SocketIO 导入成功")
except Exception as e:
    print(f"❌ Flask-SocketIO 导入失败: {e}")
    sys.exit(1)

try:
    from src.analysis.fault_engine import create_fault_rules
    print("✅ fault_engine 导入成功")
except Exception as e:
    print(f"❌ fault_engine 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from src.analysis.slider_down_detector import create_slider_detector
    print("✅ slider_down_detector 导入成功")
except Exception as e:
    print(f"❌ slider_down_detector 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🎉 所有模块导入成功！")
print("\n尝试创建规则引擎...")
try:
    engine = create_fault_rules()
    print("✅ 规则引擎创建成功")
    print(f"✅ 规则数量: {len(engine.rules)}")
except Exception as e:
    print(f"❌ 规则引擎创建失败: {e}")
    import traceback
    traceback.print_exc()

print("\n尝试创建滑块检测器...")
try:
    detector = create_slider_detector()
    print("✅ 滑块检测器创建成功")
except Exception as e:
    print(f"❌ 滑块检测器创建失败: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ 系统检查完成！")
