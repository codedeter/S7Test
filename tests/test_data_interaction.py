import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import time
import json
from src.serialization import DataSerializer, DataDelta, DataPacker
from src.socketio_handler.subscription_manager import SubscriptionManager, get_subscription_manager


class TestDataSerializer(unittest.TestCase):
    def test_json_serialization(self):
        data = {'key': 'value', 'number': 42, 'list': [1, 2, 3]}
        serialized = DataSerializer.json_serialize(data)
        deserialized = DataSerializer.json_deserialize(serialized)
        self.assertEqual(data, deserialized)
    
    def test_msgpack_serialization(self):
        data = {'key': 'value', 'number': 42, 'list': [1, 2, 3]}
        serialized = DataSerializer.msgpack_serialize(data)
        deserialized = DataSerializer.msgpack_deserialize(serialized)
        self.assertEqual(data, deserialized)
    
    def test_compression(self):
        data = {'key': 'value' * 1000}
        serialized = DataSerializer.json_serialize(data)
        compressed = DataSerializer.compress(serialized)
        decompressed = DataSerializer.decompress(compressed)
        self.assertEqual(serialized, decompressed)
        self.assertLess(len(compressed), len(serialized))


class TestDataDelta(unittest.TestCase):
    def test_compute_delta_first_time(self):
        delta = DataDelta()
        current_values = {'tag1': 1, 'tag2': 2, 'tag3': 3}
        result = delta.compute_delta('device1', current_values)
        self.assertEqual(result, current_values)
    
    def test_compute_delta_no_change(self):
        delta = DataDelta()
        current_values = {'tag1': 1, 'tag2': 2}
        delta.compute_delta('device1', current_values)
        
        result = delta.compute_delta('device1', current_values)
        self.assertEqual(result, {})
    
    def test_compute_delta_with_changes(self):
        delta = DataDelta()
        delta.compute_delta('device1', {'tag1': 1, 'tag2': 2})
        
        result = delta.compute_delta('device1', {'tag1': 1, 'tag2': 3, 'tag3': 4})
        self.assertEqual(result, {'tag2': 3, 'tag3': 4})
    
    def test_clear_device_state(self):
        delta = DataDelta()
        delta.compute_delta('device1', {'tag1': 1})
        delta.clear_device_state('device1')
        
        result = delta.compute_delta('device1', {'tag1': 1})
        self.assertEqual(result, {'tag1': 1})


class TestDataPacker(unittest.TestCase):
    def test_create_packet(self):
        packer = DataPacker()
        payload = {'data': 'test'}
        packet = packer.create_packet('data', 'device1', payload, sequence=1)
        
        self.assertEqual(packet['type'], 'data')
        self.assertEqual(packet['device_id'], 'device1')
        self.assertEqual(packet['sequence'], 1)
        self.assertEqual(packet['payload'], payload)
        self.assertIn('timestamp', packet)
    
    def test_pack_unpack(self):
        packer = DataPacker()
        data = {'key': 'value', 'number': 42}
        
        packed = packer.pack_data(data, use_compression=False, use_msgpack=False)
        unpacked = packer.unpack_data(packed, use_compression=False, use_msgpack=False)
        self.assertEqual(data, unpacked)


class TestSubscriptionManager(unittest.TestCase):
    def setUp(self):
        self.manager = get_subscription_manager()
        self.manager._clients = {}
        self.manager._client_sids = {}
    
    def test_add_remove_client(self):
        self.manager.add_client('sid1', 'client1')
        client = self.manager.get_client('sid1')
        self.assertIsNotNone(client)
        self.assertEqual(client.client_id, 'client1')
        
        self.manager.remove_client('sid1')
        client = self.manager.get_client('sid1')
        self.assertIsNone(client)
    
    def test_subscribe_device(self):
        self.manager.add_client('sid1', 'client1')
        self.manager.subscribe_to_device('sid1', 'device1')
        
        client = self.manager.get_client('sid1')
        self.assertFalse(client.subscribe_all_devices)
        self.assertIn('device1', client.subscribed_devices)
    
    def test_subscribe_tag(self):
        self.manager.add_client('sid1', 'client1')
        self.manager.subscribe_to_tag('sid1', 'tag1')
        
        client = self.manager.get_client('sid1')
        self.assertFalse(client.subscribe_all_tags)
        self.assertIn('tag1', client.subscribed_tags)
    
    def test_is_subscribed(self):
        self.manager.add_client('sid1', 'client1')
        client = self.manager.get_client('sid1')
        
        self.assertTrue(client.is_subscribed_to_device('any_device'))
        self.assertTrue(client.is_subscribed_to_tag('any_tag'))
        
        self.manager.set_subscribe_all_devices('sid1', False)
        self.manager.subscribe_to_device('sid1', 'device1')
        self.assertTrue(client.is_subscribed_to_device('device1'))
        self.assertFalse(client.is_subscribed_to_device('device2'))
    
    def test_filter_tags(self):
        self.manager.add_client('sid1', 'client1')
        self.manager.set_subscribe_all_tags('sid1', False)
        self.manager.subscribe_to_tag('sid1', 'device1:tag1')
        
        tags = {'tag1': 1, 'tag2': 2, 'tag3': 3}
        filtered = self.manager.filter_tags_for_client('sid1', 'device1', tags)
        
        self.assertEqual(filtered, {'tag1': 1})
    
    def test_get_clients_for_device(self):
        self.manager.add_client('sid1', 'client1')
        self.manager.add_client('sid2', 'client2')
        self.manager.set_subscribe_all_devices('sid2', False)
        self.manager.subscribe_to_device('sid2', 'device1')
        
        clients = self.manager.get_clients_for_device('device1')
        self.assertEqual(len(clients), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)