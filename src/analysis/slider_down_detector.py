"""
滑块下行异常检测模块
基于梯形图分析，检测滑块下行指令发出但未执行的异常情况
并推理出前置条件中不满足的原因
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class ConditionStatus(Enum):
    """条件状态"""
    SATISFIED = "满足"
    NOT_SATISFIED = "不满足"
    UNKNOWN = "未知"


@dataclass
class SliderDownCondition:
    """滑块下行前置条件"""
    name: str
    description: str
    variable_name: str
    expected_value: Any
    current_value: Any = None
    status: ConditionStatus = ConditionStatus.UNKNOWN


class SliderDownAbnormalDetector:
    """滑块下行异常检测器"""

    def __init__(self):
        # 初始化所有前置条件（基于梯形图分析得到）
        self.conditions = self._init_conditions()
        self.history = []
        self.down_command_active = False
        self.slider_moving = False
        self.facts = {}  # 存储当前facts数据
        
        # 时间追踪
        self.down_command_start_time = None  # 下行指令开始时间
        self.last_check_time = None  # 上次检查时间
        
        # 配置参数
        self.delay_tolerance = 1.5  # 允许的延迟时间(秒)
        self.error_tolerance = 1.0  # 误差允许时间(秒)

    def _init_conditions(self) -> List[SliderDownCondition]:
        """
        初始化滑块下行的所有前置条件
        根据梯形图分析整理得到
        """
        return [
            # 急停条件
            SliderDownCondition(
                name="急停合格",
                description="急停按钮未按下",
                variable_name="急停合格",
                expected_value=0
            ),
            # 滑块位置条件
            SliderDownCondition(
                name="滑块在上限",
                description="滑块处于上限位置",
                variable_name="滑块上限",
                expected_value=1
            ),
            # 双手操作条件
            SliderDownCondition(
                name="双手合格",
                description="双手操作按钮合格",
                variable_name="双手合格",
                expected_value=1
            ),
            # 电机启动条件
            SliderDownCondition(
                name="电机启动主控",
                description="电机主控已启动",
                variable_name="电机启动主控",
                expected_value=1
            ),
            # 允许下行条件
            SliderDownCondition(
                name="允许下行",
                description="系统允许滑块下行",
                variable_name="允许下行",
                expected_value=1
            ),
            # 移动台条件
            SliderDownCondition(
                name="移动台合格",
                description="移动台位置合格",
                variable_name="移动台合格",
                expected_value=1
            ),
            # 驱动器状态
            SliderDownCondition(
                name="驱动器正常",
                description="驱动器无故障",
                variable_name="驱动器正常",
                expected_value=0
            ),
            # 系统错误
            SliderDownCondition(
                name="系统无错误",
                description="系统无错误信号",
                variable_name="系统Error",
                expected_value=0
            ),
            # 安全爪条件
            SliderDownCondition(
                name="安全爪打开",
                description="安全爪已打开到位",
                variable_name="安全爪打开到位",
                expected_value=1
            ),
            # 安全爪主控
            SliderDownCondition(
                name="安全爪主控",
                description="安全爪主控激活",
                variable_name="安全爪主控",
                expected_value=1
            ),
        ]

    def update_facts(self, facts: Dict[str, Any]):
        """
        更新事实数据
        
        Args:
            facts: PLC数据字典
        """
        import time
        
        self.facts = facts.copy()  # 存储当前facts
        self.last_check_time = time.time()
        
        # 更新每个条件的状态
        for condition in self.conditions:
            if condition.variable_name in facts:
                condition.current_value = facts[condition.variable_name]
                # 比较当前值和期望值
                if condition.current_value == condition.expected_value:
                    condition.status = ConditionStatus.SATISFIED
                else:
                    condition.status = ConditionStatus.NOT_SATISFIED

        # 检测滑块下行指令
        was_active = self.down_command_active
        self.down_command_active = self._detect_down_command(facts)
        
        # 记录下行指令开始时间
        if self.down_command_active and not was_active:
            self.down_command_start_time = time.time()
        elif not self.down_command_active:
            self.down_command_start_time = None
        
        # 检测滑块是否实际在移动
        self.slider_moving = self._detect_slider_moving(facts)
    
    def _get_fact_value(self, variable_name: str) -> Any:
        """
        从facts中获取变量值
        
        Args:
            variable_name: 变量名称
            
        Returns:
            变量值，如果不存在则返回None
        """
        return self.facts.get(variable_name)

    def _detect_down_command(self, facts: Dict[str, Any]) -> bool:
        """
        检测滑块下行指令是否发出
        
        基于梯形图逻辑，下行指令由多个条件组合触发
        """
        # 检测可能的下行指令信号
        # 方式1: 检查滑块下行信号 (DB1.DBX3.1) - 主要信号
        if facts.get('滑块下行', 0) == 1:
            return True
        
        # 方式2: 检查滑块慢下信号 (辅助信号)
        if facts.get('滑块慢下', 0) == 1:
            return True
            
        # 方式3: 检查3Y1信号（通常用于下行控制）
        if facts.get('3Y1', 0) == 1:
            return True
            
        # 方式4: 检查打开充液阀信号
        if facts.get('打开充液阀', 0) == 1:
            return True
            
        return False

    def _detect_slider_moving(self, facts: Dict[str, Any]) -> bool:
        """
        检测滑块是否实际在移动
        
        通过位置变化或状态变化来判断
        """
        # 如果滑块不在上限且不在下限位，说明在中间位置（可能在移动）
        slider_upper = facts.get('滑块上限', 0)
        slider_lower = facts.get('滑块下限位', 0)
        
        if slider_upper == 0 and slider_lower == 0:
            return True
            
        # 如果滑块慢下信号激活，说明在移动
        if facts.get('滑块慢下', 0) == 1:
            return True
            
        return False

    def check_abnormal(self) -> Dict[str, Any]:
        """
        检查是否存在滑块下行异常
        
        Returns:
            异常检测结果字典
        """
        import time
        
        result = {
            'abnormal': False,
            'description': '',
            'unsatisfied_conditions': [],
            'all_conditions': [],
            'elapsed_time': 0,
            'delay_tolerance': self.delay_tolerance,
            'error_tolerance': self.error_tolerance
        }

        # 检查所有条件的状态
        for condition in self.conditions:
            condition_info = {
                'name': condition.name,
                'description': condition.description,
                'variable': condition.variable_name,
                'expected': condition.expected_value,
                'current': condition.current_value,
                'status': condition.status.value
            }
            result['all_conditions'].append(condition_info)
            
            if condition.status == ConditionStatus.NOT_SATISFIED:
                result['unsatisfied_conditions'].append(condition_info)

        # 获取当前滑块速度
        slider_speed = 0
        for condition in self.conditions:
            if condition.variable_name == '滑块速度' and condition.current_value is not None:
                slider_speed = condition.current_value
                break
        
        # 检查是否有滑块速度数据在facts中
        slider_speed_from_facts = self._get_fact_value('滑块速度')
        if slider_speed_from_facts is not None:
            slider_speed = slider_speed_from_facts

        # 计算已过去的时间
        elapsed_time = 0
        if self.down_command_active and self.down_command_start_time is not None:
            elapsed_time = time.time() - self.down_command_start_time
            result['elapsed_time'] = elapsed_time

        # 异常检测逻辑：
        # 有下行指令 AND 有条件不满足 AND (滑块速度为0 OR 滑块速度绝对值 < 0.1) 
        # AND 已经超过延迟容忍时间(1.5s) + 误差容忍时间(1s) = 2.5s
        total_tolerance = self.delay_tolerance + self.error_tolerance
        
        if (self.down_command_active and 
            result['unsatisfied_conditions'] and 
            (slider_speed == 0 or abs(slider_speed) < 0.1) and
            elapsed_time > total_tolerance):
            result['abnormal'] = True
            result['description'] = f"检测到滑块下行指令发出已{elapsed_time:.1f}秒，存在前置条件不满足且滑块未移动"
            if result['unsatisfied_conditions']:
                result['description'] += f"，{len(result['unsatisfied_conditions'])}个前置条件不满足"
        elif (self.down_command_active and 
              result['unsatisfied_conditions'] and 
              (slider_speed == 0 or abs(slider_speed) < 0.1) and
              elapsed_time <= total_tolerance):
            # 在容忍期内，不报警但记录状态
            result['abnormal'] = False
            result['description'] = f"检测到滑块下行指令发出{elapsed_time:.1f}秒，在{total_tolerance}秒容忍期内等待中"
        
        # 记录历史
        self.history.append({
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'down_command': self.down_command_active,
            'slider_moving': self.slider_moving,
            'abnormal': result['abnormal'],
            'unsatisfied_count': len(result['unsatisfied_conditions'])
        })
        
        # 只保留最近100条历史
        if len(self.history) > 100:
            self.history.pop(0)
            
        return result

    def get_abnormal_reasoning(self) -> str:
        """
        生成异常原因推理报告
        
        Returns:
            推理报告字符串
        """
        check_result = self.check_abnormal()
        
        if not check_result['abnormal']:
            return "未检测到滑块下行异常"
            
        report = ["=" * 60]
        report.append("滑块下行异常推理报告")
        report.append("=" * 60)
        report.append(f"\n异常描述: {check_result['description']}")
        
        if check_result['elapsed_time'] > 0:
            report.append(f"\n时间信息:")
            report.append(f"  下行指令激活已: {check_result['elapsed_time']:.1f}秒")
            report.append(f"  延迟容忍时间: {check_result['delay_tolerance']:.1f}秒")
            report.append(f"  误差容忍时间: {check_result['error_tolerance']:.1f}秒")
            report.append(f"  总容忍时间: {check_result['delay_tolerance'] + check_result['error_tolerance']:.1f}秒")
        
        if check_result['unsatisfied_conditions']:
            report.append(f"\n不满足的前置条件 ({len(check_result['unsatisfied_conditions'])}个):")
            for idx, cond in enumerate(check_result['unsatisfied_conditions'], 1):
                report.append(f"\n{idx}. {cond['name']}")
                report.append(f"   描述: {cond['description']}")
                report.append(f"   期望值: {cond['expected']}")
                report.append(f"   当前值: {cond['current']}")
                report.append(f"   状态: {cond['status']}")
        
        report.append(f"\n当前状态:")
        report.append(f"  下行指令: {'激活' if self.down_command_active else '未激活'}")
        report.append(f"  滑块移动: {'是' if self.slider_moving else '否'}")
        
        # 获取当前滑块速度显示
        slider_speed = self._get_fact_value('滑块速度') or 0
        report.append(f"  滑块速度: {slider_speed}")
        
        report.append("\n" + "=" * 60)
        report.append("建议排查顺序:")
        report.append("1. 检查急停按钮状态")
        report.append("2. 确认滑块是否在上限位置")
        report.append("3. 检查双手操作按钮")
        report.append("4. 确认电机是否已启动")
        report.append("5. 检查安全门和安全爪状态")
        report.append("6. 查看系统错误和驱动器状态")
        report.append("=" * 60)
        
        return "\n".join(report)


def create_slider_detector() -> SliderDownAbnormalDetector:
    """
    创建滑块下行异常检测器
    
    Returns:
        SliderDownAbnormalDetector实例
    """
    return SliderDownAbnormalDetector()


if __name__ == '__main__':
    print("=== 滑块下行异常检测器测试 ===\n")
    
    detector = create_slider_detector()
    
    # 测试1: 正常情况 - 所有条件满足
    print("测试1: 正常情况（所有条件满足）")
    normal_facts = {
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
        '滑块慢下': 0
    }
    detector.update_facts(normal_facts)
    result = detector.check_abnormal()
    print(f"异常: {result['abnormal']}")
    print()
    
    # 测试2: 下行指令发出但滑块未动（急停按下）
    print("测试2: 下行指令发出但滑块未动（急停按下）")
    abnormal_facts1 = normal_facts.copy()
    abnormal_facts1['急停合格'] = 1  # 急停按下
    abnormal_facts1['滑块慢下'] = 1  # 下行指令发出
    abnormal_facts1['滑块上限'] = 1  # 滑块仍在上限
    detector.update_facts(abnormal_facts1)
    result = detector.check_abnormal()
    print(f"异常: {result['abnormal']}")
    if result['abnormal']:
        print(f"\n推理报告:")
        print(detector.get_abnormal_reasoning())
    print()
    
    # 测试3: 多个条件不满足
    print("测试3: 多个条件不满足")
    abnormal_facts2 = normal_facts.copy()
    abnormal_facts2['急停合格'] = 1
    abnormal_facts2['双手合格'] = 0
    abnormal_facts2['滑块上限'] = 0
    abnormal_facts2['滑块慢下'] = 1
    detector.update_facts(abnormal_facts2)
    result = detector.check_abnormal()
    print(f"异常: {result['abnormal']}")
    print(f"不满足条件数: {len(result['unsatisfied_conditions'])}")
    if result['abnormal']:
        print(f"\n推理报告:")
        print(detector.get_abnormal_reasoning())
    
    print("\n=== 测试完成 ===")
