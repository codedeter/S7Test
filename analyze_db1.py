import re

def parse_db_file(db_content):
    lines = db_content.strip().split('\n')
    variables = []
    current_struct = None
    current_struct_depth = 0

    struct_pattern = re.compile(r'^\s*(\w+)\s*:\s*Struct')
    end_struct_pattern = re.compile(r'^\s*END_STRUCT')
    var_pattern = re.compile(r'^\s*"?([^"]+)"?\s*:\s*(\w+)(?:\s*;|;)')

    for line in lines:
        struct_match = struct_pattern.search(line)
        if struct_match:
            current_struct = struct_match.group(1)
            current_struct_depth += 1
            continue

        if end_struct_pattern.search(line):
            current_struct = None
            continue

        var_match = var_pattern.search(line)
        if var_match:
            var_name = var_match.group(1)
            var_type = var_match.group(2)

            full_name = var_name
            if current_struct:
                full_name = f"{current_struct}.{var_name}"

            variables.append({
                'name': var_name,
                'full_name': full_name,
                'type': var_type,
                'struct': current_struct
            })

    return variables

def calculate_offsets(variables):
    byte_offset = 0
    bit_offset = 0
    result = []

    for var in variables:
        vtype = var['type'].upper()

        if vtype == 'BOOL':
            if bit_offset >= 8:
                byte_offset += 1
                bit_offset = 0

            result.append({
                'name': var['name'],
                'full_name': var['full_name'],
                'type': var['type'],
                'byte_offset': byte_offset,
                'bit_offset': bit_offset
            })

            bit_offset += 1

        elif vtype in ('INT', 'BYTE', 'WORD'):
            if bit_offset > 0:
                byte_offset += 1
                bit_offset = 0

            result.append({
                'name': var['name'],
                'full_name': var['full_name'],
                'type': var['type'],
                'byte_offset': byte_offset,
                'bit_offset': 0
            })

            byte_offset += 2

        elif vtype in ('DINT', 'DWORD'):
            if bit_offset > 0:
                byte_offset += 1
                bit_offset = 0

            result.append({
                'name': var['name'],
                'full_name': var['full_name'],
                'type': var['type'],
                'byte_offset': byte_offset,
                'bit_offset': 0
            })

            byte_offset += 4

        elif vtype == 'REAL':
            if bit_offset > 0:
                byte_offset += 1
                bit_offset = 0

            result.append({
                'name': var['name'],
                'full_name': var['full_name'],
                'type': var['type'],
                'byte_offset': byte_offset,
                'bit_offset': 0
            })

            byte_offset += 4

        elif 'ARRAY' in vtype or 'STRUCT' in vtype:
            continue

        else:
            print(f"Unknown type: {vtype} for {var['name']}")

    return result, byte_offset

def main():
    with open(r'c:\Users\44673\Desktop\文件往这里存！！！\TRAE\S7Test\plc_definitions\GLABAL(柔性B800).db', 'r', encoding='utf-8') as f:
        content = f.read()

    db_match = re.search(r'DATA_BLOCK\s+"[^"]+"\s+(.*?)BEGIN', content, re.DOTALL)
    if not db_match:
        print("Could not find DB definition")
        return

    struct_content = db_match.group(1)
    variables = parse_db_file(struct_content)
    offsets, total_size = calculate_offsets(variables)

    print(f"=== GLABAL (DB1) - Total variables: {len(offsets)}, Size: {total_size} bytes ===\n")

    print("--- Boolean Variables (byte_offset: bit_offset) ---")
    bool_vars = [(v['full_name'], v['byte_offset'], v['bit_offset']) for v in offsets if v['type'].upper() == 'BOOL']
    for i, (name, byte_off, bit_off) in enumerate(bool_vars[:120]):
        print(f"  Byte {byte_off}, Bit {bit_off}: {name}")

    print(f"\n--- Integer/Real Variables ---")
    non_bool = [(v['full_name'], v['byte_offset'], v['type']) for v in offsets if v['type'].upper() != 'BOOL']
    for name, byte_off, vtype in non_bool:
        print(f"  Byte {byte_off}: {name} ({vtype})")

    print(f"\nTotal size: {total_size} bytes")

if __name__ == "__main__":
    main()