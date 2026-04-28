import sys
sys.path.insert(0, 'C:\\Users\\44673\\Desktop\\文件往这里存！！！\\TRAE\\S7Test')

from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

@app.route('/')
def index():
    return 'SocketIO Server'

@socketio.on('connect')
def handle_connect():
    print('Client connected')

if __name__ == '__main__':
    print('Before socketio.run()')
    try:
        socketio.run(app, host='0.0.0.0', port=3000, debug=False)
    except Exception as e:
        print(f'socketio.run() error: {e}')
    print('After socketio.run()')