import re
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class ParsedVariable:
    name: str
    data_type: str
    byte_offset: int
    bit_offset: Optional[int] = None
    struct_name: Optional[str] = None
    array_info: Optional[str] = None


@dataclass
class ParsedDataBlock:
    db_number: int
    name: str
    variables: List[ParsedVariable] = None
    total_size: int = 0
    optimized_access: bool = False

    def __post_init__(self):
        if self.variables is None:
            self.variables = []


class DBFileParser:
    TYPE_SIZES = {
        'BOOL': 1,
        'BYTE': 1,
        'WORD': 2,
        'DWORD': 4,
        'INT': 2,
        'DINT': 4,
        'REAL': 4,
        'LREAL': 8,
        'S5TIME': 2,
        'TIME': 4,
        'DATE': 2,
        'TIME_OF_DAY': 4,
        'DATE_AND_TIME': 8,
        'CHAR': 1,
        'WCHAR': 2,
        'STRING': 1,
        'WSTRING': 2,
    }

    def __init__(self):
        self.data_blocks: Dict[int, ParsedDataBlock] = {}
        self.current_db: Optional[ParsedDataBlock] = None
        self._current_byte_offset = 0

    def parse_file(self, file_path: str) -> Dict[int, ParsedDataBlock]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"DB file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除BOM字符
        if content.startswith('\ufeff'):
            content = content[1:]

        return self.parse_content(content)

    def parse_content(self, content: str) -> Dict[int, ParsedDataBlock]:
        self.data_blocks = {}
        self._current_byte_offset = 0

        lines = content.split('\n')
        in_struct = False
        struct_name = None
        current_struct_name = None
        struct_stack = []

        db_number_pattern = re.compile(r'DATA_BLOCK\s*["\']([^"\']+)["\']', re.IGNORECASE)
        optimized_pattern = re.compile(r"S7_Optimized_Access\s*:=\s*'(\w+)'", re.IGNORECASE)
        struct_pattern = re.compile(r'(\w+)\s*:\s*Struct', re.IGNORECASE)
        anonymous_struct_pattern = re.compile(r'^\s*STRUCT\s*$', re.IGNORECASE)
        end_struct_pattern = re.compile(r'END_STRUCT', re.IGNORECASE)
        var_pattern = re.compile(r'["\']?(\w+)["\']?\s*:\s*([A-Za-z0-9_]+)(?:\s*;\s*(.*))?', re.IGNORECASE)
        begin_pattern = re.compile(r'BEGIN', re.IGNORECASE)
        end_data_block_pattern = re.compile(r'END_DATA_BLOCK', re.IGNORECASE)

        for line in lines:
            line = line.strip()

            db_match = db_number_pattern.match(line)
            if db_match:
                db_name = db_match.group(1)
                db_num = self._extract_db_number(db_name)
                self.current_db = ParsedDataBlock(db_number=db_num, name=db_name)
                self._current_byte_offset = 0
                struct_stack = []
                continue

            opt_match = optimized_pattern.search(line)
            if opt_match and self.current_db:
                self.current_db.optimized_access = opt_match.group(1).upper() == 'TRUE'

            struct_match = struct_pattern.match(line)
            if struct_match and self.current_db:
                struct_name = struct_match.group(1)
                in_struct = True
                current_struct_name = struct_name
                struct_stack.append(struct_name)
                continue

            if anonymous_struct_pattern.match(line) and self.current_db:
                in_struct = True
                current_struct_name = None
                struct_stack.append(None)
                continue

            if end_struct_pattern.match(line):
                if struct_stack:
                    struct_stack.pop()
                    current_struct_name = struct_stack[-1] if struct_stack else None
                in_struct = len(struct_stack) > 0
                continue

            if begin_pattern.match(line):
                continue

            if end_data_block_pattern.match(line):
                if self.current_db and self.current_db.variables:
                    self.data_blocks[self.current_db.db_number] = self.current_db
                continue

            var_match = var_pattern.match(line)
            if var_match and self.current_db and not line.startswith('END_STRUCT'):
                var_name = var_match.group(1)
                var_type = var_match.group(2).upper()

                if var_type in self.TYPE_SIZES:
                    var_size = self.TYPE_SIZES[var_type]

                    parsed_var = ParsedVariable(
                        name=var_name,
                        data_type=var_type,
                        byte_offset=self._current_byte_offset,
                        struct_name=current_struct_name if in_struct else None
                    )
                    self.current_db.variables.append(parsed_var)
                    self._current_byte_offset += var_size
                elif var_type == 'STRUCT':
                    pass

        return self.data_blocks

    def _extract_db_number(self, db_name: str) -> int:
        # 数据块名称到DB编号的映射
        name_to_db = {
            'GLABAL': 1,
            '显示值': 10,
            '故障报警': 51,
            'GLOBAL': 1,
            'GLOBALDATA': 1,
        }
        
        # 首先检查名称映射
        if db_name.upper() in name_to_db:
            return name_to_db[db_name.upper()]
        
        patterns = [
            (r'DB(\d+)', lambda m: int(m.group(1))),
            (r'GLABAL', lambda m: 1),
        ]

        for pattern, extractor in patterns:
            match = re.match(pattern, db_name, re.IGNORECASE)
            if match:
                return extractor(match)

        match = re.search(r'\d+', db_name)
        if match:
            return int(match.group())

        return 0

    def get_db_mapping(self, db_number: int) -> Dict[int, List[tuple]]:
        if db_number not in self.data_blocks:
            return {}

        mapping = {}
        for var in self.data_blocks[db_number].variables:
            if var.byte_offset not in mapping:
                mapping[var.byte_offset] = []
            mapping[var.byte_offset].append((var.bit_offset or 0, var.name))

        return mapping

    def get_db_variables_by_type(self, db_number: int, data_type: str) -> List[ParsedVariable]:
        if db_number not in self.data_blocks:
            return []

        return [v for v in self.data_blocks[db_number].variables if v.data_type.upper() == data_type.upper()]

    def generate_collector_code(self, db_number: int) -> str:
        if db_number not in self.data_blocks:
            return ""

        db = self.data_blocks[db_number]
        lines = [f"self.db{db_number}_mapping = {{"]

        for var in db.variables:
            lines.append(f"    {var.byte_offset}: ('{var.name}', '{var.data_type}'),")

        lines.append("}")
        return "\n".join(lines)


def parse_db_files_in_directory(directory: str) -> Dict[int, ParsedDataBlock]:
    parser = DBFileParser()
    all_blocks = {}

    for filename in os.listdir(directory):
        if filename.endswith('.db'):
            file_path = os.path.join(directory, filename)
            try:
                blocks = parser.parse_file(file_path)
                all_blocks.update(blocks)
            except Exception as e:
                print(f"Failed to parse {filename}: {e}")

    return all_blocks
