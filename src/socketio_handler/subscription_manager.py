from typing import Dict, List, Set, Optional, Callable
from datetime import datetime
from threading import Lock


class ClientSubscription:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.subscribed_devices: Set[str] = set()
        self.subscribed_tags: Set[str] = set()
        self.subscribe_all_devices = True
        self.subscribe_all_tags = True
        self.last_sequence: Dict[str, int] = {}
        self.connected_at = datetime.now().timestamp()
    
    def subscribe_device(self, device_id: str):
        self.subscribed_devices.add(device_id)
        self.subscribe_all_devices = False
    
    def unsubscribe_device(self, device_id: str):
        self.subscribed_devices.discard(device_id)
    
    def subscribe_tag(self, tag_name: str):
        self.subscribed_tags.add(tag_name)
        self.subscribe_all_tags = False
    
    def unsubscribe_tag(self, tag_name: str):
        self.subscribed_tags.discard(tag_name)
    
    def is_subscribed_to_device(self, device_id: str) -> bool:
        if self.subscribe_all_devices:
            return True
        return device_id in self.subscribed_devices
    
    def is_subscribed_to_tag(self, tag_name: str) -> bool:
        if self.subscribe_all_tags:
            return True
        return tag_name in self.subscribed_tags
    
    def update_sequence(self, device_id: str, sequence: int):
        self.last_sequence[device_id] = sequence
    
    def get_last_sequence(self, device_id: str) -> int:
        return self.last_sequence.get(device_id, 0)


class SubscriptionManager:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._clients: Dict[str, ClientSubscription] = {}
                cls._client_sids: Dict[str, str] = {}
                cls._device_clients: Dict[str, Set[str]] = {}
            return cls._instance
    
    def add_client(self, sid: str, client_id: str = None):
        with self._lock:
            actual_client_id = client_id or sid
            self._clients[actual_client_id] = ClientSubscription(actual_client_id)
            self._client_sids[sid] = actual_client_id
    
    def remove_client(self, sid: str):
        with self._lock:
            if sid in self._client_sids:
                client_id = self._client_sids[sid]
                del self._client_sids[sid]
                
                if client_id in self._clients:
                    del self._clients[client_id]
    
    def get_client(self, sid: str) -> Optional[ClientSubscription]:
        with self._lock:
            client_id = self._client_sids.get(sid)
            if client_id:
                return self._clients.get(client_id)
        return None
    
    def subscribe_to_device(self, sid: str, device_id: str):
        client = self.get_client(sid)
        if client:
            client.subscribe_device(device_id)
    
    def unsubscribe_from_device(self, sid: str, device_id: str):
        client = self.get_client(sid)
        if client:
            client.unsubscribe_device(device_id)
    
    def subscribe_to_tag(self, sid: str, tag_name: str):
        client = self.get_client(sid)
        if client:
            client.subscribe_tag(tag_name)
    
    def unsubscribe_from_tag(self, sid: str, tag_name: str):
        client = self.get_client(sid)
        if client:
            client.unsubscribe_tag(tag_name)
    
    def set_subscribe_all_devices(self, sid: str, subscribe_all: bool):
        client = self.get_client(sid)
        if client:
            client.subscribe_all_devices = subscribe_all
            if subscribe_all:
                client.subscribed_devices.clear()
    
    def set_subscribe_all_tags(self, sid: str, subscribe_all: bool):
        client = self.get_client(sid)
        if client:
            client.subscribe_all_tags = subscribe_all
            if subscribe_all:
                client.subscribed_tags.clear()
    
    def get_clients_for_device(self, device_id: str) -> List[str]:
        clients = []
        with self._lock:
            for client_id, subscription in self._clients.items():
                if subscription.is_subscribed_to_device(device_id):
                    clients.append(client_id)
        return clients
    
    def filter_tags_for_client(self, sid: str, device_id: str, tags: Dict[str, Any]) -> Dict[str, Any]:
        client = self.get_client(sid)
        if not client:
            return {}
        
        if client.subscribe_all_tags:
            return tags
        
        filtered = {}
        for tag_name, value in tags.items():
            full_tag_name = f"{device_id}:{tag_name}" if not tag_name.startswith(device_id) else tag_name
            if client.is_subscribed_to_tag(full_tag_name):
                filtered[tag_name] = value
        
        return filtered
    
    def get_client_count(self) -> int:
        with self._lock:
            return len(self._clients)
    
    def get_all_client_info(self) -> List[Dict[str, Any]]:
        info = []
        with self._lock:
            for client_id, subscription in self._clients.items():
                info.append({
                    'client_id': client_id,
                    'subscribe_all_devices': subscription.subscribe_all_devices,
                    'subscribed_devices': list(subscription.subscribed_devices),
                    'subscribe_all_tags': subscription.subscribe_all_tags,
                    'subscribed_tags': list(subscription.subscribed_tags),
                    'connected_at': subscription.connected_at
                })
        return info


def get_subscription_manager() -> SubscriptionManager:
    return SubscriptionManager()