from flask import Blueprint, request, jsonify

api_bp = Blueprint('api', __name__)

@api_bp.route('/data', methods=['GET'])
def get_data():
    try:
        start_time = request.args.get('startTime')
        end_time = request.args.get('endTime')
        db_number = request.args.get('dbNumber', type=int)
        
        data_storage = request.app.config['data_storage']
        data = data_storage.get_plc_data(start_time, end_time, db_number)
        
        # 转换为字典格式
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

@api_bp.route('/anomalies', methods=['GET'])
def get_anomalies():
    try:
        start_time = request.args.get('startTime')
        end_time = request.args.get('endTime')
        
        data_storage = request.app.config['data_storage']
        data = data_storage.get_anomalies(start_time, end_time)
        
        # 转换为字典格式
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

@api_bp.route('/status', methods=['GET'])
def get_status():
    try:
        plc_client = request.app.config['plc_client']
        return jsonify({'connected': plc_client.connected})
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)})
