from flask import jsonify, request
from src.data.data_storage import DataStorage
from src.devices import DeviceManager
from src.startup import get_startup_manager
from src.utils import get_error_handler
import json
import os
import time

data_storage = DataStorage()

FAULT_RULES_FILE = 'config/custom_fault_rules.json'


def load_custom_rules():
    """加载自定义故障规则"""
    if os.path.exists(FAULT_RULES_FILE):
        with open(FAULT_RULES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_custom_rules(rules):
    """保存自定义故障规则"""
    os.makedirs(os.path.dirname(FAULT_RULES_FILE), exist_ok=True)
    with open(FAULT_RULES_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


def register_routes(app, device_manager: DeviceManager):
    @app.route('/api/health', methods=['GET'])
    def get_health():
        startup_manager = get_startup_manager()
        context = startup_manager.context
        
        if context.is_failed():
            return jsonify({
                'status': 'unhealthy',
                'reason': 'startup_failed',
                'error': context.error_message,
                'current_phase': context.current_phase.value,
                'timestamp': time.time()
            }), 503
        
        if not context.is_complete():
            return jsonify({
                'status': 'starting',
                'current_phase': context.current_phase.value,
                'progress': context.get_progress(),
                'timestamp': time.time()
            }), 200
        
        devices = device_manager.list_devices()
        connected_count = sum(1 for d in devices if d.get('connected', False))
        total_count = len(devices)
        
        health_status = 'healthy' if connected_count == total_count else 'degraded'
        
        return jsonify({
            'status': health_status,
            'version': '3.1',
            'current_phase': context.current_phase.value,
            'start_time': context.start_time,
            'uptime': time.time() - context.start_time,
            'devices': {
                'total': total_count,
                'connected': connected_count,
                'disconnected': total_count - connected_count
            },
            'timestamp': time.time()
        })

    @app.route('/api/startup/status', methods=['GET'])
    def get_startup_status():
        startup_manager = get_startup_manager()
        return jsonify(startup_manager.context.to_dict())

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

    @app.route('/api/device/<device_id>/connect', methods=['POST'])
    def connect_device(device_id):
        try:
            result = device_manager.connect_device(device_id)
            status = device_manager.get_device_status(device_id)
            return jsonify({
                'success': result,
                'device_id': device_id,
                'status': status.status.value if status else 'unknown',
                'connected': status.connected if status else False
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/device/<device_id>/disconnect', methods=['POST'])
    def disconnect_device(device_id):
        try:
            device_manager.disconnect_device(device_id)
            return jsonify({
                'success': True,
                'device_id': device_id
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/devices/connect_all', methods=['POST'])
    def connect_all_devices():
        try:
            results = device_manager.connect_all()
            return jsonify({
                'success': True,
                'results': results
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/connection/pool', methods=['GET'])
    def get_connection_pool_summary():
        try:
            summary = device_manager.get_connection_pool_summary()
            return jsonify(summary)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/device/<device_id>/connection_stats', methods=['GET'])
    def get_device_connection_stats(device_id):
        try:
            stats = device_manager.get_device_connection_stats(device_id)
            if stats:
                return jsonify(stats)
            return jsonify({'error': 'Device not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/errors', methods=['GET'])
    def get_errors():
        try:
            error_handler = get_error_handler()
            limit = request.args.get('limit', 20, type=int)
            errors = error_handler.get_recent_errors(limit)
            counts = error_handler.get_error_counts()
            
            return jsonify({
                'errors': errors,
                'counts': counts,
                'total': len(errors)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/errors/clear', methods=['POST'])
    def clear_errors():
        try:
            error_handler = get_error_handler()
            error_handler.clear_errors()
            return jsonify({'success': True, 'message': 'Error logs cleared'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/storage/stats', methods=['GET'])
    def get_storage_stats():
        try:
            stats = data_storage.get_storage_stats()
            return jsonify(stats)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/storage/optimize', methods=['POST'])
    def optimize_storage():
        try:
            result = data_storage.optimize_database()
            return jsonify({'success': result, 'message': 'Database optimization completed'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/storage/cleanup', methods=['POST'])
    def cleanup_storage():
        try:
            days = request.args.get('days', 30, type=int)
            result = data_storage.delete_old_data(days)
            return jsonify({'success': result, 'message': f'Deleted data older than {days} days'})
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

    # ===== 故障规则管理API =====
    
    @app.route('/api/fault-rules', methods=['GET'])
    def get_fault_rules():
        """获取所有故障规则"""
        try:
            device_type = request.args.get('device_type', 'RXB800')
            
            from src.analysis import create_detector
            detector = create_detector(device_type)
            
            builtin_rules = []
            if detector:
                for name, fault_bit in detector.get_all_fault_bits().items():
                    builtin_rules.append({
                        'name': fault_bit.name,
                        'bit_position': fault_bit.bit_position,
                        'severity': fault_bit.severity,
                        'description': fault_bit.description,
                        'related_variables': fault_bit.related_variables,
                        'condition_type': fault_bit.condition_type,
                        'threshold_var': fault_bit.threshold_var,
                        'threshold': fault_bit.threshold,
                        'unit': fault_bit.unit,
                        'is_builtin': True
                    })
            
            custom_rules = load_custom_rules()
            device_custom_rules = custom_rules.get(device_type, [])
            for rule in device_custom_rules:
                rule['is_builtin'] = False
            
            return jsonify({
                'device_type': device_type,
                'builtin_rules': builtin_rules,
                'custom_rules': device_custom_rules,
                'total_count': len(builtin_rules) + len(device_custom_rules)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/fault-rules', methods=['POST'])
    def add_fault_rule():
        """添加自定义故障规则"""
        try:
            data = request.json
            device_type = data.get('device_type', 'RXB800')
            
            required_fields = ['name', 'bit_position', 'severity']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'缺少必需字段: {field}'}), 400
            
            new_rule = {
                'name': data['name'],
                'bit_position': data['bit_position'],
                'severity': data.get('severity', 'warning'),
                'description': data.get('description', ''),
                'related_variables': data.get('related_variables', []),
                'condition_type': data.get('condition_type', 'status'),
                'threshold_var': data.get('threshold_var'),
                'threshold': data.get('threshold'),
                'normal_range': data.get('normal_range'),
                'unit': data.get('unit', '')
            }
            
            custom_rules = load_custom_rules()
            if device_type not in custom_rules:
                custom_rules[device_type] = []
            
            for rule in custom_rules[device_type]:
                if rule['name'] == new_rule['name']:
                    return jsonify({'error': f'规则名称已存在: {new_rule["name"]}'}), 400
            
            custom_rules[device_type].append(new_rule)
            save_custom_rules(custom_rules)
            
            return jsonify({
                'success': True,
                'message': '规则添加成功',
                'rule': new_rule
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/fault-rules/<rule_name>', methods=['PUT'])
    def update_fault_rule(rule_name):
        """更新自定义故障规则"""
        try:
            data = request.json
            device_type = data.get('device_type', 'RXB800')
            
            custom_rules = load_custom_rules()
            if device_type not in custom_rules:
                return jsonify({'error': '设备类型不存在'}), 404
            
            found = False
            for i, rule in enumerate(custom_rules[device_type]):
                if rule['name'] == rule_name:
                    custom_rules[device_type][i].update({
                        'bit_position': data.get('bit_position', rule['bit_position']),
                        'severity': data.get('severity', rule['severity']),
                        'description': data.get('description', rule['description']),
                        'related_variables': data.get('related_variables', rule['related_variables']),
                        'condition_type': data.get('condition_type', rule['condition_type']),
                        'threshold_var': data.get('threshold_var'),
                        'threshold': data.get('threshold'),
                        'normal_range': data.get('normal_range'),
                        'unit': data.get('unit', rule['unit'])
                    })
                    found = True
                    break
            
            if not found:
                return jsonify({'error': f'规则不存在: {rule_name}'}), 404
            
            save_custom_rules(custom_rules)
            
            return jsonify({
                'success': True,
                'message': '规则更新成功'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/fault-rules/<rule_name>', methods=['DELETE'])
    def delete_fault_rule(rule_name):
        """删除自定义故障规则"""
        try:
            device_type = request.args.get('device_type', 'RXB800')
            
            custom_rules = load_custom_rules()
            if device_type not in custom_rules:
                return jsonify({'error': '设备类型不存在'}), 404
            
            original_len = len(custom_rules[device_type])
            custom_rules[device_type] = [
                rule for rule in custom_rules[device_type] 
                if rule['name'] != rule_name
            ]
            
            if len(custom_rules[device_type]) == original_len:
                return jsonify({'error': f'规则不存在: {rule_name}'}), 404
            
            save_custom_rules(custom_rules)
            
            return jsonify({
                'success': True,
                'message': '规则删除成功'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/fault-rules/devices', methods=['GET'])
    def get_supported_devices():
        """获取支持的设备类型列表"""
        try:
            from src.analysis import is_rx_series_device
            from config.devices_config import DEFAULT_DEVICES
            
            devices = []
            for device in DEFAULT_DEVICES:
                device_type = device.get('device_type', '')
                device_id = device.get('device_id', '')
                device_name = device.get('device_name', '')
                
                is_rx = is_rx_series_device(device_type) if device_type else is_rx_series_device(device_id)
                
                devices.append({
                    'device_id': device_id,
                    'device_name': device_name,
                    'device_type': device_type or device_id,
                    'is_rx_series': is_rx
                })
            
            return jsonify({
                'devices': devices,
                'total': len(devices)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/fault-rules/reload', methods=['POST'])
    def reload_fault_rules():
        """重新加载故障规则"""
        try:
            data = request.json or {}
            device_type = data.get('device_type', 'RXB800')
            
            from src.analysis import FaultDetectorRegistry, create_detector
            from src.analysis.configurable_fault_detector import create_detector_from_config
            
            custom_rules = load_custom_rules()
            device_custom_rules = custom_rules.get(device_type, [])
            
            if device_custom_rules:
                config = {
                    'inherit_rx_common': True,
                    'faults': device_custom_rules
                }
                detector = create_detector_from_config(device_type, config)
                FaultDetectorRegistry.register_detector(detector)
            else:
                detector = create_detector(device_type)
            
            return jsonify({
                'success': True,
                'message': f'设备 {device_type} 故障规则已重新加载',
                'fault_count': detector.get_fault_bit_count() if detector else 0
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return app
