import yaml
from typing import Dict, Any

class ConfigManager:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        try:
            with open('config/config.yaml', 'r') as file:
                self._config = yaml.safe_load(file)
        except FileNotFoundError:
            self._config = self._default_config()

    def _default_config(self):
        return {
            'gamepad': {
                'autopilot_button': 7,
                'debug_mode': False
            },
            'camera': {
                'type': 'zed',  # или 'standard'
                'resolution': (1280, 720)
            },
            'control': {
                'priority': ['gamepad', 'autopilot']
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value
