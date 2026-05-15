"""
单元测试 - 核心模块测试

测试结构化日志、异常处理、缓存、认证和监控模块。
"""

import unittest
import time
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestExceptions(unittest.TestCase):
    """测试异常处理模块"""

    def test_exception_hierarchy(self):
        """测试异常类继承"""
        from src.exceptions import (
            PLCSystemException,
            ConnectionException,
            DataReadException,
            ConfigurationException
        )

        self.assertTrue(issubclass(ConnectionException, PLCSystemException))
        self.assertTrue(issubclass(DataReadException, PLCSystemException))
        self.assertTrue(issubclass(ConfigurationException, PLCSystemException))

    def test_connection_exception(self):
        """测试连接异常"""
        from src.exceptions import ConnectionException

        exc = ConnectionException(
            message="Connection timeout",
            device_id="plc_001",
            host="192.168.1.100",
            port=102
        )

        self.assertEqual(exc.error_code, "CONNECTION_ERROR")
        self.assertEqual(exc.message, "Connection timeout")
        self.assertEqual(exc.details["device_id"], "plc_001")
        self.assertEqual(exc.details["host"], "192.168.1.100")
        self.assertEqual(exc.details["port"], 102)

    def test_data_read_exception(self):
        """测试数据读取异常"""
        from src.exceptions import DataReadException

        exc = DataReadException(
            message="Read failed",
            device_id="plc_001",
            db_number=10,
            address="DBX0.0"
        )

        self.assertEqual(exc.error_code, "DATA_READ_ERROR")
        self.assertEqual(exc.details["db_number"], 10)
        self.assertEqual(exc.details["address"], "DBX0.0")

    def test_exception_to_dict(self):
        """测试异常转字典"""
        from src.exceptions import ConfigurationException

        exc = ConfigurationException(
            message="Invalid config",
            config_key="PLC_HOST",
            config_value="invalid-ip"
        )

        result = exc.to_dict()

        self.assertEqual(result["error_code"], "CONFIG_ERROR")
        self.assertEqual(result["message"], "Invalid config")
        self.assertEqual(result["details"]["config_key"], "PLC_HOST")
        self.assertEqual(result["type"], "ConfigurationException")

    def test_get_error_suggestion(self):
        """测试错误建议获取"""
        from src.exceptions import get_error_suggestion

        suggestion = get_error_suggestion("CONNECTION_ERROR")
        self.assertIn("检查", suggestion)

        suggestion = get_error_suggestion("UNKNOWN_CODE")
        self.assertIn("管理员", suggestion)


class TestStructuredLogging(unittest.TestCase):
    """测试结构化日志模块"""

    def test_logger_creation(self):
        """测试日志器创建"""
        from src.utils.structured_logging import StructuredLogger, get_logger

        logger = StructuredLogger("test")
        self.assertIsNotNone(logger)
        self.assertIsNotNone(logger.logger)

        logger2 = get_logger("test2")
        self.assertIsNotNone(logger2)

    def test_logger_methods(self):
        """测试日志方法"""
        from src.utils.structured_logging import get_logger

        logger = get_logger("test_methods")

        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.debug("Test debug message")

        logger.log_device_connection("plc_001", "connected")
        logger.log_data_collection("plc_001", 100)
        logger.log_fault_detection("test_fault", "warning")
        logger.log_api_request("/api/health", "GET", 200)
        logger.log_performance("test_operation", 150.5)

    def test_context_logging(self):
        """测试上下文日志"""
        from src.utils.structured_logging import get_logger

        logger = get_logger("test_context")

        logger.info("Operation with context", operation="test", user_id="user_001")


class TestLRUCache(unittest.TestCase):
    """测试LRU缓存"""

    def test_cache_basic_operations(self):
        """测试缓存基本操作"""
        from src.data.multi_level_cache import LRUCache

        cache = LRUCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        self.assertEqual(cache.get("key1"), "value1")
        self.assertEqual(cache.get("key2"), "value2")
        self.assertEqual(cache.get("key3"), "value3")

    def test_cache_lru_eviction(self):
        """测试LRU淘汰"""
        from src.data.multi_level_cache import LRUCache

        cache = LRUCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.get("key1")

        cache.set("key4", "value4")

        self.assertIsNone(cache.get("key2"))
        self.assertEqual(cache.get("key1"), "value1")

    def test_cache_ttl(self):
        """测试缓存过期"""
        from src.data.multi_level_cache import LRUCache

        cache = LRUCache(max_size=10, default_ttl=0.1)

        cache.set("key1", "value1")

        self.assertEqual(cache.get("key1"), "value1")

        time.sleep(0.15)

        self.assertIsNone(cache.get("key1"))

    def test_cache_stats(self):
        """测试缓存统计"""
        from src.data.multi_level_cache import LRUCache

        cache = LRUCache()

        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("nonexistent")

        stats = cache.get_stats()

        self.assertEqual(stats["size"], 1)
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertGreater(stats["hit_rate"], 0)


class TestQueryCache(unittest.TestCase):
    """测试查询缓存"""

    def test_query_cache(self):
        """测试查询缓存"""
        from src.data.multi_level_cache import QueryCache

        cache = QueryCache()

        query = "SELECT * FROM plc_data WHERE device_id = ?"
        params = ("plc_001",)
        result = [{"id": 1, "value": 100}]

        cached = cache.get_query_result(query, params)
        self.assertIsNone(cached)

        cache.set_query_result(query, params, result)

        cached = cache.get_query_result(query, params)
        self.assertEqual(cached, result)


class TestJWTAuth(unittest.TestCase):
    """测试JWT认证"""

    def test_token_generation(self):
        """测试Token生成"""
        from src.auth.jwt_auth import JWTAuth, UserRole

        auth = JWTAuth(secret_key="test-secret-key")

        token = auth.generate_token(
            user_id="user_001",
            username="testuser",
            role=UserRole.ADMIN
        )

        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

    def test_token_verification(self):
        """测试Token验证"""
        from src.auth.jwt_auth import JWTAuth, UserRole

        auth = JWTAuth(secret_key="test-secret-key")

        token = auth.generate_token(
            user_id="user_001",
            username="testuser",
            role=UserRole.OPERATOR
        )

        payload = auth.verify_token(token)

        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], "user_001")
        self.assertEqual(payload["username"], "testuser")
        self.assertEqual(payload["role"], "operator")

    def test_token_verification_invalid(self):
        """测试无效Token验证"""
        from src.auth.jwt_auth import JWTAuth

        auth = JWTAuth(secret_key="test-secret-key")

        payload = auth.verify_token("invalid-token")
        self.assertIsNone(payload)

    def test_user_from_token(self):
        """测试从Token获取用户"""
        from src.auth.jwt_auth import JWTAuth, UserRole

        auth = JWTAuth(secret_key="test-secret-key")

        token = auth.generate_token(
            user_id="user_001",
            username="testuser",
            role=UserRole.VIEWER
        )

        user = auth.get_user_from_token(token)

        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "user_001")
        self.assertEqual(user.role, UserRole.VIEWER)
        self.assertIn("read:data", user.permissions)

    def test_role_permissions(self):
        """测试角色权限"""
        from src.auth.jwt_auth import JWTAuth, UserRole

        auth = JWTAuth()

        admin_token = auth.generate_token("admin", "admin", UserRole.ADMIN)
        viewer_token = auth.generate_token("viewer", "viewer", UserRole.VIEWER)

        admin = auth.get_user_from_token(admin_token)
        viewer = auth.get_user_from_token(viewer_token)

        self.assertIn("admin:system", admin.permissions)
        self.assertNotIn("admin:system", viewer.permissions)

    def test_token_refresh(self):
        """测试Token刷新"""
        from src.auth.jwt_auth import JWTAuth, UserRole

        auth = JWTAuth(token_expiry_hours=1)

        old_token = auth.generate_token(
            user_id="user_001",
            username="testuser",
            role=UserRole.ADMIN
        )

        time.sleep(0.1)

        new_token = auth.refresh_token(old_token)

        self.assertIsNotNone(new_token)
        self.assertNotEqual(old_token, new_token)


class TestMetricsCollector(unittest.TestCase):
    """测试指标采集器"""

    def test_metrics_collection(self):
        """测试指标采集"""
        from src.monitoring.metrics import MetricsCollector

        collector = MetricsCollector()

        collector.record_request(100.0, success=True)
        collector.record_request(50.0, success=True)
        collector.record_request(200.0, success=False)

        collector.record_data_collection("plc_001", 100)
        collector.record_fault()
        collector.record_anomaly()

        collector.connection_opened()
        collector.connection_closed()

        metrics = collector.get_application_metrics()

        self.assertEqual(metrics.request_count, 3)
        self.assertEqual(metrics.error_count, 1)
        self.assertEqual(metrics.data_points_collected, 100)
        self.assertEqual(metrics.faults_detected, 1)
        self.assertEqual(metrics.anomalies_detected, 1)

    def test_system_metrics(self):
        """测试系统指标"""
        from src.monitoring.metrics import MetricsCollector

        collector = MetricsCollector()
        metrics = collector.get_system_metrics()

        self.assertGreaterEqual(metrics.cpu_percent, 0)
        self.assertGreaterEqual(metrics.memory_percent, 0)
        self.assertGreaterEqual(metrics.thread_count, 1)

    def test_uptime(self):
        """测试运行时间"""
        from src.monitoring.metrics import MetricsCollector

        collector = MetricsCollector()

        time.sleep(0.1)

        uptime = collector.get_uptime()
        self.assertGreater(uptime, 0.05)


class TestHealthChecker(unittest.TestCase):
    """测试健康检查"""

    def test_health_check_registration(self):
        """测试健康检查注册"""
        from src.monitoring.metrics import HealthChecker, HealthStatus

        checker = HealthChecker()

        def sample_check():
            return {
                "status": "healthy",
                "message": "Check passed"
            }

        checker.register_check("sample", sample_check)

        results = checker.run_checks()

        self.assertEqual(results["status"], "healthy")
        self.assertIn("sample", results["checks"])

    def test_health_status_determination(self):
        """测试健康状态判定"""
        from src.monitoring.metrics import HealthChecker

        checker = HealthChecker()

        def healthy_check():
            return {"status": "healthy", "message": "OK"}

        def degraded_check():
            return {"status": "degraded", "message": "Warning"}

        def unhealthy_check():
            return {"status": "unhealthy", "message": "Error"}

        checker.register_check("healthy", healthy_check)
        results = checker.run_checks()
        self.assertEqual(results["status"], "healthy")

        checker.register_check("degraded", degraded_check)
        results = checker.run_checks()
        self.assertEqual(results["status"], "degraded")

        checker.register_check("unhealthy", unhealthy_check)
        results = checker.run_checks()
        self.assertEqual(results["status"], "unhealthy")


class TestDataCompressor(unittest.TestCase):
    """测试数据压缩"""

    def test_gzip_compression(self):
        """测试GZIP压缩"""
        from src.socketio_handler.compression import DataCompressor

        data = {
            "device_id": "plc_001",
            "values": list(range(1000)),
            "timestamp": time.time()
        }

        compressed = DataCompressor.compress_gzip(data)

        self.assertIsInstance(compressed, bytes)
        self.assertLess(len(compressed), len(json.dumps(data)))

        decompressed = DataCompressor.decompress_gzip(compressed)

        self.assertEqual(decompressed["device_id"], "plc_001")
        self.assertEqual(len(decompressed["values"]), 1000)

    def test_compression_ratio(self):
        """测试压缩率"""
        from src.socketio_handler.compression import DataCompressor

        large_data = {
            "values": ["item" * 100 for _ in range(100)]
        }

        compressed = DataCompressor.compress_gzip(large_data, compress_level=9)
        original = json.dumps(large_data).encode()

        ratio = len(compressed) / len(original)

        self.assertLess(ratio, 0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
