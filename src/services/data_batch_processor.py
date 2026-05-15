"""
数据批量处理器

解决数据量大、网络负载高的问题

核心功能：
1. 数据批量打包
2. 增量计算和压缩
3. 智能批量策略
"""

import time
import threading
import zlib
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class CompressionType(Enum):
    """压缩类型"""
    NONE = "none"
    GZIP = "gzip"
    JSON = "json"


@dataclass
class DataPacket:
    """数据包"""
    device_id: str
    timestamp: float
    data: Any
    sequence: int
    size_bytes: int = 0
    compressed: bool = False
    compression_type: CompressionType = CompressionType.NONE


@dataclass
class BatchConfig:
    """批量配置"""
    batch_size: int = 100
    batch_timeout_ms: int = 50
    max_batch_delay_ms: int = 200
    enable_compression: bool = True
    compression_threshold: int = 1024


@dataclass
class CompressionStats:
    """压缩统计"""
    original_size: int = 0
    compressed_size: int = 0
    compression_ratio: float = 0.0
    packets_compressed: int = 0
    packets_uncompressed: int = 0

    def update(self, original: int, compressed: int):
        """更新统计"""
        self.original_size += original
        self.compressed_size += compressed
        if original > 0:
            self.compression_ratio = self.compressed_size / self.original_size
            if compressed < original:
                self.packets_compressed += 1
            else:
                self.packets_uncompressed += 1


class DataBatchProcessor:
    """
    数据批量处理器

    功能：
    1. 收集多个数据点，批量发送
    2. 智能等待策略（不牺牲实时性）
    3. 数据压缩
    4. 统计和监控
    """

    def __init__(self, config: Optional[BatchConfig] = None):
        self.config = config or BatchConfig()
        self._lock = threading.RLock()

        # 批量缓冲区
        self._buffers: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._buffer_timestamps: Dict[str, float] = {}
        self._sequence_counter: Dict[str, int] = defaultdict(int)

        # 统计数据
        self._stats = {
            'packets_sent': 0,
            'packets_batched': 0,
            'bytes_sent': 0,
            'compression_stats': CompressionStats(),
            'last_send_time': time.time(),
            'avg_batch_size': 0.0,
        }
        self._stats_lock = threading.Lock()

        # 回调函数
        self._send_callback: Optional[Callable[[DataPacket], None]] = None

        # 运行状态
        self._running = False
        self._flush_thread: Optional[threading.Thread] = None
        self._flush_event = threading.Event()

    def set_send_callback(self, callback: Callable[[DataPacket], None]):
        """设置发送回调"""
        self._send_callback = callback

    def start(self):
        """启动批量处理器"""
        self._running = True
        self._flush_event.clear()

        def flush_loop():
            while self._running:
                try:
                    # 定期检查缓冲区
                    self._check_and_flush()
                except Exception as e:
                    logger.error(f"Flush loop error: {e}")

                # 等待或者超时
                self._flush_event.wait(timeout=0.05)  # 50ms检查一次

        self._flush_thread = threading.Thread(target=flush_loop, daemon=True)
        self._flush_thread.start()
        logger.info("DataBatchProcessor started")

    def stop(self):
        """停止批量处理器"""
        self._running = False
        self._flush_event.set()

        if self._flush_thread:
            self._flush_thread.join(timeout=2)

        # 刷新剩余数据
        self._flush_all()
        logger.info("DataBatchProcessor stopped")

    def add_data(self, device_id: str, data: Dict[str, Any]):
        """
        添加数据到缓冲区

        Args:
            device_id: 设备ID
            data: 数据字典
        """
        with self._lock:
            if device_id not in self._buffers:
                self._buffer_timestamps[device_id] = time.time()

            self._buffers[device_id].append({
                **data,
                '_timestamp': time.time()
            })

            # 检查是否需要立即发送
            if len(self._buffers[device_id]) >= self.config.batch_size:
                self._flush_device(device_id)

    def add_data_batch(self, device_data: Dict[str, List[Dict[str, Any]]]):
        """
        批量添加数据

        Args:
            device_data: {device_id: [data_list]}
        """
        with self._lock:
            for device_id, data_list in device_data.items():
                if device_id not in self._buffers:
                    self._buffer_timestamps[device_id] = time.time()

                self._buffers[device_id].extend([
                    {**data, '_timestamp': time.time()}
                    for data in data_list
                ])

                # 检查是否需要立即发送
                if len(self._buffers[device_id]) >= self.config.batch_size:
                    self._flush_device(device_id)

    def _check_and_flush(self):
        """检查并刷新超时的缓冲区"""
        with self._lock:
            current_time = time.time()
            devices_to_flush = []

            for device_id, buffer_time in self._buffer_timestamps.items():
                elapsed_ms = (current_time - buffer_time) * 1000

                # 检查是否超时
                if elapsed_ms >= self.config.batch_timeout_ms:
                    if self._buffers[device_id]:  # 有数据
                        devices_to_flush.append(device_id)

                # 检查是否超过最大延迟
                elif elapsed_ms >= self.config.max_batch_delay_ms:
                    if self._buffers[device_id]:
                        devices_to_flush.append(device_id)

            # 刷新设备
            for device_id in devices_to_flush:
                self._flush_device(device_id)

    def _flush_device(self, device_id: str):
        """刷新单个设备的数据"""
        if device_id not in self._buffers or not self._buffers[device_id]:
            return

        data_list = self._buffers.pop(device_id)
        self._buffer_timestamps.pop(device_id, None)

        if not data_list:
            return

        # 生成序列号
        self._sequence_counter[device_id] += 1
        sequence = self._sequence_counter[device_id]

        # 创建数据包
        packet = self._create_packet(device_id, data_list, sequence)

        # 发送
        self._send_packet(packet)

        # 更新统计
        self._update_stats(len(data_list), packet.size_bytes)

    def _flush_all(self):
        """刷新所有缓冲区"""
        with self._lock:
            device_ids = list(self._buffers.keys())

        for device_id in device_ids:
            self._flush_device(device_id)

    def _create_packet(self, device_id: str, data_list: List[Dict],
                      sequence: int) -> DataPacket:
        """创建数据包"""
        # 准备数据（移除内部字段）
        clean_data = [
            {k: v for k, v in item.items() if not k.startswith('_')}
            for item in data_list
        ]

        # 序列化为JSON
        json_data = json.dumps(clean_data, ensure_ascii=False)
        original_size = len(json_data.encode('utf-8'))

        # 压缩
        compressed_data = json_data
        compression_type = CompressionType.NONE

        if self.config.enable_compression and original_size >= self.config.compression_threshold:
            try:
                compressed_bytes = zlib.compress(json_data.encode('utf-8'), level=6)
                compressed_size = len(compressed_bytes)

                # 只有压缩后更小才使用压缩
                if compressed_size < original_size:
                    compressed_data = compressed_bytes
                    compression_type = CompressionType.GZIP
                    original_size = compressed_size  # 统计压缩后的大小
            except Exception as e:
                logger.warning(f"Compression failed: {e}")

        return DataPacket(
            device_id=device_id,
            timestamp=time.time(),
            data=compressed_data,
            sequence=sequence,
            size_bytes=original_size,
            compressed=compression_type != CompressionType.NONE,
            compression_type=compression_type
        )

    def _send_packet(self, packet: DataPacket):
        """发送数据包"""
        if self._send_callback:
            try:
                self._send_callback(packet)
            except Exception as e:
                logger.error(f"Send callback error: {e}")

    def _update_stats(self, data_count: int, size_bytes: int):
        """更新统计"""
        with self._stats_lock:
            self._stats['packets_sent'] += 1
            self._stats['packets_batched'] += data_count
            self._stats['bytes_sent'] += size_bytes
            self._stats['last_send_time'] = time.time()

            # 计算平均批量大小
            total = self._stats['packets_sent']
            if total > 0:
                self._stats['avg_batch_size'] = (
                    self._stats['avg_batch_size'] * (total - 1) + data_count
                ) / total

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            stats = self._stats.copy()
            stats['compression_stats'] = {
                'original_size': stats['compression_stats'].original_size,
                'compressed_size': stats['compression_stats'].compressed_size,
                'ratio': stats['compression_stats'].compression_ratio,
                'packets_compressed': stats['compression_stats'].packets_compressed,
                'packets_uncompressed': stats['compression_stats'].packets_uncompressed,
            }
            return stats

    def reset_stats(self):
        """重置统计"""
        with self._stats_lock:
            self._stats = {
                'packets_sent': 0,
                'packets_batched': 0,
                'bytes_sent': 0,
                'compression_stats': CompressionStats(),
                'last_send_time': time.time(),
                'avg_batch_size': 0.0,
            }


class IncrementalDataManager:
    """
    增量数据管理器

    功能：
    1. 跟踪数据状态
    2. 计算数据差异
    3. 支持多种变化检测策略
    """

    def __init__(self, change_threshold: float = 0.001):
        self._lock = threading.RLock()
        self._last_values: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._change_threshold = change_threshold
        self._change_counts: Dict[str, int] = defaultdict(int)

    def update(self, device_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新数据，返回变化的部分

        Args:
            device_id: 设备ID
            data: 当前数据

        Returns:
            只包含变化数据的字典
        """
        with self._lock:
            delta = {}
            last_device_data = self._last_values[device_id]

            for key, value in data.items():
                last_value = last_device_data.get(key)

                # 检测变化
                if self._has_changed(key, last_value, value):
                    delta[key] = value
                    self._last_values[device_id][key] = value

            # 更新变化计数
            if delta:
                self._change_counts[device_id] += 1

            return delta

    def _has_changed(self, key: str, old_value: Any, new_value: Any) -> bool:
        """检测值是否变化"""
        if old_value is None:
            return True

        if type(old_value) != type(new_value):
            return True

        # 数值类型，使用阈值
        if isinstance(new_value, (int, float)):
            if old_value == 0:
                return new_value != 0
            return abs(new_value - old_value) / abs(old_value) > self._change_threshold

        # 其他类型，直接比较
        return old_value != new_value

    def get_full_state(self, device_id: str) -> Dict[str, Any]:
        """获取完整状态"""
        with self._lock:
            return self._last_values.get(device_id, {}).copy()

    def clear_device(self, device_id: str):
        """清除设备数据"""
        with self._lock:
            self._last_values.pop(device_id, None)
            self._change_counts.pop(device_id, None)

    def get_change_count(self, device_id: str) -> int:
        """获取变化次数"""
        with self._lock:
            return self._change_counts.get(device_id, 0)


def create_batch_processor(config: Optional[BatchConfig] = None) -> DataBatchProcessor:
    """创建批量处理器"""
    return DataBatchProcessor(config)


def create_incremental_manager(threshold: float = 0.001) -> IncrementalDataManager:
    """创建增量管理器"""
    return IncrementalDataManager(change_threshold=threshold)
