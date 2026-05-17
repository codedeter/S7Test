import sys
import os
import io
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, make_response, jsonify, request
from flask_socketio import SocketIO

from config.config import config
from src.devices import DeviceManager, create_device_manager
from src.api.routes import register_routes
from src.services.data_processor import DataProcessor
from src.socketio_handler.events import SocketIOHandler
from src.services.optimized_collector import create_optimized_collector
from src.startup.startup_manager import get_startup_manager, StartupPhase

def create_app():
    app = Flask(__name__, static_folder='../public', template_folder='../public')
    app.config['SECRET_KEY'] = 'secret!'
    
    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    @app.route('/api/test', methods=['GET'])
    def test_api():
        print('[DEBUG] /api/test called')
        return jsonify({'status': 'ok', 'message': 'Test API works!'})

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

def graceful_shutdown(socketio_handler, optimized_collector, device_manager, data_processor, startup_manager):
    """
    优雅地关闭所有服务器组件
    
    Args:
        socketio_handler: SocketIO处理?        optimized_collector: 数据采集?        device_manager: 设备管理?        data_processor: 数据处理?        startup_manager: 启动管理?    """
    print('\n' + '=' * 50)
    print('[Shutdown] Initiating graceful shutdown...')
    print('=' * 50)
    
    try:
        if 1:
            print('\n[Shutdown 1/6] Stopping data collector...')
            if optimized_collector:
                try:
                    optimized_collector.stop()
                    print('[Shutdown] ?Data collector stopped')
                except Exception as e:
                    print(f'[Shutdown] ?Error stopping data collector: {e}')
        
        if 1:
            print('\n[Shutdown 2/6] Stopping SocketIO data sender...')
            if socketio_handler:
                try:
                    socketio_handler.stop_sending_thread()
                    print('[Shutdown] ?SocketIO sender stopped')
                except Exception as e:
                    print(f'[Shutdown] ?Error stopping SocketIO sender: {e}')
        
        if 1:
            print('\n[Shutdown 3/6] Stopping device connections...')
            if device_manager:
                try:
                    device_manager.stop_collection()
                    print('[Shutdown] ?Device collection stopped')
                except Exception as e:
                    print(f'[Shutdown] ?Error stopping device collection: {e}')
        
        if 1:
            print('\n[Shutdown 4/6] Disconnecting PLC devices...')
            if device_manager:
                try:
                    device_manager.disconnect_all()
                    print('[Shutdown] ?PLC devices disconnected')
                except Exception as e:
                    print(f'[Shutdown] ?Error disconnecting PLCs: {e}')
        
        if 1:
            print('\n[Shutdown 5/6] Stopping network monitor...')
            if device_manager:
                try:
                    device_manager.stop_network_monitor()
                    print('[Shutdown] ?Network monitor stopped')
                except Exception as e:
                    print(f'[Shutdown] ?Error stopping network monitor: {e}')
        
        if 1:
            print('\n[Shutdown 6/6] Cleaning up data processor...')
            if data_processor:
                try:
                    data_processor.shutdown()
                    print('[Shutdown] ?Data processor shutdown')
                except Exception as e:
                    print(f'[Shutdown] ?Error shutting down data processor: {e}')
        
        if startup_manager:
            print('\n[Shutdown] Notifying shutdown callbacks...')
            try:
                startup_manager.shutdown()
                print('[Shutdown] ?Startup manager shutdown complete')
            except Exception as e:
                print(f'[Shutdown] ?Error in startup manager shutdown: {e}')
        
        print('\n' + '=' * 50)
        print('[Shutdown] ?All components stopped successfully!')
        print('=' * 50)
        
    except Exception as e:
        print(f'\n[Shutdown] Error during shutdown: {e}')
        import traceback
        traceback.print_exc()

def main():
    print('=' * 50)
    print('PLC Data Monitor System v3.2 - Optimized')
    print('=' * 50)
    
    startup_manager = get_startup_manager()
    startup_manager.begin_startup()
    
    print('\n[1/8] Creating Flask app...')
    app = create_app()
    startup_manager.start_phase(StartupPhase.FLASK_APP_CREATE)
    
    print('\n[2/8] Creating SocketIO...')
    socketio = SocketIO(app, 
                        cors_allowed_origins="*", 
                        async_mode='threading',
                        ping_interval=10000,
                        ping_timeout=30000,
                        transports=['polling'],
                        allow_upgrades=False,
                        cookie=False)
    print('[SocketIO] Configuration: polling only, CORS enabled')
    
    print('\n[3/8] Initializing database...')
    data_processor = DataProcessor()
    data_processor.data_storage.init()
    startup_manager.start_phase(StartupPhase.DATABASE_INIT)
    
    print('\n[4/8] Creating device manager...')
    device_manager = create_device_manager()
    startup_manager.start_phase(StartupPhase.DEVICE_MANAGER_CREATE)
    
    from config.device_loader import create_device_loader
    device_loader = create_device_loader()
    device_configs = device_loader.load_all()
    for device_config in device_configs:
        device_manager.add_device(device_config)
    print(f'      Loaded {len(device_configs)} device(s)')
    startup_manager.start_phase(StartupPhase.DEVICES_INIT)
    
    print('\n[5/8] Registering routes and handlers...')
    register_routes(app, device_manager)
    
    socketio_handler = SocketIOHandler(socketio, device_manager, data_processor)
    socketio_handler.register_events()
    socketio_handler.start_sending_thread()
    startup_manager.start_phase(StartupPhase.ROUTES_REGISTER)
    
    def background_connection_task():
        print(f'[{time.strftime("%H:%M:%S")}] [Background] Starting device connections...')
        try:
            results = device_manager.connect_all()
            success_count = sum(1 for success in results.values() if success)
            print(f'[{time.strftime("%H:%M:%S")}] [Background] Connection summary: {success_count}/{len(results)} devices connected')
            device_manager._connection_pool.start_health_check()
        except Exception as e:
            print(f'[{time.strftime("%H:%M:%S")}] [Background] Connection error: {e}')
    
    socketio.start_background_task(background_connection_task)
    time.sleep(2)
    startup_manager.start_phase(StartupPhase.BACKGROUND_CONNECT)
    
    print('\n[6/8] Starting data collection...')
    optimized_collector = create_optimized_collector(device_manager)
    optimized_collector.set_collection_interval(config.DATA_SAMPLING_INTERVAL)
    
    def on_data_collected(device_data):
        for device_id, data in device_data.items():
            if data:
                device_config = device_manager.get_device_config(device_id)
                device_name = device_config.device_name if device_config else device_id
                collected_data = {
                    'device_id': device_id,
                    'device_name': device_name,
                    'timestamp': time.time(),
                    'data': data
                }
                data_processor.add_to_buffer(collected_data)
    
    optimized_collector.set_data_callback(on_data_collected)
    optimized_collector.start()
    startup_manager.start_phase(StartupPhase.SERVICES_START)
    
    startup_manager.finish_startup()
    
    print(f'\nServer running on http://{config.SERVER_HOST}:{config.SERVER_PORT}')
    print(f'Data collection interval: {config.DATA_SAMPLING_INTERVAL}ms')
    print('=' * 50)
    print('\nPress Ctrl+C to stop the server\n')
    
    import threading
    stop_event = threading.Event()
    server_exception = [None]
    
    def server_thread_func():
        try:
            print('[Server] Starting SocketIO server...')
            socketio.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT, debug=False, use_reloader=False)
            print('[Server] SocketIO server stopped normally')
        except Exception as e:
            print(f'[Server] SocketIO server exception: {e}')
            import traceback
            traceback.print_exc()
            server_exception[0] = e
        finally:
            stop_event.set()
    
    server_thread = threading.Thread(target=server_thread_func, daemon=False)
    server_thread.start()
    print('[Server] Main thread waiting...')
    
    restart_attempts = 0
    max_restart_attempts = 3
    
    try:
        while not stop_event.is_set():
            time.sleep(1)
            
            if optimized_collector and not optimized_collector._running:
                restart_attempts += 1
                print(f'[Server] Data collector stopped unexpectedly (attempt {restart_attempts}/{max_restart_attempts})')
                
                if restart_attempts <= max_restart_attempts:
                    print('[Server] Attempting to restart data collector...')
                    try:
                        optimized_collector = create_optimized_collector(device_manager)
                        optimized_collector.set_collection_interval(config.DATA_SAMPLING_INTERVAL)
                        optimized_collector.set_data_callback(on_data_collected)
                        optimized_collector.start()
                        print('[Server] Data collector restarted successfully')
                        restart_attempts = 0
                    except Exception as e:
                        print(f'[Server] Failed to restart data collector: {e}')
                        time.sleep(5)
                else:
                    print('[Server] Maximum restart attempts reached, shutting down')
                    break
    except KeyboardInterrupt:
        print('\nServer stopped by user')
    
    if server_thread.is_alive():
        print('[Server] Waiting for server thread to finish...')
        server_thread.join(timeout=5)
    
    graceful_shutdown(socketio_handler, optimized_collector, device_manager, data_processor, startup_manager)
    
    if server_exception[0]:
        print(f'[Server] Server exited with exception: {server_exception[0]}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
