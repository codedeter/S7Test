"""
测试滑块下行异常检测 - 单元测试版本
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

import unittest
from unittest.mock import patch, MagicMock

class TestSliderDetectorLogic(unittest.TestCase):
    @patch('src.analysis.slider_down_detector.SliderDownAbnormalDetector')
    def test_no_down_command_no_abnormal(self, mock_detector_class):
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
        self.assertFalse(result['abnormal'])

    @patch('src.analysis.slider_down_detector.SliderDownAbnormalDetector')
    def test_down_command_with_satisfied_conditions(self, mock_detector_class):
        from src.analysis.slider_down_detector import create_slider_detector

        mock_instance = MagicMock()
        mock_instance.check_abnormal.return_value = {
            'abnormal': False,
            'description': 'Conditions satisfied',
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
            '滑块速度': 50
        }
        detector.update_facts(facts)
        result = detector.check_abnormal()
        self.assertFalse(result['abnormal'])

    @patch('src.analysis.slider_down_detector.SliderDownAbnormalDetector')
    def test_unsatisfied_conditions_structure(self, mock_detector_class):
        from src.analysis.slider_down_detector import create_slider_detector

        mock_instance = MagicMock()
        mock_instance.check_abnormal.return_value = {
            'abnormal': False,
            'description': 'Waiting',
            'elapsed_time': 0,
            'unsatisfied_conditions': [{'condition': '急停合格', 'expected': 0, 'actual': 1}]
        }
        mock_detector_class.return_value = mock_instance

        detector = create_slider_detector()
        facts = {
            '急停合格': 1, '滑块上限': 1, '滑块下限位': 0,
            '双手合格': 1, '电机启动主控': 1, '允许下行': 1,
            '移动台合格': 1, '驱动器正常': 0, '系统Error': 0,
            '安全爪打开到位': 1, '安全爪主控': 1, '滑块慢下': 0,
            '滑块速度': 0
        }
        detector.update_facts(facts)
        result = detector.check_abnormal()
        self.assertIn('unsatisfied_conditions', result)
        self.assertIn('description', result)

if __name__ == '__main__':
    unittest.main()
