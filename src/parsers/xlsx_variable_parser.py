import os
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class PLCVariable:
    name: str
    logical_address: str
    data_type: str
    db_number: Optional[int] = None
    byte_offset: Optional[int] = None
    bit_offset: Optional[int] = None
    area: Optional[str] = None
    description: str = ""
    access_type: str = "read"


class XLSXVariableParser:
    AREA_MAP = {
        'M': 'M',
        'I': 'I',
        'Q': 'Q',
        'E': 'I',
        'A': 'Q',
        'DB': 'DB',
    }

    TYPE_MAP = {
        'BOOL': 'BOOL',
        'BIT': 'BOOL',
        'BYTE': 'BYTE',
        'WORD': 'WORD',
        'DWORD': 'DWORD',
        'INT': 'INT',
        'DINT': 'DINT',
        'REAL': 'REAL',
        'LREAL': 'LREAL',
        'STRING': 'STRING',
        'CHAR': 'CHAR',
    }

    def __init__(self):
        self.variables: Dict[str, PLCVariable] = {}

    def parse_xlsx(self, file_path: str, sheet_name: str = None) -> Dict[str, PLCVariable]:
        try:
            import openpyxl
        except ImportError:
            print("openpyxl not installed, trying xlrd...")
            return self._parse_xlsx_fallback(file_path, sheet_name)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"XLSX file not found: {file_path}")

        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb[sheet_name] if sheet_name else wb.active

        self.variables = {}

        headers = []
        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if row_idx == 1:
                headers = [str(h).strip() if h else f"col_{i}"
                          for i, h in enumerate(row)]
                continue

            if not row or all(cell is None for cell in row):
                continue

            row_data = dict(zip(headers, row))

            var = self._parse_row(row_data)
            if var:
                self.variables[var.name] = var

        wb.close()
        return self.variables

    def _parse_xlsx_fallback(self, file_path: str, sheet_name: str = None) -> Dict[str, PLCVariable]:
        try:
            import xlrd
        except ImportError:
            print("xlrd not installed either, cannot parse xlsx file")
            return {}

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"XLSX file not found: {file_path}")

        wb = xlrd.open_workbook(file_path)
        ws = wb.sheet_by_name(sheet_name) if sheet_name else wb.sheet_by_index(0)

        self.variables = {}
        headers = []

        for row_idx in range(ws.nrows):
            row = ws.row_values(row_idx)
            if row_idx == 0:
                headers = [str(h).strip() if h else f"col_{i}"
                          for i, h in enumerate(row)]
                continue

            if not row or all(cell == '' for cell in row):
                continue

            row_data = dict(zip(headers, row))
            var = self._parse_row(row_data)
            if var:
                self.variables[var.name] = var

        return self.variables

    def _parse_row(self, row_data: Dict[str, Any]) -> Optional[PLCVariable]:
        name = self._get_value(row_data, ['名称', 'Name', '变量名', 'Tag Name'])
        if not name:
            return None

        name = str(name).strip()

        address = self._get_value(row_data, ['地址', 'Address', '逻辑地址', 'Logical Address'])
        if not address:
            address = self._get_value(row_data, ['偏移地址', 'Offset'])
            if address:
                address = f"%DB{int(address)}"

        data_type = self._get_value(row_data, ['类型', 'Type', '数据类型', 'Data Type'], 'BOOL')

        description = self._get_value(row_data, ['描述', 'Description', '说明', 'Comment'], '')

        if address:
            parsed = self._parse_address(str(address))
        else:
            parsed = {'area': None, 'db': None, 'offset': 0, 'bit': 0}

        return PLCVariable(
            name=name,
            logical_address=str(address) if address else '',
            data_type=self._normalize_type(str(data_type)),
            db_number=parsed.get('db'),
            byte_offset=parsed.get('offset', 0),
            bit_offset=parsed.get('bit', 0),
            area=parsed.get('area'),
            description=str(description) if description else ''
        )

    def _get_value(self, row: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
        for key in keys:
            for row_key, value in row.items():
                if key.lower() in str(row_key).lower():
                    if value is not None and str(value).strip():
                        return value
        return default

    def _parse_address(self, address: str) -> Dict[str, Any]:
        address = address.strip().upper()

        db_match = re.match(r'%DB(\d+)\.(\d+)(?:\.(\d+))?', address)
        if db_match:
            return {
                'area': 'DB',
                'db': int(db_match.group(1)),
                'offset': int(db_match.group(2)),
                'bit': int(db_match.group(3)) if db_match.group(3) else 0
            }

        m_match = re.match(r'%M(\d+)(?:\.(\d+))?', address)
        if m_match:
            return {
                'area': 'M',
                'db': None,
                'offset': int(m_match.group(1)),
                'bit': int(m_match.group(2)) if m_match.group(2) else 0
            }

        i_match = re.match(r'%I(\d+)(?:\.(\d+))?', address)
        if i_match:
            return {
                'area': 'I',
                'db': None,
                'offset': int(i_match.group(1)),
                'bit': int(i_match.group(2)) if i_match.group(2) else 0
            }

        q_match = re.match(r'%Q(\d+)(?:\.(\d+))?', address)
        if q_match:
            return {
                'area': 'Q',
                'db': None,
                'offset': int(q_match.group(1)),
                'bit': int(q_match.group(2)) if q_match.group(2) else 0
            }

        return {'area': None, 'db': None, 'offset': 0, 'bit': 0}

    def _normalize_type(self, data_type: str) -> str:
        data_type = data_type.upper().strip()

        for key, normalized in self.TYPE_MAP.items():
            if key in data_type:
                return normalized

        return 'BOOL'

    def get_variables_by_area(self, area: str) -> List[PLCVariable]:
        return [v for v in self.variables.values() if v.area == area]

    def get_variables_by_db(self, db_number: int) -> List[PLCVariable]:
        return [v for v in self.variables.values() if v.db_number == db_number]

    def get_m_variables(self) -> List[PLCVariable]:
        return self.get_variables_by_area('M')

    def get_i_variables(self) -> List[PLCVariable]:
        return self.get_variables_by_area('I')

    def get_q_variables(self) -> List[PLCVariable]:
        return self.get_variables_by_area('Q')

    def export_to_config_format(self) -> Dict[str, Any]:
        config = {
            'db_variables': {},
            'm_variables': [],
            'i_variables': [],
            'q_variables': []
        }

        for var in self.variables.values():
            if var.db_number is not None:
                if var.db_number not in config['db_variables']:
                    config['db_variables'][var.db_number] = []
                config['db_variables'][var.db_number].append({
                    'name': var.name,
                    'offset': var.byte_offset,
                    'bit': var.bit_offset,
                    'type': var.data_type
                })
            elif var.area == 'M':
                config['m_variables'].append({
                    'name': var.name,
                    'offset': var.byte_offset,
                    'bit': var.bit_offset,
                    'type': var.data_type
                })
            elif var.area == 'I':
                config['i_variables'].append({
                    'name': var.name,
                    'offset': var.byte_offset,
                    'bit': var.bit_offset,
                    'type': var.data_type
                })
            elif var.area == 'Q':
                config['q_variables'].append({
                    'name': var.name,
                    'offset': var.byte_offset,
                    'bit': var.bit_offset,
                    'type': var.data_type
                })

        return config


def parse_xlsx_variable_file(file_path: str, sheet_name: str = None) -> Dict[str, PLCVariable]:
    parser = XLSXVariableParser()
    return parser.parse_xlsx(file_path, sheet_name)
