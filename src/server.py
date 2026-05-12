import sys
import os
import io
import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, make_response
from flask_socketio import SocketIO
import threading
import time

from config.config import config
from config.devices_config import create_device_configs
from src.devices import DeviceManager, create_device_manager
from src.api.routes import register_routes
from src.services.data_processor import DataProcessor
from src.socketio_handler.events import SocketIOHandler, DataCollectionTask
from src.startup import get_startup_manager, StartupPhase

original_stderr = sys.stderr


def create_app():
    app = Flask(__name__, static_folder='../public', template_folder='../public')
    app.config['SECRET_KEY'] = 'secret!'
    
    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    
    @app.route('/')
    def index():
        html_path = os.path.join(os.path.dirname(__file__), '..', 'public', 'index.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        response = make_response(content)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        response.headers['Content-Type'] = 'text/html'
        return response
    
    return app


def init_devices(device_manager: DeviceManager):
    device_configs = create_device_configs()
    for device_config in device_configs:
        device_manager.add_device(device_config)
    return len(device_configs)


def start_background_connection(device_manager: DeviceManager):
    def connection_task():
        print(f'[{time.strftime("%H:%M:%S")}] [Background] ========================================')
        print(f'[{time.strftime("%H:%M:%S")}] [Background] Starting device connections...')
        print(f'[{time.strftime("%H:%M:%S")}] [Background] Devices to connect: {list(device_manager.devices.keys())}')
        
        try:
            print(f'[{time.strftime("%H:%M:%S")}] [Background] Connecting to devices...')
            print(f'[{time.strftime("%H:%M:%S")}] [Background] Device count: {len(device_manager.devices)}')
            
            start_time = time.time()
            results = device_manager.connect_all()
            elapsed = time.time() - start_time
            
            print(f'[{time.strftime("%H:%M:%S")}] [Background] Connection results received after {elapsed:.2f}s')
            print(f'[{time.strftime("%H:%M:%S")}] [Background] Results: {results}')
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            print(f'[{time.strftime("%H:%M:%S")}] [Background] Connection summary: {success_count}/{total_count} devices connected')
            
            for device_id, success in results.items():
                if success:
                    print(f'[{time.strftime("%H:%M:%S")}] [Background] OK {device_id} connected successfully')
                else:
                    print(f'[{time.strftime("%H:%M:%S")}] [Background] FAIL {device_id} connection failed - will retry automatically')
            
            # 在连接完成后启动健康检查，确保重连机制在后台运行
            print(f'[{time.strftime("%H:%M:%S")}] [Background] Starting connection health check...')
            device_manager._connection_pool.start_health_check()
            
        except Exception as e:
            print(f'[{time.strftime("%H:%M:%S")}] [Background] Connection error: {e}')
            import traceback
            traceback.print_exc()
            print(f'[{time.strftime("%H:%M:%S")}] [Background] Error type:', type(e).__name__)
            
        print(f'[{time.strftime("%H:%M:%S")}] [Background] ========================================')
    
    thread = threading.Thread(target=connection_task, daemon=True)
    thread.start()
    print(f'[{time.strftime("%H:%M:%S")}] Background connection thread started')


def register_shutdown_handlers(startup_manager, socketio_handler=None, collection_task=None):
    def shutdown_handler(signum, frame):
        print(f"\nReceived shutdown signal ({signum})")
        startup_manager.shutdown()
        
        if socketio_handler:
            socketio_handler.stop_sending_thread()
        if collection_task:
            collection_task.stop()
        
        time.sleep(1)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)


def main():
    startup_manager = get_startup_manager()
    startup_manager.begin_startup()
    
    socketio_handler = None
    collection_task = None
    
    try:
        print('=' * 50)
        print('PLC Data Monitor System v3.1')
        print('=' * 50)
        
        startup_manager.start_phase(StartupPhase.DATABASE_INIT)
        print('\n[1/7] Initializing database...')
        data_processor = DataProcessor()
        data_processor.data_storage.init()
        startup_manager.complete_phase(StartupPhase.DATABASE_INIT, "Database initialized")

        startup_manager.start_phase(StartupPhase.DEVICE_MANAGER_CREATE)
        print('\n[2/7] Creating device manager...')
        device_manager = create_device_manager()
        startup_manager.complete_phase(StartupPhase.DEVICE_MANAGER_CREATE, "Device manager created")

        startup_manager.start_phase(StartupPhase.DEVICES_INIT)
        print('\n[3/7] Initializing devices...')
        device_count = init_devices(device_manager)
        startup_manager.complete_phase(StartupPhase.DEVICES_INIT, f"{device_count} device(s) initialized")

        startup_manager.start_phase(StartupPhase.FLASK_APP_CREATE)
        print('\n[4/7] Creating Flask app...')
        app = create_app()
        socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
        startup_manager.complete_phase(StartupPhase.FLASK_APP_CREATE, "Flask app created")

        startup_manager.start_phase(StartupPhase.ROUTES_REGISTER)
        print('\n[5/7] Registering routes...')
        register_routes(app, device_manager)
        startup_manager.complete_phase(StartupPhase.ROUTES_REGISTER, "Routes registered")

        startup_manager.start_phase(StartupPhase.SERVICES_START)
        print('\n[6/7] Starting services...')
        socketio_handler = SocketIOHandler(socketio, device_manager, data_processor)
        socketio_handler.register_events()

        startup_manager.start_phase(StartupPhase.BACKGROUND_CONNECT)
        print('\n[7/7] Starting background connections...')
        start_background_connection(device_manager)
        
        # 等待连接完成（给后台线程一些时间）
        print('[Main] Waiting for initial connections...')
        time.sleep(2)
        
        startup_manager.complete_phase(StartupPhase.BACKGROUND_CONNECT, "Background connections started")
        
        # 在连接完成后启动数据采集任务
        print('[Main] Starting data collection task after connection...')
        collection_task = DataCollectionTask(device_manager, data_processor)
        collection_task.start()

        startup_manager.finish_startup()

        register_shutdown_handlers(startup_manager, socketio_handler, collection_task)

        print(f'\nServer running on http://{config.SERVER_HOST}:{config.SERVER_PORT}')
        print(f'Data collection interval: {config.DATA_SAMPLING_INTERVAL}ms')
        print('=' * 50)
        print('\nPress Ctrl+C to stop the server\n')
        
        socketio.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT, debug=False)
        
    except KeyboardInterrupt:
        print('\n\nServer stopped by user')
        startup_manager.shutdown()
    except Exception as e:
        print(f'\nServer startup error: {e}')
        import traceback
        traceback.print_exc()
        startup_manager.fail_phase(startup_manager.context.current_phase, e)
    finally:
        if socketio_handler:
            socketio_handler.stop_sending_thread()
        if collection_task:
            collection_task.stop()


if __name__ == '__main__':
    main()