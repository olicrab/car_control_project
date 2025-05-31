import yaml
import os
import logging
from core.interfaces.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class FileConfigManager(ConfigManager):
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        logger.info(f"FileConfigManager initialized with config_path: {config_path}")

    def _load_config(self) -> dict:
        default_config = {
            "arduino": {"port": "/dev/ttyUSB0", "baud_rate": 9600},
            "zed": {"resolution": "HD720", "fps": 30, "depth_threshold": 0.6, "output_dir": "logs"},
            "gamepad": {"joystick_index": 0},
            "logging": {"level": "DEBUG", "file": "logs/car_control.log"}
        }
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file {self.config_path} not found, using defaults")
            return default_config
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            # Объединяем с дефолтными значениями, чтобы избежать отсутствия ключей
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
                elif isinstance(config[key], dict):
                    config[key] = {**default_config[key], **config[key]}
            return config

    def get_config(self) -> dict:
        return self.config

    def update_config(self, key: str, value) -> None:
        self.config[key] = value
        with open(self.config_path, 'w') as f:
            yaml.safe_dump(self.config, f)
        logger.info(f"Config updated: {key} = {value}")