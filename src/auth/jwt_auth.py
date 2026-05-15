"""
API认证和权限控制模块

提供JWT认证、权限管理和访问控制功能。
"""

import jwt
import time
import os
from typing import Optional, Dict, Any, List
from functools import wraps
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from flask import request, jsonify


class UserRole(Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


@dataclass
class User:
    """用户信息"""
    user_id: str
    username: str
    role: UserRole
    permissions: List[str]


class JWTAuth:
    """JWT认证管理器"""

    def __init__(
        self,
        secret_key: str = None,
        algorithm: str = "HS256",
        token_expiry_hours: int = 24
    ):
        """
        初始化JWT认证器。

        Args:
            secret_key: JWT密钥
            algorithm: JWT算法
            token_expiry_hours: Token过期时间（小时）
        """
        self.secret_key = secret_key or os.environ.get(
            'JWT_SECRET_KEY',
            'your-secret-key-change-in-production'
        )
        self.algorithm = algorithm
        self.token_expiry_hours = token_expiry_hours

    def generate_token(self, user_id: str, username: str, role: UserRole, **extra_claims) -> str:
        """
        生成JWT Token。

        Args:
            user_id: 用户ID
            username: 用户名
            role: 用户角色
            **extra_claims: 额外的Token声明

        Returns:
            JWT Token字符串
        """
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role.value,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            **extra_claims
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证JWT Token。

        Args:
            token: JWT Token字符串

        Returns:
            Token解析后的Payload，如果验证失败返回None
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            print("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"JWT token validation error: {e}")
            return None

    def refresh_token(self, token: str) -> Optional[str]:
        """
        刷新JWT Token。

        Args:
            token: 旧的JWT Token

        Returns:
            新的JWT Token，如果验证失败返回None
        """
        payload = self.verify_token(token)
        if payload is None:
            return None

        return self.generate_token(
            user_id=payload['user_id'],
            username=payload['username'],
            role=UserRole(payload['role'])
        )

    def get_user_from_token(self, token: str) -> Optional[User]:
        """
        从Token获取用户信息。

        Args:
            token: JWT Token

        Returns:
            User对象，如果验证失败返回None
        """
        payload = self.verify_token(token)
        if payload is None:
            return None

        return User(
            user_id=payload['user_id'],
            username=payload['username'],
            role=UserRole(payload['role']),
            permissions=self._get_role_permissions(UserRole(payload['role']))
        )

    @staticmethod
    def _get_role_permissions(role: UserRole) -> List[str]:
        """获取角色权限"""
        permissions = {
            UserRole.ADMIN: [
                'read:data', 'write:data', 'read:config', 'write:config',
                'read:users', 'write:users', 'admin:system',
                'read:faults', 'write:faults', 'read:logs'
            ],
            UserRole.OPERATOR: [
                'read:data', 'write:data', 'read:config',
                'read:faults', 'write:faults'
            ],
            UserRole.VIEWER: [
                'read:data', 'read:faults'
            ]
        }
        return permissions.get(role, [])


_auth_instance: Optional[JWTAuth] = None


def get_auth() -> JWTAuth:
    """获取全局认证实例"""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = JWTAuth()
    return _auth_instance


def jwt_required(f):
    """
    JWT认证装饰器。

    使用方式:
        @app.route('/api/protected')
        @jwt_required
        def protected_endpoint():
            user = get_current_user()
            return jsonify({'user': user.username})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        auth = get_auth()
        user = auth.get_user_from_token(token)

        if user is None:
            return jsonify({'error': 'Token is invalid or expired'}), 401

        request.current_user = user
        return f(*args, **kwargs)

    return decorated


def require_permission(permission: str):
    """
    权限检查装饰器。

    使用方式:
        @app.route('/api/admin-only')
        @jwt_required
        @require_permission('admin:system')
        def admin_only_endpoint():
            return jsonify({'message': 'Admin access granted'})
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401

            user: User = request.current_user

            if permission not in user.permissions:
                return jsonify({
                    'error': 'Permission denied',
                    'required_permission': permission
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


def require_role(role: UserRole):
    """
    角色检查装饰器。

    使用方式:
        @app.route('/api/admin-action')
        @jwt_required
        @require_role(UserRole.ADMIN)
        def admin_action():
            return jsonify({'message': 'Admin action performed'})
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401

            user: User = request.current_user

            role_hierarchy = {
                UserRole.ADMIN: 3,
                UserRole.OPERATOR: 2,
                UserRole.VIEWER: 1
            }

            if role_hierarchy.get(user.role, 0) < role_hierarchy.get(role, 0):
                return jsonify({
                    'error': 'Insufficient role privileges',
                    'required_role': role.value
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


def get_current_user() -> Optional[User]:
    """
    获取当前请求的用户。

    Returns:
        当前用户，如果未认证返回None
    """
    return getattr(request, 'current_user', None)


class TokenBlacklist:
    """Token黑名单（用于Token主动失效）"""

    def __init__(self):
        self._blacklist: Dict[str, float] = {}
        self._cleanup_thread = None
        self._running = False

    def add(self, token: str, expiry_time: float):
        """添加Token到黑名单"""
        self._blacklist[token] = expiry_time

    def is_blacklisted(self, token: str) -> bool:
        """检查Token是否在黑名单中"""
        if token not in self._blacklist:
            return False

        if time.time() > self._blacklist[token]:
            del self._blacklist[token]
            return False

        return True

    def start_cleanup(self, interval: int = 3600):
        """启动黑名单清理线程"""
        if self._running:
            return

        self._running = True

        def cleanup():
            while self._running:
                time.sleep(interval)
                current_time = time.time()
                expired = [t for t, exp in self._blacklist.items() if current_time > exp]
                for token in expired:
                    del self._blacklist[token]

        self._cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        self._cleanup_thread.start()

    def stop_cleanup(self):
        """停止黑名单清理线程"""
        self._running = False


import threading

_blacklist = TokenBlacklist()


def get_token_blacklist() -> TokenBlacklist:
    """获取Token黑名单实例"""
    global _blacklist
    return _blacklist
