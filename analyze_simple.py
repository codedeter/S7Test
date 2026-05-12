
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.parsers.xlsx_variable_parser import XLSXVariableParser

def main():
    plc_def_dir = os.path.join(os.path.dirname(__file__), 'plc_definitions')
    file_path = os.path.join(plc_def_dir, 'RXA800PLCTags.xlsx')
    
    print("Analyzing RXA800PLCTags.xlsx...")
    
    parser = XLSXVariableParser()
    variables = parser.parse_xlsx(file_path)
    
    print(f"\nTotal variables: {len(variables)}")
    
    print("\nFirst 100 variables:")
    for idx, (name, var) in enumerate(list(variables.items())[:100], 1):
        print(f"{idx:3d}. {name} | Address={var.logical_address} | Type={var.data_type}")
        if var.description:
            print(f"    Comment: {var.description}")
    
    # Analyze address formats
    print("\n\nAddress format analysis:")
    from collections import defaultdict
    addr_formats = defaultdict(int)
    for var in variables.values():
        addr = str(var.logical_address)
        if addr.startswith('%'):
            prefix = addr[1] if len(addr) > 1 else '?'
            addr_formats[prefix] += 1
        else:
            addr_formats['other'] += 1
    
    for prefix, cnt in sorted(addr_formats.items()):
        print(f"  %{prefix}... : {cnt}")

if __name__ == '__main__':
    main()
