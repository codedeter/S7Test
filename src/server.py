from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import time
import threading
import sys
import os
from collections import deque
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config.config import config
from src.plc.plc_data_collector import create_data_collector
from src.data.data_storage import DataStorage
from src.analysis.data_analyzer import DataAnalyzer
from src.analysis.drools_lite_engine import create_drools_lite_engine
from src.analysis.plc_variable_loader import load_plc_tags
from src.analysis.slider_down_detector import create_slider_detector

app = Flask(__name__, static_folder='../public', template_folder='../public')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

plc_collector = create_data_collector()
data_storage = DataStorage()
data_analyzer = DataAnalyzer()
drools_engine = create_drools_lite_engine()
slider_detector = create_slider_detector()

data_buffer = deque(maxlen=50)
buffer_lock = threading.Lock()
latest_anomalies = []
latest_drools_results = []
latest_slider_results = []
anomalies_lock = threading.Lock()
drools_lock = threading.Lock()
slider_lock = threading.Lock()

@app.route('/')
def index():
    from flask import make_response
    response = make_response(render_template('index.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/api/status', methods=['GET'])
def get_status():
    try:
        return jsonify({'connected': plc_collector.plc.connected})
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)})

@app.route('/api/data', methods=['GET'])
def get_data():
    try:
        start_time = request.args.get('startTime')
        end_time = request.args.get('endTime')
        db_number = request.args.get('dbNumber', type=int)
        
        data = data_storage.get_plc_data(start_time, end_time, db_number)
        
        result = []
        for row in data:
            result.append({
                'id': row[0],
                'timestamp': row[1],
                'db_number': row[2],
                'address': row[3],
                'tag_name': row[4],
                'value': row[5],
                'quality': row[6]
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

def data_collection_thread():
    global latest_anomalies, latest_drools_results, latest_slider_results
    print("数据采集线程启动...")
    while True:
        try:
            if not plc_collector.plc.connected:
                print('PLC未连接，尝试重连...')
                plc_collector.plc.connect()
                print('PLC重连成功')

            data = plc_collector.collect_all_data()
            
            data_storage.batch_insert_plc_data(data)
            
            with buffer_lock:
                data_buffer.append({
                    'timestamp': time.time() * 1000,
                    'data': data
                })
            
            facts = {}
            new_anomalies = []
            for item in data:
                tag_name = item.get('tag_name')
                if tag_name:
                    facts[tag_name] = item['value']
                    
                    db_number = item['db_number']
                    address = item['address']
                    value = item['value']
                    data_analyzer.add_data_point(db_number, address, value)
                    
                    analysis_result = data_analyzer.analyze_data(db_number, address, value)
                    if not analysis_result['normal']:
                        predicted_value = data_analyzer.predict_value(db_number, address)
                        anomaly = {
                            'timestamp': time.time(),
                            'db_number': db_number,
                            'address': address,
                            'tag_name': tag_name,
                            'value': value,
                            'predicted_value': predicted_value,
                            'confidence': analysis_result['confidence'],
                            'message': analysis_result['message']
                        }
                        new_anomalies.append(anomaly)
            
            if new_anomalies:
                with anomalies_lock:
                    latest_anomalies.extend(new_anomalies)
                    if len(latest_anomalies) > 20:
                        latest_anomalies = latest_anomalies[-20:]
            
            # Drools Lite规则引擎（统一使用）
            drools_engine.clear_facts()
            drools_engine.insert_facts(facts)
            drools_results = drools_engine.fire_all_rules()
            if drools_results:
                with drools_lock:
                    for result in drools_results:
                        result['timestamp'] = time.time()
                        latest_drools_results.append(result)
                    if len(latest_drools_results) > 20:
                        latest_drools_results = latest_drools_results[-20:]
            
            # 滑块下行异常检测
            slider_detector.update_facts(facts)
            slider_result = slider_detector.check_abnormal()
            if slider_result['abnormal']:
                with slider_lock:
                    slider_result['timestamp'] = time.time()
                    latest_slider_results.append(slider_result)
                    if len(latest_slider_results) > 10:
                        latest_slider_results = latest_slider_results[-10:]
            
        except Exception as e:
            print(f'数据采集错误: {e}')

        time.sleep(config.DATA_SAMPLING_INTERVAL / 1000)

def data_sending_thread():
    global latest_anomalies, latest_drools_results, latest_slider_results
    print("数据发送线程启动...")
    while True:
        try:
            with buffer_lock:
                if data_buffer:
                    current_values = {}
                    latest_data = data_buffer[-1]['data']
                    for item in latest_data:
                        tag_name = item.get('tag_name')
                        if tag_name:
                            current_values[tag_name] = item
                    
                    history_data = list(data_buffer)
                    data_buffer.clear()
                    
                    packet_data = {
                        'current_values': current_values,
                        'history_data': history_data
                    }
                    
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
                    
        except Exception as e:
            print(f'数据发送错误: {e}')
        
        time.sleep(0.2)

@socketio.on('connect')
def handle_connect():
    print('新客户端连接')

@socketio.on('disconnect')
def handle_disconnect():
    print('客户端断开连接')

def main():
    try:
        print('初始化数据库...')
        data_storage.init()
        print('数据库初始化成功')

        print('连接PLC...')
        plc_collector.plc.connect()
        print('PLC连接成功')

        print('启动数据采集线程...')
        threading.Thread(target=data_collection_thread, daemon=True).start()
        print('数据采集线程启动成功')
        
        print('启动数据发送线程...')
        threading.Thread(target=data_sending_thread, daemon=True).start()
        print('数据发送线程启动成功')
        
        print(f'服务器运行在 http://{config.SERVER_HOST}:{config.SERVER_PORT}')
        print(f'数据采集间隔: {config.DATA_SAMPLING_INTERVAL}ms, 数据包发送间隔: 200ms')
        socketio.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT, debug=False)
    except Exception as e:
        print(f'服务器启动错误: {e}')

if __name__ == '__main__':
    main()
