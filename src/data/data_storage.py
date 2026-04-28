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
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        return conn

    def init(self):
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    self.create_tables(cursor)
                    self.add_missing_columns(cursor)
                    self.create_indexes(cursor)
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    raise
                finally:
                    conn.close()
            return True
        except Exception as e:
            print(f'Database connection failed: {e}')
            return False

    def create_indexes(self, cursor):
        try:
            indexes = [
                ('idx_plc_data_device_id', 'plc_data(device_id)'),
                ('idx_plc_data_timestamp', 'plc_data(timestamp)'),
                ('idx_plc_data_device_timestamp', 'plc_data(device_id, timestamp)'),
                ('idx_plc_data_db_address', 'plc_data(db_number, address)'),
                ('idx_plc_data_device_db', 'plc_data(device_id, db_number)'),
                ('idx_anomalies_device_id', 'anomalies(device_id)'),
                ('idx_anomalies_timestamp', 'anomalies(timestamp)'),
                ('idx_anomalies_device_timestamp', 'anomalies(device_id, timestamp)'),
                ('idx_fault_records_device', 'fault_records(device_id)'),
                ('idx_fault_records_resolved', 'fault_records(resolved)'),
                ('idx_fault_records_device_resolved', 'fault_records(device_id, resolved)'),
                ('idx_devices_device_id', 'devices(device_id)')
            ]
            
            for idx_name, idx_def in indexes:
                try:
                    cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}')
                except Exception as e:
                    print(f'Index {idx_name} creation failed (may already exist): {e}')
        except Exception as e:
            print(f'Failed to create indexes: {e}')

    def create_device_views(self, cursor, device_ids: List[str]):
        try:
            for device_id in device_ids:
                safe_name = device_id.replace('-', '_').replace('.', '_')
                
                view_name = f'plc_data_{safe_name}'
                cursor.execute(f'''
                    CREATE VIEW IF NOT EXISTS {view_name} AS
                    SELECT * FROM plc_data WHERE device_id = ?
                ''', (device_id,))
                print(f'Created view {view_name} for device {device_id}')
                
                view_name = f'anomalies_{safe_name}'
                cursor.execute(f'''
                    CREATE VIEW IF NOT EXISTS {view_name} AS
                    SELECT * FROM anomalies WHERE device_id = ?
                ''', (device_id,))
                print(f'Created view {view_name} for device {device_id}')
                
                view_name = f'fault_records_{safe_name}'
                cursor.execute(f'''
                    CREATE VIEW IF NOT EXISTS {view_name} AS
                    SELECT * FROM fault_records WHERE device_id = ?
                ''', (device_id,))
                print(f'Created view {view_name} for device {device_id}')
        except Exception as e:
            print(f'Failed to create device views: {e}')

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
        if not data_list:
            return True
        
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    sql = 'INSERT INTO plc_data (device_id, db_number, address, tag_name, value, quality) VALUES (?, ?, ?, ?, ?, ?)'
                    params = [
                        (device_id, data['db_number'], data['address'], data.get('tag_name', ''), data['value'], data.get('quality', 1))
                        for data in data_list
                    ]
                    cursor.executemany(sql, params)
                    conn.commit()
                    return True
                except Exception as e:
                    conn.rollback()
                    print(f'Batch insert PLC data failed: {e}')
                    return False
                finally:
                    conn.close()
        except Exception as e:
            print(f'Batch insert PLC data outer error: {e}')
            return False

    def insert_plc_data(self, data: Dict[str, Any], device_id: str = None):
        return self.batch_insert_plc_data([data], device_id)

    def insert_anomaly(self, data: Dict[str, Any], device_id: str = None):
        try:
            with self._lock:
                conn = self._get_conn()
                try:
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
                    return last_row_id
                except Exception as e:
                    conn.rollback()
                    print(f'Insert anomaly failed: {e}')
                    return None
                finally:
                    conn.close()
        except Exception as e:
            print(f'Insert anomaly outer error: {e}')
            return None

    def insert_fault_record(self, fault_data: Dict[str, Any]):
        try:
            with self._lock:
                conn = self._get_conn()
                try:
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
                    return last_row_id
                except Exception as e:
                    conn.rollback()
                    print(f'Insert fault record failed: {e}')
                    return None
                finally:
                    conn.close()
        except Exception as e:
            print(f'Insert fault record outer error: {e}')
            return None

    def update_fault_record(self, fault_name: str, device_id: str, end_time: str, duration_seconds: float):
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    sql = '''UPDATE fault_records
                             SET end_time = ?, duration_seconds = ?, resolved = 1
                             WHERE fault_name = ? AND device_id = ? AND resolved = 0'''
                    cursor.execute(sql, (end_time, duration_seconds, fault_name, device_id))
                    conn.commit()
                    affected = cursor.rowcount
                    return affected
                except Exception as e:
                    conn.rollback()
                    print(f'Update fault record failed: {e}')
                    return 0
                finally:
                    conn.close()
        except Exception as e:
            print(f'Update fault record outer error: {e}')
            return 0

    def get_active_faults(self, device_id: str = None):
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    
                    if device_id:
                        sql = '''SELECT fault_name, device_id, start_time, severity, related_variables
                                 FROM fault_records WHERE resolved = 0 AND device_id = ?'''
                        cursor.execute(sql, (device_id,))
                    else:
                        sql = '''SELECT fault_name, device_id, start_time, severity, related_variables
                                 FROM fault_records WHERE resolved = 0'''
                        cursor.execute(sql)
                    
                    results = cursor.fetchall()
                    return [{'fault_name': r[0], 'device_id': r[1], 'start_time': r[2],
                             'severity': r[3], 'related_variables': r[4]} for r in results]
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get active faults failed: {e}')
            return []

    def get_plc_data_by_device(
        self,
        device_id: str,
        start_time: str = None,
        end_time: str = None,
        db_number: int = None
    ) -> List:
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    
                    sql = 'SELECT * FROM plc_data WHERE device_id = ?'
                    params = [device_id]

                    if start_time and end_time:
                        sql += ' AND timestamp BETWEEN ? AND ?'
                        params.extend([start_time, end_time])

                    if db_number is not None:
                        sql += ' AND db_number = ?'
                        params.append(db_number)

                    sql += ' ORDER BY timestamp DESC'

                    cursor.execute(sql, params)
                    result = cursor.fetchall()
                    return result
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get PLC data by device failed: {e}')
            return []

    def get_plc_data(
        self,
        start_time: str = None,
        end_time: str = None,
        db_number: int = None,
        device_id: str = None
    ) -> List:
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    
                    if start_time and end_time:
                        sql = 'SELECT * FROM plc_data WHERE timestamp BETWEEN ? AND ?'
                        params = [start_time, end_time]
                    else:
                        sql = 'SELECT * FROM plc_data'
                        params = []

                    if db_number is not None:
                        sql += ' AND db_number = ?'
                        params.append(db_number)

                    if device_id is not None:
                        sql += ' AND device_id = ?'
                        params.append(device_id)

                    sql += ' ORDER BY timestamp ASC'

                    cursor.execute(sql, params)
                    result = cursor.fetchall()
                    return result
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get PLC data failed: {e}')
            return []

    def get_anomalies_by_device(
        self,
        device_id: str,
        start_time: str = None,
        end_time: str = None
    ) -> List:
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    
                    sql = 'SELECT * FROM anomalies WHERE device_id = ?'
                    params = [device_id]

                    if start_time and end_time:
                        sql += ' AND timestamp BETWEEN ? AND ?'
                        params.extend([start_time, end_time])

                    sql += ' ORDER BY timestamp DESC'

                    cursor.execute(sql, params)
                    result = cursor.fetchall()
                    return result
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get anomalies by device failed: {e}')
            return []

    def get_anomalies(
        self,
        start_time: str = None,
        end_time: str = None,
        device_id: str = None
    ) -> List:
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    
                    if start_time and end_time:
                        sql = 'SELECT * FROM anomalies WHERE timestamp BETWEEN ? AND ?'
                        params = [start_time, end_time]
                    else:
                        sql = 'SELECT * FROM anomalies'
                        params = []

                    if device_id is not None:
                        sql += ' AND device_id = ?'
                        params.append(device_id)

                    sql += ' ORDER BY timestamp DESC'

                    cursor.execute(sql, params)
                    result = cursor.fetchall()
                    return result
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get anomalies failed: {e}')
            return []

    def get_faults_by_device(self, device_id: str) -> List:
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    sql = '''SELECT * FROM fault_records 
                             WHERE device_id = ? 
                             ORDER BY resolved ASC, start_time DESC'''
                    cursor.execute(sql, (device_id,))
                    result = cursor.fetchall()
                    return result
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get faults by device failed: {e}')
            return []

    def save_device(self, device_info: Dict[str, Any]):
        try:
            with self._lock:
                conn = self._get_conn()
                try:
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
                    return True
                except Exception as e:
                    conn.rollback()
                    print(f'Save device failed: {e}')
                    return False
                finally:
                    conn.close()
        except Exception as e:
            print(f'Save device outer error: {e}')
            return False

    def get_devices(self) -> List:
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM devices ORDER BY device_id')
                    result = cursor.fetchall()
                    return result
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get devices failed: {e}')
            return []

    def get_device_ids(self) -> List[str]:
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT DISTINCT device_id FROM devices WHERE enabled = 1')
                    result = cursor.fetchall()
                    return [row[0] for row in result]
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get device IDs failed: {e}')
            return []

    def delete_old_data(self, days: int = 30):
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM plc_data WHERE timestamp < datetime('now', ? || ' days')",
                        (f'-{days}',)
                    )
                    plc_deleted = cursor.rowcount
                    
                    cursor.execute(
                        "DELETE FROM anomalies WHERE timestamp < datetime('now', ? || ' days')",
                        (f'-{days}',)
                    )
                    anomaly_deleted = cursor.rowcount
                    
                    conn.commit()
                    print(f'Deleted {plc_deleted} PLC data records and {anomaly_deleted} anomaly records')
                    return True
                except Exception as e:
                    conn.rollback()
                    print(f'Delete old data failed: {e}')
                    return False
                finally:
                    conn.close()
        except Exception as e:
            print(f'Delete old data outer error: {e}')
            return False

    def delete_device_data(self, device_id: str):
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    
                    cursor.execute('DELETE FROM plc_data WHERE device_id = ?', (device_id,))
                    plc_deleted = cursor.rowcount
                    
                    cursor.execute('DELETE FROM anomalies WHERE device_id = ?', (device_id,))
                    anomaly_deleted = cursor.rowcount
                    
                    cursor.execute('DELETE FROM fault_records WHERE device_id = ?', (device_id,))
                    fault_deleted = cursor.rowcount
                    
                    conn.commit()
                    print(f'Deleted {plc_deleted} PLC data, {anomaly_deleted} anomalies, {fault_deleted} fault records for device {device_id}')
                    return True
                except Exception as e:
                    conn.rollback()
                    print(f'Delete device data failed: {e}')
                    return False
                finally:
                    conn.close()
        except Exception as e:
            print(f'Delete device data outer error: {e}')
            return False

    def get_record_count(self, table_name: str, device_id: str = None) -> int:
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    
                    if device_id:
                        cursor.execute(f'SELECT COUNT(*) FROM {table_name} WHERE device_id = ?', (device_id,))
                    else:
                        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                    
                    result = cursor.fetchone()
                    return result[0] if result else 0
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get record count failed: {e}')
            return 0

    def get_device_data_summary(self) -> List[Dict]:
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT 
                            device_id,
                            COUNT(*) as total_records,
                            MIN(timestamp) as first_timestamp,
                            MAX(timestamp) as last_timestamp
                        FROM plc_data
                        GROUP BY device_id
                        ORDER BY device_id
                    ''')
                    results = cursor.fetchall()
                    return [
                        {
                            'device_id': r[0],
                            'total_records': r[1],
                            'first_timestamp': r[2],
                            'last_timestamp': r[3]
                        }
                        for r in results
                    ]
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get device data summary failed: {e}')
            return []

    def get_device_anomaly_summary(self) -> List[Dict]:
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT 
                            device_id,
                            COUNT(*) as total_anomalies
                        FROM anomalies
                        GROUP BY device_id
                        ORDER BY device_id
                    ''')
                    results = cursor.fetchall()
                    return [
                        {
                            'device_id': r[0],
                            'total_anomalies': r[1]
                        }
                        for r in results
                    ]
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get device anomaly summary failed: {e}')
            return []