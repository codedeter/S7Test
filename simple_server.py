import sys
sys.path.insert(0, 'C:\\Users\\44673\\Desktop\\文件往这里存！！！\\TRAE\\S7Test')

from flask import Flask
import time

app = Flask(__name__)

@app.route('/')
def index():
    return 'Simple Server Running!'

if __name__ == '__main__':
    print('Starting simple server on port 3000...')
    time.sleep(2)
    app.run(host='0.0.0.0', port=3000, debug=False)