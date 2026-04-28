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
        print('Initializing database...')
        data_processor = DataProcessor()
        data_processor.data_storage.init()
        print('Database initialized')

        print('Creating device manager...')
        device_manager = create_device_manager()

        print('Initializing devices...')
        init_devices(device_manager)

        print('Connecting to devices...')
        device_manager.connect_all()

        print('Creating Flask app...')
        app = create_app()
        socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

        print('Registering routes...')
        register_routes(app, device_manager)

        print('Creating SocketIO handler...')
        socketio_handler = SocketIOHandler(socketio, device_manager, data_processor)
        socketio_handler.register_events()

        print('Starting data collection task...')
        collection_task = DataCollectionTask(device_manager, data_processor)
        collection_task.start()

        print('Starting data sending thread...')
        socketio_handler.start_sending_thread()

        print(f'Server running on http://{config.SERVER_HOST}:{config.SERVER_PORT}')
        print(f'Data collection interval: {config.DATA_SAMPLING_INTERVAL}ms, Data sending interval: 200ms')
        
        socketio.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT, debug=False)
        
    except Exception as e:
        print(f'Server startup error: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()