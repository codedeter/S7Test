"""
PLC变量表加载模块
从Excel文件加载变量定义
"""

import openpyxl
import os

class PLCVariableLoader:
    def __init__(self, excel_path):
        self.excel_path = excel_path
        self.variables = {}
        self.tag_mapping = {}

    def load_from_excel(self):
        try:
            wb = openpyxl.load_workbook(self.excel_path)
            ws = wb['PLC Tags']

            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row[0]:
                    continue

                name = row[0]
                path = row[1]
                data_type = row[2]
                logical_addr = row[3]
                comment = row[4] if len(row) > 4 else ""

                var_info = {
                    'name': name,
                    'path': path,
                    'data_type': data_type,
                    'logical_address': logical_addr,
                    'comment': comment,
                    'hmi_visible': row[5] if len(row) > 5 else False,
                    'hmi_accessible': row[6] if len(row) > 6 else False,
                    'hmi_writeable': row[7] if len(row) > 7 else False,
                }

                self.variables[name] = var_info

                if logical_addr:
                    self.tag_mapping[str(logical_addr)] = name

            print(f"成功加载 {len(self.variables)} 个PLC变量")
            return True

        except Exception as e:
            print(f"加载PLC变量表失败: {e}")
            return False

    def get_variable(self, name):
        return self.variables.get(name)

    def get_all_variables(self):
        return self.variables

    def get_tag_by_address(self, address):
        return self.tag_mapping.get(str(address))

    def parse_db_address(self, db_number, byte_offset, bit_offset=0):
        for name, var in self.variables.items():
            addr = var.get('logical_address', '')
            if not addr:
                continue

            if f"DB{db_number}.DBX{byte_offset}.{bit_offset}" in str(addr):
                return var

            if f"DB{db_number}.DBB{byte_offset}" in str(addr):
                return var

            if f"DB{db_number}.DBW{byte_offset}" in str(addr):
                return var

            if f"DB{db_number}.DBD{byte_offset}" in str(addr):
                return var

        return None

def load_plc_tags():
    excel_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'PLCValues.xlsx'
    )

    if not os.path.exists(excel_path):
        print(f"PLC变量表文件不存在: {excel_path}")
        return None

    loader = PLCVariableLoader(excel_path)
    if loader.load_from_excel():
        return loader

    return None
