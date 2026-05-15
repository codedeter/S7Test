"""
SocketIO通信优化模块

提供数据压缩和客户端能力协商功能，减少网络带宽消耗。
"""

import gzip
import json
import struct
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class CompressionType(Enum):
    """压缩类型枚举"""
    NONE = "none"
    GZIP = "gzip"
    ZSTD = "zstd"


@dataclass
class ClientCapabilities:
    """客户端能力信息"""
    client_id: str
    supports_compression: bool = False
    supports_delta_sync: bool = True
    compression_preference: CompressionType = CompressionType.GZIP
    max_packet_size: int = 1024 * 1024  # 1MB
    supported_encodings: List[str] = field(default_factory=lambda: ['json'])

    def can_compress(self) -> bool:
        """检查客户端是否支持压缩"""
        return self.supports_compression

    def get_preferred_compression(self) -> CompressionType:
        """获取客户端首选的压缩类型"""
        return self.compression_preference


class DataCompressor:
    """数据压缩器"""

    @staticmethod
    def compress_gzip(data: Dict[str, Any], compress_level: int = 6) -> bytes:
        """
        使用gzip压缩数据。

        Args:
            data: 要压缩的数据字典
            compress_level: 压缩级别 (1-9)，6是速度和压缩率的平衡

        Returns:
            压缩后的字节串
        """
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            json_bytes = json_data.encode('utf-8')
            compressed = gzip.compress(json_bytes, compresslevel=compress_level)
            return compressed
        except Exception as e:
            print(f"Gzip compression error: {e}")
            return json.dumps(data).encode('utf-8')

    @staticmethod
    def decompress_gzip(compressed_data: bytes) -> Dict[str, Any]:
        """
        解压gzip数据。

        Args:
            compressed_data: 压缩的字节串

        Returns:
            解压后的数据字典
        """
        try:
            decompressed = gzip.decompress(compressed_data)
            return json.loads(decompressed.decode('utf-8'))
        except Exception as e:
            print(f"Gzip decompression error: {e}")
            return {}

    @staticmethod
    def compress_lzma(data: Dict[str, Any]) -> bytes:
        """
        使用LZMA压缩数据（更高压缩率）。

        Args:
            data: 要压缩的数据字典

        Returns:
            压缩后的字节串
        """
        try:
            import lzma
            json_data = json.dumps(data, ensure_ascii=False)
            json_bytes = json_data.encode('utf-8')
            compressed = lzma.compress(json_bytes)
            return compressed
        except ImportError:
            print("lzma module not available, falling back to gzip")
            return DataCompressor.compress_gzip(data)
        except Exception as e:
            print(f"LZMA compression error: {e}")
            return DataCompressor.compress_gzip(data)

    @staticmethod
    def compress_json(data: Dict[str, Any]) -> bytes:
        """
        压缩JSON数据（不实际压缩，但优化JSON）。

        Args:
            data: 要处理的数据字典

        Returns:
            JSON编码的字节串
        """
        return json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


class PacketOptimizer:
    """数据包优化器"""

    def __init__(self):
        self.client_capabilities: Dict[str, ClientCapabilities] = {}
        self.compression_enabled = True
        self.min_compression_size = 1024  # 小于1KB不压缩
        self.compression_level = 6

    def register_client(self, client_id: str, capabilities: ClientCapabilities):
        """
        注册客户端能力。

        Args:
            client_id: 客户端ID
            capabilities: 客户端能力
        """
        self.client_capabilities[client_id] = capabilities

    def get_client_capabilities(self, client_id: str) -> Optional[ClientCapabilities]:
        """
        获取客户端能力。

        Args:
            client_id: 客户端ID

        Returns:
            客户端能力，如果不存在返回None
        """
        return self.client_capabilities.get(client_id)

    def optimize_packet(self, packet: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """
        优化数据包。

        Args:
            packet: 原始数据包
            client_id: 目标客户端ID

        Returns:
            优化后的数据包
        """
        capabilities = self.get_client_capabilities(client_id)

        optimized = packet.copy()
        optimized['_meta'] = {
            'compressed': False,
            'compressed_type': 'none',
            'original_size': len(json.dumps(packet)),
        }

        if capabilities and capabilities.can_compress():
            original_size = optimized['_meta']['original_size']

            if original_size >= self.min_compression_size:
                compressed_data = DataCompressor.compress_gzip(
                    packet,
                    self.compression_level
                )

                if len(compressed_data) < original_size:
                    optimized = {
                        '_meta': {
                            'compressed': True,
                            'compressed_type': 'gzip',
                            'original_size': original_size,
                            'compressed_size': len(compressed_data),
                            'compression_ratio': len(compressed_data) / original_size,
                        },
                        'data': compressed_data
                    }

        return optimized

    def should_send_full_data(self, sequence: int, force_interval: int = 30) -> bool:
        """
        判断是否应该发送全量数据。

        Args:
            sequence: 当前序列号
            force_interval: 强制发送全量的间隔

        Returns:
            是否发送全量数据
        """
        return sequence % force_interval == 0

    def estimate_compression_savings(self, data: Dict[str, Any]) -> float:
        """
        估算压缩节省的空间。

        Args:
            data: 要压缩的数据

        Returns:
            预估的压缩比（压缩后/压缩前）
        """
        try:
            original = json.dumps(data).encode('utf-8')
            compressed = DataCompressor.compress_gzip(data, self.compression_level)
            return len(compressed) / len(original)
        except Exception:
            return 1.0


class AdaptiveSender:
    """自适应发送器，根据网络状况动态调整发送策略"""

    def __init__(self):
        self.packet_optimizer = PacketOptimizer()
        self._send_history: List[Dict[str, Any]] = []
        self._max_history_size = 100
        self._current_quality = "high"

    def record_send_result(self, packet_size: int, send_time: float, success: bool):
        """
        记录发送结果，用于自适应调整。

        Args:
            packet_size: 数据包大小
            send_time: 发送耗时
            success: 是否成功
        """
        self._send_history.append({
            'size': packet_size,
            'time': send_time,
            'success': success,
            'timestamp': __import__('time').time()
        })

        if len(self._send_history) > self._max_history_size:
            self._send_history.pop(0)

        self._adjust_quality()

    def _adjust_quality(self):
        """根据发送历史调整质量策略"""
        if not self._send_history:
            return

        recent = self._send_history[-10:]
        success_rate = sum(1 for r in recent if r['success']) / len(recent)
        avg_time = sum(r['time'] for r in recent) / len(recent)

        if success_rate < 0.8 or avg_time > 1.0:
            self._current_quality = "low"
        elif success_rate < 0.95 or avg_time > 0.5:
            self._current_quality = "medium"
        else:
            self._current_quality = "high"

    def get_send_quality(self) -> str:
        """获取当前发送质量等级"""
        return self._current_quality

    def get_quality_settings(self) -> Dict[str, Any]:
        """
        根据当前质量等级获取发送设置。

        Returns:
            质量设置字典
        """
        settings = {
            "high": {
                "compression": True,
                "compression_level": 6,
                "delta_enabled": True,
                "max_packet_size": 1024 * 1024,
                "send_interval_ms": 100
            },
            "medium": {
                "compression": True,
                "compression_level": 9,
                "delta_enabled": True,
                "max_packet_size": 512 * 1024,
                "send_interval_ms": 200
            },
            "low": {
                "compression": True,
                "compression_level": 9,
                "delta_enabled": True,
                "max_packet_size": 256 * 1024,
                "send_interval_ms": 500
            }
        }
        return settings.get(self._current_quality, settings["high"])


_packet_optimizer = None
_adaptive_sender = None


def get_packet_optimizer() -> PacketOptimizer:
    """获取数据包优化器单例"""
    global _packet_optimizer
    if _packet_optimizer is None:
        _packet_optimizer = PacketOptimizer()
    return _packet_optimizer


def get_adaptive_sender() -> AdaptiveSender:
    """获取自适应发送器单例"""
    global _adaptive_sender
    if _adaptive_sender is None:
        _adaptive_sender = AdaptiveSender()
    return _adaptive_sender


def compress_data_for_client(data: Dict[str, Any], client_id: str) -> Dict[str, Any]:
    """
    为指定客户端压缩数据。

    Args:
        data: 原始数据
        client_id: 客户端ID

    Returns:
        优化后的数据
    """
    optimizer = get_packet_optimizer()
    return optimizer.optimize_packet(data, client_id)
