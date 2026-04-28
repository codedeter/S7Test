
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Super simple test server
"""

print('=' * 50)
print('TEST SERVER STARTING...')
print('=' * 50)

import sys
print(f'Python version: {sys.version}')

from flask import Flask
from flask_socketio import SocketIO
import time
import threading

app = Flask(__name__, static_folder='../public', template_folder='../public')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', transports=['polling'])

count = 0

def sending_loop():
    global count
    while True:
        try:
            test_data = {
                'test': 'Hello World!',
                'count': count
            }
            socketio.emit('test_data', test_data)
            print(f'[SocketIO] Emitted test_data #{count}')
            count += 1
        except Exception as e:
            print(f'Error: {e}')
        time.sleep(1)

@app.route('/')
def index():
    html_path = '../public/index.html'
    with open(html_path, 'r', encoding='utf-8') as f:
        return f.read()

@socketio.on('connect')
def handle_connect():
    print('Client connected!')

if __name__ == '__main__':
    print('Starting sending thread...')
    t = threading.Thread(target=sending_loop, daemon=True)
    t.start()
    
    print('=' * 50)
    print('Server started on http://localhost:3000')
    print('=' * 50)
    
    socketio.run(app, host='0.0.0.0', port=3000, debug=False)
