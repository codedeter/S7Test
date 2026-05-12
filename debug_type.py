
import openpyxl
import os

def debug_types():
    plc_def_dir = os.path.join(os.path.dirname(__file__), 'plc_definitions')
    file_path = os.path.join(plc_def_dir, 'RXA800PLCTags.xlsx')
    
    wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
    ws = wb.active
    
    print("First 60 rows:")
    print("-" * 120)
    for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if row_idx > 60:
            break
        
        if row_idx == 1:
            print(f"Row 1: {row}")
        else:
            name = row[0]
            data_type = row[2]
            address = row[3]
            print(f"Row {row_idx}: name='{name}', type='{data_type}', addr='{address}'")
    
    wb.close()

debug_types()
