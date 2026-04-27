"""
简单服务器启动测试 - 无emoji版本
"""
import sys
import os

# 确保路径正确
sys.path.insert(0, os.path.dirname(__file__))

print("Testing module imports...")
try:
    from flask import Flask
    print("Flask imported successfully")
except Exception as e:
    print(f"Flask import failed: {e}")
    sys.exit(1)

try:
    from flask_socketio import SocketIO
    print("Flask-SocketIO imported successfully")
except Exception as e:
    print(f"Flask-SocketIO import failed: {e}")
    sys.exit(1)

try:
    from src.analysis.fault_engine import create_fault_rules
    print("fault_engine imported successfully")
except Exception as e:
    print(f"fault_engine import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from src.analysis.slider_down_detector import create_slider_detector
    print("slider_down_detector imported successfully")
except Exception as e:
    print(f"slider_down_detector import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nAll modules imported successfully!")
print("\nCreating rule engine...")
try:
    engine = create_fault_rules()
    print("Rule engine created successfully")
    print(f"Rule count: {len(engine.rules)}")
except Exception as e:
    print(f"Rule engine creation failed: {e}")
    import traceback
    traceback.print_exc()

print("\nCreating slider detector...")
try:
    detector = create_slider_detector()
    print("Slider detector created successfully")
except Exception as e:
    print(f"Slider detector creation failed: {e}")
    import traceback
    traceback.print_exc()

print("\nSystem check complete!")
