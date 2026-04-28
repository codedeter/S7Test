import sys
sys.path.insert(0, 'C:\\Users\\44673\\Desktop\\文件往这里存！！！\\TRAE\\S7Test')

from flask import Flask, make_response
from flask_socketio import SocketIO
import os

from config.config import config
from config.devices_config import create_device_configs
from src.devices import DeviceManager, create_device_manager
from src.api.routes import register_routes
from src.services.data_processor import DataProcessor
from src.socketio_handler.events import SocketIOHandler, DataCollectionTask

def create_app():
    app = Flask(__name__, static_folder='../public', template_folder='../public')
    app.config['SECRET_KEY'] = 'secret!'
    
    @app.route('/')
    def index():
        html_path = os.path.join(os.path.dirname(__file__), '..', 'public', 'index.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        response = make_response(content)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Content-Type'] = 'text/html'
        return response
    
    return app

def init_devices(device_manager: DeviceManager):
    device_configs = create_device_configs()
    for device_config in device_configs:
        device_manager.add_device(device_config)
    print(f"Initialized {len(device_configs)} device(s)")

def main():
    try:
        print('Step 1: Initializing database...')
        data_processor = DataProcessor()
        data_processor.data_storage.init()
        print('Step 1: Database initialized')

        print('Step 2: Creating device manager...')
        device_manager = create_device_manager()
        print('Step 2: Device manager created')

        print('Step 3: Initializing devices...')
        init_devices(device_manager)
        print('Step 3: Devices initialized')

        print('Step 4: SKIPPING device connection (test mode)...')
        # 跳过设备连接

        print('Step 5: Creating Flask app...')
        app = create_app()
        socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
        print('Step 5: Flask app created')

        print('Step 6: Registering routes...')
        register_routes(app, device_manager)
        print('Step 6: Routes registered')

        print('Step 7: Creating SocketIO handler...')
        socketio_handler = SocketIOHandler(socketio, device_manager, data_processor)
        socketio_handler.register_events()
        print('Step 7: SocketIO handler created')

        print('Step 8: Starting data collection task...')
        collection_task = DataCollectionTask(device_manager, data_processor)
        collection_task.start()
        print('Step 8: Data collection started')

        print('Step 9: Starting data sending thread...')
        socketio_handler.start_sending_thread()
        print('Step 9: Data sending thread started')

        print(f'Step 10: Starting server on http://{config.SERVER_HOST}:{config.SERVER_PORT}')
        socketio.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT, debug=False)
        print('Server stopped')
        
    except Exception as e:
        print(f'Server startup error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()