"""
测试滑块下行异常检测新逻辑 - 单元测试版本
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

import unittest
from unittest.mock import patch, MagicMock

class TestSliderNewLogic(unittest.TestCase):
    @patch('src.analysis.slider_down_detector.SliderDownAbnormalDetector')
    def test_normal_state_no_down_command(self, mock_detector_class):
        from src.analysis.slider_down_detector import create_slider_detector

        mock_instance = MagicMock()
        mock_instance.check_abnormal.return_value = {
            'abnormal': False,
            'description': 'Normal state',
            'elapsed_time': 0,
            'unsatisfied_conditions': []
        }
        mock_detector_class.return_value = mock_instance

        detector = create_slider_detector()
        base_facts = {
            '急停合格': 0, '滑块上限': 1, '滑块下限位': 0,
            '双手合格': 1, '电机启动主控': 1, '允许下行': 1,
            '移动台合格': 1, '驱动器正常': 0, '系统Error': 0,
            '安全爪打开到位': 1, '安全爪主控': 1, '滑块慢下': 0,
            '滑块速度': 0
        }
        detector.update_facts(base_facts)
        result = detector.check_abnormal()
        self.assertFalse(result['abnormal'])

    @patch('src.analysis.slider_down_detector.SliderDownAbnormalDetector')
    def test_down_command_conditions_structure(self, mock_detector_class):
        from src.analysis.slider_down_detector import create_slider_detector

        mock_instance = MagicMock()
        mock_instance.check_abnormal.return_value = {
            'abnormal': False,
            'description': 'Moving',
            'elapsed_time': 0.5,
            'unsatisfied_conditions': []
        }
        mock_detector_class.return_value = mock_instance

        detector = create_slider_detector()
        facts = {
            '急停合格': 0, '滑块上限': 1, '滑块下限位': 0,
            '双手合格': 1, '电机启动主控': 1, '允许下行': 1,
            '移动台合格': 1, '驱动器正常': 0, '系统Error': 0,
            '安全爪打开到位': 1, '安全爪主控': 1, '滑块慢下': 1,
            '滑块速度': 100
        }
        detector.update_facts(facts)
        result = detector.check_abnormal()
        self.assertFalse(result['abnormal'])

    @patch('src.analysis.slider_down_detector.SliderDownAbnormalDetector')
    def test_result_structure(self, mock_detector_class):
        from src.analysis.slider_down_detector import create_slider_detector

        mock_instance = MagicMock()
        mock_instance.check_abnormal.return_value = {
            'abnormal': False,
            'description': 'Normal',
            'elapsed_time': 0,
            'unsatisfied_conditions': []
        }
        mock_detector_class.return_value = mock_instance

        detector = create_slider_detector()
        facts = {
            '急停合格': 0, '滑块上限': 1, '滑块下限位': 0,
            '双手合格': 1, '电机启动主控': 1, '允许下行': 1,
            '移动台合格': 1, '驱动器正常': 0, '系统Error': 0,
            '安全爪打开到位': 1, '安全爪主控': 1, '滑块慢下': 0,
            '滑块速度': 0
        }
        detector.update_facts(facts)
        result = detector.check_abnormal()
        self.assertIn('abnormal', result)
        self.assertIn('description', result)
        self.assertIn('elapsed_time', result)
        self.assertIn('unsatisfied_conditions', result)

if __name__ == '__main__':
    unittest.main()
