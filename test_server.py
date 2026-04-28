import sys
sys.path.insert(0, 'C:\\Users\\44673\\Desktop\\文件往这里存！！！\\TRAE\\S7Test')

from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Server is running!'

if __name__ == '__main__':
    print('Starting test server on port 3001...')
    app.run(host='0.0.0.0', port=3001, debug=False)