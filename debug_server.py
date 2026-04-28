import sys
sys.path.insert(0, 'C:\\Users\\44673\\Desktop\\文件往这里存！！！\\TRAE\\S7Test')

import traceback

def main():
    try:
        print('Step 1: Initializing database...')
        from src.services.data_processor import DataProcessor
        data_processor = DataProcessor()
        data_processor.data_storage.init()
        print('Step 1: Database initialized')

        print('Step 2: Creating device manager...')
        from src.devices import create_device_manager
        device_manager = create_device_manager()
        print('Step 2: Device manager created')

        print('Step 3: Initializing devices...')
        from config.devices_config import create_device_configs
        device_configs = create_device_configs()
        for device_config in device_configs:
            device_manager.add_device(device_config)
        print(f'Step 3: Initialized {len(device_configs)} device(s)')

        print('Step 4: Connecting to devices...')
        results = device_manager.connect_all()
        print(f'Step 4: Connection results: {results}')

        print('Step 5: Creating Flask app...')
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            return 'PLC Monitor Server'
        
        print('Step 5: Flask app created')

        print('Step 6: Starting Flask server...')
        app.run(host='0.0.0.0', port=3000, debug=False)
        
    except Exception as e:
        print(f'Server startup error: {e}')
        traceback.print_exc()

if __name__ == '__main__':
    main()