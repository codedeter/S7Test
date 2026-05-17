#!/usr/bin/env python3
"""
快速查看设备变量对应关系 - 无依赖版
"""

def show_db1():
    print("="*80)
    print("RXA1300 PLC - DB1 变量对应表 (部分示例)")
    print("="*80)
    
    print("""
【DB1 - 全局数据块】
  大小: 83 字节

--- BOOL 变量 ---

  字节0:
    位0: 保压选择
    位1: 双手合格
    位2: 电机启动主控
    位3: 滑块上限
    位4: 关断上循环泵
    位5: 反行程检查
    位6: 允许下行
    位7: 回程停止位1

  字节1:
    位0: 回程停止位2
    位1: 回程停止位3
    位2: 回程停止位4
    位3: 滑块快转慢位
    位4: 滑块下限位
    位5: 压制力达到
    位6: 主缸泄压到位
    位7: 滑块合模位

--- 数值变量 ---

  Byte 32 (INT): 压机模式
  Byte 36 (DINT): 润滑次数
  Byte 40 (DINT): 润滑时间
  Byte 44 (REAL): 油超温温度
  Byte 48 (REAL): 油需冷却温度
""")

def show_db10():
    print("="*80)
    print("RXA1300 PLC - DB10 显示值数据块 (部分示例)")
    print("="*80)
    
    print("""
【DB10 - 显示值数据块】
  大小: 105 字节

--- REAL 变量 ---

  Byte 0:  2M1实时电机速度
  Byte 4:  2M2实时电机速度
  Byte 8:  2M3实时电机速度
  Byte 12: 2M4实时电机速度
  Byte 16: 液压垫位移传感器
  Byte 20: 压力传感器3S201
  Byte 24: 压力传感器3S202
  Byte 28: 油温传感器
  Byte 32: 压力传感器3S203
  ... (更多变量)
""")

def main():
    print("="*80)
    print("PLC变量与DB块对应关系快速查看")
    print("="*80)
    print("\n请选择查看内容:")
    print("  1. DB1 (全局) - RXA1300")
    print("  2. DB10 (显示值) - RXA1300")
    print("  3. 查看完整报告 (DB_VAR_MAPPING_REPORT.md)")
    print("  0. 退出")
    
    try:
        choice = input("\n请输入选项 (0-3): ").strip()
        
        if choice == '1':
            show_db1()
        elif choice == '2':
            show_db10()
        elif choice == '3':
            print("\n正在打开报告文件...")
            if os.path.exists('DB_VAR_MAPPING_REPORT.md'):
                with open('DB_VAR_MAPPING_REPORT.md', 'r', encoding='utf-8') as f:
                    print(f.read())
            else:
                print("报告文件不存在")
    except KeyboardInterrupt:
        print("\n\n退出")

if __name__ == "__main__":
    import os
    main()
