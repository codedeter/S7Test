from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import time
import threading
import sys
import os
from collections import deque
from config.config import config
from config.devices_config import create_device_configs
from src.devices import DeviceManager, create_device_manager
from src.data.data_storage import DataStorage
from src.analysis.data_analyzer import DataAnalyzer
from src.analysis.drools_lite_engine import create_drools_lite_engine
from src.analysis.plc_variable_loader import load_plc_tags
from src.analysis.slider_down_detector import create_slider_detector
from src.analysis.rxb800_rules import RXB800FaultRules
from src.analysis.fault_tracker import FaultTracker, AnomalyTracker

app = Flask(__name__, static_folder='../public', template_folder='../public')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

device_manager = create_device_manager()
data_storage = DataStorage()
data_analyzer = DataAnalyzer()
drools_engine = create_drools_lite_engine()
fault_tracker = FaultTracker(data_storage)
anomaly_tracker = AnomalyTracker()
slider_detector = create_slider_detector()

data_buffer = deque(maxlen=50)
buffer_lock = threading.Lock()
latest_anomalies = []
latest_drools_results = []
latest_slider_results = []
latest_fault_status = {}
anomalies_lock = threading.Lock()
drools_lock = threading.Lock()
slider_lock = threading.Lock()
fault_lock = threading.Lock()

def init_devices():
    device_configs = create_device_configs()
    for device_config in device_configs:
        device_manager.add_device(device_config)
    print(f"Initialized {len(device_configs)} device(s)")


@app.route('/')
def index():
    import os
    from flask import make_response
    html_path = os.path.join(os.path.dirname(__file__), '..', 'public', 'index.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    response = make_response(content)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Content-Type'] = 'text/html'
    return response


@app.route('/api/status', methods=['GET'])
def get_status():
    try:
        devices = device_manager.list_devices()
        return jsonify({
            'devices': devices,
            'total': len(devices)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/device/<device_id>/status', methods=['GET'])
def get_device_status(device_id):
    try:
        status = device_manager.get_device_status(device_id)
        if status:
            return jsonify({
                'device_id': status.device_id,
                'status': status.status.value,
                'connected': status.connected,
                'last_error': status.last_error,
                'last_update': status.last_update,
                'data_count': status.data_count
            })
        return jsonify({'error': 'Device not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data', methods=['GET'])
def get_data():
    try:
        start_time = request.args.get('startTime')
        end_time = request.args.get('endTime')
        db_number = request.args.get('dbNumber', type=int)
        device_id = request.args.get('deviceId')

        data = data_storage.get_plc_data(start_time, end_time, db_number, device_id)

        result = []
        for row in data:
            result.append({
                'id': row[0],
                'timestamp': row[1],
                'device_id': row[2] if len(row) > 2 else None,
                'db_number': row[3] if len(row) > 3 else row[2],
                'address': row[4] if len(row) > 4 else row[3],
                'tag_name': row[5] if len(row) > 5 else row[4],
                'value': row[6] if len(row) > 6 else row[5],
                'quality': row[7] if len(row) > 7 else row[6]
            })

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/anomalies', methods=['GET'])
def get_anomalies():
    try:
        start_time = request.args.get('startTime')
        end_time = request.args.get('endTime')

        data = data_storage.get_anomalies(start_time, end_time)

        result = []
        for row in data:
            result.append({
                'id': row[0],
                'timestamp': row[1],
                'db_number': row[2],
                'address': row[3],
                'tag_name': row[4],
                'value': row[5],
                'predicted_value': row[6],
                'confidence': row[7],
                'message': row[8]
            })

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def data_collection_callback(all_device_data):
    global latest_anomalies, latest_drools_results, latest_slider_results

    for device_data in all_device_data:
        device_id = device_data.device_id
        data = device_data.data

        data_storage.batch_insert_plc_data(data, device_id)

        with buffer_lock:
            data_buffer.append({
                'timestamp': time.time() * 1000,
                'device_id': device_id,
                'device_name': device_data.device_name,
                'data': data
            })

        facts = {}
        new_anomalies = []

        for item in data:
            tag_name = item.get('tag_name')
            if tag_name:
                key = f"{device_id}:{tag_name}"
                facts[key] = item['value']

                db_number = item['db_number']
                address = item['address']
                value = item['value']
                data_analyzer.add_data_point(db_number, address, value)

                analysis_result = data_analyzer.analyze_data(db_number, address, value)
                if not analysis_result['normal']:
                    predicted_value = data_analyzer.predict_value(db_number, address)
                    anomaly = {
                        'timestamp': time.time(),
                        'device_id': device_id,
                        'db_number': db_number,
                        'address': address,
                        'tag_name': tag_name,
                        'value': value,
                        'predicted_value': predicted_value,
                        'confidence': analysis_result['confidence'],
                        'message': analysis_result['message']
                    }
                    anomaly_tracker.update_anomaly(anomaly)
                    new_anomalies.append(anomaly)

        if new_anomalies:
            with anomalies_lock:
                latest_anomalies.extend(new_anomalies)
                if len(latest_anomalies) > 20:
                    latest_anomalies = latest_anomalies[-20:]

        drools_engine.clear_facts()
        drools_engine.insert_facts(facts)
        drools_results = drools_engine.fire_all_rules()
        if drools_results:
            with drools_lock:
                for result in drools_results:
                    result['timestamp'] = time.time()
                    result['device_id'] = device_id
                    latest_drools_results.append(result)
                if len(latest_drools_results) > 20:
                    latest_drools_results = latest_drools_results[-20:]

        slider_detector.update_facts(facts)
        slider_result = slider_detector.check_abnormal()
        if slider_result['abnormal']:
            with slider_lock:
                slider_result['timestamp'] = time.time()
                slider_result['device_id'] = device_id
                latest_slider_results.append(slider_result)
                if len(latest_slider_results) > 10:
                    latest_slider_results = latest_slider_results[-10:]

        if device_id == 'plc_002':
            db51_values = {}
            var_values = {}
            for item in data:
                if item.get('db_number') == 51:
                    db51_values[item['tag_name']] = item['value']
                elif item.get('db_number') in (1, 10):
                    var_values[item['tag_name']] = item['value']

            if db51_values:
                fault_analysis = RXB800FaultRules.analyze_with_rules(db51_values, var_values)
                fault_summary = RXB800FaultRules.get_fault_summary(db51_values, var_values)

                fault_tracker.update_faults(device_id, fault_summary['active_faults'], 'warning' if not fault_summary['has_critical'] else 'critical')

                active_faults_with_duration = fault_tracker.get_active_faults()
                severity = 'critical' if fault_summary['has_critical'] else 'warning'

                with fault_lock:
                    latest_fault_status[device_id] = {
                        'device_id': device_id,
                        'timestamp': time.time(),
                        'total_faults': len(active_faults_with_duration),
                        'has_critical': fault_summary['has_critical'],
                        'active_faults': active_faults_with_duration,
                        'fault_analysis': fault_analysis,
                        'severity': severity
                    }

                print(f"[{device_id}] Fault Analysis: {len(active_faults_with_duration)} active faults, Critical: {fault_summary['has_critical']}")
                if fault_summary['total_faults'] > 0:
                    print(f"[{device_id}] Active faults: {fault_summary['active_faults'][:5]}...")


def data_collection_thread():
    print("Data collection thread started...")
    while True:
        try:
            all_device_data = device_manager.collect_all_data()
            if all_device_data:
                for device_data in all_device_data:
                    print(f"[{device_data.device_id}] Collected {len(device_data.data)} data points, connected={device_data.connected}")
                data_collection_callback(all_device_data)
            else:
                print("No data collected from any device")
        except Exception as e:
            print(f'Data collection error: {e}')

        time.sleep(config.DATA_SAMPLING_INTERVAL / 1000)


def data_sending_thread():
    global latest_anomalies, latest_drools_results, latest_slider_results
    print("Data sending thread started...")
    while True:
        try:
            with buffer_lock:
                if data_buffer:
                    device_data_map = {}

                    for buffer_item in list(data_buffer):
                        device_id = buffer_item.get('device_id', 'unknown')
                        if device_id not in device_data_map:
                            device_data_map[device_id] = {
                                'device_id': device_id,
                                'device_name': buffer_item.get('device_name', device_id),
                                'current_values': {},
                                'history_data': []
                            }

                        latest_data = buffer_item['data']
                        for item in latest_data:
                            tag_name = item.get('tag_name')
                            if tag_name:
                                key = f"{device_id}:{tag_name}"
                                device_data_map[device_id]['current_values'][key] = item

                        device_data_map[device_id]['history_data'].append({
                            'timestamp': buffer_item['timestamp'],
                            'data': latest_data
                        })

                    data_buffer.clear()

                    for device_id, packet_data in device_data_map.items():
                        print(f"[SocketIO] Emitting data to clients: {device_id}, {len(packet_data.get('current_values'))} values")
                        socketio.emit('data', packet_data)

            with anomalies_lock:
                if latest_anomalies:
                    for anomaly in latest_anomalies:
                        socketio.emit('anomaly', anomaly)
                    latest_anomalies.clear()

            with drools_lock:
                if latest_drools_results:
                    for result in latest_drools_results:
                        socketio.emit('drools_result', result)
                    latest_drools_results.clear()

            with slider_lock:
                if latest_slider_results:
                    for result in latest_slider_results:
                        socketio.emit('slider_fault', result)
                    latest_slider_results.clear()

            with fault_lock:
                if latest_fault_status:
                    for device_id, fault_data in latest_fault_status.items():
                        socketio.emit('fault_status', fault_data)

            active_anomalies = anomaly_tracker.get_active_anomalies()
            if active_anomalies:
                for anomaly in active_anomalies:
                    socketio.emit('anomaly_update', anomaly)

        except Exception as e:
            print(f'Data sending error: {e}')

        time.sleep(0.2)


@socketio.on('connect')
def handle_connect():
    print('New client connected')


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@socketio.on('switch_device')
def handle_switch_device(data):
    device_id = data.get('deviceId')
    if device_id:
        print(f'Client switched to device: {device_id}')

        with buffer_lock:
            for buffer_item in list(data_buffer):
                if buffer_item.get('device_id') == device_id:
                    socketio.emit('data', {
                        'timestamp': buffer_item.get('timestamp', time.time() * 1000),
                        'device_id': buffer_item.get('device_id'),
                        'device_name': buffer_item.get('device_name'),
                        'current_values': {},
                        'history_data': []
                    })
                    latest_data = buffer_item.get('data', [])
                    for item in latest_data:
                        tag_name = item.get('tag_name')
                        if tag_name:
                            key = f"{device_id}:{tag_name}"
                            socketio.emit('data', {
                                'timestamp': buffer_item.get('timestamp', time.time() * 1000),
                                'device_id': buffer_item.get('device_id'),
                                'device_name': buffer_item.get('device_name'),
                                'current_values': {key: item},
                                'history_data': []
                            })


def main():
    try:
        print('Initializing database...')
        data_storage.init()
        print('Database initialized')

        print('Initializing devices...')
        init_devices()

        print('Connecting to devices...')
        device_manager.connect_all()

        print('Starting data collection thread...')
        threading.Thread(target=data_collection_thread, daemon=True).start()
        print('Data collection thread started')

        print('Starting data sending thread...')
        threading.Thread(target=data_sending_thread, daemon=True).start()
        print('Data sending thread started')

        print(f'Server running on http://{config.SERVER_HOST}:{config.SERVER_PORT}')
        print(f'Data collection interval: {config.DATA_SAMPLING_INTERVAL}ms, Data sending interval: 200ms')
        socketio.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT, debug=False)
    except Exception as e:
        print(f'Server startup error: {e}')


if __name__ == '__main__':
    main()
