
import openpyxl
import os

def view_excel(file_path):
    wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
    ws = wb.active
    
    print(f"Worksheet: {ws.title}")
    print(f"\nFirst 50 rows, all columns:")
    print("="*120)
    
    for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if row_idx > 50:
            break
        
        print(f"Row {row_idx}: {row}")
    
    wb.close()

def main():
    plc_def_dir = os.path.join(os.path.dirname(__file__), 'plc_definitions')
    file_path = os.path.join(plc_def_dir, 'RXA800PLCTags.xlsx')
    view_excel(file_path)

if __name__ == '__main__':
    main()
