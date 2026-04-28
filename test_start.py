import sys
sys.path.insert(0, 'C:\\Users\\44673\\Desktop\\文件往这里存！！！\\TRAE\\S7Test')

import traceback

try:
    print('Loading config...')
    from config.config import config
    print('Config loaded')
    
    print('Loading device config...')
    from config.devices_config import create_device_configs
    print('Device config loaded')
    
    print('Loading device manager...')
    from src.devices import DeviceManager, create_device_manager
    print('Device manager loaded')
    
    print('Loading routes...')
    from src.api.routes import register_routes
    print('Routes loaded')
    
    print('Loading data processor...')
    from src.services.data_processor import DataProcessor
    print('Data processor loaded')
    
    print('Loading socketio handler...')
    from src.socketio_handler.events import SocketIOHandler, DataCollectionTask
    print('SocketIO handler loaded')
    
    print('\nInitializing database...')
    data_processor = DataProcessor()
    data_processor.data_storage.init()
    print('Database initialized')
    
    print('\nCreating device manager...')
    device_manager = create_device_manager()
    
    print('\nInitializing devices...')
    device_configs = create_device_configs()
    for device_config in device_configs:
        device_manager.add_device(device_config)
    print(f'Initialized {len(device_configs)} device(s)')
    
    print('\nConnecting to devices...')
    results = device_manager.connect_all()
    print(f'Connection results: {results}')
    
    print('\nStarting Flask app...')
    from flask import Flask, make_response
    from flask_socketio import SocketIO
    
    app = Flask(__name__, static_folder='../public', template_folder='../public')
    app.config['SECRET_KEY'] = 'secret!'
    
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    print('SocketIO created')
    
    register_routes(app, device_manager)
    print('Routes registered')
    
    socketio_handler = SocketIOHandler(socketio, device_manager, data_processor)
    socketio_handler.register_events()
    print('SocketIO events registered')
    
    collection_task = DataCollectionTask(device_manager, data_processor)
    collection_task.start()
    print('Data collection task started')
    
    socketio_handler.start_sending_thread()
    print('Data sending thread started')
    
    print(f'\nServer running on http://{config.SERVER_HOST}:{config.SERVER_PORT}')
    socketio.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT, debug=False)
    
except Exception as e:
    print(f'Error: {e}')
    traceback.print_exc()
    import time
    time.sleep(5)
