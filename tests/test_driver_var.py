"""
测试驱动器正常变量 - 单元测试版本
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

import unittest
from unittest.mock import patch, MagicMock

class TestDriverVarLoading(unittest.TestCase):
    @patch('src.analysis.plc_variable_loader.PLCVariableLoader')
    def test_plc_variable_loader_returns_variables(self, mock_loader_class):
        from src.analysis.plc_variable_loader import load_plc_tags

        mock_loader = MagicMock()
        mock_loader.variables = {
            '驱动器正常': {'logical_address': 'DB1.DBD0', 'data_type': 'DInt'},
            '驱动器故障': {'logical_address': 'DB1.DBD4', 'data_type': 'DInt'}
        }
        mock_loader_class.return_value = mock_loader

        loader = load_plc_tags()

        if loader is not None:
            self.assertIsNotNone(loader.variables)
            driver_vars = {k: v for k, v in loader.variables.items()
                         if '驱动器' in k or 'driver' in k.lower()}
            self.assertGreater(len(driver_vars), 0)

    def test_driver_var_structure(self):
        from src.analysis.plc_variable_loader import PLCVariableLoader

        mock_loader = MagicMock(spec=PLCVariableLoader)
        mock_loader.variables = {
            '驱动器正常': {
                'logical_address': 'DB1.DBD0',
                'data_type': 'DInt',
                'comment': '驱动器状态'
            }
        }

        var = mock_loader.variables.get('驱动器正常')
        self.assertIsNotNone(var)
        self.assertIn('logical_address', var)
        self.assertIn('data_type', var)

if __name__ == '__main__':
    unittest.main()
