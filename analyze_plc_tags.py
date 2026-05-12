
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.parsers.xlsx_variable_parser import XLSXVariableParser

def analyze_file(file_path, device_name):
    print(f"\n{'=' * 80}")
    print(f"详细分析: {device_name}")
    print(f"{'=' * 80}")
    
    parser = XLSXVariableParser()
    variables = parser.parse_xlsx(file_path)
    
    print(f"\n所有变量列表 (全部 {len(variables)} 个:")
    
    # 打印所有变量的地址
    for i, (name, var) in enumerate(variables.items()):
        if i &lt; 50:  # 只打印前50个查看
            print(f"  {i+1}. {name} | {var.logical_address} | {var.data_type}")
            if hasattr(var, 'description') and var.description:
                print(f"       描述: {var.description}")
    
    # 查看地址模式分析
    print(f"\n地址模式分析:")
    addr_patterns = set()
    for var in variables.values():
        addr = str(var.logical_address)
        if addr:
            if addr.startswith('%'):
                pattern = addr[1] if len(addr) &gt; 1 else 'unknown'
                addr_patterns.add(pattern)
    print(f"  发现的地址类型: {sorted(list(addr_patterns))}")
    
    # 统计各类型
    type_counts = {}
    for var in variables.values():
        t = var.data_type
        type_counts[t] = type_counts.get(t, 0) + 1
    
    print(f"\n数据类型分布:")
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count}")

def main():
    plc_def_dir = os.path.join(os.path.dirname(__file__), 'plc_definitions')
    
    # 只分析一个文件看详细内容
    analyze_file(os.path.join(plc_def_dir, 'RXA800PLCTags.xlsx'), 'RXA800')

if __name__ == '__main__':
    main()
