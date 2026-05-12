import subprocess
import time
import threading

def capture_output(process):
    """捕获进程输出"""
    while True:
        line = process.stdout.readline()
        if not line:
            break
        print(line.decode('utf-8').strip())

# 启动服务器
process = subprocess.Popen(
    ['python', '-u', 'run.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    cwd='c:\\Users\\44673\\Desktop\\文件往这里存！！！\\TRAE\\S7Test'
)

# 启动输出捕获线程
thread = threading.Thread(target=capture_output, args=(process,), daemon=True)
thread.start()

# 等待5秒后终止服务器
time.sleep(5)
process.terminate()
process.wait()