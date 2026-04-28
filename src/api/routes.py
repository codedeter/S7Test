from flask import jsonify, request
from src.data.data_storage import DataStorage
from src.devices import DeviceManager

data_storage = DataStorage()

def register_routes(app, device_manager: DeviceManager):
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

    return app