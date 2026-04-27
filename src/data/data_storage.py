import sqlite3
import os
from datetime import datetime
import threading
from typing import List, Dict, Any, Optional


class DataStorage:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database.db')
        self._lock = threading.Lock()

    def _get_conn(self):
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
            print(f'Database connection failed: {e}')
            return False

    def add_missing_columns(self, cursor):
        try:
            cursor.execute("PRAGMA table_info(plc_data)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'device_id' not in columns:
                cursor.execute("ALTER TABLE plc_data ADD COLUMN device_id TEXT")
                print("Added device_id column to plc_data table")

            if 'tag_name' not in columns:
                cursor.execute("ALTER TABLE plc_data ADD COLUMN tag_name TEXT")
                print("Added tag_name column to plc_data table")

            if 'quality' not in columns:
                cursor.execute("ALTER TABLE plc_data ADD COLUMN quality INTEGER")
                print("Added quality column to plc_data table")

            cursor.execute("PRAGMA table_info(anomalies)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'device_id' not in columns:
                cursor.execute("ALTER TABLE anomalies ADD COLUMN device_id TEXT")
                print("Added device_id column to anomalies table")

            if 'tag_name' not in columns:
                cursor.execute("ALTER TABLE anomalies ADD COLUMN tag_name TEXT")
                print("Added tag_name column to anomalies table")
        except Exception as e:
            print(f'Failed to add missing columns: {e}')

    def create_tables(self, cursor):
        create_plc_data_table = '''
        CREATE TABLE IF NOT EXISTS plc_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            device_id TEXT,
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
            device_id TEXT,
            db_number INTEGER,
            address INTEGER,
            tag_name TEXT,
            value REAL,
            predicted_value REAL,
            confidence REAL,
            message TEXT
        );
        '''

        create_fault_records_table = '''
        CREATE TABLE IF NOT EXISTS fault_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fault_name TEXT NOT NULL,
            device_id TEXT NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            duration_seconds REAL,
            severity TEXT,
            related_variables TEXT,
            resolved INTEGER DEFAULT 0,
            notes TEXT
        );
        '''

        create_devices_table = '''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT UNIQUE,
            device_name TEXT,
            ip_address TEXT,
            device_type TEXT,
            rack INTEGER,
            slot INTEGER,
            enabled INTEGER,
            last_connected DATETIME,
            status TEXT
        );
        '''

        try:
            cursor.execute(create_plc_data_table)
            cursor.execute(create_anomaly_table)
            cursor.execute(create_fault_records_table)
            cursor.execute(create_devices_table)
        except Exception as e:
            print(f'Failed to create tables: {e}')

    def batch_insert_plc_data(self, data_list: List[Dict[str, Any]], device_id: str = None):
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                sql = 'INSERT INTO plc_data (device_id, db_number, address, tag_name, value, quality) VALUES (?, ?, ?, ?, ?, ?)'
                params = [
                    (device_id, data['db_number'], data['address'], data.get('tag_name', ''), data['value'], data.get('quality', 1))
                    for data in data_list
                ]
                cursor.executemany(sql, params)
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f'Batch insert PLC data failed: {e}')
            return False

    def insert_plc_data(self, data: Dict[str, Any], device_id: str = None):
        return self.batch_insert_plc_data([data], device_id)

    def insert_anomaly(self, data: Dict[str, Any], device_id: str = None):
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                sql = '''INSERT INTO anomalies
                         (device_id, db_number, address, tag_name, value, predicted_value, confidence, message)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
                cursor.execute(sql, (
                    device_id,
                    data['db_number'],
                    data['address'],
                    data.get('tag_name', ''),
                    data['value'],
                    data.get('predicted_value'),
                    data.get('confidence'),
                    data.get('message')
                ))
                conn.commit()
                last_row_id = cursor.lastrowid
                conn.close()
                return last_row_id
        except Exception as e:
            print(f'Insert anomaly failed: {e}')
            return None

    def insert_fault_record(self, fault_data: Dict[str, Any]):
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                sql = '''INSERT INTO fault_records
                         (fault_name, device_id, start_time, end_time, duration_seconds, severity, related_variables, resolved)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
                cursor.execute(sql, (
                    fault_data.get('fault_name'),
                    fault_data.get('device_id'),
                    fault_data.get('start_time'),
                    fault_data.get('end_time'),
                    fault_data.get('duration_seconds'),
                    fault_data.get('severity'),
                    fault_data.get('related_variables'),
                    fault_data.get('resolved', 0)
                ))
                conn.commit()
                last_row_id = cursor.lastrowid
                conn.close()
                return last_row_id
        except Exception as e:
            print(f'Insert fault record failed: {e}')
            return None

    def update_fault_record(self, fault_name: str, device_id: str, end_time: str, duration_seconds: float):
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                sql = '''UPDATE fault_records
                         SET end_time = ?, duration_seconds = ?, resolved = 1
                         WHERE fault_name = ? AND device_id = ? AND resolved = 0'''
                cursor.execute(sql, (end_time, duration_seconds, fault_name, device_id))
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                return affected
        except Exception as e:
            print(f'Update fault record failed: {e}')
            return 0

    def get_active_faults(self):
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                sql = '''SELECT fault_name, device_id, start_time, severity, related_variables
                         FROM fault_records WHERE resolved = 0'''
                cursor.execute(sql)
                results = cursor.fetchall()
                conn.close()
                return [{'fault_name': r[0], 'device_id': r[1], 'start_time': r[2],
                         'severity': r[3], 'related_variables': r[4]} for r in results]
        except Exception as e:
            print(f'Get active faults failed: {e}')
            return []

    def get_plc_data(
        self,
        start_time: str,
        end_time: str,
        db_number: int = None,
        device_id: str = None
    ) -> List:
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                sql = 'SELECT * FROM plc_data WHERE timestamp BETWEEN ? AND ?'
                params = [start_time, end_time]

                if db_number is not None:
                    sql += ' AND db_number = ?'
                    params.append(db_number)

                if device_id is not None:
                    sql += ' AND device_id = ?'
                    params.append(device_id)

                sql += ' ORDER BY timestamp ASC'

                cursor.execute(sql, params)
                result = cursor.fetchall()
                conn.close()
                return result
        except Exception as e:
            print(f'Get PLC data failed: {e}')
            return []

    def get_anomalies(
        self,
        start_time: str,
        end_time: str,
        device_id: str = None
    ) -> List:
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                sql = 'SELECT * FROM anomalies WHERE timestamp BETWEEN ? AND ?'
                params = [start_time, end_time]

                if device_id is not None:
                    sql += ' AND device_id = ?'
                    params.append(device_id)

                sql += ' ORDER BY timestamp DESC'

                cursor.execute(sql, params)
                result = cursor.fetchall()
                conn.close()
                return result
        except Exception as e:
            print(f'Get anomalies failed: {e}')
            return []

    def save_device(self, device_info: Dict[str, Any]):
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                sql = '''INSERT OR REPLACE INTO devices
                         (device_id, device_name, ip_address, device_type, rack, slot, enabled, status)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
                cursor.execute(sql, (
                    device_info.get('device_id'),
                    device_info.get('device_name'),
                    device_info.get('ip_address'),
                    device_info.get('device_type'),
                    device_info.get('rack', 0),
                    device_info.get('slot', 1),
                    device_info.get('enabled', 1),
                    device_info.get('status', 'unknown')
                ))
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f'Save device failed: {e}')
            return False

    def get_devices(self) -> List:
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM devices ORDER BY device_id')
                result = cursor.fetchall()
                conn.close()
                return result
        except Exception as e:
            print(f'Get devices failed: {e}')
            return []

    def delete_old_data(self, days: int = 30):
        try:
            with self._lock:
                conn = self._get_conn()
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM plc_data WHERE timestamp < datetime('now', ? || ' days')",
                    (f'-{days}',)
                )
                cursor.execute(
                    "DELETE FROM anomalies WHERE timestamp < datetime('now', ? || ' days')",
                    (f'-{days}',)
                )
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f'Delete old data failed: {e}')
            return False
