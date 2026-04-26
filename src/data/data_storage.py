import sqlite3
import os
from datetime import datetime
import threading

class DataStorage:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database.db')
        self._lock = threading.Lock()  # 添加线程锁
    
    def _get_conn(self):
        # 每次都创建新连接，完全线程安全
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        return conn
    
    def init(self):
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                self.create_tables(cursor)
                self.add_missing_columns(cursor)
                conn.commit()
                conn.close()
            return True
        except Exception as e:
            print(f'数据库连接失败: {e}')
            return False

    def add_missing_columns(self, cursor):
        try:
            cursor.execute("PRAGMA table_info(plc_data)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'tag_name' not in columns:
                cursor.execute("ALTER TABLE plc_data ADD COLUMN tag_name TEXT")
                print("添加tag_name列到plc_data表")
            if 'quality' not in columns:
                cursor.execute("ALTER TABLE plc_data ADD COLUMN quality INTEGER")
                print("添加quality列到plc_data表")

            cursor.execute("PRAGMA table_info(anomalies)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'tag_name' not in columns:
                cursor.execute("ALTER TABLE anomalies ADD COLUMN tag_name TEXT")
                print("添加tag_name列到anomalies表")
        except Exception as e:
            print(f'添加缺失列失败: {e}')
    
    def create_tables(self, cursor):
        create_plc_data_table = '''
        CREATE TABLE IF NOT EXISTS plc_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            db_number INTEGER,
            address INTEGER,
            tag_name TEXT,
            value REAL,
            quality INTEGER
        );
        '''

        create_anomaly_table = '''
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            db_number INTEGER,
            address INTEGER,
            tag_name TEXT,
            value REAL,
            predicted_value REAL,
            confidence REAL,
            message TEXT
        );
        '''

        try:
            cursor.execute(create_plc_data_table)
            cursor.execute(create_anomaly_table)
        except Exception as e:
            print(f'创建表失败: {e}')
    
    def batch_insert_plc_data(self, data_list):
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                sql = 'INSERT INTO plc_data (db_number, address, tag_name, value, quality) VALUES (?, ?, ?, ?, ?)'
                params = [(data['db_number'], data['address'], data.get('tag_name', ''), data['value'], data['quality']) 
                         for data in data_list]
                cursor.executemany(sql, params)
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f'批量插入PLC数据失败: {e}')
            return False

    def insert_plc_data(self, data):
        return self.batch_insert_plc_data([data])

    def insert_anomaly(self, data):
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                sql = 'INSERT INTO anomalies (db_number, address, tag_name, value, predicted_value, confidence, message) VALUES (?, ?, ?, ?, ?, ?, ?)'
                cursor.execute(sql, (
                    data['db_number'],
                    data['address'],
                    data.get('tag_name', ''),
                    data['value'],
                    data['predicted_value'],
                    data['confidence'],
                    data['message']
                ))
                conn.commit()
                last_row_id = cursor.lastrowid
                conn.close()
                return last_row_id
        except Exception as e:
            print(f'插入异常数据失败: {e}')
            return None
    
    def get_plc_data(self, start_time, end_time, db_number=None):
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                sql = 'SELECT * FROM plc_data WHERE timestamp BETWEEN ? AND ?'
                params = [start_time, end_time]
                
                if db_number is not None:
                    sql += ' AND db_number = ?'
                    params.append(db_number)
                
                sql += ' ORDER BY timestamp ASC'
                
                cursor.execute(sql, params)
                result = cursor.fetchall()
                conn.close()
                return result
        except Exception as e:
            print(f'获取PLC数据失败: {e}')
            return []
    
    def get_anomalies(self, start_time, end_time):
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                sql = 'SELECT * FROM anomalies WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp DESC'
                cursor.execute(sql, (start_time, end_time))
                result = cursor.fetchall()
                conn.close()
                return result
        except Exception as e:
            print(f'获取异常数据失败: {e}')
            return []
