"""
优化的Socket.IO配置模块

解决ping timeout问题和优化传输性能
"""

import os


class SocketIOConfig:
    """
    Socket.IO 优化配置类

    关键优化点：
    1. 缩短心跳间隔，提高断开检测速度
    2. 批量传输优化
    3. 数据压缩配置
    4. 前端重连策略优化
    """

    # ==================== 心跳配置优化 ====================
    # 问题：pingInterval=30000, pingTimeout=60000 导致30秒才能检测到断开
    # 优化：使用更短的检测周期，快速响应网络问题

    # 心跳间隔（客户端发送ping的间隔）
    PING_INTERVAL: int = int(os.environ.get('SOCKETIO_PING_INTERVAL', '10000'))  # 10秒
    PING_TIMEOUT: int = int(os.environ.get('SOCKETIO_PING_TIMEOUT', '15000'))   # 15秒

    # 建议值说明：
    # - 生产环境：pingInterval=10000, pingTimeout=15000 (总共25秒检测)
    # - 开发环境：pingInterval=5000, pingTimeout=8000 (总共13秒检测)
    # - 极端场景：pingInterval=5000, pingTimeout=10000 (总共15秒检测)

    # ==================== 批量传输配置 ====================
    # 问题：每秒70次推送，每次500个数据点，网络负载大
    # 优化：批量打包，减少网络往返

    # 批量大小（每个包包含的数据点数量）
    BATCH_SIZE: int = int(os.environ.get('SOCKETIO_BATCH_SIZE', '100'))
    # 推荐值：100-200，平衡延迟和带宽

    # 批量超时（等待凑齐批量数据的最大时间）
    BATCH_TIMEOUT_MS: int = int(os.environ.get('SOCKETIO_BATCH_TIMEOUT', '50'))
    # 推荐值：50-100ms，超过则立即发送

    # 最大批量延迟（确保数据不会延迟太久）
    MAX_BATCH_DELAY_MS: int = int(os.environ.get('SOCKETIO_MAX_BATCH_DELAY', '200'))

    # ==================== 增量更新配置 ====================
    # 问题：每次发送500个数据点，但大部分没变化
    # 优化：只发送变化的数据

    # 启用增量更新
    ENABLE_DELTA_UPDATES: bool = bool(int(os.environ.get('SOCKETIO_ENABLE_DELTA', '1')))

    # 强制全量更新的间隔（每N次增量后发送一次全量）
    FULL_UPDATE_INTERVAL: int = int(os.environ.get('SOCKETIO_FULL_UPDATE_INTERVAL', '30'))
    # 推荐值：20-50，太频繁浪费带宽，太少可能丢失状态

    # 数据变化阈值（变化超过多少才发送）
    VALUE_CHANGE_THRESHOLD: float = float(os.environ.get('SOCKETIO_VALUE_CHANGE_THRESHOLD', '0.001'))

    # ==================== 数据压缩配置 ====================
    # 问题：大数据包传输慢
    # 优化：启用压缩

    # 启用压缩
    ENABLE_COMPRESSION: bool = bool(int(os.environ.get('SOCKETIO_ENABLE_COMPRESSION', '1')))

    # 压缩阈值（超过多少字节才压缩）
    COMPRESSION_THRESHOLD: int = int(os.environ.get('SOCKETIO_COMPRESSION_THRESHOLD', '1024'))

    # ==================== 重连配置优化 ====================
    # 问题：重连延迟太长，delayMax=5000太长
    # 优化：更智能的重连策略

    RECONNECTION_DELAY: int = int(os.environ.get('SOCKETIO_RECONNECTION_DELAY', '1000'))     # 初始延迟1秒
    RECONNECTION_DELAY_MAX: int = int(os.environ.get('SOCKETIO_RECONNECTION_DELAY_MAX', '3000'))  # 最大延迟3秒
    RECONNECTION_ATTEMPTS: int = int(os.environ.get('SOCKETIO_RECONNECTION_ATTEMPTS', '-1'))  # -1表示无限重连

    # 指数退避参数
    RECONNECTION_BACKOFF_MULTIPLIER: float = 1.5
    RECONNECTION_BACKOFF_JITTER: float = 0.3  # 30%抖动，避免雷群效应

    # ==================== 前端节流配置 ====================
    # 问题：数据更新太快，前端渲染跟不上
    # 优化：前端节流

    # UI更新节流间隔
    UI_UPDATE_THROTTLE_MS: int = int(os.environ.get('SOCKETIO_UI_UPDATE_THROTTLE', '100'))
    # 推荐值：100-200ms，太快导致CPU高，太慢数据更新不及时

    # 图表更新节流间隔
    CHART_UPDATE_THROTTLE_MS: int = int(os.environ.get('SOCKETIO_CHART_UPDATE_THROTTLE', '200'))
    # 推荐值：200-500ms，图表不需要太频繁更新

    # 变量列表更新节流间隔
    VARIABLE_GRID_UPDATE_THROTTLE_MS: int = int(os.environ.get('SOCKETIO_VARIABLE_UPDATE_THROTTLE', '500'))

    # ==================== 性能监控配置 ====================
    # 启用性能监控
    ENABLE_PERFORMANCE_MONITORING: bool = bool(int(os.environ.get('SOCKETIO_ENABLE_MONITORING', '1')))

    # 性能指标采样间隔
    METRICS_SAMPLE_INTERVAL_MS: int = int(os.environ.get('SOCKETIO_METRICS_SAMPLE_INTERVAL', '5000'))

    # ==================== 连接配置 ====================
    TRANSPORTS: list = ['websocket', 'polling']  # 优先websocket，fallback到polling
    UPGRADE: bool = True  # 允许从polling升级到websocket
    TIMEOUT: int = int(os.environ.get('SOCKETIO_TIMEOUT', '20000'))  # 连接超时20秒

    def __repr__(self) -> str:
        return (
            f"<SocketIOConfig "
            f"ping={self.PING_INTERVAL}/{self.PING_TIMEOUT}ms "
            f"batch={self.BATCH_SIZE} "
            f"delta={self.ENABLE_DELTA_UPDATES}>"
        )

    def to_dict(self) -> dict:
        """转换为字典，用于客户端配置"""
        return {
            'pingInterval': self.PING_INTERVAL,
            'pingTimeout': self.PING_TIMEOUT,
            'reconnectionDelay': self.RECONNECTION_DELAY,
            'reconnectionDelayMax': self.RECONNECTION_DELAY_MAX,
            'reconnectionAttempts': self.RECONNECTION_ATTEMPTS,
            'timeout': self.TIMEOUT,
            'transports': self.TRANSPORTS,
            'batchSize': self.BATCH_SIZE,
            'batchTimeout': self.BATCH_TIMEOUT_MS,
            'enableDelta': self.ENABLE_DELTA_UPDATES,
            'fullUpdateInterval': self.FULL_UPDATE_INTERVAL,
            'uiUpdateThrottle': self.UI_UPDATE_THROTTLE_MS,
            'chartUpdateThrottle': self.CHART_UPDATE_THROTTLE_MS,
        }


# 全局实例
socketio_config = SocketIOConfig()


def get_socketio_config() -> SocketIOConfig:
    """获取Socket.IO配置实例"""
    return socketio_config


def get_client_config() -> dict:
    """获取客户端配置（用于前端初始化）"""
    return socketio_config.to_dict()
