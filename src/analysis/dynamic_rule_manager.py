import json
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import os


class RuleSourceType(Enum):
    FILE = "file"
    DATABASE = "database"
    API = "api"


@dataclass
class RuleCondition:
    type: str = 'status'
    field: str = ""
    operator: str = '=='
    value: Any = None
    threshold_var: Optional[str] = None
    debounce_ms: int = 0
    min_duration_ms: int = 0


@dataclass
class RuleAction:
    type: str = 'alert'
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    severity: str = 'warning'


@dataclass
class DynamicFaultRule:
    rule_id: str
    name: str
    description: str = ""
    device_types: List[str] = field(default_factory=list)
    conditions: List[RuleCondition] = field(default_factory=list)
    actions: List[RuleAction] = field(default_factory=list)
    priority: int = 100
    enabled: bool = True
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'description': self.description,
            'device_types': self.device_types,
            'conditions': [{
                'type': c.type, 'field': c.field, 'operator': c.operator,
                'value': c.value, 'threshold_var': c.threshold_var,
                'debounce_ms': c.debounce_ms, 'min_duration_ms': c.min_duration_ms
            } for c in self.conditions],
            'actions': [{
                'type': a.type, 'target': a.target, 'parameters': a.parameters,
                'severity': a.severity
            } for a in self.actions],
            'priority': self.priority,
            'enabled': self.enabled,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DynamicFaultRule':
        conditions = []
        for c_data in data.get('conditions', []):
            conditions.append(RuleCondition(
                type=c_data.get('type', 'status'),
                field=c_data.get('field', ''),
                operator=c_data.get('operator', '=='),
                value=c_data.get('value'),
                threshold_var=c_data.get('threshold_var'),
                debounce_ms=c_data.get('debounce_ms', 0),
                min_duration_ms=c_data.get('min_duration_ms', 0)
            ))

        actions = []
        for a_data in data.get('actions', []):
            actions.append(RuleAction(
                type=a_data.get('type', 'alert'),
                target=a_data.get('target', ''),
                parameters=a_data.get('parameters', {}),
                severity=a_data.get('severity', 'warning')
            ))

        return cls(
            rule_id=data['rule_id'],
            name=data['name'],
            description=data.get('description', ''),
            device_types=data.get('device_types', []),
            conditions=conditions,
            actions=actions,
            priority=data.get('priority', 100),
            enabled=data.get('enabled', True),
            created_at=data.get('created_at', 0.0),
            updated_at=data.get('updated_at', 0.0)
        )


class DynamicRuleManager:
    def __init__(self, rules_dir: str = 'config/rules'):
        self._rules: Dict[str, DynamicFaultRule] = {}
        self._rules_by_device: Dict[str, List[DynamicFaultRule]] = {}
        self._lock = threading.RLock()
        self._rules_dir = rules_dir
        self._watch_thread = None
        self._watch_running = False
        self._last_modified = {}
        self._callbacks: List[Callable[[str, str, DynamicFaultRule], None]] = []
        self._debounce_timers: Dict[str, float] = {}
        self._fault_durations: Dict[str, float] = {}

        os.makedirs(rules_dir, exist_ok=True)

    def load_rules_from_file(self, file_path: str) -> int:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)

            count = 0
            for rule_data in rules_data:
                rule = DynamicFaultRule.from_dict(rule_data)
                self.register_rule(rule)
                count += 1

            print(f"[DynamicRuleManager] Loaded {count} rules from {file_path}")
            return count
        except Exception as e:
            print(f"[DynamicRuleManager] Error loading rules from {file_path}: {e}")
            return 0

    def load_all_rules(self) -> int:
        count = 0
        for filename in os.listdir(self._rules_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self._rules_dir, filename)
                count += self.load_rules_from_file(filepath)
        return count

    def register_rule(self, rule: DynamicFaultRule):
        with self._lock:
            self._rules[rule.rule_id] = rule

            for device_type in rule.device_types:
                if device_type not in self._rules_by_device:
                    self._rules_by_device[device_type] = []
                self._rules_by_device[device_type].append(rule)

            for device_type in rule.device_types:
                self._rules_by_device[device_type].sort(key=lambda r: r.priority)

    def unregister_rule(self, rule_id: str) -> bool:
        with self._lock:
            if rule_id not in self._rules:
                return False

            rule = self._rules[rule_id]
            del self._rules[rule_id]

            for device_type in rule.device_types:
                if device_type in self._rules_by_device:
                    self._rules_by_device[device_type] = [
                        r for r in self._rules_by_device[device_type]
                        if r.rule_id != rule_id
                    ]

            return True

    def get_rules_for_device(self, device_type: str) -> List[DynamicFaultRule]:
        with self._lock:
            return list(self._rules_by_device.get(device_type, []))

    def evaluate_rules(self, device_type: str, device_data: Dict[str, Any],
                       var_values: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        results = []
        rules = self.get_rules_for_device(device_type)
        current_time = time.time()

        for rule in rules:
            if not rule.enabled:
                continue

            if self._evaluate_rule(rule, device_data, var_values, current_time):
                results.append({
                    'rule_id': rule.rule_id,
                    'rule_name': rule.name,
                    'description': rule.description,
                    'actions': [a.__dict__ for a in rule.actions],
                    'timestamp': current_time,
                    'priority': rule.priority
                })

        return results

    def _evaluate_rule(self, rule: DynamicFaultRule, device_data: Dict[str, Any],
                       var_values: Dict[str, Any], current_time: float) -> bool:
        all_conditions_met = True

        for condition in rule.conditions:
            if not self._evaluate_condition(condition, device_data, var_values):
                all_conditions_met = False
                break

        if not all_conditions_met:
            self._fault_durations.pop(f"{rule.rule_id}", None)
            return False

        return self._check_debounce_and_duration(rule, current_time)

    def _evaluate_condition(self, condition: RuleCondition,
                           device_data: Dict[str, Any], var_values: Dict[str, Any]) -> bool:
        data_source = {**device_data, **(var_values or {})}

        if condition.field not in data_source:
            return False

        value = data_source[condition.field]

        if condition.threshold_var and condition.threshold_var in data_source:
            condition.value = data_source[condition.threshold_var]

        try:
            if condition.operator == '==':
                return value == condition.value
            elif condition.operator == '!=':
                return value != condition.value
            elif condition.operator == '>':
                return value > condition.value
            elif condition.operator == '<':
                return value < condition.value
            elif condition.operator == '>=':
                return value >= condition.value
            elif condition.operator == '<=':
                return value <= condition.value
            elif condition.operator == 'in':
                return value in condition.value
            elif condition.operator == 'contains':
                return str(condition.value) in str(value)
            else:
                print(f"[DynamicRuleManager] Unknown operator: {condition.operator}")
                return False
        except (TypeError, ValueError) as e:
            print(f"[DynamicRuleManager] Condition evaluation error: {e}")
            return False

    def _check_debounce_and_duration(self, rule: DynamicFaultRule, current_time: float) -> bool:
        rule_key = f"{rule.rule_id}"

        if rule.conditions and rule.conditions[0].debounce_ms > 0:
            last_trigger = self._debounce_timers.get(rule_key, 0)
            if current_time - last_trigger < rule.conditions[0].debounce_ms / 1000:
                return False
            self._debounce_timers[rule_key] = current_time

        if rule.conditions and rule.conditions[0].min_duration_ms > 0:
            start_time = self._fault_durations.get(rule_key)

            if start_time is None:
                self._fault_durations[rule_key] = current_time
                return False

            duration_ms = (current_time - start_time) * 1000
            if duration_ms < rule.conditions[0].min_duration_ms:
                return False

            self._fault_durations.pop(rule_key, None)

        return True

    def add_callback(self, callback: Callable[[str, str, DynamicFaultRule], None]):
        self._callbacks.append(callback)

    def _notify_callbacks(self, action: str, rule_id: str, rule: DynamicFaultRule):
        for callback in self._callbacks:
            try:
                callback(action, rule_id, rule)
            except Exception as e:
                print(f"[DynamicRuleManager] Callback error: {e}")

    def start_watching(self, interval: float = 5.0):
        if self._watch_running:
            return

        self._watch_running = True

        def watch_loop():
            while self._watch_running:
                try:
                    self._check_file_changes()
                except Exception as e:
                    print(f"[DynamicRuleManager] Watch error: {e}")
                time.sleep(interval)

        self._watch_thread = threading.Thread(target=watch_loop, daemon=True)
        self._watch_thread.start()

    def stop_watching(self):
        self._watch_running = False
        if self._watch_thread:
            self._watch_thread.join(timeout=2)

    def _check_file_changes(self):
        for filename in os.listdir(self._rules_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self._rules_dir, filename)
                mtime = os.path.getmtime(filepath)

                if filepath not in self._last_modified or self._last_modified[filepath] < mtime:
                    print(f"[DynamicRuleManager] Detected rule file change: {filename}")
                    self._last_modified[filepath] = mtime
                    self.load_rules_from_file(filepath)


def create_dynamic_rule_manager(rules_dir: str = 'config/rules') -> DynamicRuleManager:
    manager = DynamicRuleManager(rules_dir)
    manager.load_all_rules()
    manager.start_watching()
    return manager