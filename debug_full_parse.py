
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from src.parsers.xlsx_variable_parser import XLSXVariableParser

plc_def_dir = os.path.join(os.path.dirname(__file__), 'plc_definitions')
file_path = os.path.join(plc_def_dir, 'RXA800PLCTags.xlsx')

parser = XLSXVariableParser()
variables = parser.parse_xlsx(file_path)

print(f"Total variables: {len(variables)}")

print("\nFirst 35 variables with full info:")
for idx, (name, var) in enumerate(list(variables.items())[:35], 1):
    print(f"\n{idx}. {name}")
    print(f"   data_type: {repr(var.data_type)}")
    print(f"   logical_address: {repr(var.logical_address)}")
    print(f"   area: {repr(var.area)}")
    print(f"   byte_offset: {repr(var.byte_offset)}")
    print(f"   bit_offset: {repr(var.bit_offset)}")
