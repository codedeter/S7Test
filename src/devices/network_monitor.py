import subprocess
import re
import platform
import socket
import threading
import time
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .device_config import NetworkInterface


class NetworkStatus(Enum):
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class NetworkStatusInfo:
    interface_name: str
    ip_address: str
    status: NetworkStatus
    last_check: float
    latency_ms: Optional[float] = None
    packet_loss: Optional[float] = None


class NetworkMonitor:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(NetworkMonitor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._interfaces: Dict[str, NetworkInterface] = {}
        self._interface_status: Dict[str, NetworkStatusInfo] = {}
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._check_interval = 5.0
        self._callbacks: List[Callable[[str, NetworkStatus, str], None]] = []
        self._lock = threading.Lock()
    
    def add_callback(self, callback: Callable[[str, NetworkStatus, str], None]):
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[str, NetworkStatus, str], None]):
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def _notify_callbacks(self, iface_name: str, status: NetworkStatus, reason: str):
        with self._lock:
            for callback in self._callbacks:
                try:
                    callback(iface_name, status, reason)
                except Exception as e:
                    print(f"[NetworkMonitor] Error in callback: {e}")

    def start(self, check_interval: float = 5.0):
        if self._running:
            return
        self._running = True
        self._check_interval = check_interval
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)

    def _monitor_loop(self):
        while self._running:
            try:
                self._check_all_interfaces()
            except Exception as e:
                print(f"[NetworkMonitor] Error in monitor loop: {e}")
            time.sleep(self._check_interval)

    def _check_all_interfaces(self):
        interfaces = self.get_all_interfaces()
        for iface in interfaces:
            status = self._check_interface_status(iface)
            latency = self._ping_host(iface.ip_address)
            
            with self._lock:
                old_status = self._interface_status.get(iface.name)
                
                self._interface_status[iface.name] = NetworkStatusInfo(
                    interface_name=iface.name,
                    ip_address=iface.ip_address,
                    status=status,
                    last_check=time.time(),
                    latency_ms=latency
                )

                if old_status and old_status.status != status:
                    reason = f"Network interface {iface.name} changed from {old_status.status.value} to {status.value}"
                    self._notify_callbacks(iface.name, status, reason)

    def _check_interface_status(self, iface: NetworkInterface) -> NetworkStatus:
        try:
            if platform.system() == 'Windows':
                result = subprocess.run(
                    ['ipconfig', '/all'],
                    capture_output=True,
                    text=True
                )
                output = result.stdout
                if iface.name in output and 'DHCP Enabled' in output:
                    return NetworkStatus.UP
            else:
                result = subprocess.run(
                    ['ip', 'addr', 'show', iface.name],
                    capture_output=True,
                    text=True
                )
                if 'UP' in result.stdout:
                    return NetworkStatus.UP
            return NetworkStatus.DOWN
        except Exception:
            return NetworkStatus.UNKNOWN

    def _ping_host(self, host: str, count: int = 1, timeout: int = 2) -> Optional[float]:
        try:
            if platform.system() == 'Windows':
                result = subprocess.run(
                    ['ping', '-n', str(count), '-w', str(timeout * 1000), host],
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ['ping', '-c', str(count), '-W', str(timeout), host],
                    capture_output=True,
                    text=True
                )
            
            if result.returncode == 0:
                if platform.system() == 'Windows':
                    for line in result.stdout.split('\n'):
                        if 'Average' in line:
                            parts = line.split('=')
                            if len(parts) > 1:
                                return float(parts[-1].replace('ms', '').strip())
                else:
                    for line in result.stdout.split('\n'):
                        if 'avg' in line:
                            parts = line.split('/')
                            if len(parts) >= 5:
                                return float(parts[4])
            return None
        except Exception:
            return None

    def get_all_interfaces(self) -> List[NetworkInterface]:
        interfaces = []
        try:
            if platform.system() == 'Windows':
                result = subprocess.run(['ipconfig', '/all'], capture_output=True, text=True)
                lines = result.stdout.split('\n')
                current_iface = None
                
                # Windows adapter name patterns
                adapter_pattern = re.compile(r'^(.*?) adapter (.*?):$', re.IGNORECASE)
                
                for line in lines:
                    line = line.strip()
                    
                    # Check for adapter name lines
                    adapter_match = adapter_pattern.search(line)
                    if adapter_match:
                        if current_iface and current_iface.ip_address:
                            interfaces.append(current_iface)
                        
                        adapter_type = adapter_match.group(1).strip()
                        adapter_name = adapter_match.group(2).strip()
                        
                        # Clean up the name
                        clean_name = adapter_name
                        if 'Wireless' in adapter_type:
                            clean_name = f"Wi-Fi: {adapter_name}"
                        elif 'Ethernet' in adapter_type:
                            clean_name = f"Ethernet: {adapter_name}"
                        
                        current_iface = NetworkInterface(name=clean_name, ip_address='')
                    elif current_iface and ('IPv4 Address' in line or 'IPv4 地址' in line):
                        # Extract IPv4 address
                        ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                        if ip_match:
                            ip = ip_match.group(1)
                            if ip and not ip.startswith('169.254'):
                                current_iface.ip_address = ip
                
                # Add the last interface if it has an IP
                if current_iface and current_iface.ip_address:
                    interfaces.append(current_iface)
            else:
                # Linux/macOS
                try:
                    result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
                    lines = result.stdout.split('\n')
                    current_name = None
                    
                    for line in lines:
                        line = line.strip()
                        if line and line[0].isdigit():
                            parts = line.split(':')
                            if len(parts) >= 2:
                                current_name = parts[1].strip()
                        elif current_name and 'inet ' in line:
                            ip_match = re.search(r'inet (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                            if ip_match:
                                ip = ip_match.group(1)
                                if ip and not ip.startswith('127.') and not ip.startswith('169.254'):
                                    interfaces.append(NetworkInterface(name=current_name, ip_address=ip))
                except Exception:
                    pass
        except Exception:
            pass
        
        return interfaces

def get_network_monitor() -> NetworkMonitor:
    return NetworkMonitor()