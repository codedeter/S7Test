import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import time
from src.startup import (
    StartupManager, StartupPhase, StartupStatus, 
    StartupContext, PhaseResult, get_startup_manager
)


class TestStartupContext(unittest.TestCase):
    def test_initial_state(self):
        context = StartupContext()
        self.assertEqual(context.current_phase, StartupPhase.INITIALIZING)
        self.assertEqual(context.overall_status, StartupStatus.PENDING)
        self.assertFalse(context.is_complete())
        self.assertFalse(context.is_failed())
    
    def test_mark_phase_start(self):
        context = StartupContext()
        context.mark_phase_start(StartupPhase.DATABASE_INIT)
        
        self.assertEqual(context.current_phase, StartupPhase.DATABASE_INIT)
        self.assertIn(StartupPhase.DATABASE_INIT, context.phase_results)
        self.assertEqual(context.phase_results[StartupPhase.DATABASE_INIT].status, StartupStatus.IN_PROGRESS)
    
    def test_mark_phase_complete(self):
        context = StartupContext()
        context.start_time = time.time() - 0.1
        context.mark_phase_start(StartupPhase.DATABASE_INIT)
        time.sleep(0.01)
        context.mark_phase_complete(StartupPhase.DATABASE_INIT, "Test complete")
        
        result = context.phase_results[StartupPhase.DATABASE_INIT]
        self.assertEqual(result.status, StartupStatus.COMPLETED)
        self.assertEqual(result.message, "Test complete")
        self.assertGreaterEqual(result.duration_ms, 0)
    
    def test_mark_phase_failed(self):
        context = StartupContext()
        context.start_time = time.time() - 0.1
        context.mark_phase_start(StartupPhase.DATABASE_INIT)
        
        error = Exception("Test error")
        context.mark_phase_failed(StartupPhase.DATABASE_INIT, error)
        
        self.assertTrue(context.is_failed())
        self.assertEqual(context.error_message, str(error))
        self.assertEqual(context.current_phase, StartupPhase.DATABASE_INIT)
    
    def test_get_progress(self):
        context = StartupContext()
        context.start_time = time.time()
        
        context.mark_phase_start(StartupPhase.DATABASE_INIT)
        context.mark_phase_complete(StartupPhase.DATABASE_INIT)
        
        context.mark_phase_start(StartupPhase.DEVICE_MANAGER_CREATE)
        context.mark_phase_complete(StartupPhase.DEVICE_MANAGER_CREATE)
        
        progress = context.get_progress()
        self.assertGreater(progress, 0)
        self.assertLess(progress, 100)
    
    def test_to_dict(self):
        context = StartupContext()
        context.start_time = 1234567890.0
        context.end_time = 1234567895.0
        context.mark_phase_start(StartupPhase.DATABASE_INIT)
        context.mark_phase_complete(StartupPhase.DATABASE_INIT)
        
        result = context.to_dict()
        
        self.assertIn('current_phase', result)
        self.assertIn('overall_status', result)
        self.assertIn('progress', result)
        self.assertIn('phase_details', result)


class TestStartupManager(unittest.TestCase):
    def setUp(self):
        manager = get_startup_manager()
        manager._context = StartupContext()
        manager._shutdown_callbacks = []
        manager._startup_callbacks = []
        manager._is_shutting_down = False
    
    def test_singleton(self):
        manager1 = get_startup_manager()
        manager2 = get_startup_manager()
        self.assertIs(manager1, manager2)
    
    def test_startup_sequence(self):
        manager = get_startup_manager()
        
        manager.begin_startup()
        self.assertEqual(manager.context.overall_status, StartupStatus.IN_PROGRESS)
        
        manager.start_phase(StartupPhase.DATABASE_INIT)
        self.assertEqual(manager.context.current_phase, StartupPhase.DATABASE_INIT)
        
        manager.complete_phase(StartupPhase.DATABASE_INIT)
        self.assertEqual(manager.context.phase_results[StartupPhase.DATABASE_INIT].status, StartupStatus.COMPLETED)
        
        manager.start_phase(StartupPhase.DEVICE_MANAGER_CREATE)
        manager.complete_phase(StartupPhase.DEVICE_MANAGER_CREATE)
        
        manager.start_phase(StartupPhase.DEVICES_INIT)
        manager.complete_phase(StartupPhase.DEVICES_INIT)
        
        manager.start_phase(StartupPhase.FLASK_APP_CREATE)
        manager.complete_phase(StartupPhase.FLASK_APP_CREATE)
        
        manager.start_phase(StartupPhase.ROUTES_REGISTER)
        manager.complete_phase(StartupPhase.ROUTES_REGISTER)
        
        manager.start_phase(StartupPhase.SERVICES_START)
        manager.complete_phase(StartupPhase.SERVICES_START)
        
        manager.start_phase(StartupPhase.BACKGROUND_CONNECT)
        manager.complete_phase(StartupPhase.BACKGROUND_CONNECT)
        
        manager.finish_startup()
        self.assertTrue(manager.is_running)
        self.assertEqual(manager.context.current_phase, StartupPhase.RUNNING)
    
    def test_startup_failure(self):
        manager = get_startup_manager()
        manager.begin_startup()
        
        error = Exception("Startup failed")
        manager.start_phase(StartupPhase.DATABASE_INIT)
        manager.fail_phase(StartupPhase.DATABASE_INIT, error)
        
        self.assertTrue(manager.context.is_failed())
        self.assertEqual(manager.context.error_message, str(error))
    
    def test_shutdown_callbacks(self):
        manager = get_startup_manager()
        callback_called = []
        
        def test_callback():
            callback_called.append(True)
        
        manager.add_shutdown_callback(test_callback)
        manager._is_shutting_down = False
        manager.shutdown()
        
        self.assertTrue(len(callback_called) > 0)
    
    def test_startup_callbacks(self):
        manager = get_startup_manager()
        phases_called = []
        
        def test_callback(phase):
            phases_called.append(phase)
        
        manager.add_startup_callback(test_callback)
        manager.begin_startup()
        
        self.assertIn(StartupPhase.INITIALIZING, phases_called)


if __name__ == '__main__':
    unittest.main(verbosity=2)