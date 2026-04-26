#!/usr/bin/env python3
"""
PLC监控系统 - 打包工具
自动打包所有部署文件到桌面
"""

import os
import sys
import shutil
import zipfile
from datetime import datetime

def get_base_path():
    return os.path.dirname(os.path.abspath(__file__))

def create_package():
    base_path = get_base_path()
    package_name = 'PLCMonitor_Package'
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(desktop, f'{package_name}_{timestamp}.zip')

    print("=" * 50)
    print("   PLC监控系统 - 打包工具")
    print("=" * 50)
    print()

    # 要复制的文件列表
    files_to_copy = {
        'config/config.py': 'config/config.py',
        'config/plc_tags.py': 'config/plc_tags.py',
        'public/index.html': 'public/index.html',
        'src/server.py': 'src/server.py',
        'src/analysis/data_analyzer.py': 'src/analysis/data_analyzer.py',
        'src/analysis/fault_engine.py': 'src/analysis/fault_engine.py',
        'src/analysis/plc_variable_loader.py': 'src/analysis/plc_variable_loader.py',
        'src/api/api_routes.py': 'src/api/api_routes.py',
        'src/data/data_storage.py': 'src/data/data_storage.py',
        'src/plc/plc_client.py': 'src/plc/plc_client.py',
        'src/plc/plc_data_collector.py': 'src/plc/plc_data_collector.py',
        'requirements.txt': 'requirements.txt',
        'start.bat': 'start.bat',
        'start.sh': 'start.sh',
        'README.md': 'README.md',
    }

    # 可选文件（可能不存在）
    optional_files = [
        'GLABAL.db',
        'PLCValues.xlsx',
    ]

    temp_dir = os.path.join(base_path, '_temp_package')

    try:
        print("[1/4] 准备打包目录...")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        print("[2/4] 复制项目文件...")
        for src, dst in files_to_copy.items():
            src_path = os.path.join(base_path, src)
            dst_path = os.path.join(temp_dir, dst)

            if os.path.exists(src_path):
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
                print(f"  + {src}")
            else:
                print(f"  - {src} (文件不存在)")

        # 复制可选文件
        for filename in optional_files:
            src_path = os.path.join(base_path, filename)
            if os.path.exists(src_path):
                shutil.copy2(src_path, os.path.join(temp_dir, filename))
                print(f"  + {filename} (可选)")

        print("[3/4] 创建压缩包...")
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

        print("[4/4] 清理临时文件...")
        shutil.rmtree(temp_dir)

        print()
        print("=" * 50)
        print("   [OK] 打包完成!")
        print("=" * 50)
        print()
        print(f"打包文件位置: {output_file}")
        print()
        print("部署步骤:")
        print("  1. 解压文件到目标目录")
        print("  2. 双击运行 start.bat")
        print("  3. 打开浏览器访问 http://localhost:3000")
        print()

        return True

    except Exception as e:
        print()
        print(f"[错误] 打包失败: {e}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return False

if __name__ == '__main__':
    success = create_package()
    input("\n按 Enter 键退出...")
    sys.exit(0 if success else 1)
