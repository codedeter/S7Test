import os
import re
import shutil
import sys

base = r"c:\Users\44673\Desktop\文件往这里存！！！\TRAE\S7Test"

# Read network monitor
nm_path = os.path.join(base, "src", "devices", "network_monitor.py")
with open(nm_path, "r", encoding="utf-8") as f:
    content = f.read()

# Step 1: Backup the file
backup_path = nm_path + ".backup"
shutil.copy2(nm_path, backup_path)
print("Backed up to:", backup_path)

# Step 2: Add import re
if "import re" not in content:
    content = content.replace("import subprocess", "import subprocess\nimport re")
    print("Added import re")

# Step 3: Parse the file
lines = content.splitlines()

# Find get_all_interfaces
in_method = False
method_start = 0
method_end = 0

for i, line in enumerate(lines):
    if "def get_all_interfaces" in line:
        method_start = i
        in_method = True
    elif in_method:
        if line.strip() and not line.startswith((" ", "\t")):
            method_end = i
            break
        if i == len(lines) - 1:
            method_end = i + 1

if method_end > method_start:
    print("Found method from line", method_start, "to", method_end)
    
    # Create new method content
    new_method = '''    def get_all_interfaces(self) -> List[NetworkInterface]:
        interfaces = []
        try:
            if platform.system() == 'Windows':
                result = subprocess.run(['ipconfig', '/all'], capture_output=True, text=True)
                lines = result.stdout.split('\\n')
                current_iface = None
                
                # Windows adapter name patterns
                adapter_pattern = re.compile(r'^(.*?) adapter (.*?):$', re.IGNORECASE)
                
                for line in lines:
                    line = line.strip()
                    
                    # Check for adapter name lines
                    adapter_match = adapter_pattern.search(line)
                    if adapter_match:
                        if current_iface and current_iface.ip_address:
                            interfaces.append(current_iface)
                        
                        adapter_type = adapter_match.group(1).strip()
                        adapter_name = adapter_match.group(2).strip()
                        
                        # Clean up the name
                        clean_name = adapter_name
                        if 'Wireless' in adapter_type:
                            clean_name = f"Wi-Fi: {adapter_name}"
                        elif 'Ethernet' in adapter_type:
                            clean_name = f"Ethernet: {adapter_name}"
                        
                        current_iface = NetworkInterface(name=clean_name, ip_address='')
                    elif current_iface and ('IPv4 Address' in line or 'IPv4 地址' in line):
                        # Extract IPv4 address
                        ip_match = re.search(r'(\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})', line)
                        if ip_match:
                            ip = ip_match.group(1)
                            if ip and not ip.startswith('169.254'):
                                current_iface.ip_address = ip
                
                # Add the last interface if it has an IP
                if current_iface and current_iface.ip_address:
                    interfaces.append(current_iface)
'''
    
    new_method_lines = new_method.splitlines()
    
    # Build new content
    new_content = lines[:method_start] + new_method_lines + lines[method_end:]
    
    with open(nm_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_content))
    
    print("Network monitor updated successfully")
else:
    print("Could not find method")

print()
print("=== Complete ===")
