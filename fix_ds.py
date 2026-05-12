import os
import shutil

base = r"c:\Users\44673\Desktop\文件往这里存！！！\TRAE\S7Test"

# Read data storage
ds_path = os.path.join(base, "src", "data", "data_storage.py")
with open(ds_path, "r", encoding="utf-8") as f:
    content = f.read()

# Backup
backup_path = ds_path + ".backup"
shutil.copy2(ds_path, backup_path)
print("Backed up to:", backup_path)

# Step 1: Update __init__
old_init = '''    def __init__(self):
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
        self._stats_lock = threading.Lock()'''

new_init = '''    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database.db')
        self._write_lock = threading.Lock()
        self._read_lock = threading.RLock()
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
        self._stats_lock = threading.Lock()'''

if old_init in content:
    content = content.replace(old_init, new_init)
    print("Updated __init__")

# Step 2: Update _get_conn
old_get_conn = '''    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        conn.execute('PRAGMA cache_size=10000;')
        return conn'''

new_get_conn = '''    def _get_conn(self, readonly=False):
        conn = sqlite3.connect(
            self.db_path, 
            check_same_thread=False, 
            timeout=30.0,
            isolation_level=None if readonly else 'DEFERRED'
        )
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        conn.execute('PRAGMA cache_size=-10000;')
        conn.execute('PRAGMA temp_store=MEMORY;')
        if readonly:
            conn.execute('PRAGMA query_only=ON;')
        return conn'''

if old_get_conn in content:
    content = content.replace(old_get_conn, new_get_conn)
    print("Updated _get_conn")

# Step 3: Replace _lock references
# This is more complex, let's do a simple replacement first
content = content.replace('with self._lock:', 'with self._write_lock:')

# Write back
with open(ds_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Data storage updated")
print("=== Complete ===")
