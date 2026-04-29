import sqlite3
import os
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Callable
from collections import OrderedDict
from queue import Queue, Empty
from dataclasses import dataclass, field

from src.utils.error_handling import get_error_handler, ErrorType


@dataclass
class DataWriteTask:
    table_name: str
    data: List[Dict[str, Any]]
    callback: Optional[Callable] = None


class DataStorage:
    MAX_BATCH_SIZE = 1000
    CACHE_MAX_SIZE = 10000
    CACHE_EXPIRE_SECONDS = 300
    
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database.db')
        self._lock = threading.Lock()
        self._write_queue = Queue(maxsize=10000)
        self._write_thread = None
        self._write_running = False
        self._cache = OrderedDict()
        self._cache_lock = threading.Lock()
        self._stats = {
            'inserts': 0,
            'updates': 0,
            'deletes': 0,
            'queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'batch_writes': 0,
            'async_writes': 0
        }
        self._stats_lock = threading.Lock()
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        conn.execute('PRAGMA cache_size=10000;')
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
            
            self._start_write_thread()
            return True
        except Exception as e:
            print(f'Database connection failed: {e}')
            return False
    
    def _start_write_thread(self):
        if self._write_running:
            return
        
        self._write_running = True
        
        def write_worker():
            while self._write_running:
                try:
                    tasks = []
                    try:
                        tasks.append(self._write_queue.get(timeout=0.5))
                        while not self._write_queue.empty() and len(tasks) < 10:
                            tasks.append(self._write_queue.get_nowait())
                    except Empty:
                        pass
                    
                    if tasks:
                        self._process_write_tasks(tasks)
                    
                except Exception as e:
                    get_error_handler().log_error(
                        ErrorType.DATA_WRITE_ERROR, 
                        f'Write thread error: {e}'
                    )
        
        self._write_thread = threading.Thread(target=write_worker, daemon=True)
        self._write_thread.start()
    
    def _process_write_tasks(self, tasks: List[DataWriteTask]):
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    
                    for task in tasks:
                        if task.table_name == 'plc_data':
                            self._batch_insert_plc_data_internal(cursor, task.data)
                        elif task.table_name == 'anomalies':
                            self._batch_insert_anomalies_internal(cursor, task.data)
                        elif task.table_name == 'fault_records':
                            self._batch_insert_fault_records_internal(cursor, task.data)
                        
                        if task.callback:
                            try:
                                task.callback()
                            except Exception as e:
                                print(f'Task callback error: {e}')
                    
                    conn.commit()
                    self._update_stats('async_writes', len(tasks))
                except Exception as e:
                    conn.rollback()
                    print(f'Batch write failed: {e}')
                finally:
                    conn.close()
        except Exception as e:
            print(f'Process write tasks error: {e}')
    
    def _batch_insert_plc_data_internal(self, cursor, data_list: List[Dict[str, Any]]):
        if not data_list:
            return
        
        sql = '''INSERT INTO plc_data 
                 (device_id, db_number, address, tag_name, value, quality) 
                 VALUES (?, ?, ?, ?, ?, ?)'''
        params = [
            (data.get('device_id'), data['db_number'], data['address'], 
             data.get('tag_name', ''), data['value'], data.get('quality', 1))
            for data in data_list
        ]
        cursor.executemany(sql, params)
    
    def _batch_insert_anomalies_internal(self, cursor, data_list: List[Dict[str, Any]]):
        if not data_list:
            return
        
        sql = '''INSERT INTO anomalies 
                 (device_id, db_number, address, tag_name, value, predicted_value, confidence, message) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
        params = [
            (data.get('device_id'), data['db_number'], data['address'], 
             data.get('tag_name', ''), data['value'], data.get('predicted_value'), 
             data.get('confidence'), data.get('message'))
            for data in data_list
        ]
        cursor.executemany(sql, params)
    
    def _batch_insert_fault_records_internal(self, cursor, data_list: List[Dict[str, Any]]):
        if not data_list:
            return
        
        sql = '''INSERT INTO fault_records 
                 (fault_name, device_id, start_time, end_time, duration_seconds, severity, related_variables, resolved) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
        params = [
            (data.get('fault_name'), data.get('device_id'), data.get('start_time'),
             data.get('end_time'), data.get('duration_seconds'), data.get('severity'),
             data.get('related_variables'), data.get('resolved', 0))
            for data in data_list
        ]
        cursor.executemany(sql, params)
    
    def _update_stats(self, key: str, delta: int = 1):
        with self._stats_lock:
            self._stats[key] += delta
    
    def _get_cache_key(self, table_name: str, **kwargs) -> str:
        parts = [table_name]
        for k, v in sorted(kwargs.items()):
            parts.append(f'{k}={v}')
        return ':'.join(parts)
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        with self._cache_lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._update_stats('cache_hits')
                return self._cache[key]
            self._update_stats('cache_misses')
            return None
    
    def _add_to_cache(self, key: str, value: Any):
        with self._cache_lock:
            while len(self._cache) >= self.CACHE_MAX_SIZE:
                self._cache.popitem(last=False)
            self._cache[key] = value
            self._cache.move_to_end(key)
    
    def _invalidate_cache(self, table_name: str):
        with self._cache_lock:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(table_name + ':')]
            for k in keys_to_remove:
                del self._cache[k]
    
    def create_indexes(self, cursor):
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
    
    def create_device_views(self, cursor, device_ids: List[str]):
        for device_id in device_ids:
            safe_name = device_id.replace('-', '_').replace('.', '_')
            
            view_name = f'plc_data_{safe_name}'
            cursor.execute(f'''
                CREATE VIEW IF NOT EXISTS {view_name} AS
                SELECT * FROM plc_data WHERE device_id = ?
            ''', (device_id,))
            
            view_name = f'anomalies_{safe_name}'
            cursor.execute(f'''
                CREATE VIEW IF NOT EXISTS {view_name} AS
                SELECT * FROM anomalies WHERE device_id = ?
            ''', (device_id,))
            
            view_name = f'fault_records_{safe_name}'
            cursor.execute(f'''
                CREATE VIEW IF NOT EXISTS {view_name} AS
                SELECT * FROM fault_records WHERE device_id = ?
            ''', (device_id,))
    
    def add_missing_columns(self, cursor):
        cursor.execute("PRAGMA table_info(plc_data)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'device_id' not in columns:
            cursor.execute("ALTER TABLE plc_data ADD COLUMN device_id TEXT")
        
        if 'tag_name' not in columns:
            cursor.execute("ALTER TABLE plc_data ADD COLUMN tag_name TEXT")
        
        if 'quality' not in columns:
            cursor.execute("ALTER TABLE plc_data ADD COLUMN quality INTEGER")
        
        cursor.execute("PRAGMA table_info(anomalies)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'device_id' not in columns:
            cursor.execute("ALTER TABLE anomalies ADD COLUMN device_id TEXT")
        
        if 'tag_name' not in columns:
            cursor.execute("ALTER TABLE anomalies ADD COLUMN tag_name TEXT")
    
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
        
        cursor.execute(create_plc_data_table)
        cursor.execute(create_anomaly_table)
        cursor.execute(create_fault_records_table)
        cursor.execute(create_devices_table)
    
    def batch_insert_plc_data(self, data_list: List[Dict[str, Any]], device_id: str = None, async_write: bool = True):
        if not data_list:
            return True
        
        for data in data_list:
            if device_id:
                data['device_id'] = device_id
        
        if async_write and self._write_running:
            try:
                self._write_queue.put(DataWriteTask(table_name='plc_data', data=data_list), timeout=5)
                self._update_stats('batch_writes')
                return True
            except Exception as e:
                print(f'Failed to enqueue PLC data: {e}')
                async_write = False
        
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    sql = '''INSERT INTO plc_data 
                             (device_id, db_number, address, tag_name, value, quality) 
                             VALUES (?, ?, ?, ?, ?, ?)'''
                    params = [
                        (data.get('device_id'), data['db_number'], data['address'], 
                         data.get('tag_name', ''), data['value'], data.get('quality', 1))
                        for data in data_list
                    ]
                    cursor.executemany(sql, params)
                    conn.commit()
                    self._update_stats('inserts', len(data_list))
                    self._invalidate_cache('plc_data')
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
    
    def insert_anomaly(self, data: Dict[str, Any], device_id: str = None, async_write: bool = True):
        if device_id:
            data['device_id'] = device_id
        
        if async_write and self._write_running:
            try:
                self._write_queue.put(DataWriteTask(table_name='anomalies', data=[data]), timeout=5)
                return True
            except Exception as e:
                print(f'Failed to enqueue anomaly: {e}')
                async_write = False
        
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    sql = '''INSERT INTO anomalies
                             (device_id, db_number, address, tag_name, value, predicted_value, confidence, message)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
                    cursor.execute(sql, (
                        data.get('device_id'),
                        data['db_number'],
                        data['address'],
                        data.get('tag_name', ''),
                        data['value'],
                        data.get('predicted_value'),
                        data.get('confidence'),
                        data.get('message')
                    ))
                    conn.commit()
                    self._update_stats('inserts')
                    self._invalidate_cache('anomalies')
                    return cursor.lastrowid
                except Exception as e:
                    conn.rollback()
                    print(f'Insert anomaly failed: {e}')
                    return None
                finally:
                    conn.close()
        except Exception as e:
            print(f'Insert anomaly outer error: {e}')
            return None
    
    def insert_fault_record(self, fault_data: Dict[str, Any], async_write: bool = True):
        if async_write and self._write_running:
            try:
                self._write_queue.put(DataWriteTask(table_name='fault_records', data=[fault_data]), timeout=5)
                return True
            except Exception as e:
                print(f'Failed to enqueue fault record: {e}')
                async_write = False
        
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
                    self._update_stats('inserts')
                    self._invalidate_cache('fault_records')
                    return cursor.lastrowid
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
                    self._update_stats('updates')
                    self._invalidate_cache('fault_records')
                    return cursor.rowcount
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
        cache_key = self._get_cache_key('fault_records', device_id=device_id, active=True)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
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
                    result_list = [{'fault_name': r[0], 'device_id': r[1], 'start_time': r[2],
                                   'severity': r[3], 'related_variables': r[4]} for r in results]
                    
                    self._add_to_cache(cache_key, result_list)
                    self._update_stats('queries')
                    return result_list
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get active faults failed: {e}')
            return []
    
    def get_plc_data(
        self,
        start_time: str = None,
        end_time: str = None,
        db_number: int = None,
        device_id: str = None,
        limit: int = None,
        offset: int = 0
    ) -> List:
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    
                    sql_parts = ['SELECT * FROM plc_data WHERE 1=1']
                    params = []
                    
                    if device_id:
                        sql_parts.append('AND device_id = ?')
                        params.append(device_id)
                    
                    if start_time:
                        sql_parts.append('AND timestamp >= ?')
                        params.append(start_time)
                    
                    if end_time:
                        sql_parts.append('AND timestamp <= ?')
                        params.append(end_time)
                    
                    if db_number is not None:
                        sql_parts.append('AND db_number = ?')
                        params.append(db_number)
                    
                    sql_parts.append('ORDER BY timestamp DESC')
                    
                    if limit is not None:
                        sql_parts.append('LIMIT ? OFFSET ?')
                        params.extend([limit, offset])
                    
                    sql = ' '.join(sql_parts)
                    cursor.execute(sql, params)
                    
                    self._update_stats('queries')
                    return cursor.fetchall()
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get PLC data failed: {e}')
            return []
    
    def get_plc_data_by_device(
        self,
        device_id: str,
        start_time: str = None,
        end_time: str = None,
        db_number: int = None
    ) -> List:
        return self.get_plc_data(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            db_number=db_number
        )
    
    def get_anomalies(
        self,
        start_time: str = None,
        end_time: str = None,
        device_id: str = None,
        limit: int = None,
        offset: int = 0
    ) -> List:
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    
                    sql_parts = ['SELECT * FROM anomalies WHERE 1=1']
                    params = []
                    
                    if device_id:
                        sql_parts.append('AND device_id = ?')
                        params.append(device_id)
                    
                    if start_time:
                        sql_parts.append('AND timestamp >= ?')
                        params.append(start_time)
                    
                    if end_time:
                        sql_parts.append('AND timestamp <= ?')
                        params.append(end_time)
                    
                    sql_parts.append('ORDER BY timestamp DESC')
                    
                    if limit is not None:
                        sql_parts.append('LIMIT ? OFFSET ?')
                        params.extend([limit, offset])
                    
                    sql = ' '.join(sql_parts)
                    cursor.execute(sql, params)
                    
                    self._update_stats('queries')
                    return cursor.fetchall()
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get anomalies failed: {e}')
            return []
    
    def get_anomalies_by_device(
        self,
        device_id: str,
        start_time: str = None,
        end_time: str = None
    ) -> List:
        return self.get_anomalies(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time
        )
    
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
                    
                    self._update_stats('queries')
                    return cursor.fetchall()
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
                    self._update_stats('inserts')
                    self._invalidate_cache('devices')
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
        cache_key = self._get_cache_key('devices')
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM devices ORDER BY device_id')
                    result = cursor.fetchall()
                    
                    self._add_to_cache(cache_key, result)
                    self._update_stats('queries')
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
                    
                    self._update_stats('queries')
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
                        "DELETE FROM plc_data WHERE timestamp < datetime('now', ?)",
                        (f'-{days} days',)
                    )
                    plc_deleted = cursor.rowcount
                    
                    cursor.execute(
                        "DELETE FROM anomalies WHERE timestamp < datetime('now', ?)",
                        (f'-{days} days',)
                    )
                    anomaly_deleted = cursor.rowcount
                    
                    conn.commit()
                    self._update_stats('deletes', plc_deleted + anomaly_deleted)
                    self._invalidate_cache('plc_data')
                    self._invalidate_cache('anomalies')
                    
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
                    self._update_stats('deletes', plc_deleted + anomaly_deleted + fault_deleted)
                    self._invalidate_cache('plc_data')
                    self._invalidate_cache('anomalies')
                    self._invalidate_cache('fault_records')
                    
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
                    self._update_stats('queries')
                    return result[0] if result else 0
                finally:
                    conn.close()
        except Exception as e:
            print(f'Get record count failed: {e}')
            return 0
    
    def get_device_data_summary(self) -> List[Dict]:
        cache_key = self._get_cache_key('device_data_summary')
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
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
                    result_list = [
                        {
                            'device_id': r[0],
                            'total_records': r[1],
                            'first_timestamp': r[2],
                            'last_timestamp': r[3]
                        }
                        for r in results
                    ]
                    
                    self._add_to_cache(cache_key, result_list)
                    self._update_stats('queries')
                    return result_list
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
                    
                    self._update_stats('queries')
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
    
    def get_storage_stats(self) -> Dict[str, Any]:
        with self._stats_lock:
            stats = self._stats.copy()
        
        stats['queue_size'] = self._write_queue.qsize()
        stats['cache_size'] = len(self._cache)
        
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM plc_data")
                stats['plc_data_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM anomalies")
                stats['anomalies_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM fault_records")
                stats['fault_records_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM devices")
                stats['devices_count'] = cursor.fetchone()[0]
            finally:
                conn.close()
        
        return stats
    
    def close(self):
        self._write_running = False
        if self._write_thread:
            self._write_thread.join(timeout=5)
    
    def optimize_database(self):
        try:
            with self._lock:
                conn = self._get_conn()
                try:
                    cursor = conn.cursor()
                    cursor.execute("VACUUM")
                    cursor.execute("ANALYZE")
                    conn.commit()
                    print("Database optimized")
                    return True
                except Exception as e:
                    conn.rollback()
                    print(f'Database optimization failed: {e}')
                    return False
                finally:
                    conn.close()
        except Exception as e:
            print(f'Database optimization outer error: {e}')
            return False