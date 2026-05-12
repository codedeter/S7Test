
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.parsers.xlsx_variable_parser import XLSXVariableParser, get_xlsx_variable_summary

def main():
    plc_def_dir = os.path.join(os.path.dirname(__file__), 'plc_definitions')
    
    files = [
        ('RXA800PLCTags.xlsx', 'RXA800'),
        ('RXA1300PLCTags.xlsx', 'RXA1300'),
        ('RXA630-1PLCTags.xlsx', 'RXA630-1'),
        ('RXA630-2PLCTags.xlsx', 'RXA630-2'),
        ('RXA630-3PLCTags.xlsx', 'RXA630-3'),
        ('RXA630-4PLCTags.xlsx', 'RXA630-4'),
        ('RXB800PLCTags.xlsx', 'RXB800'),
    ]
    
    all_devices_data = {}
    
    for filename, device_name in files:
        file_path = os.path.join(plc_def_dir, filename)
        
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            continue
        
        print(f"\n{'=' * 80}")
        print(f"解析文件: {filename}")
        print(f"设备: {device_name}")
        print(f"{'=' * 80}")
        
        try:
            summary = get_xlsx_variable_summary(file_path)
            print(f"\n摘要:")
            print(f"  总变量数: {summary.get('total', 0)}")
            print(f"  DB变量数: {summary.get('db_count', 0)}")
            print(f"  M变量数: {summary.get('m_count', 0)}")
            print(f"  I变量数: {summary.get('i_count', 0)}")
            print(f"  Q变量数: {summary.get('q_count', 0)}")
            
            parser = XLSXVariableParser()
            parser.parse_xlsx(file_path)
            
            print(f"\nDB变量分布:")
            db_vars = parser.get_db_variables()
            db_nums = sorted(list(set(v.db_number for v in db_vars if v.db_number is not None)))
            for db_num in db_nums:
                db_vars_for_num = [v for v in db_vars if v.db_number == db_num]
                print(f"  DB{db_num}: {len(db_vars_for_num)} 个变量")
            
            all_devices_data[device_name] = {
                'summary': summary,
                'parser': parser,
                'db_variables': db_vars,
                'm_variables': parser.get_m_variables(),
                'i_variables': parser.get_i_variables(),
                'q_variables': parser.get_q_variables()
            }
            
            print(f"\n示例变量 (前10个):")
            for i, var in enumerate(list(parser.variables.values())[:10]):
                print(f"  {i+1}. {var.name} - {var.logical_address} - {var.data_type}")
                
        except Exception as e:
            print(f"解析失败: {e}")
            import traceback
            traceback.print_exc()
    
    return all_devices_data

if __name__ == '__main__':
    main()
