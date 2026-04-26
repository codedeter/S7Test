"""
滑块下行异常检测使用示例
展示如何集成和使用新增的滑块下行异常推理功能
"""

from src.analysis.slider_down_detector import create_slider_detector


def example_1_basic_usage():
    """基本使用示例"""
    print("=" * 70)
    print("示例1: 基本使用 - 检测滑块下行异常")
    print("=" * 70)
    
    # 创建检测器
    detector = create_slider_detector()
    
    # 模拟PLC数据
    plc_data = {
        '急停合格': 0,
        '滑块上限': 1,
        '滑块下限位': 0,
        '双手合格': 1,
        '电机启动主控': 1,
        '允许下行': 1,
        '移动台合格': 1,
        '驱动器正常': 0,
        '系统Error': 0,
        '安全爪打开到位': 1,
        '安全爪主控': 1,
        '滑块慢下': 0  # 暂时无下行指令
    }
    
    # 更新数据
    detector.update_facts(plc_data)
    
    # 检查异常
    result = detector.check_abnormal()
    print(f"当前状态 - 异常: {result['abnormal']}")
    print(f"所有条件状态:")
    for cond in result['all_conditions']:
        print(f"  {cond['name']}: {cond['status']} (当前={cond['current']}, 期望={cond['expected']})")
    
    print("\n现在模拟：发出下行指令但急停按下...")
    plc_data['急停合格'] = 1  # 急停按下
    plc_data['滑块慢下'] = 1  # 发出下行指令
    detector.update_facts(plc_data)
    
    result = detector.check_abnormal()
    print(f"\n异常检测: {result['abnormal']}")
    if result['abnormal']:
        print("\n详细推理报告:")
        print(detector.get_abnormal_reasoning())


def example_2_multiple_conditions():
    """多个条件不满足的情况"""
    print("\n" + "=" * 70)
    print("示例2: 多个前置条件不满足")
    print("=" * 70)
    
    detector = create_slider_detector()
    
    # 多个条件不满足的情况
    plc_data = {
        '急停合格': 1,          # 不满足
        '滑块上限': 1,
        '滑块下限位': 0,
        '双手合格': 0,           # 不满足
        '电机启动主控': 0,       # 不满足
        '允许下行': 1,
        '移动台合格': 1,
        '驱动器正常': 1,        # 不满足
        '系统Error': 0,
        '安全爪打开到位': 0,    # 不满足
        '安全爪主控': 1,
        '滑块慢下': 1           # 下行指令
    }
    
    detector.update_facts(plc_data)
    result = detector.check_abnormal()
    
    print(f"异常检测: {result['abnormal']}")
    print(f"不满足的条件数量: {len(result['unsatisfied_conditions'])}")
    
    if result['abnormal']:
        print("\n不满足的条件:")
        for cond in result['unsatisfied_conditions']:
            print(f"  - {cond['name']}: {cond['description']}")
            print(f"    当前={cond['current']}, 期望={cond['expected']}")
        
        print("\n完整推理报告:")
        print(detector.get_abnormal_reasoning())


def example_3_integration_workflow():
    """集成工作流示例"""
    print("\n" + "=" * 70)
    print("示例3: 集成到监控工作流")
    print("=" * 70)
    
    detector = create_slider_detector()
    
    # 模拟实时数据流
    data_stream = [
        # 初始状态：正常
        {'急停合格': 0, '滑块上限': 1, '双手合格': 1, '电机启动主控': 1, 
         '滑块慢下': 0, '驱动器正常': 0, '系统Error': 0, '移动台合格': 1,
         '允许下行': 1, '安全爪打开到位': 1, '安全爪主控': 1, '滑块下限位': 0},
        
        # 发出下行指令
        {'急停合格': 0, '滑块上限': 1, '双手合格': 1, '电机启动主控': 1, 
         '滑块慢下': 1, '驱动器正常': 0, '系统Error': 0, '移动台合格': 1,
         '允许下行': 1, '安全爪打开到位': 1, '安全爪主控': 1, '滑块下限位': 0},
        
        # 系统出现错误
        {'急停合格': 0, '滑块上限': 1, '双手合格': 1, '电机启动主控': 1, 
         '滑块慢下': 1, '驱动器正常': 0, '系统Error': 1, '移动台合格': 1,
         '允许下行': 1, '安全爪打开到位': 1, '安全爪主控': 1, '滑块下限位': 0},
    ]
    
    for i, data in enumerate(data_stream, 1):
        print(f"\n--- 时间点 {i} ---")
        detector.update_facts(data)
        result = detector.check_abnormal()
        
        print(f"下行指令: {'激活' if data.get('滑块慢下', 0) == 1 else '未激活'}")
        print(f"异常: {result['abnormal']}")
        
        if result['abnormal']:
            print(f"不满足条件: {[c['name'] for c in result['unsatisfied_conditions']]}")


if __name__ == '__main__':
    print("滑块下行异常检测系统使用示例\n")
    
    example_1_basic_usage()
    example_2_multiple_conditions()
    example_3_integration_workflow()
    
    print("\n" + "=" * 70)
    print("示例完成")
    print("=" * 70)
