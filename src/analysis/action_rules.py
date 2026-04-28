"""
滑块动作规则表
基于电磁动作表定义的17个动作阶段检测规则
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class ActionStage(Enum):
    """动作阶段"""
    MOTOR_START = "0.01"      # 电机启动
    SLIDER_FAST_DOWN = "0.02" # 滑块快下
    SLIDER_SLOW_DOWN = "0.03" # 滑块慢下
    PRESS_MIDDLE = "0.04"     # 压制（中间位）
    PRESS_THREE = "0.05"      # 压制（三位）
    HOLD_PRESSURE = "0.06"   # 保压
    PRESSURE_RELEASE = "0.07" # 泄压
    RETURN_PREPARE = "0.08"  # 回程准备
    SLIDER_SLOW_RETURN = "0.09" # 滑块慢回
    SLIDER_FAST_RETURN = "0.10" # 滑块快回
    SLIDER_RETURN = "0.11"    # 滑块回程
    STOP_POSITION = "0.12"    # 停止到位
    ADJUST_MOVE = "0.13"      # 微动调整
    ADJUST_DOWN = "0.14"       # 调整下行
    ADJUST_RETURN = "0.15"     # 调整回程
    BUFFER = "0.16"           # 缓冲
    BUFFER_RETURN = "0.17"    # 缓冲回程


@dataclass
class ActionRule:
    """动作规则"""
    stage: ActionStage
    stage_name: str
    description: str
    # 电磁铁状态（True=激活/√）
    solenoid_2Y1c: bool = False
    solenoid_2Y1b: bool = False
    solenoid_2Y2: bool = False
    solenoid_2Y3: bool = False
    solenoid_2Y4: bool = False
    solenoid_3Y1: bool = False
    solenoid_3Y3a: bool = False
    solenoid_3Y3b: bool = False
    solenoid_3Y4: bool = False
    solenoid_3Y5: bool = False
    solenoid_3Y6: bool = False
    solenoid_3Y8: bool = False
    solenoid_3Y9: bool = False
    solenoid_3Y10: bool = False
    solenoid_3Y11: bool = False
    solenoid_3Y30: bool = False
    # 电机状态
    motor_2M1: bool = False
    motor_2M2: bool = False
    # 相关故障检测
    associated_faults: List[str] = None
    # 前序阶段
    previous_stages: List[ActionStage] = None
    
    def __post_init__(self):
        if self.associated_faults is None:
            self.associated_faults = []
        if self.previous_stages is None:
            self.previous_stages = []


# ============== 动作规则表定义 ==============

ACTION_RULES = [
    # 0.01 电机启动
    ActionRule(
        stage=ActionStage.MOTOR_START,
        stage_name="电机启动",
        description="系统电机启动阶段，准备后续动作",
        solenoid_2Y1c=True,
        solenoid_2Y1b=True,
        solenoid_2Y2=True,
        solenoid_2Y3=True,
        solenoid_3Y1=True,
        solenoid_3Y3a=True,
        solenoid_3Y3b=True,
        solenoid_3Y4=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=["电机启动主控", "驱动器正常", "系统无错误"],
        previous_stages=[]
    ),
    
    # 0.02 滑块快下
    ActionRule(
        stage=ActionStage.SLIDER_FAST_DOWN,
        stage_name="滑块快下",
        description="滑块快速下行阶段",
        solenoid_2Y1c=True,
        solenoid_2Y2=True,
        solenoid_2Y3=True,
        solenoid_2Y4=True,
        solenoid_3Y1=True,
        solenoid_3Y3a=True,
        solenoid_3Y3b=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=["允许下行", "滑块上限", "安全爪打开", "安全爪主控"],
        previous_stages=[ActionStage.MOTOR_START]
    ),
    
    # 0.03 滑块慢下
    ActionRule(
        stage=ActionStage.SLIDER_SLOW_DOWN,
        stage_name="滑块慢下",
        description="滑块慢速下行阶段，接近模具",
        solenoid_2Y1c=True,
        solenoid_2Y2=True,
        solenoid_2Y3=True,
        solenoid_2Y4=True,
        solenoid_3Y1=True,
        solenoid_3Y3a=True,
        solenoid_3Y3b=True,
        solenoid_3Y4=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=["滑块慢下", "3Y1液压阀", "打开充液阀"],
        previous_stages=[ActionStage.SLIDER_FAST_DOWN]
    ),
    
    # 0.04 压制（中间位）
    ActionRule(
        stage=ActionStage.PRESS_MIDDLE,
        stage_name="压制（中间位）",
        description="滑块到达中间位置，开始压制",
        solenoid_2Y1c=True,
        solenoid_2Y2=True,
        solenoid_2Y3=True,
        solenoid_2Y4=True,
        solenoid_3Y1=True,
        solenoid_3Y3a=True,
        solenoid_3Y3b=True,
        solenoid_3Y4=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=[],
        previous_stages=[ActionStage.SLIDER_SLOW_DOWN]
    ),
    
    # 0.05 压制（三位）
    ActionRule(
        stage=ActionStage.PRESS_THREE,
        stage_name="压制（三位）",
        description="滑块到达三位位置，强力压制",
        solenoid_2Y1c=True,
        solenoid_2Y2=True,
        solenoid_2Y3=True,
        solenoid_3Y1=True,
        solenoid_3Y3a=True,
        solenoid_3Y3b=True,
        solenoid_3Y4=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=[],
        previous_stages=[ActionStage.PRESS_MIDDLE]
    ),
    
    # 0.06 保压
    ActionRule(
        stage=ActionStage.HOLD_PRESSURE,
        stage_name="保压",
        description="维持压制压力，确保成型",
        solenoid_2Y1c=True,
        solenoid_2Y2=True,
        solenoid_2Y3=True,
        solenoid_3Y1=True,
        solenoid_3Y3a=True,
        solenoid_3Y3b=True,
        solenoid_3Y4=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=[],
        previous_stages=[ActionStage.PRESS_THREE]
    ),
    
    # 0.07 泄压
    ActionRule(
        stage=ActionStage.PRESSURE_RELEASE,
        stage_name="泄压",
        description="释放压制压力",
        solenoid_2Y1c=True,
        solenoid_2Y2=True,
        solenoid_2Y3=True,
        solenoid_3Y1=True,
        solenoid_3Y3a=True,
        solenoid_3Y3b=True,
        solenoid_3Y4=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=[],
        previous_stages=[ActionStage.HOLD_PRESSURE]
    ),
    
    # 0.08 回程准备
    ActionRule(
        stage=ActionStage.RETURN_PREPARE,
        stage_name="回程准备",
        description="滑块回程准备阶段",
        solenoid_2Y1c=True,
        solenoid_3Y4=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=[],
        previous_stages=[ActionStage.PRESSURE_RELEASE]
    ),
    
    # 0.09 滑块慢回
    ActionRule(
        stage=ActionStage.SLIDER_SLOW_RETURN,
        stage_name="滑块慢回",
        description="滑块慢速回程阶段",
        solenoid_2Y1c=True,
        solenoid_2Y1b=True,
        solenoid_3Y4=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=[],
        previous_stages=[ActionStage.RETURN_PREPARE]
    ),
    
    # 0.10 滑块快回
    ActionRule(
        stage=ActionStage.SLIDER_FAST_RETURN,
        stage_name="滑块快回",
        description="滑块快速回程阶段",
        solenoid_2Y1c=True,
        solenoid_2Y1b=True,
        solenoid_2Y2=True,
        solenoid_2Y3=True,
        solenoid_2Y4=True,
        solenoid_3Y4=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=[],
        previous_stages=[ActionStage.SLIDER_SLOW_RETURN]
    ),
    
    # 0.11 滑块回程
    ActionRule(
        stage=ActionStage.SLIDER_RETURN,
        stage_name="滑块回程",
        description="滑块回程阶段",
        solenoid_2Y1c=True,
        solenoid_2Y1b=True,
        solenoid_2Y2=True,
        solenoid_2Y3=True,
        solenoid_2Y4=True,
        solenoid_3Y4=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=["滑块上限"],
        previous_stages=[ActionStage.SLIDER_FAST_RETURN]
    ),
    
    # 0.12 停止到位
    ActionRule(
        stage=ActionStage.STOP_POSITION,
        stage_name="停止到位",
        description="滑块停止到目标位置",
        # 所有电磁铁均不激活（表格中空白）
        associated_faults=["滑块上限", "滑块下限位"],
        previous_stages=[ActionStage.SLIDER_RETURN]
    ),
    
    # 0.13 微动调整
    ActionRule(
        stage=ActionStage.ADJUST_MOVE,
        stage_name="微动调整",
        description="滑块微动调整阶段",
        solenoid_2Y1c=True,
        solenoid_2Y2=True,
        solenoid_2Y3=True,
        solenoid_2Y4=True,
        solenoid_3Y1=True,
        solenoid_3Y3a=True,
        solenoid_3Y3b=True,
        solenoid_3Y4=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=[],
        previous_stages=[ActionStage.STOP_POSITION]
    ),
    
    # 0.14 调整下行
    ActionRule(
        stage=ActionStage.ADJUST_DOWN,
        stage_name="调整下行",
        description="调整模式下的滑块下行",
        solenoid_2Y1c=True,
        solenoid_2Y2=True,
        solenoid_2Y3=True,
        solenoid_2Y4=True,
        solenoid_3Y1=True,
        solenoid_3Y3a=True,
        solenoid_3Y3b=True,
        solenoid_3Y4=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=[],
        previous_stages=[ActionStage.ADJUST_MOVE]
    ),
    
    # 0.15 调整回程
    ActionRule(
        stage=ActionStage.ADJUST_RETURN,
        stage_name="调整回程",
        description="调整模式下的滑块回程",
        solenoid_2Y1c=True,
        solenoid_3Y4=True,
        solenoid_3Y5=True,
        solenoid_3Y6=True,
        solenoid_3Y8=True,
        solenoid_3Y9=True,
        solenoid_3Y10=True,
        solenoid_3Y11=True,
        solenoid_3Y30=True,
        motor_2M1=True,
        motor_2M2=True,
        associated_faults=[],
        previous_stages=[ActionStage.ADJUST_DOWN]
    ),
    
    # 0.16 缓冲
    ActionRule(
        stage=ActionStage.BUFFER,
        stage_name="缓冲",
        description="缓冲阶段，平稳停止",
        # 所有电磁铁均不激活（表格中空白）
        associated_faults=[],
        previous_stages=[ActionStage.ADJUST_RETURN]
    ),
    
    # 0.17 缓冲回程
    ActionRule(
        stage=ActionStage.BUFFER_RETURN,
        stage_name="缓冲回程",
        description="缓冲后的回程阶段",
        # 所有电磁铁均不激活（表格中空白）
        associated_faults=[],
        previous_stages=[ActionStage.BUFFER]
    ),
]


# ============== 变量映射表 ==============

VARIABLE_MAP = {
    # 电磁铁变量名映射
    "2Y1c": "2Y1c",
    "2Y1b": "2Y1b",
    "2Y2": "2Y2",
    "2Y3": "2Y3",
    "2Y4": "2Y4",
    "3Y1": "3Y1",
    "3Y3a": "3Y3a",
    "3Y3b": "3Y3b",
    "3Y4": "3Y4",
    "3Y5": "3Y5",
    "3Y6": "3Y6",
    "3Y8": "3Y8",
    "3Y9": "3Y9",
    "3Y10": "3Y10",
    "3Y11": "3Y11",
    "3Y30": "3Y30",
    # 电机变量名映射
    "2M1": "2M1",
    "2M2": "2M2",
}


class ActionStageDetector:
    """动作阶段检测器"""
    
    def __init__(self):
        self.rules = ACTION_RULES
        self.current_stage: Optional[ActionStage] = None
        self.stage_history: List[ActionStage] = []
        self.max_history = 50
    
    def detect_stage(self, facts: Dict[str, Any]) -> Optional[ActionStage]:
        """
        检测当前动作阶段
        
        Args:
            facts: PLC数据字典
            
        Returns:
            检测到的动作阶段
        """
        for rule in self.rules:
            if self._match_rule(rule, facts):
                return rule.stage
        return None
    
    def _match_rule(self, rule: ActionRule, facts: Dict[str, Any]) -> bool:
        """
        匹配动作规则
        
        Args:
            rule: 动作规则
            facts: PLC数据
            
        Returns:
            是否匹配
        """
        # 检查所有电磁铁状态
        solenoids = {
            "2Y1c": rule.solenoid_2Y1c,
            "2Y1b": rule.solenoid_2Y1b,
            "2Y2": rule.solenoid_2Y2,
            "2Y3": rule.solenoid_2Y3,
            "2Y4": rule.solenoid_2Y4,
            "3Y1": rule.solenoid_3Y1,
            "3Y3a": rule.solenoid_3Y3a,
            "3Y3b": rule.solenoid_3Y3b,
            "3Y4": rule.solenoid_3Y4,
            "3Y5": rule.solenoid_3Y5,
            "3Y6": rule.solenoid_3Y6,
            "3Y8": rule.solenoid_3Y8,
            "3Y9": rule.solenoid_3Y9,
            "3Y10": rule.solenoid_3Y10,
            "3Y11": rule.solenoid_3Y11,
            "3Y30": rule.solenoid_3Y30,
        }
        
        # 检查所有电磁铁是否符合期望（激活/不激活）
        for var_name, expected in solenoids.items():
            if var_name in facts:
                actual = (facts[var_name] == 1)
                if actual != expected:
                    return False
        
        # 检查电机状态
        motors = {
            "2M1": rule.motor_2M1,
            "2M2": rule.motor_2M2,
        }
        
        for var_name, expected in motors.items():
            if var_name in facts:
                actual = (facts[var_name] == 1)
                if actual != expected:
                    return False
        
        return True
    
    def get_stage_info(self, stage: ActionStage) -> Optional[ActionRule]:
        """
        获取阶段信息
        
        Args:
            stage: 动作阶段
            
        Returns:
            动作规则
        """
        for rule in self.rules:
            if rule.stage == stage:
                return rule
        return None
    
    def check_stage_transition(self, new_stage: ActionStage) -> Dict[str, Any]:
        """
        检查阶段转换是否正确
        
        Args:
            new_stage: 新检测到的阶段
            
        Returns:
            检查结果
        """
        result = {
            'valid': True,
            'message': '',
            'expected_previous': [],
            'actual_previous': self.current_stage,
        }
        
        rule = self.get_stage_info(new_stage)
        
        if rule and rule.previous_stages:
            if self.current_stage not in rule.previous_stages:
                result['valid'] = False
                result['message'] = f"阶段{rule.stage.value} {rule.stage_name}的前序阶段应该是{[s.value for s in rule.previous_stages]}，但实际是{self.current_stage.value if self.current_stage else 'None'}"
                result['expected_previous'] = rule.previous_stages
        
        # 更新当前阶段和历史
        if self.current_stage != new_stage:
            self.stage_history.append(new_stage)
            if len(self.stage_history) > self.max_history:
                self.stage_history.pop(0)
            self.current_stage = new_stage
        
        return result


def create_action_detector() -> ActionStageDetector:
    """
    创建动作阶段检测器
    
    Returns:
        ActionStageDetector实例
    """
    return ActionStageDetector()


# ============== 规则查询函数 ==============

def get_rule_by_stage(stage: ActionStage) -> Optional[ActionRule]:
    """
    根据阶段获取规则
    
    Args:
        stage: 动作阶段
        
    Returns:
        动作规则
    """
    for rule in ACTION_RULES:
        if rule.stage == stage:
            return rule
    return None


def get_rule_by_name(stage_name: str) -> Optional[ActionRule]:
    """
    根据名称获取规则
    
    Args:
        stage_name: 阶段名称
        
    Returns:
        动作规则
    """
    for rule in ACTION_RULES:
        if rule.stage_name == stage_name:
            return rule
    return None


def get_all_rules() -> List[ActionRule]:
    """
    获取所有规则
    
    Returns:
        规则列表
    """
    return ACTION_RULES


# ============== 打印规则表 ==============

def print_rule_table():
    """打印完整的规则表"""
    print("=" * 100)
    print("滑块动作规则表（基于电磁动作表）")
    print("=" * 100)
    print()
    
    for rule in ACTION_RULES:
        print(f"[{rule.stage.value}] {rule.stage_name}")
        print(f"    描述: {rule.description}")
        
        # 显示激活的电磁铁
        active_solenoids = []
        if rule.solenoid_2Y1c: active_solenoids.append("2Y1c")
        if rule.solenoid_2Y1b: active_solenoids.append("2Y1b")
        if rule.solenoid_2Y2: active_solenoids.append("2Y2")
        if rule.solenoid_2Y3: active_solenoids.append("2Y3")
        if rule.solenoid_2Y4: active_solenoids.append("2Y4")
        if rule.solenoid_3Y1: active_solenoids.append("3Y1")
        if rule.solenoid_3Y3a: active_solenoids.append("3Y3a")
        if rule.solenoid_3Y3b: active_solenoids.append("3Y3b")
        if rule.solenoid_3Y4: active_solenoids.append("3Y4")
        if rule.solenoid_3Y5: active_solenoids.append("3Y5")
        if rule.solenoid_3Y6: active_solenoids.append("3Y6")
        if rule.solenoid_3Y8: active_solenoids.append("3Y8")
        if rule.solenoid_3Y9: active_solenoids.append("3Y9")
        if rule.solenoid_3Y10: active_solenoids.append("3Y10")
        if rule.solenoid_3Y11: active_solenoids.append("3Y11")
        if rule.solenoid_3Y30: active_solenoids.append("3Y30")
        
        if active_solenoids:
            print(f"    激活电磁铁: {', '.join(active_solenoids)}")
        
        # 显示激活的电机
        active_motors = []
        if rule.motor_2M1: active_motors.append("2M1")
        if rule.motor_2M2: active_motors.append("2M2")
        
        if active_motors:
            print(f"    激活电机: {', '.join(active_motors)}")
        
        # 显示关联故障
        if rule.associated_faults:
            print(f"    关联故障: {', '.join(rule.associated_faults)}")
        
        # 显示前序阶段
        if rule.previous_stages:
            prev_stages = [s.value for s in rule.previous_stages]
            print(f"    前序阶段: {', '.join(prev_stages)}")
        
        print()


if __name__ == '__main__':
    print_rule_table()
