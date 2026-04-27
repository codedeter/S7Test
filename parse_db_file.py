import re

def parse_db_file(content):
    lines = content.strip().split('\n')

    variables = []
    struct_stack = []

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        if not line_stripped:
            continue

        if ': Struct' in line_stripped and not line_stripped.startswith('END_STRUCT'):
            struct_match = re.match(r'^\s*(\w+)\s*:', line_stripped)
            if struct_match:
                struct_name = struct_match.group(1)
                struct_stack.append(struct_name)
            continue

        if line_stripped.startswith('END_STRUCT'):
            if struct_stack:
                struct_stack.pop()
            continue

        var_match = re.match(r'^\s*(?:"?)([^":]+)(?:"?)\s*:\s*(\w+)(?:\s*\[.*?\])?\s*;', line_stripped)
        if var_match:
            var_name = var_match.group(1).strip()
            var_type = var_match.group(2).strip()

            if var_type.upper() == 'STRUCT':
                continue

            full_name = var_name
            if struct_stack:
                full_name = '.'.join(struct_stack) + '.' + var_name

            variables.append({
                'name': var_name,
                'full_name': full_name,
                'type': var_type,
                'struct': struct_stack[-1] if struct_stack else None
            })

    return variables

def calculate_offsets_s7(variables):
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
                'struct': var['struct'],
                'byte_offset': byte_offset,
                'bit_offset': bit_offset,
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
                'struct': var['struct'],
                'byte_offset': byte_offset,
                'bit_offset': 0,
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
                'struct': var['struct'],
                'byte_offset': byte_offset,
                'bit_offset': 0,
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
                'struct': var['struct'],
                'byte_offset': byte_offset,
                'bit_offset': 0,
            })

            byte_offset += 4

    return result, byte_offset

def main():
    with open(r'c:\Users\44673\Desktop\文件往这里存！！！\TRAE\S7Test\plc_definitions\GLABAL(柔性B800).db', 'r', encoding='utf-8') as f:
        content = f.read()

    variables = parse_db_file(content)
    offsets, total_size = calculate_offsets_s7(variables)

    print(f"\n=== GLABAL (DB1) Analysis ===")
    print(f"Total variables: {len(offsets)}")
    print(f"Calculated size: {total_size} bytes")

    print("\n--- Global bools (first 50) ---")
    global_bools = [v for v in offsets if v['type'].upper() == 'BOOL' and v['struct'] is None][:50]
    for v in global_bools:
        print(f"  Byte {v['byte_offset']}, Bit {v['bit_offset']}: {v['full_name']}")

    print("\n--- Struct bools (first 20) ---")
    struct_bools = [v for v in offsets if v['type'].upper() == 'BOOL' and v['struct'] is not None][:20]
    for v in struct_bools:
        print(f"  Byte {v['byte_offset']}, Bit {v['bit_offset']}: {v['full_name']}")

    print("\n--- Int/Real/DInt variables ---")
    int_vars = [v for v in offsets if v['type'].upper() in ('INT', 'DINT', 'REAL')]
    for v in int_vars:
        print(f"  Byte {v['byte_offset']}: {v['full_name']} ({v['type']})")

if __name__ == "__main__":
    main()