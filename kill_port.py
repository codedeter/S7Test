
import subprocess
import sys
import re
import time

def kill_process_using_port(port):
    print(f"查找使用端口 {port} 的进程...")
    try:
        result = subprocess.check_output(
            ['netstat', '-ano', '-p', 'TCP'],
            encoding='gbk',
            errors='ignore'
        )
        
        found = False
        for line in result.split('\n'):
            line = line.strip()
            if f':{port}' in line and ('LISTENING' in line or 'LISTEN' in line):
                parts = re.split(r'\s+', line)
                if parts:
                    pid = parts[-1]
                    print(f"找到进程 PID: {pid}")
                    print(f"正在终止进程...")
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=True)
                        print("进程已终止")
                        found = True
                        time.sleep(1)
                    except Exception as e:
                        print(f"终止进程失败: {e}")
        
        if not found:
            print(f"没有找到使用端口 {port} 的进程")
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    kill_process_using_port(3000)
